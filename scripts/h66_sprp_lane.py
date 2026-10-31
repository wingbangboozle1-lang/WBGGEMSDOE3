#!/usr/bin/env python3
"""H66-SPRP lane: catalogue-independent supervised ridge-probability emission.

HYPOTHESIS
----------
The official 19-band GeoDAWN stack carries a fault signal that generalises to
faults that are NOT in the public USGS/INGENIOUS catalogue.  A per-cell
classifier trained on the *visible* catalogue, using only catalogue-independent
transforms of that stack, should recover withheld catalogue segments far above
chance on the shared hide-and-recover instrument.  The emission is then built
from the model's probability field and selected with the shared exact-DTI
allocator, and the near-catalogue band is excluded with the mechanism that the
byte-verified GEMSDOE31 -> GEMSDOE32 chain documents (the organiser masks
known-fault pixels from scoring, so dots within ~2 px of a mapped fault keep
their whole false-positive weight while earning little true-positive credit).

LANE BOUNDARY
-------------
* Metric, evaluator, allocator and writer are the pinned shared template
  (57GEMSDOE @ 822a0ce5546c7b6749cdd82eb145b6b3e616603d).  No private fork.
* The 38 model features are quantile transforms (global rank `q` and local
  standardised contrast `z`) of the official 19 bands, cached by the template's
  own `scripts/prep_feature_stack.py`.  NONE of them is catalogue-derived, so
  the fold-local holdout has no catalogue channel that could leak.
* Every number written here is HOLDOUT-DTI (shared evaluator, withheld count,
  95 % CI) or ESTIMATE.  A projection is never written as a score, and no
  competition slot is selected here.

Usage
-----
    python scripts/h66_sprp_lane.py --stage holdout
    python scripts/h66_sprp_lane.py --stage build
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_COMMIT = "822a0ce5546c7b6749cdd82eb145b6b3e616603d"
TPL = ROOT / ".cache" / f"57GEMSDOE-{TEMPLATE_COMMIT}"
sys.path.insert(0, str(TPL / "src"))

from gems57 import grid as G                              # noqa: E402
from gems57 import holdout as H                           # noqa: E402
from gems57 import metric as M                            # noqa: E402
from gems57 import evaluate_holdout as EH                 # noqa: E402
from gems57 import emit as E                              # noqa: E402
from gems57 import submission_writer as W                 # noqa: E402
from gems57 import validate as V                          # noqa: E402
from gems57 import gates as GT                            # noqa: E402

OUT = ROOT / "evidence" / "h66_sprp"
OUT.mkdir(parents=True, exist_ok=True)
WORK = ROOT / "data" / "work" / "h66_sprp"
WORK.mkdir(parents=True, exist_ok=True)
BANK = TPL / "out" / "features" / "bank_u8.npy"
SAMPLE = TPL / "data" / "bridge" / "sample_submission.tif"

SEEDS = (20,)
EXCLUDE_PX = 2            # catalogue exclusion band (GEMSDOE31 -> GEMSDOE32 mechanism)
N_NEG = 60000
CHUNK_ROWS = 256
RANDOM_STATE = 20261031
BUDGETS = (10000, 20000, 40000, 80000, 160000)
SPACINGS = (2, 3, 4)

STAGES: dict[str, float] = {}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def stage(name: str):
    class Ctx:
        def __enter__(self):
            self.t0 = time.time()
            log(f"--- stage: {name} ---")
            return self

        def __exit__(self, *exc):
            STAGES[name] = round(time.time() - self.t0, 1)
            log(f"--- done: {name} ({STAGES[name]}s) ---")
    return Ctx()


# --------------------------------------------------------------------------- #
# grid + features (template-owned)
# --------------------------------------------------------------------------- #
def load_grid():
    g = G.load_grid(TPL / "data" / "bridge")
    assert g.shape == (G.HEIGHT, G.WIDTH)
    assert g.crs.to_epsg() == G.EPSG
    assert tuple(g.transform)[:6] == tuple(G.TRANSFORM)[:6]
    log(f"footprint={int(g.footprint.sum())} catalogue={int(g.catalogue.sum())}")
    return g


def load_bank():
    bank = np.load(BANK, mmap_mode="r")
    assert bank.shape == (38, G.HEIGHT, G.WIDTH), bank.shape
    return bank


def gather(bank, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    out = np.empty((ys.size, 38), np.float32)
    for i in range(38):
        out[:, i] = np.asarray(bank[i][ys, xs], dtype=np.float32)
    return out / 255.0


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
def make_model():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.08, max_leaf_nodes=31,
        min_samples_leaf=40, l2_regularization=1.0,
        early_stopping=False, random_state=RANDOM_STATE)


def fit_fold(bank, g, visible: np.ndarray, seed: int):
    """Fit on VISIBLE catalogue positives only; negatives sampled outside the
    catalogue and outside the visible mask.  No catalogue-derived feature."""
    rng = np.random.default_rng(RANDOM_STATE + seed)
    cat = np.asarray(g.catalogue, bool)
    visible = np.asarray(visible, bool)
    pos = np.argwhere(visible & g.footprint)
    if pos.size == 0:
        raise RuntimeError("no visible catalogue positives")
    neg_pool = np.argwhere(g.footprint & ~cat & ~visible)
    take = min(N_NEG, neg_pool.shape[0])
    neg = neg_pool[rng.choice(neg_pool.shape[0], take, replace=False)]
    ys = np.concatenate([pos[:, 0], neg[:, 0]])
    xs = np.concatenate([pos[:, 1], neg[:, 1]])
    y = np.concatenate([np.ones(pos.shape[0], np.int8), np.zeros(take, np.int8)])
    X = gather(bank, ys, xs)
    model = make_model()
    model.fit(X, y)
    insample = float(model.score(X, y))
    log(f"train n={len(y)} pos={pos.shape[0]} neg={take} in-sample acc={insample:.4f}")
    return model, dict(n_train=int(len(y)), n_pos=int(pos.shape[0]), n_neg=int(take),
                        in_sample_accuracy=insample)


def predict_full(bank, model, shape) -> np.ndarray:
    p = np.zeros(shape, np.float32)
    H, W = shape
    for y0 in range(0, H, CHUNK_ROWS):
        y1 = min(H, y0 + CHUNK_ROWS)
        blk = np.asarray(bank[:, y0:y1, :], dtype=np.float32).reshape(38, -1).T / 255.0
        p[y0:y1] = model.predict_proba(blk)[:, 1].reshape(y1 - y0, W).astype(np.float32)
    return p


# --------------------------------------------------------------------------- #
# emission
# --------------------------------------------------------------------------- #
def allowed_mask(catalogue: np.ndarray, footprint: np.ndarray, exclude_px: int) -> np.ndarray:
    """Footprint minus the catalogue and minus the near-catalogue band.

    Dots on a mapped fault cannot earn true-positive credit (the organiser
    masks known-fault pixels) and dots within ~2 px of one keep their full
    false-positive weight, which is the mechanism the byte-verified
    GEMSDOE31 -> GEMSDOE32 chain isolates.
    """
    band = ndi.binary_dilation(np.asarray(catalogue, bool), iterations=int(exclude_px))
    return np.asarray(footprint, bool) & ~band


def nms_pool(p: np.ndarray, allowed: np.ndarray, spacing_px: int,
             max_candidates: int = 250_000) -> np.ndarray:
    """Greedy non-maximum suppression on the probability field.

    Pure feature-space selection (no metric arithmetic): it only decides which
    cells may carry a dot.  The metric decision is the shared allocator's.
    """
    H, W = p.shape
    ys, xs = np.nonzero(allowed)
    if ys.size == 0:
        return np.zeros((H, W), bool)
    vals = p[ys, xs]
    order = np.argsort(-vals, kind="stable")
    ys, xs = ys[order], xs[order]
    taken = np.zeros((H, W), bool)
    r = int(spacing_px)
    keep = []
    for i in range(ys.size):
        y, x = int(ys[i]), int(xs[i])
        if taken[y, x]:
            continue
        keep.append(i)
        taken[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] = True
        if len(keep) >= max_candidates:
            break
    out = np.zeros((H, W), bool)
    out[ys[keep], xs[keep]] = True
    return out


def top_budget_field(pool: np.ndarray, p: np.ndarray, budget: int) -> np.ndarray:
    ys, xs = np.nonzero(pool)
    vals = p[ys, xs]
    order = np.argsort(-vals, kind="stable")[:budget]
    field = np.zeros(p.shape, np.float32)
    field[ys[order], xs[order]] = 1.0
    return field


def allocate(p: np.ndarray, pool: np.ndarray, k_truth: float,
             max_dots: int) -> E.Allocation:
    """Shared exact-DTI allocator restricted to the candidate pool."""
    p_pool = np.where(pool, p, 0.0).astype(np.float32)
    return E.allocate_by_marginal_bar(p_pool, pool, float(k_truth), max_dots=int(max_dots))


# --------------------------------------------------------------------------- #
# holdout
# --------------------------------------------------------------------------- #
class GridNS:
    def __init__(self, foot, cat):
        self.footprint = foot
        self.catalogue = cat
        self.height, self.width = foot.shape


def build_folds(g):
    folds_all = []
    for seed in SEEDS:
        folds, _quad = H.buffered_component_draw(GridNS(g.footprint, g.catalogue),
                                                 seed=seed, hide_frac=0.20,
                                                 buffer_px=3, boundary_px=12)
        for f in folds:
            f["seed"] = seed
        folds_all.extend(folds)
        n = sum(int(f["truth"].sum()) for f in folds)
        log(f"seed={seed}: 4 folds, withheld truth px={n}")
    (OUT / "folds_receipt.json").write_text(json.dumps(
        [{"seed": f["seed"], "fold": f["name"], "n_truth": int(f["truth"].sum()),
          **{k: v for k, v in f["receipt"].items() if isinstance(v, (int, float, str))}}
         for f in folds_all], indent=1))
    return folds_all


def canary(bank, g, folds) -> dict:
    """Single-feature AUC against the withheld positives (leakage canary)."""
    from sklearn.metrics import roc_auc_score
    rows = []
    for f in folds:
        truth = np.asarray(f["truth"], bool)
        region = np.asarray(f["region"], bool)
        pos = np.argwhere(truth)
        neg_pool = np.argwhere(region & g.footprint
                               & ~np.asarray(g.catalogue, bool)
                               & ~np.asarray(f["masked_known"], bool))
        if pos.shape[0] == 0 or neg_pool.shape[0] == 0:
            continue
        rng = np.random.default_rng(RANDOM_STATE + 7)
        neg = neg_pool[rng.choice(neg_pool.shape[0], min(40000, neg_pool.shape[0]),
                                  replace=False)]
        ys = np.concatenate([pos[:, 0], neg[:, 0]])
        xs = np.concatenate([pos[:, 1], neg[:, 1]])
        X = gather(bank, ys, xs)
        y = np.concatenate([np.ones(pos.shape[0], np.int8), np.zeros(neg.shape[0], np.int8)])
        for i in range(38):
            auc = float(roc_auc_score(y, X[:, i]))
            auc = max(auc, 1.0 - auc)
            rows.append(dict(fold=f"{f['seed']}_{f['name']}", feature_index=i,
                             feature=f"bank_layer_{i:02d}", auc=auc,
                             n_pos=int(pos.shape[0]), n_neg=int(neg.shape[0])))
    worst = max(rows, key=lambda r: r["auc"]) if rows else None
    out = dict(rule="each feature alone vs withheld positives; max(AUC, 1-AUC) > 0.90 => leakage",
               threshold=0.90, n_features=38, rows=rows,
               max_auc=(worst["auc"] if worst else None),
               worst_feature=(worst["feature"] if worst else None),
               leakage=bool(worst and worst["auc"] > 0.90))
    (OUT / "leakage_canary.json").write_text(json.dumps(out, indent=1))
    log(f"leakage canary: max AUC {out['max_auc']} ({out['worst_feature']})")
    return out


def run_holdout(g, bank, folds):
    """Fold-local fit -> emission arms -> shared pooled DTI + spatial-block CI.

    The catalogue exclusion band is derived from the fold's VISIBLE faults only:
    the withheld components are the truth this instrument measures, so an
    exclusion band built from the full catalogue would delete every recoverable
    pixel before the model could place a dot on it.  The fold-local band is the
    exact analogue of the production band (which is built from the full
    published catalogue, because the hidden faults are not in it).
    """
    terms_by_arm: dict[str, np.ndarray] = {}
    per_fold = []
    rng = np.random.default_rng(RANDOM_STATE + 99)
    for f in folds:
        key = f"{f['seed']}_{f['name']}"
        visible = np.asarray(f["visible"], bool)
        model, info = fit_fold(bank, g, visible, f["seed"])
        p = predict_full(bank, model, g.shape)
        allow = allowed_mask(visible, g.footprint, EXCLUDE_PX)
        g_hat = float(p[allow].sum())
        arms = {}
        for sp in SPACINGS:
            pool = nms_pool(p, allow, sp)
            for b in BUDGETS:
                arms[f"sp{sp}_b{b}"] = top_budget_field(pool, p, b)
            alloc = allocate(p, pool, max(g_hat, 1.0), max(BUDGETS))
            arms[f"sp{sp}_alloc"] = alloc.emitted.astype(np.float32)
        arm_dti = {}
        n_dots = {a: int((fld > 0).sum()) for a, fld in arms.items()}
        for arm, field in arms.items():
            _res, t = EH.evaluate(field, f, g.footprint, block_side=200,
                                   origin=(0, 0), global_shape=g.shape)
            terms_by_arm.setdefault(arm, np.zeros_like(t))
            terms_by_arm[arm] += t
            arm_dti[arm] = float(_res["dti"])
        # Matched control: the same number of dots, placed uniformly at random
        # over the same allowed domain of the same fold.
        best_fold_arm = max(arm_dti, key=lambda a: arm_dti[a])
        n_ctrl = n_dots[best_fold_arm]
        ys, xs = np.nonzero(allow)
        take = rng.choice(ys.size, size=min(n_ctrl, ys.size), replace=False)
        control = np.zeros(g.shape, np.float32)
        control[ys[take], xs[take]] = 1.0
        arms["random_control"] = control
        _res, t = EH.evaluate(control, f, g.footprint, block_side=200,
                               origin=(0, 0), global_shape=g.shape)
        terms_by_arm["random_control"] = terms_by_arm.get(
            "random_control", np.zeros_like(t)) + t
        arm_dti["random_control"] = float(_res["dti"])
        per_fold.append(dict(fold=key, n_truth=int(_res["n_truth"]), g_truth_hat=g_hat,
                             train=info, arm_dti=arm_dti, n_dots=n_dots))
        log(f"  {key}: " + " ".join(f"{a}={d:.4f}" for a, d in
                                   sorted(per_fold[-1]["arm_dti"].items(),
                                          key=lambda kv: -kv[1])[:4]))
        del p, model
    scores = {}
    for arm, t in terms_by_arm.items():
        tp, fp, fn, nt = (float(t.sum(axis=0)[i]) for i in range(4))
        scores[arm] = dict(pooled_dti=float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS)),
                           tp=tp, fp=fp, fn=fn, n_withheld_positives=int(round(nt)))
    best = max((a for a in scores if a != "random_control"),
               key=lambda a: scores[a]["pooled_dti"])
    pooled = EH.pooled_summary(terms_by_arm, candidate=best)
    summary = dict(
        evidence_class="HOLDOUT-DTI",
        evaluator_version=EH.VERSION,
        evaluator_sha256=EH.implementation_hashes(),
        arms=scores, best_arm=best,
        best_pooled_dti=scores[best]["pooled_dti"],
        ci95=pooled["scores"][best]["ci95"],
        baseline_pooled_dti=scores["random_control"]["pooled_dti"],
        paired_delta_ci95=pooled["paired_differences"]["random_control"]["ci95"],
        paired_delta_vs_control=pooled["paired_differences"]["random_control"]["delta"],
        pooled_summary=pooled,
        n_withheld_positives=scores[best]["n_withheld_positives"],
        per_fold=per_fold,
        note=("Fold-local classifier trained on the fold's visible catalogue only; all 38 "
              "model features are catalogue-independent transforms of the official "
              "19-band stack (template-cached quantile bank). The catalogue exclusion "
              "band is derived from the visible faults of the fold only, so the "
              "withheld components remain recoverable."),
    )
    (OUT / "holdout.json").write_text(json.dumps(summary, indent=1))
    log(f"best arm {best}: pooled HOLDOUT-DTI {scores[best]['pooled_dti']:.4f} "
        f"CI {summary['ci95']} control {summary['baseline_pooled_dti']:.4f} "
        f"delta CI {summary['paired_delta_ci95']}")
    return summary


# --------------------------------------------------------------------------- #
# final build
# --------------------------------------------------------------------------- #
def final_build(g, bank, name: str, note: str, best_arm: str | None):
    model, info = fit_fold(bank, g, g.catalogue, 0)
    p = predict_full(bank, model, g.shape)
    np.save(WORK / "prob_full.npy", p)
    allow = allowed_mask(g.catalogue, g.footprint, EXCLUDE_PX)
    g_hat = float(p[allow].sum())
    sp = int(best_arm.split("_")[0][2:]) if best_arm else 3
    budget = int(best_arm.split("_b")[1]) if (best_arm and "_b" in best_arm) else 40000
    pool = nms_pool(p, allow, sp)
    if best_arm and best_arm.endswith("_alloc"):
        alloc = allocate(p, pool, max(g_hat, 1.0), budget)
        field = alloc.emitted.astype(np.float32)
        n_dots = int(alloc.n_dots)
        surrogate = float(alloc.surrogate_dti)
    else:
        field = top_budget_field(pool, p, budget)
        n_dots = int((field > 0).sum())
        surrogate = None
    field[~g.footprint] = 0.0
    path = ROOT / "submission" / f"{name}.tif"
    receipt = W.write_submission(path, field, sample=SAMPLE, footprint=g.footprint,
                                 catalogue=g.catalogue, name=name, note=note,
                                 metadata=dict(lane="h66_sprp", g_truth_hat=g_hat,
                                               surrogate_dti=surrogate, arm=best_arm))
    report = V.validate(path, g.footprint, g.catalogue)
    template_report = GT.format_report(path, SAMPLE, footprint=g.footprint)
    out = dict(receipt=receipt, validator=report, template_report=template_report,
               emission=dict(n_dots=n_dots, arm=best_arm, spacing_px=sp, budget=budget,
                             surrogate_dti=surrogate, g_truth_hat=g_hat,
                             exclude_px=EXCLUDE_PX, train=info))
    (OUT / "final_build.json").write_text(json.dumps(out, indent=1))
    log(f"final emission: {n_dots} dots -> {path}")
    return path, out


def run_ci(g, bank, folds, best_arm: str):
    """Paired spatial-cluster bootstrap CI for the selected arm on the same folds.

    Rebuilds the selected arm and a matched random-dot control (same dot count,
    uniform over the same allowed domain) on identical folds, then uses the
    shared pooled summary, which pools metric terms before resampling physical
    20 km blocks.
    """
    sp = int(best_arm.split("_")[0][2:])
    budget = int(best_arm.split("_b")[1]) if "_b" in best_arm else None
    terms = {}
    rng = np.random.default_rng(RANDOM_STATE + 99)
    for f in folds:
        key = f"{f['seed']}_{f['name']}"
        visible = np.asarray(f["visible"], bool)
        model, _info = fit_fold(bank, g, visible, f["seed"])
        p = predict_full(bank, model, g.shape)
        allow = allowed_mask(visible, g.footprint, EXCLUDE_PX)
        pool = nms_pool(p, allow, sp)
        field = top_budget_field(pool, p, budget) if budget else pool.astype(np.float32)
        n = int((field > 0).sum())
        control = np.zeros(g.shape, np.float32)
        ys = np.nonzero(allow)
        take = rng.choice(ys[0].size, size=min(n, ys[0].size), replace=False)
        control[ys[0][take], ys[1][take]] = 1.0
        for arm, fld in (("candidate", field), ("random_control", control)):
            _res, t = EH.evaluate(fld, f, g.footprint, block_side=200,
                                   origin=(0, 0), global_shape=g.shape)
            terms.setdefault(arm, np.zeros_like(t))
            terms[arm] += t
        log(f"  {key}: candidate emitted {n} dots, control {int((control > 0).sum())}")
        del p, model
    summary = EH.pooled_summary(terms, candidate="candidate")
    summary["evidence_class"] = "HOLDOUT-DTI"
    summary["arm"] = best_arm
    summary["note"] = ("Pooled DTI over the four spatial-quadrant folds with the shared "
                        "paired spatial-cluster percentile bootstrap; the matched control is a "
                        "uniform random dot field with the same dot count on the same folds.")
    (OUT / "holdout_ci.json").write_text(json.dumps(summary, indent=1))
    log(f"HOLDOUT-DTI {summary['scores']['candidate']['dti']:.4f} "
        f"CI {summary['scores']['candidate']['ci95']} "
        f"(withheld {summary['scores']['candidate']['withheld_positive_pixels']})")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all",
                    choices=["all", "holdout", "build", "canary", "ci"])
    ap.add_argument("--name", default="wbggems3-h66-sprp-ridgeprob-20261031T000000Z-00000000")
    ap.add_argument("--best-arm", default=None,
                    help="arm id for --stage ci (e.g. sp3_b40000)")
    ap.add_argument("--note", default=("H66-SPRP: supervised ridge probability on the official "
                                       "19-band stack, DTI-bar allocation, catalogue band excluded"))
    args = ap.parse_args()

    g = load_grid()
    bank = load_bank()
    folds = build_folds(g)

    best_arm = None
    if args.stage in ("all", "canary", "holdout"):
        with stage("canary"):
            canary(bank, g, folds)
    if args.stage in ("all", "holdout"):
        with stage("holdout"):
            summary = run_holdout(g, bank, folds)
            best_arm = summary["best_arm"]
    if args.stage == "ci":
        best_arm = args.best_arm
        with stage("ci"):
            ci = run_ci(g, bank, folds, best_arm)
        holdout = json.loads((OUT / "holdout.json").read_text())
        holdout["ci95"] = ci["scores"]["candidate"]["ci95"]
        holdout["paired_delta_ci95"] = ci["paired_differences"]["random_control"]["ci95"]
        holdout["baseline_pooled_dti"] = ci["scores"]["random_control"]["dti"]
        holdout["paired_delta_vs_control"] = ci["paired_differences"]["random_control"]["delta"]
        holdout["pooled_summary"] = ci
        (OUT / "holdout.json").write_text(json.dumps(holdout, indent=1))
    if args.stage in ("all", "build"):
        with stage("build"):
            final_build(g, bank, args.name, args.note, best_arm or args.best_arm)

    (OUT / "stages.json").write_text(json.dumps(
        dict(stages=STAGES, wall_clock_s=round(time.time() - T0, 1), best_arm=best_arm), indent=1))
    log(f"total {time.time() - T0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
