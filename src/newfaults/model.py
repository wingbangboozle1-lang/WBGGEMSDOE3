"""Fault-likelihood model and metric-aware emission geometry.

Model: histogram gradient boosting on the static evidence stack plus a
fold-specific distance-to-visible-catalogue channel (computable at inference
time; it is a function of the *published* labels only).

Emission: the DTI rewards recall heavily (beta/alpha = 4) and charges redundant
mass in full (a truth pixel takes the max over nearby predictions).  Therefore the
emitted map is binary dots placed on the skeleton of the high-probability field,
greedily thinned to a minimum separation.  Both knobs (threshold quantile and
minimum separation) are tuned on the holdout, never on the hidden competition score.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

from .features import mask_distance  # noqa: F401  (re-exported convenience)


# ----------------------------------------------------------------------------------------------
# sampling / design matrix
# ----------------------------------------------------------------------------------------------

def balanced_negative_sample(train_mask: np.ndarray, cat_visible: np.ndarray, n: int,
                            block: int = 96, seed: int = 3) -> np.ndarray:
    """Sample negatives evenly across the map so no single basin dominates training."""
    rng = np.random.default_rng(seed)
    legal = train_mask & ~cat_visible
    ys, xs = np.nonzero(legal)
    if ys.size <= n:
        return ys * legal.shape[1] + xs
    H, W = legal.shape
    b = (ys // block) * ((W + block - 1) // block) + (xs // block)
    uniq, inv = np.unique(b, return_inverse=True)
    per = max(1, n // uniq.size)
    take = []
    for k in range(uniq.size):
        idx = np.flatnonzero(inv == k)
        if idx.size == 0:
            continue
        take.append(rng.choice(idx, min(per, idx.size), replace=False))
    idx = np.concatenate(take)
    if idx.size > n:
        idx = rng.choice(idx, n, replace=False)
    return ys[idx] * W + xs[idx]


def design(arr_path, indices: np.ndarray, shape: tuple[int, int], extra: list[np.ndarray] | None = None,
           dtype=np.float32) -> np.ndarray:
    """Gather rows of the feature-major memmap at flat indices, plus extra channels."""
    arr = np.lib.format.open_memmap(arr_path, mode="r")
    F = arr.shape[0]
    flat = np.asarray(indices, np.int64)
    out = np.empty((flat.size, F + len(extra or [])), dtype=dtype)
    for f in range(F):
        out[:, f] = arr[f].ravel()[flat]
    for j, ex in enumerate(extra or []):
        out[:, F + j] = ex.ravel()[flat]
    del arr
    return out


# ----------------------------------------------------------------------------------------------
# model
# ----------------------------------------------------------------------------------------------

def fit(X: np.ndarray, y: np.ndarray, seed: int = 0, max_iter: int = 220):
    from sklearn.ensemble import HistGradientBoostingClassifier

    clf = HistGradientBoostingClassifier(
        max_iter=max_iter, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=60,
        l2_regularization=1.0, max_bins=128, early_stopping=False, random_state=seed,
    )
    clf.fit(X, y)
    return clf


def predict_surface(clf, arr_path, extra: list[np.ndarray], shape: tuple[int, int],
                    rows_per_block: int = 256) -> np.ndarray:
    arr = np.lib.format.open_memmap(arr_path, mode="r")
    F = arr.shape[0]
    H, W = shape
    out = np.zeros((H, W), np.float32)
    for r0 in range(0, H, rows_per_block):
        r1 = min(H, r0 + rows_per_block)
        n = (r1 - r0) * W
        X = np.empty((n, F + len(extra)), np.float32)
        base = arr[:, r0:r1, :].reshape(F, n)
        for f in range(F):
            X[:, f] = base[f]
        for j, ex in enumerate(extra):
            X[:, F + j] = ex[r0:r1].ravel()
        out[r0:r1] = clf.predict_proba(X)[:, 1].reshape(r1 - r0, W)
    del arr
    return out


# ----------------------------------------------------------------------------------------------
# metric-aware emission
# ----------------------------------------------------------------------------------------------

def _greedy_thin(ys: np.ndarray, xs: np.ndarray, vals: np.ndarray, shape, min_sep: float,
                 cap: int | None = None) -> np.ndarray:
    """Accept candidates in descending score order with a hard minimum separation.

    Implemented with an exclusion raster (O(1) per decision) instead of rebuilding a
    KD-tree per acceptance, which was quadratic and unusable at 10^5 candidates.
    """
    dots = np.zeros(shape, bool)
    if ys.size == 0:
        return dots
    order = np.argsort(-vals)
    ys, xs = ys[order], xs[order]
    if cap is not None and ys.size > cap:
        ys, xs = ys[:cap], xs[:cap]
    r = int(np.ceil(min_sep))
    off = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
           if dy * dy + dx * dx <= min_sep * min_sep + 1e-9]
    blocked = np.zeros(shape, bool)
    H, W = shape
    n = 0
    for i in range(ys.size):
        y, x = int(ys[i]), int(xs[i])
        if blocked[y, x]:
            continue
        dots[y, x] = True
        n += 1
        for dy, dx in off:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
        if cap is not None and n >= cap:
            break
    return dots


def candidates(prob: np.ndarray, allowed: np.ndarray, quantile: float | None = None,
               threshold: float | None = None, skeleton: bool = True) -> tuple:
    """Threshold the surface (optionally skeletonise) and return (ys, xs, values)."""
    p = np.where(allowed, prob, -np.inf)
    if threshold is None:
        finite = p[np.isfinite(p)]
        if finite.size == 0:
            return np.zeros(0, int), np.zeros(0, int), np.zeros(0)
        threshold = float(np.quantile(finite, quantile if quantile is not None else 0.99))
    keep = p >= threshold
    if skeleton and keep.any():
        keep = skeletonize(keep)
    ys, xs = np.nonzero(keep)
    return ys.astype(np.int64), xs.astype(np.int64), prob[ys, xs]


def select_dots(prob: np.ndarray, allowed: np.ndarray, quantile: float | None = None,
                min_sep: float = 1.0, threshold: float | None = None,
                cap: int | None = None, skeleton: bool = True,
                cands: tuple | None = None) -> np.ndarray:
    """Binary dot map from a probability surface.

    * ``quantile`` -- keep pixels above this quantile of the allowed population;
    * ``skeleton`` -- restrict to the 1-px skeleton of the kept set (removes interior
      mass that the metric charges as redundant);
    * ``min_sep``  -- greedy thinning, highest probability first.
    """
    ys, xs, vals = cands if cands is not None else candidates(prob, allowed, quantile, threshold, skeleton)
    if ys.size == 0:
        return np.zeros(prob.shape, bool)
    return _greedy_thin(ys, xs, vals, prob.shape, min_sep, cap)


def band_dots(prob: np.ndarray, allowed: np.ndarray, lo: float, hi: float, min_sep: float = 1.0,
              cap: int | None = None) -> np.ndarray:
    """Keep only the probability band [lo, hi] (used by the geothermal-contrast variant)."""
    q = prob.copy()
    q[~allowed] = -np.inf
    keep = (q >= lo) & (q <= hi)
    ys, xs = np.nonzero(keep)
    return _greedy_thin(ys.astype(np.int64), xs.astype(np.int64), prob[ys, xs], prob.shape, min_sep, cap)
