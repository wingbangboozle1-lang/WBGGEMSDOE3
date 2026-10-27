"""Hide-and-recover surrogate: withhold whole fault segments, score globally.

Why this design
---------------
The organiser's scored ground truth is a set of expert-mapped faults that are
*not* in the public catalogue (official problem description). We cannot see it.
The best available stand-in is a hidden subset of the public catalogue:

* withhold WHOLE connected fault segments (never partial segments), so no part of
  a held-out segment can be memorised or edge-detected from the visible network;
* keep the *global* scored domain (the whole footprint). False positives are
  counted everywhere, exactly as the organiser metric does. (The earlier shared
  evaluator `scripts/evaluate_holdout.py` blanked predictions outside the withheld
  buffers, which makes false positives free; that defect is documented in
  knowledge/review-and-irregularities and fixed here.)
* report pooled DTI plus a spatial-block bootstrap CI, with the number of
  withheld positives and the evaluator version.

The surrogate answers "can these features recover faults the model has not seen?"
It does NOT measure performance on the organiser's private new-fault set, and no
surrogate value is ever reported as a competition score.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import ndimage as ndi

from . import config as C
from . import io as gio
from . import metric as M

EVALUATOR_VERSION = "gemsdoe-dti-hide-recover-v1.0"


def catalogue_components(sample_px: int = 300_000, seed: int = 20261027) -> np.ndarray:
    """Connected-component id per catalogue pixel (8-connectivity, 0 = background).

    Very long components are split at their top-`sample_px` quantile chain distance
    is not needed here: Basin-and-Range fault traces are short, so plain connected
    components already behave like "whole segments".
    """
    lab = gio.read_labels()
    return ndi.label(lab, structure=np.ones((3, 3), dtype=bool))[0]


def fold_assignment(block: int = 621, n_folds: int = 4):
    """Assign every catalogue component to a fold using its centroid's spatial block."""
    comp = catalogue_components()
    blocks = gio.block_grid(block)
    n_comp = int(comp.max())
    ids = np.arange(1, n_comp + 1)
    cy = ndi.sum(np.ones_like(comp), comp, ids) * 0  # placeholder to keep dtypes clear
    del cy
    cent = ndi.center_of_mass(np.ones_like(comp, dtype=np.float32), comp, ids)
    block_of = np.zeros(n_comp, dtype=np.int32)
    for i, (r, c) in enumerate(cent):
        block_of[i] = blocks[int(round(r)), int(round(c))]
    uniq = np.unique(block_of)
    # deterministic hash-free assignment: block order -> fold round robin
    order = {b: i for i, b in enumerate(uniq)}
    fold_of_block = {b: order[b] % n_folds for b in uniq}
    fold_of_comp = np.array([fold_of_block[block_of[i]] for i in range(n_comp)], dtype=np.int32)
    return comp, fold_of_comp, blocks


def withhold_masks(comp: np.ndarray, fold_of_comp: np.ndarray, fold: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (withheld_pixels, visible_pixels) for one fold."""
    ids = np.nonzero(fold_of_comp == fold)[0] + 1
    sel = np.isin(comp, ids)
    cat = comp > 0
    return sel, cat & ~sel


def evaluator_for(withheld: np.ndarray, footprint: np.ndarray) -> M.FastDTI:
    return M.FastDTI(withheld, valid=footprint)


def block_bootstrap_ci(pred: np.ndarray, withheld: np.ndarray, footprint: np.ndarray,
                       block: int = 621, n_boot: int = 400, seed: int = 7) -> dict:
    """Spatial-block bootstrap CI of the pooled DTI (resample blocks with replacement)."""
    blocks = gio.block_grid(block)
    ids = np.unique(blocks[withheld])
    per_block = []
    for b in ids:
        blk = blocks == b
        truth = withheld & blk
        if truth.sum() == 0:
            continue
        e = M.FastDTI(truth, valid=footprint & blk)
        r = e.evaluate(pred)
        per_block.append((r["tp"], r["fp"], r["fn"], int(truth.sum())))
    if not per_block:
        return {"lo": float("nan"), "hi": float("nan"), "n_blocks": 0}
    arr = np.asarray(per_block, dtype=np.float64)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(arr), len(arr))
        tp, fp, fn = arr[idx, 0].sum(), arr[idx, 1].sum(), arr[idx, 2].sum()
        vals.append(tp / (tp + C.ALPHA * fp + C.BETA * fn + C.EPS))
    vals = np.sort(np.asarray(vals))
    return {"lo": float(np.percentile(vals, 2.5)), "hi": float(np.percentile(vals, 97.5)),
            "n_blocks": len(per_block)}


def evaluate_named(pred: np.ndarray, withheld: np.ndarray, footprint: np.ndarray,
                   label: str = "") -> dict:
    e = evaluator_for(withheld, footprint)
    r = e.evaluate(pred)
    ci = block_bootstrap_ci(pred, withheld, footprint)
    return {
        "label": label,
        "evaluator_version": EVALUATOR_VERSION,
        "dti": round(r["dti"], 6),
        "ci95_lo": round(ci["lo"], 6),
        "ci95_hi": round(ci["hi"], 6),
        "n_withheld_positives": int(r["n_truth"]),
        "tp_w": round(r["tp"], 3),
        "fp_w": round(r["fp"], 3),
        "fn_w": round(r["fn"], 3),
        "mass": round(r["mass"], 1),
        "hit_rate": round(r["tp"] / max(r["mass"], 1e-9), 6),
        "n_blocks": ci["n_blocks"],
    }


def save_folds(path=None) -> dict:
    path = path or (C.CACHE_DIR / "folds.json")
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    comp, fold_of_comp, blocks = fold_assignment()
    np.save(C.CACHE_DIR / "components.npy", comp)
    np.save(C.CACHE_DIR / "fold_of_comp.npy", fold_of_comp)
    cat = comp > 0
    info = {"evaluator_version": EVALUATOR_VERSION,
            "n_components": int(comp.max()), "catalogue_px": int(cat.sum()),
            "block_px": 621, "n_folds": int(fold_of_comp.max()) + 1,
            "folds": []}
    for f in range(int(fold_of_comp.max()) + 1):
        w, v = withhold_masks(comp, fold_of_comp, f)
        info["folds"].append({"fold": f, "withheld_px": int(w.sum()),
                              "visible_px": int(v.sum()),
                              "withheld_components": int((fold_of_comp == f).sum())})
    path.write_text(json.dumps(info, indent=1))
    return info
