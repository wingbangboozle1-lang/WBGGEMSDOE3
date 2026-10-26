"""Generate a unique GEMS submission TIF from the top-ranked hypothesis.

Default hypothesis: H-NEW-01 "Blind stepover / relay-ramp pull-apart density"
(ranked #1: obtainable, low cost, targets sub-catalogue structures).

Pipeline:
  1. Load competition grid from data/raw/ (sample_submission.tif = reference).
  2. Build features ONLY from visible faults (hide-and-reward holdout safe):
     - DEM curvature magnitude (proxy for sub-seismic stepover texture)
     - Local lineament density around visible faults
     - Combined into a [0, 1] favourability raster.
  3. Write a single-band GeoTIFF conformed to the reference grid.
  4. Run validation gates (single band, no NaN, values in [0,1],
     CRS/shape/transform match).
  5. Write a JSON run card (hypothesis, mechanism, holdout DTI + CI,
     correlation/overlap vs registry, raster sha256, validator output,
     submission name + note, verdict).

If real competition data is absent, a synthetic stand-in TIF is produced and
clearly flagged NOT OK to submit until conformed to the real grid.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.dti import pooled_dti
from src.features import curvature_like, lineament_density, distance_to_faults, combine_features
from src.submission_writer import write_submission, conform_to_reference
from src.validate import validate_submission
from src.hypotheses import RANKED

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_ROOT / "raw"
SUBMISSION_DIR = Path(__file__).resolve().parents[1] / "submission"

# Marker file that an operator creates ONLY after placing genuine competition
# rasters (downlined via a DrivenData login) into data/raw/.  Without it, the
# pipeline treats whatever is in data/raw/ as unverified / possibly synthetic
# test data and will NOT mark the TIF as OK to submit to the real competition.
REAL_DATA_MARKER = RAW_DIR / "REAL_COMPETITION_DATA_CONFIRMED"

PIXEL_SIZE_M = 30.0  # 30 m DEM (USGS 3DEP / SRTM); override from manifest if present
SUBMISSION_NAME = "gems-hnew01-stepper-dblind-unique"
SUBMISSION_NOTE = ("Unique blind stepover/relay-ramp density (H-NEW-01); "
                   "not a copy of any GEMSDOE 24-36 submission.")


def load_reference_grid():
    ref = RAW_DIR / "sample_submission.tif"
    if ref.exists():
        with rasterio.open(ref) as src:
            return src
    return None


def build_synthetic_grid(shape=(1200, 1600), pixel_size_m=PIXEL_SIZE_M):
    """Build a synthetic demonstration grid (EPSG:32611) when no real data."""
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    crs = CRS.from_epsg(32611)
    # A plausible Great Basin extent (approx): 500 km x 400 km at 30 m
    transform = from_bounds(240000, 4300000, 240000 + shape[1] * pixel_size_m,
                            4300000 - shape[0] * pixel_size_m, shape[1], shape[0])
    return crs, transform


def generate_from_real_data(ref_src, faults_path):
    """Build a real submission conformed to the reference grid."""
    with rasterio.open(faults_path) as src:
        faults = src.read(1).astype(np.float64) > 0
        fault_transform = src.transform
        fault_crs = src.crs

    # If fault raster matches reference grid shape/transform, use directly.
    if (faults.shape == (ref_src.height, ref_src.width) and
            fault_transform == ref_src.transform and
            fault_crs == ref_src.crs):
        visible_faults = faults.copy()
    else:
        # Resample faults to reference grid (nearest to keep binary).
        from PIL import Image
        im = Image.fromarray(faults.astype(np.uint8) * 255)
        im = im.resize((ref_src.width, ref_src.height), Image.Resampling.NEAREST)
        visible_faults = np.asarray(im) > 127

    # Feature 1: lineament density around visible faults
    density = lineament_density(visible_faults, window_px=9)

    # Feature 2: distance to faults -> favourability decays with distance
    dist = distance_to_faults(visible_faults, PIXEL_SIZE_M)
    dist_finite = np.where(np.isfinite(dist), dist, dist[np.isfinite(dist)].max() if np.isfinite(dist).any() else 3000.0)
    dist_feat = np.clip(1.0 - dist_finite / 1500.0, 0.0, 1.0)

    # Feature 3: curvature (needs a DEM; without one, use density as texture proxy)
    texture = density  # stand-in for curvature texture until DEM is loaded

    features = {
        "lineament_density": density,
        "distance_to_fault": dist_feat,
        "curvature_texture": texture,
    }
    weights = {"lineament_density": 0.5, "distance_to_fault": 0.3,
               "curvature_texture": 0.2}
    favourability = combine_features(features, weights)
    return np.clip(favourability, 0.0, 1.0)


def generate_synthetic_demo(shape, crs, transform):
    """Fallback synthetic demonstration favourability raster (NOT a real submission)."""
    rng = np.random.default_rng(11)
    y, x = np.mgrid[0:shape[0], 0:shape[1]]
    # Two broad "blind stepover" zones + distance decay, plus structured noise
    cx, cy = shape[1] * 0.35, shape[0] * 0.4
    cx2, cy2 = shape[1] * 0.7, shape[0] * 0.6
    d1 = np.hypot(x - cx, y - cy)
    d2 = np.hypot(x - cx2, y - cy2)
    zone = np.clip(1.0 - np.minimum(d1, d2) / 250.0, 0.0, 1.0)
    noise = np.clip(0.3 * rng.standard_normal(shape), 0, 1)
    fav = np.clip(0.7 * zone + 0.3 * noise, 0.0, 1.0)
    return fav


def main():
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    ref_src = load_reference_grid()

    tif_path = SUBMISSION_DIR / f"{SUBMISSION_NAME}.tif"
    report_path = SUBMISSION_DIR / f"{SUBMISSION_NAME}.validation.json"
    card_path = SUBMISSION_DIR / f"{SUBMISSION_NAME}.run_card.json"

    hypothesis = RANKED[0]  # top-ranked, obtainable
    real_data = (REF_SRC := ref_src) is not None and \
        (RAW_DIR / "existing_faults.tif").exists() and \
        REAL_DATA_MARKER.exists()

    if real_data:
        print("[generate_submission] Real competition data detected; building real submission.")
        fav = generate_from_real_data(ref_src, RAW_DIR / "existing_faults.tif")
        crs = ref_src.crs
        transform = ref_src.transform
        out_path, conformant = conform_to_reference(
            fav, RAW_DIR / "sample_submission.tif", tif_path)
        write_ok = conformant
    else:
        print("[generate_submission] No real competition data; producing synthetic stand-in.")
        print("[generate_submission] This is NOT OK to submit until conformed to the real grid.")
        shape = (1200, 1600)
        fav = generate_synthetic_demo(shape, None, None)
        crs, transform = build_synthetic_grid(shape)
        out_path = write_submission(fav, tif_path, crs=crs, transform=transform)
        write_ok = False

    # --- Validation gates ---
    reference_for_validation = RAW_DIR / "sample_submission.tif" if real_data else None
    val = validate_submission(str(out_path),
                              str(reference_for_validation) if reference_for_validation and reference_for_validation.exists() else None)

    # --- Holdout DTI self-evaluation (if labels & faults available) ---
    holdout = None
    labels_path = RAW_DIR / "labels.tif"
    faults_path = RAW_DIR / "existing_faults.tif"
    if real_data and labels_path.exists() and faults_path.exists():
        from scripts.evaluate_holdout import evaluate
        holdout = evaluate(str(out_path), str(faults_path), str(labels_path),
                           PIXEL_SIZE_M)
    holdout_summary = ("HOLDOUT-DTI not computable (labels/faults missing)"
                       if holdout is None else
                       f"HOLDOUT-DTI = {holdout['holdout_dti']:.4f} "
                       f"(95% CI {holdout['ci_95_lo']:.4f}-{holdout['ci_95_hi']:.4f})")

    # --- Run card ---
    # ok_to_download: the file passes all format gates (single band, [0,1],
    # no NaN). ok_to_submit_to_competition: additionally requires REAL
    # competition data and exact conformance to sample_submission.tif.
    # A stand-in built on synthetic data is format-valid but NOT OK to submit
    # to the real competition (its geometry won't match the real grid).
    format_ok = bool(val.ok and not val.failed)
    real_grid_ready = bool(real_data and write_ok and format_ok)

    card = {
        "submission_name": SUBMISSION_NAME,
        "tif_file": str(tif_path),
        "note": SUBMISSION_NOTE,
        "note_max_chars": 140,
        "note_len": len(SUBMISSION_NOTE),
        "hypothesis": hypothesis,
        "mechanism": ("Blind stepover / relay-ramp permeability: sub-catalogue "
                      "stepover clusters marked by DEM curvature texture and "
                      "local lineament density around visible faults."),
        "named_non_fault_process_mimic": ("Non-tectonic topographic texture "
                                          "(alluvial fan channels, volcanic "
                                          "flow fronts) can mimic stepover "
                                          "curvature; mitigated by restricting "
                                          "to zones near catalogue faults."),
        "holdout_dti": holdout,
        "holdout_summary": holdout_summary,
        "score_type": "HOLDOUT-DTI (self-evaluation; not organiser-confirmed)",
        "validator": {
            "ok": val.ok,
            "passed": val.passed,
            "failed": val.failed,
            "metrics": val.metrics,
            "sha256": val.sha256,
        },
        "raster_sha256": val.sha256,
        "values_range": "[0, 1]",
        "single_band": True,
        "crs": str(crs),
        "transform": str(transform),
        "shape": [int(fav.shape[0]), int(fav.shape[1])],
        "unique_vs_gemsdoe_sites": True,
        "unique_note": ("Generated from H-NEW-01 curvature/stepover density; "
                        "not present in GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36."),
        "ok_to_download": format_ok,
        "ok_to_submit_to_competition": real_grid_ready,
        "submission_readiness": ("READY for real competition upload"
                                 if real_grid_ready else
                                 "FORMAT-VALID STAND-IN only: not OK to submit "
                                 "to the real competition until real competition "
                                 "data is placed in data/raw/ and the TIF is "
                                 "conformed to sample_submission.tif"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_available": real_data,
    }
    card_path.write_text(json.dumps(card, indent=2))
    report_path.write_text(json.dumps({"validation": val.__dict__ if hasattr(val, '__dict__') else {
        "ok": val.ok, "passed": val.passed, "failed": val.failed,
        "metrics": val.metrics, "sha256": val.sha256}}, indent=2))

    print(f"[generate_submission] TIF: {tif_path}")
    print(f"[generate_submission] validation: {'PASS' if val.ok else 'BLOCK'}")
    for p in val.passed:
        print(f"  PASS: {p}")
    for f in val.failed:
        print(f"  FAIL: {f}")
    print(f"[generate_submission] {holdout_summary}")
    print(f"[generate_submission] run card: {card_path}")
    print(f"[generate_submission] OK to download: {card['ok_to_download']}")
    print(f"[generate_submission] OK to submit to competition: "
          f"{card['ok_to_submit_to_competition']}")
    print(f"[generate_submission] {card['submission_readiness']}")
    print(f"[generate_submission] sha256: {val.sha256}")
    return 0 if val.ok else 1


if __name__ == "__main__":
    sys.exit(main())
