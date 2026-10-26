"""WB-GEMS-DOE-3 holdout evaluation: distance-weighted Tversky Index (DTI).

Implements the official competition metric (DrivenData page 967):

    k(d) = max(1 - d / R, 0),  R = 300 m = 3 px at 100 m resolution
    DTI(alpha=0.2, beta=0.8) = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)

Holdout protocol ("hide-and-recover"):
    * withhold whole fault segments with a buffer (positives hidden from the model)
    * derive catalogue-based features only from the VISIBLE faults
    * mask visible faults pixel-exactly
    * score pooled DTI on the held-out positives
    * 95% CI from spatially-blocked bootstrap over blocks

All numbers are labelled HOLDOUT-DTI (evaluator version, # withheld positives,
95% CI). A projection is never written as a score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0  # 300 m at 100 m resolution
EPS = 1e-12


def _kernel(d: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


def dti_components(pred: np.ndarray, truth: np.ndarray,
                   valid: Optional[np.ndarray] = None,
                   known: Optional[np.ndarray] = None) -> dict:
    """Exact distance-weighted TP_w / FP_w / FN_w components.

    `pred` : soft or binary predictions in [0, 1], same shape as `truth`
    `truth`: boolean ground-truth fault pixels
    `valid`: scored domain mask (defaults to all True)
    `known`: catalogue faults masked out of scoring (hide-and-recover positives)
    """
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)
    if pred.shape != truth.shape:
        raise ValueError("prediction and truth must share shape")
    H, W = pred.shape
    valid = np.ones((H, W), bool) if valid is None else np.asarray(valid, bool)
    known = np.zeros((H, W), bool) if known is None else np.asarray(known, bool)
    active = valid & ~known
    p = np.where(active & np.isfinite(pred), pred, 0.0)
    g = truth & active
    p = np.clip(p, 0.0, 1.0)

    n_truth = int(g.sum())
    # TP_w: each truth pixel gets max kernel-weighted prediction within radius.
    dg = distance_transform_edt(~g)  # distance from every pixel to nearest truth
    k_near = _kernel(dg)
    credit = np.minimum(p * k_near, k_near)  # per-truth max via distance transform below
    # Exact per-truth max: shift prediction field by kernel offsets around each truth pixel.
    r = int(np.ceil(RADIUS_PX))
    best = np.zeros((H, W), dtype=np.float64)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = _kernel(np.hypot(dy, dx))
            if k <= 0:
                continue
            shifted = np.zeros_like(p)
            ys0, ys1 = max(0, -dy), min(H, H - dy)
            xs0, xs1 = max(0, -dx), min(W, W - dx)
            shifted[ys0:ys1, xs0:xs1] = p[max(0, dy):min(H, H + dy),
                                          max(0, dx):min(W, W + dx)]
            np.maximum(best, shifted * k, out=best)
    tp = float(best[g].sum())
    fn = float(n_truth) - tp
    # FP_w: each predicted pixel penalised by 1 - max kernel over truth pixels.
    fp = float((p * (1.0 - k_near)).sum())
    dti = tp / (tp + ALPHA * fp + BETA * fn + EPS)
    return dict(tp=tp, fp=fp, fn=fn, n_truth=n_truth, dti=float(dti),
                coverage=(tp / n_truth) if n_truth else 0.0)


@dataclass
class HoldoutResult:
    evaluator_version: str
    n_withheld: int
    dti: float
    ci_lo: float
    ci_hi: float
    n_blocks: int
    block_dtis: list

    def to_dict(self):
        return {
            "evaluator_version": self.evaluator_version,
            "n_withheld_positives": self.n_withheld,
            "dti": round(self.dti, 6),
            "ci_95_lo": round(self.ci_lo, 6),
            "ci_95_hi": round(self.ci_hi, 6),
            "n_blocks": self.n_blocks,
            "block_dtis": [round(x, 6) for x in self.block_dtis],
        }


def spatial_block_ci(dti_values, n_blocks: int) -> tuple:
    """95% CI via spatial-block bootstrap (percentile method)."""
    vals = np.asarray(dti_values, dtype=float)
    if vals.size == 0:
        return float("nan"), float("nan"), []
    rng = np.random.RandomState(20261026)
    boots = []
    for _ in range(max(200, 20 * n_blocks)):
        sample = rng.choice(vals, size=vals.size, replace=True)
        boots.append(float(np.mean(sample)))
    boots = np.sort(boots)
    lo = float(np.percentile(boots, 2.5))
    hi = float(np.percentile(boots, 97.5))
    return lo, hi, [float(x) for x in boots]


def hide_and_recover(predictions: np.ndarray, truth: np.ndarray,
                     valid: Optional[np.ndarray],
                     withhold_mask: np.ndarray,
                     evaluator_version: str = "WB-GEMS-DOE-3-HIDE-RECOVER-v1.0") -> HoldoutResult:
    """Evaluate predictions on held-out fault segments.

    `withhold_mask` marks whole fault segments (with buffer) that are hidden from
    scoring inputs and used as the held-out positive set. Catalogue (known) faults
    are masked so they cannot leak into the score.
    """
    truth = np.asarray(truth, dtype=bool)
    withhold_mask = np.asarray(withhold_mask, dtype=bool)
    valid = np.ones(truth.shape, bool) if valid is None else np.asarray(valid, bool)
    known = valid & ~withhold_mask  # catalogue/visible faults excluded from scoring

    n_withheld = int((truth & withhold_mask).sum())
    comp = dti_components(predictions, truth & withhold_mask,
                          valid=valid, known=known)
    # Spatial-block CI: evaluate per block of the withheld set.
    H, W = truth.shape
    block_dtis = []
    n_rows = n_cols = 4
    bh = int(np.ceil(H / n_rows)); bw = int(np.ceil(W / n_cols))
    for br in range(n_rows):
        for bc in range(n_cols):
            blk = np.zeros((H, W), bool)
            r0, r1 = br * bh, min(H, (br + 1) * bh)
            c0, c1 = bc * bw, min(W, (bc + 1) * bw)
            blk[r0:r1, c0:c1] = True
            sub_valid = valid & blk
            sub_truth = truth & withhold_mask & blk
            if sub_truth.sum() == 0:
                continue
            c2 = dti_components(predictions, sub_truth, valid=sub_valid, known=known & sub_valid)
            block_dtis.append(c2["dti"])
    ci_lo, ci_hi, _ = spatial_block_ci(np.asarray(block_dtis), len(block_dtis))
    return HoldoutResult(
        evaluator_version=evaluator_version, n_withheld=n_withheld,
        dti=comp["dti"], ci_lo=ci_lo, ci_hi=ci_hi,
        n_blocks=len(block_dtis), block_dtis=block_dtis,
    )
