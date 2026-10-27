"""Per-raster sufficient statistics for the official DTI under a cell-wise density.

For a prediction ``p`` the official truth-side credit of a pixel ``g`` is
``c_p(g) = max_{x: d(x,g) <= R} p(x) k(d(x,g))`` with ``k(d) = max(0, 1 - d/R)``
and ``R = 3 px`` (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
Aggregating ``c_p`` and ``p`` over the joint feature cells gives everything the
density model needs:  ``C[cell] = sum c_p``,  ``P[cell] = sum p``,  ``N = sum p``.
"""
from __future__ import annotations

import numpy as np

R_PX = 3.0
OFFSETS = [(dy, dx, 1.0 - float(np.hypot(dy, dx)) / R_PX)
           for dy in range(-3, 4) for dx in range(-3, 4)
           if np.hypot(dy, dx) < R_PX]  # 25 offsets with k > 0 (k(3 px) = 0 exactly)


def max_credit(p: np.ndarray) -> np.ndarray:
    """``max_x p(x) k(d(x,g))`` for every pixel ``g`` (exact for the official kernel)."""
    H, W = p.shape
    best = np.zeros((H, W), dtype=np.float32)
    for dy, dx, k in OFFSETS:
        ys = slice(max(0, dy), H + min(0, dy))      # source rows
        yd = slice(max(0, -dy), H + min(0, -dy))    # destination rows
        xs = slice(max(0, dx), W + min(0, dx))
        xd = slice(max(0, -dx), W + min(0, -dx))
        np.maximum(best[yd, xd], p[ys, xs] * np.float32(k), out=best[yd, xd])
    return best


def stats(p: np.ndarray, foot: np.ndarray, cell: np.ndarray, ncell: int, d_cat: np.ndarray) -> dict:
    """Sufficient statistics of one prediction (values outside the footprint are ignored)."""
    q = np.where(foot, np.clip(p, 0.0, 1.0), 0.0).astype(np.float32)
    c = max_credit(q)
    idx = cell[foot]
    C = np.bincount(idx, weights=c[foot].astype(np.float64), minlength=ncell)
    P = np.bincount(idx, weights=q[foot].astype(np.float64), minlength=ncell)
    pos = q > 0
    vals = q[pos]
    dpos = d_cat[pos]
    return dict(
        C=C, P=P, N=float(q.sum(dtype=np.float64)), n_pos=int(pos.sum()),
        binary=bool(vals.size == 0 or np.all((vals == 1.0))),
        mean_pos_value=float(vals.mean()) if vals.size else 0.0,
        frac_footprint_positive=float(pos.sum() / foot.sum()),
        mass_on_catalogue=float(q[d_cat == 0].sum()),
        mass_within_2px=float(q[(d_cat > 0) & (d_cat < 2.95)].sum()),
        median_dcat_pos=float(np.median(dpos)) if dpos.size else float("nan"),
    )
