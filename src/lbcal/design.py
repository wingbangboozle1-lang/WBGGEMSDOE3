"""Dinkelbach batch-greedy dot placement under a hidden-fault density ``pi``.

Maximises the model-expected official DTI

    E[DTI] = T / (0.2 * (T + FP) + 0.8 * G),
    T  = sum_g pi(g) c(g),   c = max-credit map of the dots (25 kernel offsets),
    FP = sum_{dots} (1 - 3 pi(x)),   G = sum_g pi(g),

by repeatedly adding the non-overlapping local maxima of the exact marginal gain
``(1 - 0.2 theta) dT(x) - 0.2 theta dFP(x)`` (theta = current E[DTI]), which is
positive iff adding the dot raises E[DTI] (Dinkelbach ratio condition).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .coverage import OFFSETS, max_credit

ALPHA, BETA, K_FACTOR = 0.2, 0.8, 3.0


def _shift_add(dst, src, dy, dx):
    """dst[y, x] += src[y + dy, x + dx] (zero outside)."""
    H, W = src.shape
    ys = slice(max(0, dy), H + min(0, dy))
    yd = slice(max(0, -dy), H + min(0, -dy))
    xs = slice(max(0, dx), W + min(0, dx))
    xd = slice(max(0, -dx), W + min(0, -dx))
    dst[yd, xd] += src[ys, xs]


def marginal_tp(pi: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Exact increase of T if a dot is added at each pixel (given current credit map c)."""
    g = np.zeros_like(pi)
    for dy, dx, k in OFFSETS:
        contrib = pi * np.maximum(np.float32(k) - c, 0.0)
        _shift_add(g, contrib, dy, dx)
    return g


def expected_terms(pi: np.ndarray, dots: np.ndarray, G: float | None = None) -> dict:
    c = max_credit(dots.astype(np.float32))
    T = float((pi * c).sum(dtype=np.float64))
    N = int(dots.sum())
    FP = float(N - K_FACTOR * pi[dots].sum(dtype=np.float64))
    G = float(pi.sum(dtype=np.float64)) if G is None else G
    D = ALPHA * (T + FP) + BETA * G
    return dict(T=T, FP=FP, N=N, G=G, dti=T / D if D > 0 else 0.0)


_DISK3 = (lambda r: (np.add.outer(np.arange(-r, r + 1) ** 2, np.arange(-r, r + 1) ** 2) <= r * r))(3)


def place(pi: np.ndarray, allowed: np.ndarray, *, theta_fixed: float | None = None,
          G: float | None = None, max_iter: int = 80, min_batch: int = 200,
          batch_frac: float = 0.25, max_batch: int = 6000, seed: int = 20261027,
          log=print) -> tuple[np.ndarray, list[dict]]:
    """Return a boolean dot mask and the iteration history.

    If ``theta_fixed`` is given the ratio threshold is frozen (used for fold-local
    holdout replays with a global operating point); otherwise theta is updated
    to the current expected DTI after every batch (Dinkelbach iteration).
    """
    pi = np.where(allowed | (pi > 0), pi, 0).astype(np.float32)
    rng = np.random.default_rng(seed)
    tie = (rng.random(pi.shape, dtype=np.float32) * 1e-7).astype(np.float32)
    G = float(pi.sum(dtype=np.float64)) if G is None else G
    dots = np.zeros(pi.shape, bool)
    c = np.zeros(pi.shape, np.float32)
    theta = 0.0 if theta_fixed is None else theta_fixed
    history = []
    for it in range(max_iter):
        dT = marginal_tp(pi, c)
        dFP = 1.0 - K_FACTOR * pi
        gain = (1 - ALPHA * theta) * dT - ALPHA * theta * dFP
        gain = np.where(allowed & ~dots, gain, -np.inf).astype(np.float32)
        if theta_fixed is None and it == 0:
            # first batch: seed at the top-density local maxima to get a non-zero theta
            gain = np.where(allowed & ~dots, dT, -np.inf).astype(np.float32)
        g2 = gain + tie
        locmax = (g2 == ndi.maximum_filter(g2, footprint=_DISK3, mode="constant", cval=-np.inf)) & (gain > 0)
        cand = np.flatnonzero(locmax)
        if cand.size == 0:
            break
        n_now = int(dots.sum())
        B = int(min(max_batch, max(min_batch, batch_frac * max(n_now, 4 * min_batch))))
        if cand.size > B:
            top = np.argpartition(-g2.ravel()[cand], B - 1)[:B]
            cand = cand[top]
        dots.ravel()[cand] = True
        c = max_credit(dots.astype(np.float32))
        T = float((pi * c).sum(dtype=np.float64))
        N = int(dots.sum())
        FP = float(N - K_FACTOR * pi[dots].sum(dtype=np.float64))
        dti = T / (ALPHA * (T + FP) + BETA * G)
        history.append(dict(iter=it, added=int(cand.size), dots=N, T=round(T, 2), FP=round(FP, 1),
                            expected_dti=round(dti, 5), theta_used=round(theta, 5)))
        if log and (it % 5 == 0 or cand.size < min_batch):
            log(f"  [place] it={it} +{cand.size} dots={N} E[DTI]={dti:.4f} theta={theta:.4f}")
        if theta_fixed is None:
            theta = dti
    return dots, history


def prune(pi: np.ndarray, dots: np.ndarray, G: float, rounds: int = 2, log=print) -> np.ndarray:
    """Remove dots whose exact removal raises E[DTI] (leave-one-out credit, batch form)."""
    dots = dots.copy()
    H, W = pi.shape
    for r in range(rounds):
        t = expected_terms(pi, dots, G)
        theta = t["dti"]
        c = max_credit(dots.astype(np.float32))
        ys, xs = np.nonzero(dots)
        loss = np.zeros(ys.size, dtype=np.float64)
        for i, (y, x) in enumerate(zip(ys, xs)):
            # targets within 3 px of the dot; competing dots within 6 px of it
            y0, y1, x0, x1 = max(0, y - 6), min(H, y + 7), max(0, x - 6), min(W, x + 7)
            sub = dots[y0:y1, x0:x1].astype(np.float32)
            sub[y - y0, x - x0] = 0.0
            c_wo = max_credit(sub)
            ty0, ty1 = max(0, y - 3) - y0, min(H, y + 4) - y0
            tx0, tx1 = max(0, x - 3) - x0, min(W, x + 4) - x0
            loss[i] = float((pi[y0:y1, x0:x1][ty0:ty1, tx0:tx1] *
                             (c[y0:y1, x0:x1][ty0:ty1, tx0:tx1] - c_wo[ty0:ty1, tx0:tx1])).sum())
        dfp = 1.0 - K_FACTOR * pi[ys, xs]
        bad = (1 - ALPHA * theta) * loss < ALPHA * theta * dfp
        if not bad.any():
            break
        dots[ys[bad], xs[bad]] = False
        if log:
            t2 = expected_terms(pi, dots, G)
            log(f"  [prune] round {r}: removed {int(bad.sum())}; E[DTI] {theta:.4f} -> {t2['dti']:.4f}")
    return dots
