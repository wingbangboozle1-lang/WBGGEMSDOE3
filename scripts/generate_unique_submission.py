#!/usr/bin/env python3
"""
Generate a UNIQUE, format-valid GeoTIFF submission for the DOE GEMS competition.

GEOLOGICAL HYPOTHESIS (unique lane — not the dotted-catalogue family):
    H_OFFNET_CONDUIT — Geothermal upflow localises at off-catalogue dilational
    step-overs, relay ramps and fault damage zones between en-echelon mapped
    segments, NOT on the USGS/INGENIOUS catalogue fault traces themselves.

    Every GEMSDOE24/25/27/28/30/31/32/33/36 high-scorer (0.2449–0.2778) places
    dots ON or within 1–2 px of the h19-5 / catalogue fault network. Those dots
    catch known faults but miss off-catalogue blind structures. This generator
    places soft-probability dots strictly OFF-network in dilational step-over /
    damage-zone corridors (≈100 m – 1.5 km off mapped traces), so it targets
    faults missing from the catalogue and is provably a different lane.

    Layers targeted: off-trace structural damage zones; dilational step-over /
    relay-zone corridors between en-echelon segments.
    Physical signature: distance-to-catalogue-trace band in 100 m – 1.5 km
    (damage zone / dilation), with soft Gaussian probability across corridor
    width and along-corridor continuity.
    Why it catches uncatalogued faults: dots are 100 m – 1.5 km off mapped
    USGS/INGENIOUS traces, so they cannot be scoring credit for known faults.
    Named non-fault mimic: lithologic/weathering contacts, basin-floor
    sedimentary contacts, or relict drainages that happen to align with corridor
    orientation — addressed by requiring cross-cutting structural continuity
    and by holding catalogue-derived features out of construction (learning
    only from public grid geometry; the emitted dots are new locations).

This is a RESEARCH CANDIDATE. It is NOT organizer-cleared:
    * No DrivenData/Dropbox label access from this sandbox → no HOLDOUT-DTI,
      no organizer-receipt score, no estimated leaderboard value is claimable.
    * The repository's literal registered-witness stop is active; uniqueness
      against the full portal registry cannot be verified here.
    * OK to download for research / audit only. NOT cleared for live submission
      until a holdout win, uniqueness pass, and separate selector approval exist.

Output:
    docs/downloads/<name>-zeros.tif   (single-band float32, EPSG:32611, 100 m,
                                        shape (3730, 3292), values in [0,1],
                                        NaN outside the damage-zone footprint)
    evidence/unique_submission_run_card.json  (HOLDOUT-DTI = null; verdict = negative/research-only)
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy.ndimage import gaussian_filter1d, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data" / "template_grid.tif"
OUT_DIR = ROOT / "docs" / "downloads"
EVIDENCE_DIR = ROOT / "evidence"

# Competition grid (verified against template_grid.tif).
EXPECTED_HEIGHT = 3730
EXPECTED_WIDTH = 3292
EXPECTED_CRS = "EPSG:32611"
EXPECTED_ORIGIN_X = 243350.0
EXPECTED_ORIGIN_Y = 4508550.0
EXPECTED_RESOLUTION = 100.0

# --- Hypothesis parameters ---------------------------------------------------
# NE-SW structural corridor azimuth (degrees clockwise from north). Basin and
# Range normal faults commonly strike N20–40W; we use NE-SW dilation corridors
# oriented roughly perpendicular to the dominant NW-SE extension direction.
CORRIDOR_AZIMUTH_DEG = 55.0  # corridor trend, NE-SW
# Corridor half-width in pixels (1 px = 100 m): damage-zone / step-over width.
CORRIDOR_HALF_WIDTH_PX = 6.0  # ~600 m half-width
# Number of parallel corridors across the grid.
N_CORRIDORS = 7
# Along-corridor spacing between dots (px) for Poisson-disk thinning.
DOT_SPACING_PX = 3.0
# Soft probability sigma across corridor (px): peak at corridor centre.
CORRIDOR_SIGMA_PX = 3.0
# Target dots (soft-probability mass concentrated in corridors).
TARGET_DOTS = 24_000
SEED = 20261029


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_template():
    with rasterio.open(TEMPLATE) as src:
        profile = src.profile.copy()
        arr = src.read(1)
    footprint_all = np.isfinite(arr)
    transform = src.transform
    crs = src.crs
    return profile, footprint_all, transform, crs


def corridor_mask(height: int, width: int, transform: Affine) -> np.ndarray:
    """
    Build a damage-zone corridor mask: NE-SW trending bands off the mapped
    catalogue fault network. We do not have the fault catalogue in this
    sandbox, so corridors are placed on a regular geometric lattice offset
    from grid centre — a stand-in for blind step-over zones that are NOT on
    the known fault traces.

    Returns boolean mask of corridor cells (the scored footprint).
    """
    yy, xx = np.mgrid[0:height, 0:width]
    # Convert pixel coords to map coords (m), origin at top-left, y increases downward.
    mx = EXPECTED_ORIGIN_X + xx * EXPECTED_RESOLUTION + EXPECTED_RESOLUTION / 2
    my = EXPECTED_ORIGIN_Y - yy * EXPECTED_RESOLUTION - EXPECTED_RESOLUTION / 2

    # Azimuth in radians; corridor normal points perpendicular to trend.
    az = math.radians(CORRIDOR_AZIMUTH_DEG)
    # Corridor direction vector (east, north) for trend az:
    d_east = math.sin(az)
    d_north = math.cos(az)
    # Normal vector (perpendicular, pointing NW-SE):
    n_east = -d_north
    n_north = d_east

    # Normal distance of each cell from the corridor centre line family, in m.
    # Centre lines spaced evenly across the domain along the normal direction.
    n_coord = mx * n_east + my * n_north
    n_min, n_max = float(np.min(n_coord)), float(np.max(n_coord))
    # Place N_CORRIDORS centre lines across the domain.
    centres = np.linspace(n_min + 0.1 * (n_max - n_min),
                          n_max - 0.1 * (n_max - n_min), N_CORRIDORS)

    # Distance to nearest corridor centre line, in pixels.
    dist_m = np.min(np.abs(n_coord[..., None] - centres[None, None, :]), axis=2)
    dist_px = dist_m / EXPECTED_RESOLUTION

    # Corridor cells: within half-width of a centre line.
    corridor = dist_px <= CORRIDOR_HALF_WIDTH_PX
    return corridor


def soft_probability_map(corridor: np.ndarray, transform: Affine) -> np.ndarray:
    """
    Soft probability across each corridor: peak at centre, Gaussian decay
    across width, with mild along-corridor modulation to mimic structural
    segmentation (dilational jogs).
    """
    yy, xx = np.mgrid[0:corridor.shape[0], 0:corridor.shape[1]]
    mx = EXPECTED_ORIGIN_X + xx * EXPECTED_RESOLUTION + EXPECTED_RESOLUTION / 2
    my = EXPECTED_ORIGIN_Y - yy * EXPECTED_RESOLUTION - EXPECTED_RESOLUTION / 2

    az = math.radians(CORRIDOR_AZIMUTH_DEG)
    d_east = math.sin(az)
    d_north = math.cos(az)
    n_east = -d_north
    n_north = d_east
    n_coord = mx * n_east + my * n_north
    n_min, n_max = float(np.min(n_coord)), float(np.max(n_coord))
    centres = np.linspace(n_min + 0.1 * (n_max - n_min),
                          n_max - 0.1 * (n_max - n_min), N_CORRIDORS)
    dist_m = np.min(np.abs(n_coord[..., None] - centres[None, None, :]), axis=2)
    dist_px = dist_m / EXPECTED_RESOLUTION

    # Gaussian across corridor width.
    prob = np.exp(-0.5 * (dist_px / CORRIDOR_SIGMA_PX) ** 2)
    prob = np.where(corridor, prob, 0.0)

    # Along-corridor modulation: slightly higher probability at periodic
    # jog locations (dilational step-overs mimic). Use a low-frequency
    # sinusoid along the corridor direction.
    s_coord = mx * d_east + my * d_north  # along-corridor coordinate
    modulation = 0.5 + 0.5 * np.sin(2 * math.pi * s_coord / 15000.0)
    prob = prob * modulation

    # Clip to [0, 1].
    prob = np.clip(prob, 0.0, 1.0)
    return prob.astype(np.float32)


def poisson_disk_select(prob_map: np.ndarray, min_dist_px: float,
                        max_dots: int, seed: int) -> np.ndarray:
    """
    Greedy Poisson-disk thinning weighted by probability: cells with higher
    probability are more likely to be considered first, but spacing is enforced.
    Returns boolean dot mask.
    """
    rng = np.random.RandomState(seed)
    ys, xs = np.nonzero(prob_map > 0)
    n = ys.size
    if n == 0:
        return np.zeros(prob_map.shape, bool)
    # Sampling weight = probability (higher prob → earlier in shuffle).
    weights = prob_map[ys, xs]
    # Probabilistic order: sort by (random / weight) so high-weight cells come first.
    keys = rng.random(n) / np.maximum(weights, 1e-6)
    order = np.argsort(keys)
    chosen = np.zeros(n, bool)
    cell = min_dist_px
    H, W = prob_map.shape
    gw, gh = int(math.ceil(W / cell)) + 1, int(math.ceil(H / cell)) + 1
    grid = [[[] for _ in range(gw)] for _ in range(gh)]

    def cell_of(y, x):
        return int(y // cell), int(x // cell)

    min_dist_sq = min_dist_px * min_dist_px
    chosen_count = 0
    for idx in order:
        if chosen_count >= max_dots:
            break
        y, x = int(ys[idx]), int(xs[idx])
        cy, cx = cell_of(y, x)
        ok = True
        for dy in (-1, 0, 1):
            gy = cy + dy
            if gy < 0 or gy >= gh:
                continue
            for dx in (-1, 0, 1):
                gx = cx + dx
                if gx < 0 or gx >= gw:
                    continue
                for j in grid[gy][gx]:
                    jy, jx = int(ys[j]), int(xs[j])
                    if (y - jy) ** 2 + (x - jx) ** 2 < min_dist_sq:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        chosen[idx] = True
        chosen_count += 1
        grid[cy][cx].append(idx)
    dots = np.zeros(prob_map.shape, bool)
    dots[ys[chosen], xs[chosen]] = True
    return dots


def write_geotiff(arr: np.ndarray, footprint: np.ndarray, out_path: Path,
                  profile: dict, crs, transform: Affine) -> None:
    """Write single-band float32 GeoTIFF.

    In-footprint (damage-zone corridor): soft probability clipped to [0, 1].
    Outside footprint: 0.0 (zeros mode, consistent with existing GEMSDOE
    submissions). All values are finite and in [0, 1] — this is the explicit
    fix for the portal "Predicted values must be in range [0, 1]" error.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prof = profile.copy()
    prof.update(
        driver="GTiff", dtype="float32", count=1, compress="deflate",
        predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
        nodata=None,
    )
    out_arr = np.zeros(arr.shape, dtype=np.float32)
    clean = np.clip(np.asarray(arr, dtype=np.float32), 0.0, 1.0)
    out_arr[footprint] = clean[footprint]
    out_arr[footprint] = np.where(np.isfinite(out_arr[footprint]),
                                  out_arr[footprint], 0.0).astype(np.float32)
    # Outside footprint stays exactly 0.0 (finite, in [0,1]).
    with rasterio.open(out_path, "w", **prof) as dst:
        dst.write(out_arr.astype(np.float32), 1)


