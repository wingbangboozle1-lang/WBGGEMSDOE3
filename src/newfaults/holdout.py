"""Segment-level hide-and-recover holdout for the withheld-fault problem.

Protocol (documented in knowledge/protocol-newfaults-2026-10-31.md):

1. The published catalogue is split into 8-connected fault *segments*.
2. Each fold hides a size-weighted random subset of segments (default 20 % of
   pixels), stratified by quadrant so the hidden set is interleaved, like the
   organizer's "privately withheld subset".
3. Hidden segments are dilated by ``buffer_px`` to form the *hide zone*; nothing in
   the hide zone is used for training (neither positives nor negatives).
4. Scoring uses ``src/gemsw/metric.py`` (verified DTI, alpha 0.2 / beta 0.8 / R=3 px)
   with the visible catalogue masked as *known*, exactly as the organizer masks
   known faults.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label

from ..gemsw import metric


@dataclass
class Fold:
    index: int
    hidden: np.ndarray            # bool, hidden catalogue pixels (the scored truth)
    hide_zone: np.ndarray         # bool, hidden + buffer (excluded from training)
    visible: np.ndarray           # bool, catalogue pixels available for training
    train_mask: np.ndarray        # bool, legal training locations
    known_mask: np.ndarray        # bool, masked at scoring (visible catalogue + 1 px)
    meta: dict = field(default_factory=dict)


def segments(cat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """8-connected components of the catalogue. Returns (labels, sizes)."""
    lab, n = label(cat, structure=np.ones((3, 3), int))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    sizes[0] = 0
    return lab, sizes


def make_fold(cat: np.ndarray, index: int, hide_frac: float = 0.2, buffer_px: int = 2,
              seed: int = 11, n_quad: int = 4) -> Fold:
    lab, sizes = segments(cat)
    n = lab.max()
    rng = np.random.default_rng(seed + 1000 * index)
    # components' centroids -> quadrant id, so hidden segments are spread over the map
    rows = np.zeros(n + 1)
    cols = np.zeros(n + 1)
    ys, xs = np.nonzero(cat)
    ids = lab[ys, xs]
    np.add.at(rows, ids, ys)
    np.add.at(cols, ids, xs)
    counts = np.maximum(sizes, 1)
    rows /= counts
    cols /= counts
    H, W = cat.shape
    quad = (rows > H / 2).astype(int) * 2 + (cols > W / 2).astype(int)
    total = sizes.sum()
    target = hide_frac * total
    chosen = np.zeros(n + 1, bool)
    per_quad_target = target / n_quad
    # NOTE (fixed 2026-10-31): an earlier version shuffled and then re-sorted by size,
    # which made every fold identical (the sort destroyed the shuffle).  Draw a random
    # permutation and accumulate until the per-quadrant pixel quota is met instead.
    for q in range(n_quad):
        got = 0.0
        cand = np.array([i for i in range(1, n + 1) if quad[i] == q and sizes[i] > 0], dtype=np.int64)
        if cand.size == 0:
            continue
        for i in rng.permutation(cand):
            if got >= per_quad_target:
                break
            if chosen[i]:
                continue
            chosen[i] = True
            got += sizes[i]
    hidden = chosen[lab]
    hide_zone = binary_dilation(hidden, binary_dilation(np.ones((1, 1), bool), np.ones((3, 3), bool)))
    for _ in range(buffer_px):
        hide_zone = binary_dilation(hide_zone, np.ones((3, 3), bool))
    visible = cat & ~hidden
    known = binary_dilation(visible, np.ones((3, 3), bool))
    train_mask = ~hide_zone
    return Fold(index=index, hidden=hidden, hide_zone=hide_zone, visible=visible,
                train_mask=train_mask, known_mask=known,
                meta={"n_hidden_px": int(hidden.sum()), "n_visible_px": int(visible.sum()),
                      "hide_frac": float(hidden.sum()) / float(total), "buffer_px": buffer_px,
                      "seed": seed, "n_segments": int(n),
                      "n_hidden_segments": int(chosen.sum())})


def make_folds(cat: np.ndarray, n_folds: int = 3, **kw) -> list[Fold]:
    return [make_fold(cat, i, **kw) for i in range(n_folds)]


# ----------------------------------------------------------------------------------------------
# scoring
# ----------------------------------------------------------------------------------------------

def score_dots(dots: np.ndarray, truth: np.ndarray, valid: np.ndarray, known: np.ndarray) -> dict:
    """Binary submission scored with the repo's verified DTI (gemsw.metric.dti_binary)."""
    return metric.dti_binary(dots, truth, valid=valid, known=known)


