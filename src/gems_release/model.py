"""Supervised structural-fault ranking on catalogue-free feature planes.

Two arms are compared, differing only in the positive class:

``CAT``
    Positives = visible catalogue fault cells (the competition's own labels).
``UNION``
    Positives = visible catalogue **plus** SGMC state-map faults that are absent
    from the catalogue. The competition target is "faults missing from the
    catalogue", so teaching the model only what is already mapped optimises the
    wrong objective; the union asks it to detect *structures*, of which the
    catalogue is one partial inventory.

Negatives are cells at least ``NEG_MIN_PX`` from every known fault, so the label
noise in the unlabelled domain cannot dominate.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import features, shared, truth

ROOT = Path(__file__).resolve().parents[2]
PLANE_DIR = ROOT / "data" / "work" / "planes"
DEFAULT_PLANES = ["topo_ridge", "topo_valley", "topo_curv", "topo_relief",
                  "mag_hg_line", "mag_vg_line", "mag_low_line",
                  "grav_hg_line", "grav_bp_line", "strain_line", "seis_line",
                  "cond_line", "depth_bp_line", "concord"]
NEG_MIN_PX = 10.0
Z_CLIP = 8.0


def plane_names() -> list[str]:
    return [n for n in DEFAULT_PLANES if (PLANE_DIR / f"{n}.npy").is_file()]


def open_planes(names: list[str] | None = None) -> tuple[list[str], list[np.ndarray]]:
    names = names or plane_names()
    return names, [np.load(PLANE_DIR / f"{n}.npy", mmap_mode="r") for n in names]


def features_at(planes: list[np.ndarray], rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    x = np.empty((rows.size, len(planes)), np.float32)
    for j, p in enumerate(planes):
        v = p[rows, cols].astype(np.float32)
        v = np.where(np.isfinite(v), v, 0.0)     # median imputation after z-scoring
        x[:, j] = np.clip(v, -Z_CLIP, Z_CLIP)
    return x


def _sample_index(mask: np.ndarray, n: int, rng: np.random.Generator) -> tuple:
    flat = np.flatnonzero(mask.ravel())
    if flat.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    if flat.size > n:
        flat = rng.choice(flat, size=n, replace=False)
    w = mask.shape[1]
    return flat // w, flat % w


def build_training(arm: str, holdout: str, catalogue: np.ndarray,
                   sgmc_off: np.ndarray, n_pos: int = 25_000,
                   n_neg: int = 40_000, seed: int = 7) -> dict:
    """Training samples drawn strictly outside one spatial quadrant."""
    rng = np.random.default_rng(seed)
    quads = truth.quadrant_masks(catalogue.shape)
    outside = ~quads[holdout]
    footprint, _ = shared.load_masks()
    pos_cat = catalogue & outside
    pos = pos_cat if arm == "CAT" else (pos_cat | (sgmc_off & outside))
    negatives = truth.background_mask(catalogue, footprint, NEG_MIN_PX) & outside
    pr, pc = _sample_index(pos, n_pos, rng)
    nr, nc = _sample_index(negatives, n_neg, rng)
    return dict(pos_rows=pr, pos_cols=pc, neg_rows=nr, neg_cols=nc,
                n_pos_sampled=int(pr.size), n_neg_sampled=int(nr.size),
                n_pos_available=int(pos.sum()), n_neg_available=int(negatives.sum()))


def fit(planes, names, train: dict, kind: str = "hgb", seed: int = 7):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    r = np.concatenate([train["pos_rows"], train["neg_rows"]])
    c = np.concatenate([train["pos_cols"], train["neg_cols"]])
    y = np.concatenate([np.ones(train["pos_rows"].size), np.zeros(train["neg_rows"].size)])
    x = features_at(planes, r, c)
    if kind == "logit":
        model = make_pipeline(StandardScaler(),
                             LogisticRegression(max_iter=2000, C=0.5,
                                                class_weight="balanced"))
    else:
        model = HistGradientBoostingClassifier(
            max_iter=120, learning_rate=0.08, max_leaf_nodes=31,
            min_samples_leaf=40, l2_regularization=1.0,
            class_weight="balanced", random_state=seed)
    model.fit(x, y)
    return model, dict(n_samples=int(y.size), n_pos=int(y.sum()), n_features=x.shape[1],
                       kind=kind, feature_names=list(names))


def score_region(model, planes, region: np.ndarray, chunk_rows: int = 256,
                 batch: int = 600_000) -> np.ndarray:
    """Score every active cell of ``region`` (bool grid); NaN elsewhere."""
    h, w = region.shape
    out = np.full((h, w), np.nan, np.float32)
    rows_any = np.flatnonzero(region.any(axis=1))
    if rows_any.size == 0:
        return out
    for r0 in range(int(rows_any.min()), int(rows_any.max()) + 1, chunk_rows):
        r1 = min(r0 + chunk_rows, h)
        sub = region[r0:r1]
        rr, cc = np.nonzero(sub)
        if rr.size == 0:
            continue
        for start in range(0, rr.size, batch):
            sl = slice(start, start + batch)
            x = features_at(planes, rr[sl] + r0, cc[sl])
            out[r0 + rr[sl], cc[sl]] = model.predict_proba(x)[:, 1].astype(np.float32)
    return out


def single_feature_auc(planes, names, truth_mask: np.ndarray,
                       background: np.ndarray, n: int = 60_000,
                       seed: int = 11) -> dict:
    """Leakage canary: AUC of each plane *alone* against the holdout truth."""
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)
    tr, tc = _sample_index(truth_mask, n, rng)
    br, bc = _sample_index(background, n, rng)
    if tr.size < 50 or br.size < 50:
        return {}
    x_t = features_at(planes, tr, tc)
    x_b = features_at(planes, br, bc)
    y = np.concatenate([np.ones(tr.size), np.zeros(br.size)])
    out = {}
    for j, name in enumerate(names):
        v = np.concatenate([x_t[:, j], x_b[:, j]])
        if np.allclose(v.std(), 0.0):
            out[name] = None
            continue
        out[name] = float(roc_auc_score(y, v))
    return out