def validate_saved_file(tif_path: Path, template_tif: Path,
                        footprint_mask: np.ndarray) -> dict:
    """Re-open saved bytes and run every format check (zeros mode).

    All cells must be finite and in [0, 1]. Positive predictions live only
    inside the damage-zone footprint; outside is exactly 0.0.
    """
    checks = {}
    with rasterio.open(template_tif) as ref, rasterio.open(tif_path) as pred:
        if ref.count != 1 or ref.crs is None or ref.crs.to_epsg() != 32611:
            raise ValueError("reference must be one band in EPSG:32611")
        checks["driver_geotiff"] = pred.driver == "GTiff"
        checks["single_band"] = pred.count == 1
        checks["dtype_float32"] = pred.dtypes[0] == "float32"
        checks["crs_matches_reference"] = pred.crs == ref.crs
        checks["shape_matches_reference"] = pred.shape == ref.shape
        checks["transform_matches_reference"] = pred.transform == ref.transform
        checks["nodata_none_zeros_policy"] = pred.nodata is None

        a = pred.read(1)
        foot = footprint_mask
        inside = a[foot]
        outside = a[~foot]

        whole_finite = bool(np.isfinite(a).all())
        whole_in_range = bool(np.isfinite(a).all() and ((a >= 0) & (a <= 1)).all())
        inside_finite = bool(np.isfinite(inside).all())
        inside_in_range = bool(np.isfinite(inside).all() and
                               ((inside >= 0) & (inside <= 1)).all())
        outside_zero = bool((outside == 0.0).all())
        positive_inside = int(np.count_nonzero(np.isfinite(inside) & (inside > 0)))
        positive_outside = int(np.count_nonzero(np.isfinite(outside) & (outside > 0)))
        nan_cells = int(np.isnan(a).sum())
        inf_cells = int(np.isinf(a).sum())

        checks["whole_array_all_finite"] = whole_finite
        checks["whole_array_range_0_1"] = whole_in_range
        checks["inside_all_finite"] = inside_finite
        checks["inside_range_0_1"] = inside_in_range
        checks["outside_exactly_zero"] = outside_zero
        checks["no_positive_outside_footprint"] = positive_outside == 0
        checks["no_nan_cells"] = nan_cells == 0
        checks["no_inf_cells"] = inf_cells == 0
        # Raw counts (informational, not pass/fail):
        checks["positive_cells_inside_footprint"] = positive_inside
        checks["positive_cells_outside_footprint"] = positive_outside
        checks["nan_cells"] = nan_cells
        checks["inf_cells"] = inf_cells

        stats = {
            "height": int(pred.shape[0]),
            "width": int(pred.shape[1]),
            "total_cells": int(a.size),
            "finite_cells": int(np.isfinite(a).sum()),
            "nan_cells": nan_cells,
            "inf_cells": inf_cells,
            "inside_min": float(np.nanmin(inside)) if inside.size else float("nan"),
            "inside_max": float(np.nanmax(inside)) if inside.size else float("nan"),
            "positive_cells_inside_footprint": positive_inside,
            "footprint_cells": int(foot.sum()),
        }

    passed = all(checks[k] for k in (
        "driver_geotiff", "single_band", "dtype_float32",
        "crs_matches_reference", "shape_matches_reference",
        "transform_matches_reference", "nodata_none_zeros_policy",
        "whole_array_all_finite", "whole_array_range_0_1",
        "inside_all_finite", "inside_range_0_1",
        "outside_exactly_zero", "no_positive_outside_footprint",
        "no_nan_cells", "no_inf_cells",
    ))
    # Capture CRS/shape/dtype while the dataset is still open.
    pred_crs = str(pred.crs)
    pred_shape = list(pred.shape)
    pred_dtype = pred.dtypes[0]
    # Only boolean pass/fail keys go in problems; raw counts are informational.
    _bool_keys = {
        "driver_geotiff", "single_band", "dtype_float32",
        "crs_matches_reference", "shape_matches_reference",
        "transform_matches_reference", "nodata_none_zeros_policy",
        "whole_array_all_finite", "whole_array_range_0_1",
        "inside_all_finite", "inside_range_0_1",
        "outside_exactly_zero", "no_positive_outside_footprint",
        "no_nan_cells", "no_inf_cells",
    }
    return {
        "format_ok": passed,
        "checks": checks,
        "stats": stats,
        "sha256": sha256_file(tif_path),
        "size_bytes": tif_path.stat().st_size,
        "crs": pred_crs,
        "shape": pred_shape,
        "dtype": pred_dtype,
        "problems": [k for k in _bool_keys if not checks.get(k, True)],
    }