def decompose(dots: np.ndarray, truth: np.ndarray, active: np.ndarray) -> dict:
    """Per-pixel decompositions of TP and FP so a block bootstrap is cheap.

    TP   = sum over truth pixels g of k(distance from g to the nearest dot)
    FP   = sum over dot pixels x of (1 - k(distance from x to the nearest truth pixel))
    """
    d = np.asarray(dots, bool) & active
    g = np.asarray(truth, bool) & active
    dg = distance_transform_edt(~g).astype(np.float32)
    # TP credit for truth pixel g is the kernel weight at the distance from g to the
    # NEAREST DOT (not to the nearest truth pixel -- an earlier version used dg here,
    # which returned a constant 1.0 and inflated DTI; fixed 2026-10-31).
    dp = distance_transform_edt(~d).astype(np.float32) if d.any() else None
    tp_px = metric.kernel(dp[g]) if d.any() else np.zeros(int(g.sum()))
    fp_px = (1.0 - metric.kernel(dg[d])) if d.any() else np.zeros(0)
    return {
        "truth_idx": np.flatnonzero(g.ravel()),
        "dot_idx": np.flatnonzero(d.ravel()),
        "tp_px": tp_px.astype(np.float64),
        "fp_px": fp_px.astype(np.float64),
        "n_truth": int(g.sum()),
        "n_dots": int(d.sum()),
        "tp": float(tp_px.sum()),
        "fp": float(fp_px.sum()),
        "dti": float(metric.dti(tp_px.sum(), fp_px.sum(), g.sum() - tp_px.sum())),
    }


def block_bootstrap_dti(dec: dict, shape: tuple[int, int], block: int = 256, n_boot: int = 300,
                        seed: int = 7) -> dict:
    """95 % CI for pooled DTI by resampling spatial blocks with replacement."""
    H, W = shape
    bh, bw = (H + block - 1) // block, (W + block - 1) // block
    ytr = dec["truth_idx"] // W
    xtr = dec["truth_idx"] % W
    ydo = dec["dot_idx"] // W
    xdo = dec["dot_idx"] % W
    tb = (ytr // block) * bw + (xtr // block)
    db = (ydo // block) * bw + (xdo // block)
    nb = bh * bw
    tp_b = np.bincount(tb, weights=dec["tp_px"], minlength=nb)
    nt_b = np.bincount(tb, minlength=nb).astype(float)
    fp_b = np.bincount(db, weights=dec["fp_px"], minlength=nb)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, nb, nb)
        tp = tp_b[pick].sum()
        fp = fp_b[pick].sum()
        nt = nt_b[pick].sum()
        vals.append(metric.dti(tp, fp, nt - tp))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"dti": dec["dti"], "ci95": [float(lo), float(hi)], "n_boot": n_boot,
            "block_px": block, "n_blocks": int(nb)}


def paired_bootstrap_delta(dec_a: dict, dec_b: dict, shape: tuple[int, int], block: int = 256,
                           n_boot: int = 300, seed: int = 7) -> dict:
    """95 % CI for DTI(a) - DTI(b) using the SAME resampled blocks for both.

    Paired resampling is what makes a positive lower bound meaningful: the two maps see
    identical block draws, so block-to-block variability cancels instead of being counted
    twice.  Both decompositions must be defined on the same grid and the same active mask.
    """
    H, W = shape
    bh, bw = (H + block - 1) // block, (W + block - 1) // block
    nb = bh * bw

    def parts(dec):
        tb = (dec["truth_idx"] // W // block) * bw + ((dec["truth_idx"] % W) // block)
        db = (dec["dot_idx"] // W // block) * bw + ((dec["dot_idx"] % W) // block)
        return (np.bincount(tb, weights=dec["tp_px"], minlength=nb),
                np.bincount(db, weights=dec["fp_px"], minlength=nb),
                np.bincount(tb, minlength=nb).astype(float))

    ta, fa, na = parts(dec_a)
    tb, fb, nb_ = parts(dec_b)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, nb, nb)
        tpa, fpa, nta = ta[pick].sum(), fa[pick].sum(), na[pick].sum()
        tpb, fpb, ntb = tb[pick].sum(), fb[pick].sum(), nb_[pick].sum()
        vals.append(metric.dti(tpa, fpa, nta - tpa) - metric.dti(tpb, fpb, ntb - tpb))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"delta": dec_a["dti"] - dec_b["dti"], "ci95": [float(lo), float(hi)],
            "n_boot": n_boot, "block_px": block}
