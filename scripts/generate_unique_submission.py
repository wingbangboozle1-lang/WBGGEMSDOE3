#!/usr/bin/env python3
"""
Generate a UNIQUE competition submission GeoTIFF for the DOE GEMS Prize.

Scientific hypothesis (H2 — lidar scarp × thermal convergence):
  Target concealed / young surface faults that are NOT in the USGS/INGENIOUS
  catalogue by combining two independent physical signatures:

  1. Lidar-derived subtle scarps (1 m DEM -> 100 m u8 scarp bands) image
     recent fault scarps that surface mapping missed.
  2. Known geothermal springs and Quaternary volcanic vents mark active
     permeability. A scarp within ~300 m of a thermal feature is a strong
     blind-fault candidate.

  Known-fault pixels are EXCLUDED from scoring (organizer clarification), so
  dots ON catalogue faults waste prediction mass. This submission places dots
  OFF the catalogue, near thermal features with lidar scarp support — a
  different region of predictor space from the dotted family (GEMSDOE24/25/27/
  30/31/32/33/36) that dots adjacent to known faults. That separation is what
  makes the raster unique under the 3-px / 70% directed-overlap rule.

Output:
  submission/wbg3-h2-scarp-thermal-<UTC>-<sha8>.tif   (float32, [0,1], NaN outside)
  submission/wbg3-h2-scarp-thermal-<UTC>-<sha8>.zip

Validation (local, not organizer-confirmed):
  - single band, float32, EPSG:32611, 3730x3292, exact transform
  - finite values in [0,1] inside the footprint
  - NaN outside the footprint
  - SHA-256 recorded

This is a RESEARCH ARTIFACT. The repository-wide release gate is DO-NOT-SUBMIT
because the literal registry-stop is unresolved. Do not upload until the gate
passes and a separate selector approves the exact SHA-256.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
SUBMISSION = ROOT / "submission"
SUBMISSION.mkdir(parents=True, exist_ok=True)

# Competition grid (matches sample_submission.tif / labels.tif).
HEIGHT = 3730
WIDTH = 3292
RES = 100.0
ORIGIN_X = 243350.0
ORIGIN_Y = 4508550.0
CRS = "EPSG:32611"
KERNEL_RADIUS_PX = 3.0  # 300 m at 100 m
PACIFIC = ZoneInfo("US/Pacific")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_labels() -> tuple:
    """Return (labels, footprint_mask, known_fault_mask)."""
    with rasterio.open(DATA / "labels.tif") as src:
        labels = src.read(1).astype(np.float32)
    footprint = labels != -1.0
    known = labels == 1.0
    return labels, footprint, known


def lidar_scarp_score() -> np.ndarray:
    """Combine lidar scarp bands into a single scarp-strength map [0,1].

    Per-pixel max across bands (any strong scarp response registers), then
    robust min-max normalise. One band at a time to limit memory.
    """
    lidar_path = DATA / "external" / "lidar_scarp_features_u8.tif"
    running_max = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    with rasterio.open(lidar_path) as src:
        for b in range(1, src.count + 1):
            band = src.read(b).astype(np.float32)
            running_max = np.maximum(running_max, band)
    lo, hi = np.percentile(running_max, 1), np.percentile(running_max, 99.9)
    score = np.clip((running_max - lo) / (hi - lo + 1e-6), 0.0, 1.0).astype(np.float32)
    return score


def radiometric_anomaly_score() -> np.ndarray:
    """GeoDAWN radiometric anomaly from K/Th/U/TC + ratio bands [0,1].

    Hydrothermal alteration (illite, argillic) enriches K and mobilises U/Th.
    We flag high K / total count (top-decile within the footprint) and extreme
    Th/K and U/Th ratios (alteration indicator). No sliding window — fast.
    """
    rad_path = DATA / "external" / "geodawn_rad_u8.tif"
    ext_path = DATA / "external" / "geodawn_extensions_u8.tif"

    with rasterio.open(rad_path) as src:
        k = src.read(1).astype(np.float32)
        tc = src.read(4).astype(np.float32)
    with rasterio.open(ext_path) as src:
        thk = src.read(1).astype(np.float32)   # Th/K ratio
        uth = src.read(3).astype(np.float32)   # U/Th ratio

    def top_decile(img: np.ndarray) -> np.ndarray:
        v = img[img > 0]
        hi = np.percentile(v, 90)
        return np.clip(img / (hi + 1e-6), 0.0, 1.0)

    k_z = top_decile(k)
    tc_z = top_decile(tc)
    thk_dev = np.clip(np.abs(thk - 128.0) / 128.0, 0.0, 1.0)
    uth_dev = np.clip(np.abs(uth - 128.0) / 128.0, 0.0, 1.0)

    anomaly = 0.4 * k_z + 0.3 * tc_z + 0.15 * thk_dev + 0.15 * uth_dev
    del k, tc, thk, uth, k_z, tc_z, thk_dev, uth_dev
    return np.clip(anomaly, 0.0, 1.0).astype(np.float32)


def thermal_proximity_score(footprint: np.ndarray) -> np.ndarray:
    """Proximity to known geothermal springs and Quaternary volcanic vents.

    Reads row/col from the GDR #1391 CSV mirrors (label-free point sets).
    Builds a binary thermal-point mask, then a single distance transform gives
    distance to the nearest thermal point. Triangular kernel (300 m = 3 px)
    applied once — already in [0,1].
    """
    thermal = np.zeros((HEIGHT, WIDTH), dtype=bool)
    csv_files = [
        DATA / "external" / "gdr_volcanic_vents_in_footprint.csv",
        DATA / "external" / "gdr_wellspring_in_footprint.csv",
    ]
    for csv_path in csv_files:
        with csv_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    r = int(float(row["row"]))
                    c = int(float(row["col"]))
                except (KeyError, ValueError, TypeError):
                    continue
                if 0 <= r < HEIGHT and 0 <= c < WIDTH and footprint[r, c]:
                    thermal[r, c] = True

    n_pts = int(thermal.sum())
    print(f"  Thermal points in footprint: {n_pts}")
    if n_pts == 0:
        return np.zeros((HEIGHT, WIDTH), dtype=np.float32)

    inv = ~thermal
    dist = distance_transform_edt(inv).astype(np.float32)  # 0 at thermal points
    score = np.clip(1.0 - dist / KERNEL_RADIUS_PX, 0.0, 1.0).astype(np.float32)
    return score


def catalogue_buffer_mask(known: np.ndarray, buffer_px: float = 3.5) -> np.ndarray:
    """Mask known faults plus a buffer; dots here earn no scoring credit."""
    iters = int(math.ceil(buffer_px))
    return binary_dilation(known, iterations=iters)


def dots_to_probability(dots: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Convert boolean dots to a smooth [0,1] probability map.

    Each dot contributes a triangular kernel (300 m) truncated at 1.5 px so
    dots remain sharp. Outside the footprint -> NaN.
    """
    prob = np.full((HEIGHT, WIDTH), np.nan, dtype=np.float32)
    if not dots.any():
        prob[footprint] = 0.0
        return prob
    inv = ~dots
    dist = distance_transform_edt(inv).astype(np.float32)  # 0 at dots
    kern = np.clip(1.0 - dist / KERNEL_RADIUS_PX, 0.0, 1.0).astype(np.float32)
    kern[dist > 1.5] = 0.0  # sharp dots
    prob = np.where(footprint, kern, np.nan).astype(np.float32)
    return prob


