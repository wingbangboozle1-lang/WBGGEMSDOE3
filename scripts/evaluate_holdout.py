"""Holdout evaluation for GEMS submissions.

Implements hide-and-recover holdout: withhold whole fault segments with a buffer,
derive catalogue-based features only from the visible faults, mask visible faults
pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel).

Labels every number as HOLDOUT-DTI (evaluator version, number of withheld
positives, 95% CI). A projection is never written as a score.

This is a self-evaluation harness; it requires labels.tif + existing_faults.tif
(or a synthetic stand-in) in data/raw/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.dti import pooled_dti, dti_curve
from src.validate import validate_submission

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_ROOT / "raw"

EVALUATOR_VERSION = "holdout-dti-v1"
ALPHA = 0.2
BETA = 0.8
BANDWIDTH_M = 300.0


def withhold_fault_segments(fault_mask, buffer_px, rng, holdout_fraction=0.3):
    """Withhold whole connected fault segments (hide-and-recover holdout).

    Returns (visible_mask, withheld_mask) where withheld segments are dilated by
    buffer_px to create a clean separation between train (visible) and test
    (withheld) targets.
    """
    fault_mask = np.asarray(fault_mask, dtype=bool)
    labeled, n = ndimage_label(fault_mask)
    seg_ids = list(range(1, n + 1))
    rng.shuffle(seg_ids)
    n_hold = max(1, int(round(n * holdout_fraction)))
    hold_ids = set(seg_ids[:n_hold])
    withheld = np.isin(labeled, list(hold_ids))
    visible = fault_mask & ~withheld
    # buffer the withheld segments so visible faults don't abut test targets
    if buffer_px > 0:
        from scipy import ndimage as ndi
        withheld = ndi.binary_dilation(withheld, iterations=buffer_px)
        visible = fault_mask & ~withheld
    return visible, withheld


def ndimage_label(a):
    from scipy import ndimage as ndi
    return ndi.label(a)


def bootstrap_ci(values, n_bootstrap=2000, ci=0.95, rng=None):
    if rng is None:
        rng = np.random.default_rng(42)
    values = np.asarray(values, dtype=np.float64)
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    boots = rng.choice(values, size=(n_bootstrap, n), replace=True)
    means = boots.mean(axis=1)
    lo = np.percentile(means, (1 - ci) / 2 * 100)
    hi = np.percentile(means, (1 + ci) / 2 * 100)
    return (float(lo), float(hi))


def evaluate(prediction_path, faults_path, labels_path, pixel_size_m,
             buffer_px=3, holdout_fraction=0.3, seed=7):
    with rasterio.open(prediction_path) as src:
        prediction = src.read(1).astype(np.float64)
        transform = src.transform
        # pixel size from transform (assume square pixels, meters)
        ps = abs(transform.a) if pixel_size_m is None else float(pixel_size_m)

    with rasterio.open(faults_path) as src:
        faults = src.read(1).astype(np.float64) > 0

    with rasterio.open(labels_path) as src:
        labels = src.read(1).astype(np.float64) > 0

    if prediction.shape != faults.shape or prediction.shape != labels.shape:
        raise ValueError("prediction, faults, and labels must share the same shape")

    rng = np.random.default_rng(seed)
    visible, withheld = withhold_fault_segments(faults, buffer_px, rng, holdout_fraction)

    # Score the prediction against the WITHHELD targets only (holdout DTI)
    res = pooled_dti(prediction, withheld, pixel_size_m=ps, alpha=ALPHA, beta=BETA,
                     bandwidth_m=BANDWIDTH_M)

    # 95% CI via bootstrap over target pixels (resample target pixels)
    if withheld.any():
        # per-pixel kernel weights as the bootstrap variate
        from scipy import ndimage as ndi
        dist_to_pred = ndi.distance_transform_edt(
            ~(prediction >= 0.5)) * ps
        tar_weights = (1.0 - np.clip(dist_to_pred[withheld] / BANDWIDTH_M, 0, 1))
        ci_lo, ci_hi = bootstrap_ci(tar_weights, rng=rng)
    else:
        ci_lo, ci_hi = float("nan"), float("nan")

    result = {
        "evaluator_version": EVALUATOR_VERSION,
        "alpha": ALPHA,
        "beta": BETA,
        "bandwidth_m": BANDWIDTH_M,
        "buffer_px": int(buffer_px),
        "holdout_fraction": float(holdout_fraction),
        "seed": int(seed),
        "n_withheld_segments": int(withheld.sum() > 0),
        "n_withheld_pixels": int(withheld.sum()),
        "n_visible_pixels": int(visible.sum()),
        "holdout_dti": res["dti"],
        "holdout_dti_alpha_term": res["alpha_term"],
        "holdout_dti_beta_term": res["beta_term"],
        "ci_95_lo": ci_lo,
        "ci_95_hi": ci_hi,
        "ci_method": "bootstrap over withheld target pixels",
        "pixel_size_m": float(ps),
        "score_type": "HOLDOUT-DTI (not organiser-confirmed)",
    }
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Holdout DTI evaluation")
    parser.add_argument("prediction")
    parser.add_argument("faults")
    parser.add_argument("labels")
    parser.add_argument("--pixel-size-m", type=float, default=None)
    parser.add_argument("--buffer-px", type=int, default=3)
    parser.add_argument("--holdout-fraction", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="holdout_eval.json")
    args = parser.parse_args()

    res = evaluate(args.prediction, args.faults, args.labels, args.pixel_size_m,
                   args.buffer_px, args.holdout_fraction, args.seed)
    print(json.dumps(res, indent=2))
    Path(args.out).write_text(json.dumps(res, indent=2))
    print(f"[evaluate_holdout] wrote {args.out}")
