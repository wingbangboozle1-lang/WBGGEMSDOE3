#!/usr/bin/env python3
"""Sensitivity of the chosen emission density to the SIZE of the hidden truth set.

The sponsor's new-fault set is not public, so its pixel count K is unknown.  The
density that maximises the official DTI depends on K: more (or fewer) hidden
fault pixels shift the true-positive/false-positive balance.  This scan emulates
a smaller hidden set by randomly thinning the WITHHELD catalogue truth inside
each held-out quadrant, and re-ranks the candidate emission policies at each
level.  It is a sensitivity analysis of an already-selected design, not a new
model fit.  Evidence class: HOLDOUT-DTI (thinned-truth variant).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(TEMPLATE / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from session_2026_10_31_holdout import greedy_support, QUAD_NAMES  # noqa: E402
from session_2026_10_31_scan3 import capacity_support  # noqa: E402

SEED = 20261031
THINS = (1.0, 0.5, 0.25)
GRID = [("cap3", 3, 2, 0.20), ("cap3", 3, 2, 0.30), ("cap3", 3, 2, 0.40),
        ("cap3", 3, 2, 0.50), ("cap3", 3, 3, 0.20), ("cap3", 3, 3, 0.30),
        ("cap3", 3, 4, 0.30), ("cap3", 3, 1, 0.20), ("topN", None, None, None)]


def main() -> int:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    rng = np.random.default_rng(SEED + 5)
    results = {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        truth_full = catalogue & region
        folds_by_thin = {}
        for thin in THINS:
            t = truth_full
            if thin < 1.0:
                yy, xx = np.nonzero(truth_full)
                keep = rng.random(len(yy)) < thin
                t = np.zeros(shape, bool)
                t[yy[keep], xx[keep]] = True
            folds_by_thin[thin] = dict(region=region, truth=t,
                                       visible=catalogue & ~region,
                                       masked_known=catalogue & ~region)
        arms_cache: dict[str, np.ndarray] = {}
        for tag, b, c, floor in GRID:
            if tag == "topN":
                m = greedy_support(prob, region, 50000, None, 0)
            else:
                m = capacity_support(prob, region, b, c, floor)
            name = tag + (f"_c{c}" + ("" if floor is None else f"_f{floor:.2f}"))
            arms_cache[name] = m
        for thin, fold in folds_by_thin.items():
            for name, m in arms_cache.items():
                vals = np.where(m, 1.0, 0.0).astype(np.float32)
                res, terms = eh.evaluate(vals, fold, footprint, block_side=200,
                                         origin=(0, 0), global_shape=shape)
                key = f"thin{thin}"
                results.setdefault(key, {})
                results[key].setdefault(name, np.zeros_like(terms))
                results[key][name] += terms
        print(f"fold {f}: {len(arms_cache)} arms x {len(THINS)} truth levels", flush=True)

    out = {"session": "2026-10-31", "evidence_class": "HOLDOUT-DTI (thinned-truth sensitivity)",
           "evaluator_version": eh.VERSION, "levels": {}}
    for thin in THINS:
        key = f"thin{thin}"
        names = sorted(results[key], key=lambda n: -eh.from_terms(results[key][n].sum(axis=0)))
        summ = eh.pooled_summary({n: results[key][n] for n in names}, candidate=names[0],
                                 draws=400, seed=SEED)
        out["levels"][key] = {n: dict(dti=s["dti"], ci95=s["ci95"],
                                      withheld=int(s["withheld_positive_pixels"]),
                                      tp=round(s["tpw"]), fp=round(s["fpw"]))
                              for n, s in summ["scores"].items()}
        print(f"\n=== truth thinned to {thin:.0%} (K = "
              f"{summ['scores'][names[0]]['withheld_positive_pixels']:,} px) ===")
        for n, s in sorted(summ["scores"].items(), key=lambda kv: -kv[1]["dti"]):
            print(f"   {n:20s} DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}]")
    (WORK / "holdout_scan4b_2026_10_31.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