def main() -> None:
    print("== WBGGEMSDOE3 unique submission generator ==")
    print("Hypothesis: H2 — lidar scarp x thermal convergence (off-catalogue dots)")

    labels, footprint, known = load_labels()
    print(f"Footprint: {int(footprint.sum()):,} cells | known faults: {int(known.sum()):,}")

    print("Computing lidar scarp score…")
    lidar = lidar_scarp_score()
    print("Computing radiometric anomaly score…")
    rad = radiometric_anomaly_score()
    print("Computing thermal proximity score…")
    therm = thermal_proximity_score(footprint)

    # Combine: thermal + scarp weighted highest (direct fault indicators).
    geo = 0.45 * lidar + 0.35 * therm + 0.20 * rad
    del lidar, rad, therm
    geo = np.clip(geo, 0.0, 1.0).astype(np.float32)

    # Mask catalogue faults + buffer (organizer excludes known-fault pixels;
    # dots there are pure false-positive mass with no TP credit).
    buf_mask = catalogue_buffer_mask(known, buffer_px=3.5)
    valid_for_dots = footprint & ~buf_mask
    del buf_mask
    print(f"Valid off-catalogue cells: {int(valid_for_dots.sum()):,}"
          f" ({100 * valid_for_dots.sum() / footprint.sum():.1f}% of footprint)")

    # Threshold off-catalogue score at the level that yields ~18k dots.
    geo_valid = np.where(valid_for_dots, geo, -1.0)
    n_target = 18000
    kth = len(geo_valid.ravel()) - n_target
    threshold = np.partition(geo_valid.ravel(), kth)[kth]
    if threshold < 0:
        threshold = 0.0
    dots = (geo_valid >= threshold) & valid_for_dots
    del geo_valid
    n_dots = int(dots.sum())
    print(f"Threshold {threshold:.4f} -> {n_dots:,} dots off-catalogue")

    # Convert to probability map.
    prob = dots_to_probability(dots, footprint)
    del dots, geo

    finite = prob[np.isfinite(prob)]
    print(f"Probability range: [{finite.min():.4f}, {finite.max():.4f}]")
    print(f"All values in [0,1]: {bool((finite >= 0).all() and (finite <= 1).all())}")
    print(f"Positive cells: {int((finite > 0).sum()):,}")

    # --- Write GeoTIFF ---
    ts = datetime.now(PACIFIC).strftime("%Y%m%dT%H%M%SZ")
    script_sha = sha256_file(Path(__file__))[:8]
    base = f"wbg3-h2-scarp-thermal-{ts}-{script_sha}"
    tif_path = SUBMISSION / f"{base}.tif"
    zip_path = SUBMISSION / f"{base}.zip"

    transform = from_origin(ORIGIN_X, ORIGIN_Y, RES, RES)
    profile = {
        "driver": "GTiff", "dtype": "float32", "count": 1,
        "height": HEIGHT, "width": WIDTH, "crs": CRS, "transform": transform,
        "nodata": np.nan, "compress": "deflate", "predictor": 3,
        "zlevel": 9, "tiled": True, "blockxsize": 256, "blockysize": 256,
    }

    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(prob.astype(np.float32), 1)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif_path, arcname=tif_path.name)

    digest = sha256_file(tif_path)
    print(f"\nWrote {tif_path}")
    print(f"SHA-256: {digest}")
    print(f"ZIP: {zip_path}")

    manifest = {
        "hypothesis": "H2-lidar-scarp-x-thermal-convergence",
        "mechanism": "Subtle lidar scarps near geothermal springs/Quaternary vents, placed off known catalogue faults",
        "mimic": "Glacial/fluvial terraces, landslide scarps, survey leveling/clearance",
        "submission_name": tif_path.name,
        "note": "Off-catalogue blind faults near geothermal springs with lidar scarp support",
        "sha256": digest,
        "bytes": int(tif_path.stat().st_size),
        "shape": [HEIGHT, WIDTH],
        "crs": CRS,
        "resolution_m": RES,
        "n_dots": n_dots,
        "positive_cells": int((finite > 0).sum()),
        "values_in_01": bool((finite >= 0).all() and (finite <= 1).all()),
        "nan_outside_footprint": bool((~np.isfinite(prob))[~footprint].all()) if (~footprint).any() else True,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_ARTIFACT_DO_NOT_SUBMIT",
        "reason": "Repository-wide release gate is DO-NOT-SUBMIT (literal registry stop unresolved)",
    }
    (SUBMISSION / f"{base}.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Manifest: {SUBMISSION / f'{base}.manifest.json'}")


if __name__ == "__main__":
    main()
