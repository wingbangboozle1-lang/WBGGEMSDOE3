#!/usr/bin/env python3
"""SMSR (Seismogeodetic Missing-Shear Ridge) lane: leave-one-quadrant-out CV.

Directly reuses the shared, pinned ``gems57`` template (``load_grid``,
``build_holdout``, ``cell_geometry``, ``fit_model``, ``canary``, ``run_cell``,
``pooled``, ``evaluate_holdout``) exactly as ``scripts/run_cv_r2.py`` in that
template does; the only new code is the three geophysical planes in
``smsr.geo_ext`` (no catalogue/holdout/label access, so no new leakage
surface). Evaluator version and implementation SHA-256 are the shared
``gems57-pooled-hide-v2``, printed with every result.

Variants
--------
``shipped_g``  -- anatomy FEATURES (11 cols) + shipped 9-plane ``geo.GEO_FEATURES``.
                  This is the control: the best-documented prior configuration
                  in the shared template.
``smsr_g``     -- ``shipped_g`` + the 3 new SMSR planes (14 geo columns total).

Both variants train the identical ``HistGradientBoostingClassifier`` recipe
(``gems57.fitting.GBM_KW``) on the identical leave-one-quadrant-out folds, so
any DTI delta is attributable to the 3 new planes alone.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_project.template import ensure_template  # noqa: E402

TEMPLATE = ensure_template()
sys.path.insert(0, str(TEMPLATE / "src"))

from gems57 import load_grid  # noqa: E402
from gems57 import geo as G  # noqa: E402
from gems57.anatomy import FEATURES  # noqa: E402
from gems57.fitting import canary, cell_geometry, fit_model, pooled, run_cell  # noqa: E402
from gems57.holdout import FOLD_NAMES, build_holdout  # noqa: E402

from smsr.geo_ext import NEW_GEO_FEATURES, load_combined_planes  # noqa: E402

EVID = ROOT / "evidence"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="all", choices=["all", "detached"])
    ap.add_argument("--max-dots", type=int, default=120_000)
    ap.add_argument("--floor", type=float, default=0.015)
    a = ap.parse_args()

    t0 = time.time()
    grid = load_grid()
    ctx = build_holdout(grid)
    cells = ctx.cells_of(a.mode)
    print(f"[{time.time()-t0:5.1f}s] holdout ready: {len(cells)} cells, mode={a.mode}", flush=True)

    planes_all = load_combined_planes(grid.footprint)
    planes_shipped = {k: planes_all[k] for k in G.GEO_FEATURES}
    print(f"[{time.time()-t0:5.1f}s] geo planes loaded: shipped={list(planes_shipped)} "
          f"new={list(NEW_GEO_FEATURES)}", flush=True)

    variants = {
        "shipped_g": planes_shipped,
        "smsr_g": planes_all,
    }

    out = {"mode": a.mode, "n_cells": len(cells),
           "evaluator_version": "gems57-pooled-hide-v2", "variants": {}}

    # ---- Gate 0: single-feature leakage canary on BOTH variants ------------
    for vname, planes in variants.items():
        geoms_canary = [cell_geometry(ctx, c, geo=planes) for c in cells[:4]]
        can = canary(geoms_canary)
        max_disc = max(r["discriminative_auc_max"] for r in can.values() if r["discriminative_auc_max"] is not None)
        flagged = [n for n, r in can.items() if r["leakage_flag"]]
        print(f"[{time.time()-t0:5.1f}s] canary[{vname}] max_discriminative_auc={max_disc:.4f} "
              f"flagged={flagged}", flush=True)
        out["variants"].setdefault(vname, {})["canary"] = can
        geoms_canary.clear()
        gc.collect()

    # ---- Gate 1: leave-one-quadrant-out CV, pooled DTI ---------------------
    for vname, planes in variants.items():
        t1 = time.time()
        results = []
        for qi, q in enumerate(FOLD_NAMES):
            test = [c for c in cells if c.key.split("_")[1] == f"fold{q}"]
            train = [c for c in cells if c.key.split("_")[1] != f"fold{q}"]
            geoms = [cell_geometry(ctx, c, geo=planes) for c in train]
            clf, scale, base = fit_model(geoms, seed=qi)
            geoms.clear()
            gc.collect()
            for c in test:
                g = cell_geometry(ctx, c, geo=planes)
                results.append(run_cell(ctx, c, clf, scale, g=g,
                                        max_dots=a.max_dots, floor=a.floor))
            del clf
            gc.collect()
        pl = pooled(results)
        out["variants"][vname]["pooled"] = pl
        out["variants"][vname]["per_cell"] = results
        ci = pl["dti_ci95_quadrant_jackknife"]
        print(f"[{time.time()-t1:5.1f}s] {vname:12s} HOLDOUT-DTI pooled={pl['pooled_dti']:.4f} "
              f"CI95(jackknife)=[{ci[0]:.4f},{ci[1]:.4f}] coverage={pl['coverage']:.4f} "
              f"dots={pl['n_dots']} tp={pl['tp']:.0f} fp={pl['fp']:.0f} K={pl['n_truth']}", flush=True)

    EVID.mkdir(exist_ok=True)
    (EVID / f"smsr_cv_{a.mode}.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote evidence/smsr_cv_{a.mode}.json   total {time.time()-t0:.1f}s")

    sh = out["variants"]["shipped_g"]["pooled"]["pooled_dti"]
    sm = out["variants"]["smsr_g"]["pooled"]["pooled_dti"]
    print(f"\nSMSR delta vs shipped_g: {sm - sh:+.4f} DTI")


if __name__ == "__main__":
    main()