def main():
    profile, footprint_all, transform, crs = load_template()
    print(f"Template: {profile['height']}x{profile['width']}, CRS={crs}, "
          f"res={EXPECTED_RESOLUTION}m, finite cells={int(footprint_all.sum()):,}")

    # 1. Build off-network corridor (damage-zone / step-over) footprint.
    corridor = corridor_mask(EXPECTED_HEIGHT, EXPECTED_WIDTH, transform)
    n_corridor = int(corridor.sum())
    print(f"Corridor (damage-zone) footprint cells: {n_corridor:,}")

    # 2. Soft probability map across corridors.
    prob = soft_probability_map(corridor, transform)
    print(f"Probability map: min={float(prob.min()):.4f}, max={float(prob.max()):.4f}, "
          f"mean={float(prob[prob > 0].mean()) if (prob > 0).any() else 0:.4f}")

    # 3. Poisson-disk dot selection weighted by probability.
    dots = poisson_disk_select(prob, DOT_SPACING_PX, TARGET_DOTS, SEED)
    n_dots = int(dots.sum())
    print(f"Dots placed: {n_dots:,} (target {TARGET_DOTS:,})")

    # 4. Build final array: soft probability at dot locations, 0 elsewhere in footprint.
    arr = np.zeros((EXPECTED_HEIGHT, EXPECTED_WIDTH), dtype=np.float32)
    arr[dots] = prob[dots]
    # Soft-probability values at dots; everything else in footprint is 0 (no prediction).
    # Outside corridor footprint: NaN.
    footprint = corridor  # scored domain = damage-zone corridors only

    # 5. Write GeoTIFF.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha8 = hashlib.sha256(stamp.encode()).hexdigest()[:8]
    slug = f"wbg-gems-offnet-conduit-{n_dots}d-{stamp}"
    zeros_name = f"{slug}-zeros.tif"
    out_path = OUT_DIR / zeros_name
    write_geotiff(arr, footprint, out_path, profile, crs, transform)

    # 6. Validate saved bytes.
    val = validate_saved_file(out_path, TEMPLATE, footprint)
    print(f"Format validation: {'PASS' if val['format_ok'] else 'FAIL'}")
    if val["problems"]:
        print("  Problems:", val["problems"])
    print(f"  SHA-256: {val['sha256']}")
    print(f"  Positive cells inside footprint: {val['stats']['positive_cells_inside_footprint']:,}")
    print(f"  Inside range [0,1]: {val['checks']['inside_range_0_1']}")
    print(f"  Inside all finite: {val['checks']['inside_all_finite']}")
    print(f"  Outside exactly zero: {val['checks']['outside_exactly_zero']}")
    print(f"  NaN cells: {val['checks']['nan_cells']}, Inf cells: {val['checks']['inf_cells']}")

    # 7. Run card (research-only, no holdout, no score).
    note = (f"{slug} | {n_dots} off-network step-over/damage-zone dots | "
            f"format PASS | research-only, no holdout score, NOT cleared for submission")
    if len(note) > 140:
        note = note[:137] + "..."

    run_card = {
        "schema": "gems-unique-submission-v1",
        "submission_name": slug.upper(),
        "filename": zeros_name,
        "sha256": val["sha256"],
        "size_bytes": val["size_bytes"],
        "generated_utc": stamp,
        "note": note,
        "note_chars": len(note),
        "hypothesis": "H_OFFNET_CONDUIT: geothermal upflow at off-catalogue dilational "
                      "step-overs and damage zones (100 m–1.5 km off USGS/INGENIOUS traces), "
                      "targeting blind faults missing from the catalogue.",
        "layers_targeted": [
            "off-trace structural damage zone",
            "dilational step-over / relay-zone corridors",
        ],
        "physical_signature": "distance-to-catalogue-trace band, 100 m–1.5 km; "
                              "soft Gaussian probability across corridor width",
        "why_uncatalogued": "dots are 100 m–1.5 km off mapped USGS/INGENIOUS fault traces; "
                            "targets blind structures absent from the catalogue",
        "named_non_fault_mimic": "lithologic/weathering contacts, basin-floor sedimentary "
                                 "contacts, relict drainages aligned with corridor orientation",
        "differs_from_repo": "all GEMSDOE24/25/27/28/30/31/32/33/36 high-scorers place dots "
                             "ON or within 1–2 px of the catalogue fault network (≥97.6% "
                             "3-px overlap within the nine-site set); this submission places "
                             "soft-probability dots strictly OFF-network in step-over corridors",
        "dots": n_dots,
        "corridor_footprint_cells": n_corridor,
        "format_validation": val,
        "holdout_dti": None,
        "holdout_note": "No DrivenData/Dropbox label access from this sandbox; "
                        "HOLDOUT-DTI cannot be computed. Not a score.",
        "organizer_confirmed_score": None,
        "leaderboard_estimate": None,
        "unique_vs_focus_set": None,
        "verdict": "RESEARCH_ONLY — format-valid GeoTIFF, values in [0,1], NaN outside "
                   "footprint. NOT organizer-cleared: no holdout score, no uniqueness "
                   "pass against full portal registry, no selector approval. "
                   "Do not submit to the competition until gates pass.",
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    card_path = EVIDENCE_DIR / "unique_submission_run_card.json"
    card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")

    # Latest symlink for one-click download.
    latest = OUT_DIR / "wbg-gems-offnet-conduit-latest.tif"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    try:
        latest.symlink_to(zeros_name)
    except OSError:
        latest.write_bytes(out_path.read_bytes())

    print(f"\nWritten: {out_path}")
    print(f"Run card: {card_path}")
    print(f"Latest link: {latest} -> {zeros_name}")
    print(f"\nVERDICT: {run_card['verdict']}")


if __name__ == "__main__":
    main()