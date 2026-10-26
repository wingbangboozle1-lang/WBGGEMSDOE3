"""Dinkelbach / lazy-greedy dot allocation for the distance-weighted Tversky index.

Maximise  J(S) = (1-0.2 mu) TP(S) + 0.2 mu M(S) - 0.2 mu N(S) - 0.8 mu G   with mu = current DTI
(Dinkelbach: DTI(S) > mu  <=>  J(S) > 0 for the SAME mu; iterate mu <- DTI(S)).
For a dot x given the current credit map K:
   dTP(x) = sum_y rho(y) max(0, k(x,y) - K(y))     (submodular: gains only shrink)
   dM(x)  = sum_y rho(y) k(x,y) / 3
   gain(x) = (1-0.2 mu) dTP + 0.2 mu dM - 0.2 mu
Implementation = rounds of non-maximum suppression (a dot's gain depends only on pixels within 3 px, so dots
>= 7 px apart are exactly independent): each round adds every positive-gain local maximum of the gain map within a
7x7 window, then updates K.  rho is the (projected) hidden-truth density; it is a MODEL, not truth.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi
from .ledger import OFFS


def gain_map(rho: np.ndarray, K: np.ndarray, mu: float) -> np.ndarray:
    H, W = rho.shape
    dtp = np.zeros((H, W), np.float32)
    dm = np.zeros((H, W), np.float32)
    for dy, dx, k in OFFS:
        # dot at x covers y = x + (dy, dx)
        xs0, xs1 = max(0, -dy), min(H, H - dy)
        ys0, ys1 = max(0, -dx), min(W, W - dx)
        r = rho[xs0 + dy:xs1 + dy, ys0 + dx:ys1 + dx]
        c = K[xs0 + dy:xs1 + dy, ys0 + dx:ys1 + dx]
        dtp[xs0:xs1, ys0:ys1] += r * np.maximum(np.float32(k) - c, 0.0)
        dm[xs0:xs1, ys0:ys1] += r * np.float32(k)
    return (1 - 0.2 * mu) * dtp + 0.2 * mu * dm / 3.0 - 0.2 * mu


def _update_K(K: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> None:
    H, W = K.shape
    for dy, dx, k in OFFS:
        ty, tx = ys + dy, xs + dx
        ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
        t = (ty[ok], tx[ok])
        K[t] = np.maximum(K[t], np.float32(k))


def allocate(rho: np.ndarray, cand: np.ndarray, mu: float, n_max: int, init_dots: np.ndarray | None = None,
             min_gain: float = 0.0, max_rounds: int = 400, verbose=False) -> dict:
    """Batch-greedy (NMS rounds).  Returns dict(dots=bool mask incl. init, ys, xs, gains of NEW dots in pick order).

    init_dots: dots already placed (they reduce the marginal gain of neighbours and are kept in the output mask).
    """
    rho = np.asarray(rho, np.float32)
    K = np.zeros(rho.shape, np.float32)
    dots = np.zeros(rho.shape, bool)
    if init_dots is not None and init_dots.any():
        iy, ix = np.nonzero(init_dots)
        _update_K(K, iy, ix)
        dots |= init_dots
    allowed = cand & ~dots
    new_y, new_x, new_g = [], [], []
    n_new = 0
    for rd in range(max_rounds):
        g = gain_map(rho, K, mu)
        g[~allowed] = -1e9
        loc = ndi.maximum_filter(g, size=7, mode="constant", cval=-1e9)
        sel = (g >= loc) & (g > min_gain) & allowed
        if not sel.any():
            break
        ys, xs = np.nonzero(sel)
        gv = g[ys, xs]
        order = np.argsort(-gv)
        ys, xs, gv = ys[order], xs[order], gv[order]
        room = n_max - n_new
        if room <= 0:
            break
        ys, xs, gv = ys[:room], xs[:room], gv[:room]
        dots[ys, xs] = True
        allowed[ys, xs] = False
        new_y.append(ys); new_x.append(xs); new_g.append(gv)
        n_new += len(ys)
        _update_K(K, ys, xs)
        if verbose:
            print(f"  round {rd}: +{len(ys)} total_new={n_new} best_gain={gv[0]:.4f}", flush=True)
    cat = lambda l, dt: np.concatenate(l) if l else np.zeros(0, dt)
    return dict(dots=dots, ys=cat(new_y, int), xs=cat(new_x, int), gains=cat(new_g, np.float32))


def expected_dti(rho: np.ndarray, dots: np.ndarray, g_total: float | None = None) -> dict:
    """Model-expected DTI of a binary dot set under density rho."""
    from .ledger import credit_maps
    p = dots.astype(np.float32)
    K, C = credit_maps(p)
    tp = float((rho * K).sum()); m = float((rho * C).sum()) / 3.0
    g = float(rho.sum()) if g_total is None else g_total
    n = float(p.sum()); fp = max(n - m, 0.0)
    return dict(tp=tp, m=m, g=g, n=n, dti=tp / (tp + 0.2 * fp + 0.8 * (g - tp)))
