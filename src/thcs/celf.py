"""Exact 300 m triangular-kernel submodular facility-location (CELF) dot placement.

Mathematical foundation (Fractional-Linear DTI Optimality):
For the official Distance-Weighted Tversky Index (alpha=0.2, beta=0.8, R=300 m = 3 px),
    DTI(p) = TP_w(p) / (0.2 * (TP_w(p) + FP_w(p)) + 0.8 * |G|),
under marginal posterior fault probability w(y) = P(y in G | X), expected weighted true-positive
capture from binary centers S is the monotone submodular weighted-coverage function
    F(S) = sum_y w(y) * max_{x in S} k(||x - y||_2),   k(d) = max(1 - d / 3, 0).
Because DTI is linear-fractional in isolated dot amplitudes a_x in [0, 1], extreme-point
(bang-bang) amplitudes a_x in {0, 1} are optimal for separated centers, and greedy CELF
selection achieves the tight (1 - 1/e) monotone submodular approximation guarantee while
accounting exactly for overlapping 300 m kernel footprints along curved fault traces.
"""

from __future__ import annotations

import heapq
import numpy as np
from src.gemsw.metric import _OFFS, ALPHA, BETA


def celf_select(
    prob: np.ndarray,
    eligible: np.ndarray,
    budget_k: int,
    max_candidates: int = 360_000,
    min_gain: float = 0.0,
) -> tuple[np.ndarray, dict]:
    """Select up to ``budget_k`` binary dot centers maximizing 300 m kernel-covered posterior mass.

    Parameters
    ----------
    prob : (H, W) float32 array of non-negative posterior fault probabilities.
    eligible : (H, W) bool mask of valid candidate locations (e.g. ``foot & (d_visible > 2.0)``).
    budget_k : maximum number of dots to emit.
    max_candidates : top-ranked eligible pixels entering the CELF priority queue.
    min_gain : optional marginal kernel-gain floor (stops early if marginal gain < min_gain).
    """
    H, W = prob.shape
    pad = 3
    Hp, Wp = H + 2 * pad, W + 2 * pad

    w_pad = np.zeros((Hp, Wp), dtype=np.float32)
    w_pad[pad : pad + H, pad : pad + W] = np.where(np.isfinite(prob) & (prob > 0.0), prob, 0.0)

    elig_pad = np.zeros((Hp, Wp), dtype=bool)
    elig_pad[pad : pad + H, pad : pad + W] = eligible & (w_pad[pad : pad + H, pad : pad + W] > 0.0)

    # Vectorized initial marginal gain g_0(x) = sum_{(dy,dx,k)} w(x + delta) * k
    g0 = np.zeros((Hp, Wp), dtype=np.float32)
    for dy, dx, k in _OFFS:
        r0, r1 = pad + dy, pad + dy + H
        c0, c1 = pad + dx, pad + dx + W
        g0[pad : pad + H, pad : pad + W] += w_pad[r0:r1, c0:c1] * np.float32(k)

    cand_flat = np.flatnonzero(elig_pad.ravel())
    if cand_flat.size == 0 or budget_k <= 0:
        return np.zeros((H, W), dtype=bool), {"selected": 0, "initial_max_gain": 0.0, "final_marginal_gain": 0.0}

    gains0 = g0.ravel()[cand_flat]
    if cand_flat.size > max_candidates:
        keep_idx = np.argpartition(gains0, -max_candidates)[-max_candidates:]
        cand_flat = cand_flat[keep_idx]
        gains0 = gains0[keep_idx]

    # Build min-heap on (-gain, flat_idx) for lazy CELF updates
    heap: list[tuple[float, int]] = [(-float(g), int(idx)) for g, idx in zip(gains0, cand_flat) if g > min_gain]
    heapq.heapify(heap)

    w_flat = w_pad.ravel()
    cov_flat = np.zeros(Hp * Wp, dtype=np.float32)
    strides = tuple((int(dy * Wp + dx), float(k)) for dy, dx, k in _OFFS)

    selected_pad_idx: list[int] = []
    init_max = -heap[0][0] if heap else 0.0
    last_gain = 0.0
    n_recomputes = 0

    while heap and len(selected_pad_idx) < budget_k:
        neg_g, idx = heapq.heappop(heap)
        # Recompute exact current marginal gain against cov_flat
        gain = 0.0
        for d_idx, k in strides:
            j = idx + d_idx
            c_old = cov_flat[j]
            if k > c_old:
                gain += w_flat[j] * (k - c_old)
        n_recomputes += 1

        if gain <= min_gain:
            continue

        # Lazy optimality: if gain >= upper bound of next best item in heap, accept immediately!
        if not heap or gain >= -heap[0][0] - 1e-7:
            selected_pad_idx.append(idx)
            last_gain = gain
            for d_idx, k in strides:
                j = idx + d_idx
                if k > cov_flat[j]:
                    cov_flat[j] = k
        else:
            heapq.heappush(heap, (-gain, idx))

    out = np.zeros((Hp, Wp), dtype=bool)
    if selected_pad_idx:
        out.ravel()[np.asarray(selected_pad_idx, dtype=np.int64)] = True
    dots = out[pad : pad + H, pad : pad + W].copy()

    return dots, {
        "selected": int(dots.sum()),
        "budget_k": int(budget_k),
        "candidate_pool": int(cand_flat.size),
        "celf_recomputes": int(n_recomputes),
        "initial_max_gain": float(init_max),
        "final_marginal_gain": float(last_gain),
        "covered_posterior_mass": float((w_flat * cov_flat).sum()),
    }


def optimal_dti_budget_from_gain_curve(
    gains: np.ndarray,
    expected_n_truth: float,
    alpha: float = ALPHA,
    beta: float = BETA,
) -> tuple[int, float]:
    """Closed-form linear-fractional DTI optimizer along a monotone decreasing marginal-gain curve."""
    if gains.size == 0 or expected_n_truth <= 0.0:
        return 0, 0.0
    cum_tp = np.minimum(np.cumsum(np.maximum(gains.astype(np.float64), 0.0)), float(expected_n_truth))
    ks = np.arange(1, gains.size + 1, dtype=np.float64)
    # Approximate TP_w + FP_w by emitted dot count k (exact for binary dots in sparse regime)
    denom = alpha * np.maximum(ks, cum_tp) + beta * float(expected_n_truth) + 1e-12
    curve = cum_tp / denom
    best_i = int(np.argmax(curve))
    return best_i + 1, float(curve[best_i])
