"""Supervised fault-likelihood model on catalogue-free features.

The model is deliberately catalogue-free (no distance-to-known-fault features). A
distance-to-catalogue feature scores very high on random cross-validation and near
zero on unseen faults: it is the classic leakage trap for this competition, and it
is explicitly rejected here. It is fitted only to distinguish "fault-like physics"
from "non-fault physics".

Training is blocked: whole connected catalogue segments are withheld, so the model
never sees any pixel of the segments it is evaluated on.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from . import config as C
from . import io as gio
from . import surrogate as S


def load_stack():
    from . import features
    return features.build_feature_stack(verbose=False)


def _gather(stack, rows, cols, n_feat):
    out = np.empty((rows.size, n_feat), dtype=np.float32)
    for j in range(n_feat):
        out[:, j] = stack[j][rows, cols]
    return out


def sample_training(stack, valid, catalogue, exclude, n_neg_per_pos=4, seed=20261027,
                    buffer_px=4):
    """Sample (positives = visible catalogue, negatives = valid non-catalogue)."""
    rng = np.random.default_rng(seed)
    pos_mask = catalogue & valid & ~exclude
    buf = ndi.binary_dilation(exclude, iterations=buffer_px) if exclude.any() else np.zeros_like(exclude)
    neg_mask = valid & ~catalogue & ~buf
    prow, pcol = np.nonzero(pos_mask)
    nrow, ncol = np.nonzero(neg_mask)
    n_neg = min(nrow.size, int(n_neg_per_pos * prow.size))
    sel = rng.choice(nrow.size, size=n_neg, replace=False)
    rows = np.concatenate([prow, nrow[sel]])
    cols = np.concatenate([pcol, ncol[sel]])
    y = np.concatenate([np.ones(prow.size, np.int8), np.zeros(n_neg, np.int8)])
    X = _gather(stack, rows, cols, stack.shape[0])
    return X, y, rows, cols


def fit(stack, valid, catalogue, exclude, max_iter=200, learning_rate=0.08,
        max_leaf_nodes=63, l2_regularization=1.0, seed=20261027, verbose=False):
    X, y, _, _ = sample_training(stack, valid, catalogue, exclude, seed=seed)
    clf = HistGradientBoostingClassifier(
        max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes,
        l2_regularization=l2_regularization, early_stopping=False,
        min_samples_leaf=40, random_state=seed, verbose=0,
    )
    clf.fit(X, y)
    if verbose:
        print(f"[model] fit on {X.shape[0]} samples x {X.shape[1]} features "
              f"({int(y.sum())} positives)", flush=True)
    return clf


def predict_full(clf, stack, valid, rows_per_block=256, verbose=False) -> np.ndarray:
    """Predict the whole grid, block by block; invalid cells are 0."""
    n_feat = stack.shape[0]
    out = np.zeros((C.HEIGHT, C.WIDTH), dtype=np.float32)
    for r0 in range(0, C.HEIGHT, rows_per_block):
        r1 = min(C.HEIGHT, r0 + rows_per_block)
        v = valid[r0:r1]
        rr, cc = np.nonzero(v)
        if rr.size == 0:
            continue
        X = np.empty((rr.size, n_feat), dtype=np.float32)
        for j in range(n_feat):
            X[:, j] = stack[j][r0:r1][rr, cc]
        out[r0:r1][rr, cc] = clf.predict_proba(X)[:, 1].astype(np.float32)
        if verbose:
            print(f"[model] predicted rows {r0}:{r1}", flush=True)
    return out


def oof_predictions(stack, valid, folds_info=None, **kw):
    """One prediction map per fold, each from a model that never saw that fold."""
    comp = np.load(C.CACHE_DIR / "components.npy")
    fold_of_comp = np.load(C.CACHE_DIR / "fold_of_comp.npy")
    cat = comp > 0
    preds = {}
    for f in range(int(fold_of_comp.max()) + 1):
        withheld, visible = S.withhold_masks(comp, fold_of_comp, f)
        clf = fit(stack, valid, visible, withheld, **kw)
        preds[f] = {"clf": clf, "pred": predict_full(clf, stack, valid),
                    "withheld": withheld}
        print(f"[model] fold {f}: withheld {int(withheld.sum())} px, "
              f"trained on {int(visible.sum())} visible fault px", flush=True)
    return preds
