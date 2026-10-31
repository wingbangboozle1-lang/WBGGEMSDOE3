#!/usr/bin/env python3
"""Spatially blocked experiments for the release lane.

For every spatial fold (NW/NE/SW/SE) and every positive-class arm (CAT = catalogue
only, UNION = catalogue + SGMC off-catalogue) this script

1. trains on cells *outside* the held-out quadrant,
2. scores the held-out quadrant,
3. sweeps emission density and dot separation,
4. records the exact pooled DTI plus a physical-block bootstrap CI,
5. runs the single-feature leakage canary (AUC of each plane alone).

Outputs ``evidence/release/experiments.json`` and cached score planes under
``data/work/scores/``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_release import emit, model, shared, truth  # noqa: E402

EVID = ROOT / "evidence" / "release"
SCORES = ROOT / "data" / "work" / "scores"
DENSITIES = (4000, 8000, 12000, 16000, 20000, 30000, 45000)  # dots per million active cells
SEPARATIONS = (1, 2, 3)
ARMS = ("CAT", "UNION")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=list(ARMS))
    ap.add_argument("--folds", nargs="*", default=list(truth.QUADRANTS))
    ap.add_argument("--kind", default="hgb", choices=["hgb", "logit"])
    ap.add_argument("--n-pos", type=int, default=25000)
    ap.add_argument("--n-neg", type=int, default=40000)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    EVID.mkdir(parents=True, exist_ok=True)
    SCORES.mkdir(parents=True, exist_ok=True)
    footprint, catalogue = shared.load_masks()
    names, planes = model.open_planes()
    sg = truth.sgmc_offcatalogue(catalogue)
    sgmc_off = sg["mask"]
    print(f"[setup] planes={len(names)} footprint={int(footprint.sum()):,} "
          f"catalogue={int(catalogue.sum()):,} sgmc_off={int(sgmc_off.sum()):,}", flush=True)

    result = dict(
        generated_by="scripts/release_experiments.py",
        evaluator="gems57.metric (pinned shared template) + official formula",
        alpha=0.2, beta=0.8, radius_m=300.0,
        collar_px=emit.DEFAULT_COLLAR_PX,
        densities_per_million=DENSITIES, separations_px=SEPARATIONS,
        planes=names, arms=list(args.arms), kind=args.kind,
        folds={}, canary={}, runs={},
    )

    folds = {}
    for q in args.folds:
        f = truth.fold_truth(q, catalogue)
        folds[q] = f
        result["folds"][q] = dict(n_truth=f["n_truth"], n_withheld_raw=f["n_withheld_raw"],
                                  n_dropped_by_buffer=f["n_dropped_by_buffer"],
                                  n_active=int(f["active"].sum()))
    print("[folds]", json.dumps(result["folds"]), flush=True)

    # --- leakage canary -----------------------------------------------------
    for q, f in folds.items():
        bg = truth.background_mask(catalogue, footprint, 10.0) & f["region"]
        result["canary"][q] = model.single_feature_auc(planes, names, f["truth"], bg)
    print("[canary]", json.dumps({k: {n: (round(v, 3) if v else v) for n, v in d.items()}
                                  for k, d in result["canary"].items()}), flush=True)

    score_paths = {}
    for arm in args.arms:
        for q, f in folds.items():
            tag = f"{arm}_{q}"
            dest = SCORES / f"{tag}.npy"
            if dest.is_file() and not args.force:
                print(f"[skip] score {tag}", flush=True)
                score_paths[(arm, q)] = dest
                continue
            t0 = time.time()
            train = model.build_training(arm, q, catalogue, sgmc_off,
                                         n_pos=args.n_pos, n_neg=args.n_neg)
            fitted, meta = model.fit(planes, names, train, kind=args.kind)
            region = f["footprint"] & f["region"]
            score = model.score_region(fitted, planes, region)
            np.save(dest, score, allow_pickle=False)
            score_paths[(arm, q)] = dest
            result["runs"][tag] = dict(training=meta, train_counts={
                k: int(v) for k, v in train.items() if k.startswith("n_")},
                score_sha256=shared.sha256_file(dest),
                score_valid=int(np.isfinite(score).sum()),
                seconds=round(time.time() - t0, 1))
            print(f"[fit] {tag} pos={meta['n_pos']} neg={meta['n_samples']-meta['n_pos']} "
                  f"valid={int(np.isfinite(score).sum()):,} {time.time()-t0:.0f}s", flush=True)

    # --- sweep --------------------------------------------------------------
    grid = {}
    for arm in args.arms:
        for q, f in folds.items():
            score = np.load(score_paths[(arm, q)], mmap_mode="r")
            # the collar must come from the *visible* faults of this fold: the
            # withheld truth is exactly what the model is asked to recover.
            allowed, _ = emit.allowed_mask(f["footprint"], f["visible"],
                                           valid=np.isfinite(np.asarray(score)))
            allowed &= f["region"]
            n_active = int((f["active"] & f["region"]).sum())
            d_truth = None
            for dens in DENSITIES:
                k = int(round(dens * n_active / 1_000_000))
                for sep in SEPARATIONS:
                    dots = emit.select_dots(np.asarray(score), allowed, k, nms_px=sep)
                    ev = emit.evaluate(dots, f)
                    if d_truth is None:
                        from scipy.ndimage import distance_transform_edt
                        d_truth = distance_transform_edt(~f["truth"])
                    hit = float((d_truth[dots] <= 3.0).mean()) if dots.any() else 0.0
                    blocks = emit.block_terms(dots, f)
                    grid[f"{arm}|{dens}|{sep}|{q}"] = dict(
                        arm=arm, density=dens, separation=sep, fold=q, k_target=k,
                        dti=ev["dti"], tp=ev["tp"], fp=ev["fp"], fn=ev["fn"],
                        n_truth=ev["n_truth"], n_emitted=ev["n_emitted"],
                        hit_rate_within_3px=hit,
                        blocks=blocks.tolist())
            print(f"[sweep] {arm} {q} done", flush=True)

    # --- harness controls: oracle and random must bracket the metric -------
    result["controls"] = {}
    rng = np.random.default_rng(20261031)
    for q, f in folds.items():
        region = f["footprint"] & f["region"]
        allowed, _ = emit.allowed_mask(f["footprint"], f["visible"], valid=region)
        allowed &= f["region"]
        k = int(round(10000 * (f["active"] & f["region"]).sum() / 1_000_000))
        oracle = f["truth"] & allowed
        flat = np.flatnonzero(allowed.ravel())
        pick = rng.choice(flat, size=min(k, flat.size), replace=False)
        rand = np.zeros(allowed.shape, bool)
        rand.ravel()[pick] = True
        result["controls"][q] = {
            "oracle": emit.evaluate(oracle, f), "oracle_dots": int(oracle.sum()),
            "random": emit.evaluate(rand, f), "random_dots": int(rand.sum())}
        print(f"[control] {q} oracle={result['controls'][q]['oracle']['dti']:.4f} "
              f"random={result['controls'][q]['random']['dti']:.4f}", flush=True)
    result["grid"] = grid
    # pooled per configuration
    pooled = {}
    for key in grid:
        if not key.endswith("NW"):
            continue
        arm, dens, sep, _ = key.split("|")
        rows = [grid[f"{arm}|{dens}|{sep}|{q}"] for q in args.folds]
        tp = sum(r["tp"] for r in rows); fp = sum(r["fp"] for r in rows)
        fn = sum(r["fn"] for r in rows); nt = sum(r["n_truth"] for r in rows)
        ne = sum(r["n_emitted"] for r in rows)
        metric = shared.shared_metric()
        blocks = np.concatenate([np.asarray(r["blocks"]) for r in rows])
        pooled[f"{arm}|{dens}|{sep}"] = dict(
            arm=arm, density=int(dens), separation=int(sep),
            dti=float(metric.dti_from_components(tp, fp, fn)),
            tp=tp, fp=fp, fn=fn, n_truth=nt, n_emitted=ne,
            recall=float(tp / max(1e-12, nt)),
            hit_rate_within_3px=float(sum(r["hit_rate_within_3px"] * r["n_emitted"]
                                          for r in rows) / max(1, ne)),
            ci95=emit.bootstrap_ci(blocks),
            per_fold={q: grid[f"{arm}|{dens}|{sep}|{q}"]["dti"] for q in args.folds})
    result["pooled"] = pooled
    best = max(pooled.items(), key=lambda kv: kv[1]["dti"])
    result["best"] = {"config": best[0], **best[1]}
    print("[best]", json.dumps({k: v for k, v in best[1].items() if k != "per_fold"},
                               indent=1), flush=True)

    out = EVID / "experiments.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[done] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
