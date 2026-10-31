#!/usr/bin/env python3
"""Spatially-blocked quadrant holdout for the 2026-10-31 lane (cached + scannable).

Session 2026-10-31 (branch arena/69eaf63d-wbggemsdoe3).  Uses the PINNED shared
template: `gems57.metric` (official distance-weighted Tversky index) and
`gems57.evaluate_holdout` (pooled terms + paired physical spatial-cluster
bootstrap).  The shared evaluator is imported, never forked.

Instrument
----------
The footprint is cut into four spatial quadrants at the median row/col.  For
fold k the model is trained on the three OTHER quadrants only and scored on the
catalogue pixels inside quadrant k, eroded by 12 px so no withheld strand
touches the fold boundary.  The feature stack contains NO catalogue-derived
field, so a model trained on the other three quadrants cannot see the withheld
faults at all (leakage canary below).

Two-stage: `--fit` trains and caches the fold probability surfaces; `--scan`
re-uses the cache to evaluate any number of emission policies cheaply.

Evidence class: HOLDOUT-DTI (evaluator `gems57-pooled-hide-v2`, withheld
positive pixels, 95% CI).  It measures the PUBLIC catalogue, not the sponsor's
hidden new-fault set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(TEMPLATE / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402  (pinned shared evaluator)

DOMAIN_ERODE = 12
NEG_PER_POS = 6
SEED = 20261031
QUAD_NAMES = ("NW", "NE", "SW", "SE")


def load_base():
    footprint = np.load(WORK / "footprint_mask_2026_10_31.npy")
    fp_idx = np.load(WORK / "footprint_index_2026_10_31.npy")
    sidecar = json.loads((WORK / "features_2026_10_31.json").read_text())
    n, p = sidecar["footprint_cells"], sidecar["n_features"]
    X = np.memmap(WORK / "features_2026_10_31.dat", dtype=np.float32, mode="r", shape=(n, p))
    import rasterio
    with rasterio.open(ROOT / "data" / "raw" / "labels.tif") as src:
        lab = src.read(1)
    catalogue = (lab > 0) & footprint
    return footprint, fp_idx, X, sidecar, catalogue


def quadrant_ids(footprint: np.ndarray) -> np.ndarray:
    yy, xx = np.nonzero(footprint)
    ym, xm = int(np.median(yy)), int(np.median(xx))
    gy, gx = np.ogrid[: footprint.shape[0], : footprint.shape[1]]
    q = np.full(footprint.shape, -1, np.int8)
    q[(gy < ym) & (gx < xm) & footprint] = 0
    q[(gy < ym) & (gx >= xm) & footprint] = 1
    q[(gy >= ym) & (gx < xm) & footprint] = 2
    q[(gy >= ym) & (gx >= xm) & footprint] = 3
    return q


def region_of(footprint: np.ndarray, q: np.ndarray, fold: int) -> np.ndarray:
    return ndi.binary_erosion(q == fold, iterations=DOMAIN_ERODE) & footprint


def rows_in(mask: np.ndarray, fp_idx: np.ndarray) -> np.ndarray:
    lin = np.flatnonzero(mask.ravel())
    pos = np.searchsorted(fp_idx, lin)
    pos = np.clip(pos, 0, len(fp_idx) - 1)
    return pos[fp_idx[pos] == lin]


def fit_fold(X, fp_idx, catalogue, region, seed=SEED):
    train_zone = np.load(WORK / "footprint_mask_2026_10_31.npy") & ~region
    pos_rows = rows_in(catalogue & train_zone, fp_idx)
    neg_pool = rows_in(train_zone & ~catalogue, fp_idx)
    rng = np.random.default_rng(seed)
    n_neg = int(min(len(neg_pool), NEG_PER_POS * len(pos_rows)))
    neg_rows = rng.choice(neg_pool, size=n_neg, replace=False)
    rows = np.concatenate([pos_rows, neg_rows])
    y = np.concatenate([np.ones(len(pos_rows), np.uint8), np.zeros(n_neg, np.uint8)])
    clf = HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.12, max_leaf_nodes=31, min_samples_leaf=40,
        l2_regularization=1.0, max_bins=128, early_stopping=False, random_state=seed)
    clf.fit(X[rows], y)
    return clf, int(len(pos_rows)), int(n_neg)


def predict_rows(clf, X, rows, shape, fp_idx) -> np.ndarray:
    out = np.zeros(shape, np.float32)
    vals = np.empty(len(rows), np.float32)
    step = 200_000
    for s in range(0, len(rows), step):
        r = rows[s:s + step]
        vals[s:s + step] = clf.predict_proba(X[r])[:, 1]
    out.ravel()[fp_idx[rows]] = vals
    return out


def do_fit() -> int:
    footprint, fp_idx, X, sidecar, catalogue = load_base()
    quad = quadrant_ids(footprint)
    cache = WORK / "fold_probs_2026_10_31.npz"
    payload, receipts = {}, []
    for f in range(4):
        region = region_of(footprint, quad, f)
        clf, npos, nneg = fit_fold(X, fp_idx, catalogue, region)
        prob = predict_rows(clf, X, rows_in(region, fp_idx), footprint.shape, fp_idx)
        # leakage canary: single-feature AUC on the WITHHELD fold
        canary = {}
        r_region = rows_in(region, fp_idx)
        truth = catalogue.ravel()[fp_idx[r_region]]
        for i, nm in enumerate(sidecar["feature_names"]):
            v = np.asarray(X[r_region, i], np.float64)
            ok = np.isfinite(v)
            if ok.sum() < 100 or truth[ok].sum() < 20 or (~truth[ok]).sum() < 20:
                canary[nm] = None
                continue
            a = roc_auc_score(truth[ok], v[ok])
            canary[nm] = round(float(max(a, 1 - a)), 4)
        payload[f"prob{f}"] = prob
        receipts.append(dict(fold=f, name=QUAD_NAMES[f], region_cells=int(region.sum()),
                             truth_pixels=int(truth.sum()), train_positives=npos,
                             train_negatives=nneg,
                             model_auc_fold=float(roc_auc_score(
                                 truth, np.nan_to_num(prob.ravel()[fp_idx[r_region]],
                                                      nan=0.0)))))
        print(f"fold {f} {QUAD_NAMES[f]}: region {region.sum():,} truth {truth.sum():,} "
              f"AUC {receipts[-1]['model_auc_fold']:.4f}")
        payload[f"region{f}"] = region
    np.savez_compressed(cache, **payload, catalogue=catalogue, footprint=footprint)
    (WORK / "fold_probs_2026_10_31.json").write_text(json.dumps(
        dict(session="2026-10-31", seed=SEED, doman_erode_px=DOMAIN_ERODE,
             folds=receipts, canary_auc=canary), indent=1))
    print(f"cached {cache}")
    return 0


# --------------------------------------------------------------------------- scan

def greedy_support(score: np.ndarray, region: np.ndarray, budget: int | None,
                   threshold: float | None, min_spacing: int) -> np.ndarray:
    s = np.where(region, score, -np.inf)
    idx = np.flatnonzero(region & np.isfinite(score))
    if idx.size == 0:
        return np.zeros(score.shape, bool)
    order = idx[np.argsort(-s.ravel()[idx], kind="stable")]
    if threshold is not None:
        order = order[: int(np.searchsorted(-s.ravel()[order], -float(threshold), side="right"))]
    # NOTE: with NMS the candidate list must NOT be pre-truncated to `budget`,
    # because thinning discards most candidates; the budget only caps ACCEPTED dots.
    if min_spacing <= 0:
        if budget is not None:
            order = order[:budget]
        m = np.zeros(score.size, bool)
        m[order] = True
        return m.reshape(score.shape)
    h, w = score.shape
    accepted = np.zeros(score.size, bool)
    taken = np.zeros(score.shape, bool)
    count = 0
    for lin in order:
        y, x = divmod(int(lin), w)
        y0, y1 = max(0, y - min_spacing), min(h, y + min_spacing + 1)
        x0, x1 = max(0, x - min_spacing), min(w, x + min_spacing + 1)
        if taken[y0:y1, x0:x1].any():
            continue
        accepted[lin] = True
        taken[y0:y1, x0:x1] = True
        count += 1
        if budget is not None and count >= budget:
            break
    return accepted.reshape(score.shape)


def do_scan(budgets, spacings, thresholds, graded) -> int:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    rng = np.random.default_rng(SEED + 1)
    uniform = rng.random(shape).astype(np.float32)
    arms: dict[str, np.ndarray] = {}
    per_fold: dict[str, dict] = {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        truth = catalogue & region
        fold = dict(region=region, truth=truth, visible=catalogue & ~region,
                    masked_known=catalogue & ~region)
        cand: dict[str, tuple[np.ndarray, np.ndarray]] = {}   # name -> (emission values)
        for b in budgets:
            m = greedy_support(prob, region, b, None, 0)
            cand[f"model_b{b}_s0"] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
            u = greedy_support(np.where(region, uniform, -np.inf), region, b, None, 0)
            cand[f"random_b{b}"] = (u, np.where(u, 1.0, 0.0).astype(np.float32))
        for sp in spacings:
            if sp <= 0:
                continue
            m = greedy_support(prob, region, None, None, sp)
            cand[f"model_nms{sp}_all"] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
            u = greedy_support(np.where(region, uniform, -np.inf), region,
                               int(m.sum()), None, 0)
            cand[f"random_matched_nms{sp}_all"] = (u, np.where(u, 1.0, 0.0).astype(np.float32))
            for t in thresholds:
                m = greedy_support(prob, region, None, t, sp)
                cand[f"model_nms{sp}_thr{t:.2f}"] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
                # count-matched random control (same number of dots, no skill)
                u = greedy_support(np.where(region, uniform, -np.inf), region,
                                   int(m.sum()), None, 0)
                cand[f"random_matched_nms{sp}_thr{t:.2f}"] = (u, np.where(u, 1.0, 0.0).astype(np.float32))
        for t in thresholds:
            m = greedy_support(prob, region, None, t, 0)
            cand[f"model_thr{t:.2f}"] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
            if graded:
                cand[f"modelsoft_thr{t:.2f}"] = (m, np.where(m, prob, 0.0).astype(np.float32))
        for name, (mask, vals) in cand.items():
            res, terms = eh.evaluate(vals, fold, footprint, block_side=200,
                                     origin=(0, 0), global_shape=shape)
            if name not in arms:
                arms[name] = np.zeros_like(terms)
            arms[name] += terms
            per_fold.setdefault(name, {})[QUAD_NAMES[f]] = dict(
                dti=round(res["dti"], 5), emitted=int(mask.sum()),
                tp=round(res["tp"], 2), fp=round(res["fp"], 2),
                fn=round(res["fn"], 2), n_truth=res["n_truth"])
            print(f"  fold{f} {QUAD_NAMES[f]} {name:22s} dots {int(mask.sum()):>7,} DTI {res['dti']:.4f}")
    names = sorted(arms, key=lambda n: -eh.from_terms(arms[n].sum(axis=0)))
    ref = names[0]
    summary = eh.pooled_summary({n: arms[n] for n in names}, candidate=ref,
                                draws=600, seed=SEED)
    out = dict(session="2026-10-31", evidence_class="HOLDOUT-DTI",
               evaluator_version=eh.VERSION,
               instrument="spatial-quadrant leave-one-quadrant-out; 12 px domain erosion; "
                          "no catalogue-derived feature",
               per_fold=per_fold, pooled=summary["scores"],
               paired_differences_vs_best=summary.get("paired_differences"),
               bootstrap=summary["bootstrap"],
               implementation_sha256=summary["implementation_sha256"])
    (WORK / "holdout_2026_10_31.json").write_text(json.dumps(out, indent=1))
    print("\n=== pooled HOLDOUT-DTI (best first) ===")
    for n, s in sorted(summary["scores"].items(), key=lambda kv: -kv[1]["dti"]):
        print(f"  {n:24s} DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] "
              f"tp {s['tpw']:.0f} fp {s['fpw']:.0f} fn {s['fnw']:.0f} "
              f"withheld {s['withheld_positive_pixels']:,}")
    print("\n--- paired differences vs", ref)
    for n, v in sorted(summary["paired_differences"].items(), key=lambda kv: -kv[1]["delta"]):
        print(f"  {n:24s} delta {v['delta']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--budgets", default="6250,12500,25000,50000,100000")
    ap.add_argument("--spacings", default="0,3")
    ap.add_argument("--thresholds", default="0.50,0.30,0.20,0.10")
    ap.add_argument("--graded", action="store_true", help="also score soft (probability-valued) emissions")
    a = ap.parse_args()
    if a.fit:
        return do_fit()
    if a.scan:
        return do_scan([int(v) for v in a.budgets.split(",")],
                       [int(v) for v in a.spacings.split(",")],
                       [float(v) for v in a.thresholds.split(",")], a.graded)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
