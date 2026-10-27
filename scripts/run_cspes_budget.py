#!/usr/bin/env python3
"""CSPES experiment 3: prespecified budget sweep (no surface reweighting).

Tests whether the CSPES ranking adds any value over a same-count random null at
budgets 30k / 45k / 60k, using the same shared hide-and-recover evaluator. This
sharpens the negative verdict; it is not a new estimator.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import cspes as C, grid as G, holdout as H  # noqa: E402

T0 = time.time()
rng = np.random.default_rng(20261027)
g = G.load_grid()
ctx = H.load_holdout_context(ROOT / "data/raw")
bands = C.read_cspes_bands(ROOT / "data/raw/training_features.tif")
fields = C.build_surface(bands, g.foot)
elig = np.flatnonzero((g.foot & ~g.labels).ravel())

rows = []
for budget in (30_000, 45_000, 60_000):
    dots = C.place_dots(fields.surface, g.foot, g.labels, budget=budget)
    ev = H.evaluate_hide_and_recover(dots, ctx, name=f"cspes_k{budget}", n_boot=1000)
    null_dots = np.zeros(g.foot.shape, bool)
    null_dots.ravel()[rng.choice(elig, budget, replace=False)] = True
    nv = H.evaluate_hide_and_recover(null_dots, ctx, name=f"null_k{budget}", n_boot=1000)
    tpa, fpa, fna, act = ev["_block_totals"]
    tpb, fpb, fnb, _ = nv["_block_totals"]
    rng2 = np.random.default_rng(7)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    ds = []
    for _ in range(2000):
        idx = rng2.choice(act, size=act.size, replace=True)
        ds.append(f(tpa[idx], fpa[idx], fna[idx]) - f(tpb[idx], fpb[idx], fnb[idx]))
    rows.append({
        "budget": budget,
        "cspes_dti": ev["pooled_dti"], "cspes_ci95": ev["ci95_cluster_bootstrap"],
        "random_null_dti": nv["pooled_dti"], "null_ci95": nv["ci95_cluster_bootstrap"],
        "paired_delta_cspes_minus_null": float(np.median(ds)),
        "delta_ci95": [float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
        "elapsed_s": round(time.time() - T0, 1),
    })
    print(rows[-1], flush=True)

out = {"lane": "CSPES", "experiment": 3, "kind": "prespecified budget sweep",
       "evaluator_version": ev["evaluator_version"], "rows": rows}
json.dump(out, open(ROOT / "evidence/cspes_budget.json", "w"), indent=1)
print("wrote evidence/cspes_budget.json")
