"""Exact distance-weighted Tversky index (DTI) for a *known* truth field.

Implements the organiser's formula literally (DrivenData competition 306,
problem-description page 967, "Mathematical representation"):

    k(d)  = max(1 - d / R, 0),  R = 300 m = 3 px at 100 m
    TP_w  = sum_{g in G} max_{x in P, d(x,g) <= R} p(x) k(d(x,g))
    FP_w  = sum_{x in P} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w  = sum_{g in G} [1 - max_{x in P, d(x,g) <= R} p(x) k(d(x,g))]
    DTI   = TP_w / (TP_w + alpha FP_w + beta FN_w + eps),  alpha = 0.2, beta = 0.8

For binary predictions (p = 1 on the support P) both maxima are attained by the
nearest neighbour, so

    TP_w = sum_g k(dist(g, P)),   FP_w = |P| - sum_{x in P} k(dist(x, G))

which is what this module evaluates with one Euclidean distance transform per
side.  No approximation, no block grid, no smoothing.

IMPORTANT algebra used throughout the project (see content/why-0.2778.md):
since FN_w = |G| - TP_w,

    DTI = TP_w / (0.2 (TP_w + FP_w) + 0.8 |G|)

so adding one dot of unit probability raises the denominator by exactly 0.2 and
raises the numerator by its kernel credit k.  A dot is worth placing only if its
expected credit exceeds 0.2 * DTI (about 0.056 at DTI = 0.28).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-12


def kernel_from_distance(d_px, radius_px: float = RADIUS_PX) -> np.ndarray:
    return np.clip(1.0 - np.asarray(d_px, dtype=np.float64) / float(radius_px), 0.0, 1.0)


def kernel_credit_field(support: np.ndarray, radius_px: float = RADIUS_PX) -> np.ndarray:
    """k(distance from every cell to the nearest True cell of `support`)."""
    support = np.asarray(support, bool)
    if not support.any():
        return np.zeros(support.shape, np.float64)
    d = ndi.distance_transform_edt(~support)
    return kernel_from_distance(d, radius_px)


def exact_dti(pred: np.ndarray, truth: np.ndarray, footprint: np.ndarray | None = None) -> dict:
    """Exact DTI of a prediction raster against a known truth mask.

    Parameters
    ----------
    pred : float array in [0, 1] (NaN treated as 0)
    truth : bool array, the hidden truth field G
    footprint : optional bool array; cells outside are ignored for the FP term.

    Returns a dict with dti, tp_w, fp_w, fn_w, n_truth, n_pred_support.
    """
    p = np.asarray(pred, np.float64)
    p = np.where(np.isfinite(p), p, 0.0)
    p = np.clip(p, 0.0, 1.0)
    g = np.asarray(truth, bool).copy()
    if footprint is not None:
        g &= np.asarray(footprint, bool)
    if not g.any():
        raise ValueError("truth field is empty")

    # TP_w: every truth cell takes the best kernel-weighted prediction within R.
    # With p == 1 on the support this is k(dist(g, support)); for soft p we use the
    # max over the 3-px neighbourhood of p(x) * k(d), evaluated exactly on the
    # (small) set of cells that carry prediction mass.
    supp = p > 0
    if supp.sum() == 0:
        return {"dti": 0.0, "tp_w": 0.0, "fp_w": 0.0, "fn_w": float(g.sum()),
                "n_truth": int(g.sum()), "n_pred_support": 0, "mean_credit_per_dot": 0.0}
    if np.allclose(p[supp], 1.0):
        k_pred = kernel_credit_field(supp)
        tp = float(k_pred[g].sum())
    else:
        k_pred = _soft_credit(supp, p)
        tp = float(k_pred[g].sum())

    k_truth = kernel_credit_field(g)          # max_g k(d(x,g)) for every cell
    fp = float((p * (1.0 - k_truth)).sum())
    n_truth = float(g.sum())
    fn = n_truth - tp
    dti = tp / (tp + ALPHA * fp + BETA * fn + EPS)
    return {
        "dti": float(dti),
        "tp_w": float(tp),
        "fp_w": float(fp),
        "fn_w": float(fn),
        "n_truth": int(n_truth),
        "n_pred_support": int(supp.sum()),
        "mean_credit_per_dot": float(tp / supp.sum()),
    }


def _soft_credit(supp: np.ndarray, p: np.ndarray) -> np.ndarray:
    """max over the 3-px neighbourhood of p(x) * k(d(x, .)) for soft predictions."""
    out = np.zeros(supp.shape, np.float64)
    r = int(np.ceil(RADIUS_PX))
    offsets = [(dy, dx)
               for dy in range(-r, r + 1)
               for dx in range(-r, r + 1)
               if dy * dy + dx * dx <= RADIUS_PX ** 2]
    h, w = supp.shape
    for dy, dx in offsets:
        k = float(kernel_from_distance(np.hypot(dy, dx)))
        if k <= 0:
            continue
        ys = slice(max(0, dy), h + min(0, dy))
        xs = slice(max(0, dx), w + min(0, dx))
        ys2 = slice(max(0, -dy), h + min(0, -dy))
        xs2 = slice(max(0, -dx), w + min(0, -dx))
        np.maximum(out[ys2, xs2], p[ys, xs] * k, out=out[ys2, xs2])
    return out


def score_from_credit_counts(tp_w: float, fp_w: float, mass: float) -> float:
    """DTI from the three sufficient statistics (used for analytics)."""
    return float(tp_w / (tp_w + ALPHA * fp_w + BETA * (mass - tp_w) + EPS))
