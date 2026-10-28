"""IR-28-04 diagnostic: why did ADJDIS attempt-1 Phase-A emit only 35 cells?

Measures (no scoring, no submission): eligibility sizes, draw-budget ratios, and a
one-cell replay of celf_knapsack_allocate for Phase-A.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fchd.features import build_or_load_static_features  # noqa: E402
from src.fchd.registry_full import build_or_load_full_registry, celf_knapsack_allocate  # noqa: E402
from src.gemsw.holdout import DRAWS, FOLDS, load_holdout_context  # noqa: E402
import scripts.run_adjdis_lane as lane  # noqa: E402

D_INNER, D_OUTER, CAP, K = 2.0, 10.0, 0.635, 38_000
s_split, d0 = 0.60, 4.0

ctx = load_holdout_context(ROOT / "data" / "raw")
feat = build_or_load_static_features()
foot = feat["foot"]

cell_by_key = {c.key: c for c in ctx.cells}
d_full = ndi.distance_transform_edt(~ctx.labels)
a_full_mask = foot & (d_full > D_INNER) & (d_full <= D_OUTER)
b_full_mask = foot & (d_full > D_OUTER)
a_full_count = int(a_full_mask.sum())
b_full_count = int(b_full_mask.sum())

report: dict = {
    "a_full_count": a_full_count,
    "b_full_count": b_full_count,
    "labels_positive": int(np.count_nonzero(ctx.labels & foot)),
    "cells": {},
}
phase_a, phase_b = {}, {}
for cell in ctx.cells:
    sl = cell.bbox
    d_vis = cell.d_vis_sub
    a_elig = cell.active_sub & (d_vis > D_INNER) & (d_vis <= D_OUTER)
    b_elig = cell.active_sub & (d_vis > D_OUTER)
    w_a = np.where(a_elig, lane.band_of(d_vis, d0), 0.0).astype(np.float32)
    phase_a[cell.key] = (w_a, a_elig, sl)
    phase_b[cell.key] = (b_elig.astype(np.float32), b_elig, sl)
    report["cells"][cell.key] = {
        "active": int(cell.active_sub.sum()),
        "a_elig": int(a_elig.sum()),
        "b_elig": int(b_elig.sum()),
        "d_vis_minmax": [float(np.nanmin(d_vis)), float(np.nanmax(d_vis))],
        "visible_true": int(getattr(cell, "visible_true", -1)),
    }

k_a_total = int(round(s_split * K))
k_b_total = K - k_a_total
report["k_a_total"] = k_a_total
report["k_b_total"] = k_b_total
report["draw_budgets"] = {}
for seed in DRAWS:
    draw_cells = [cell_by_key[f"draw{seed}_fold{f}"] for f in FOLDS]
    a_cells_px = sum(int(phase_a[c.key][1].sum()) for c in draw_cells)
    b_cells_px = sum(int(phase_b[c.key][1].sum()) for c in draw_cells)
    draw_a = int(round(k_a_total * min(1.0, a_cells_px / a_full_count)))
    draw_b = int(round(k_b_total * min(1.0, b_cells_px / b_full_count)))
    a_mass = {c.key: float(phase_a[c.key][0][phase_a[c.key][1]].sum()) for c in draw_cells}
    a_tot = max(sum(a_mass.values()), 1e-9)
    report["draw_budgets"][f"draw{seed}"] = {
        "a_cells_px": a_cells_px,
        "b_cells_px": b_cells_px,
        "draw_a": draw_a,
        "draw_b": draw_b,
        "per_cell_k_a": {
            c.key: int(round(draw_a * (a_mass[c.key] / a_tot))) for c in draw_cells
        },
    }

reg = build_or_load_full_registry(foot)
cell0 = cell_by_key["draw20_fold0"]
w_a, e_a, sl = phase_a[cell0.key]
w2 = np.zeros(foot.shape, dtype=np.float32)
e2 = np.zeros(foot.shape, dtype=bool)
w2[sl], e2[sl] = w_a, e_a
per_cell_k_a = report["draw_budgets"]["draw20"]["per_cell_k_a"][cell0.key]
sel, info = celf_knapsack_allocate(w2, e2, foot, reg, budget_k=max(per_cell_k_a, 1), max_overlap_cap=CAP)
report["phaseA_fold0_replay"] = {
    "eligible": int(e2.sum()),
    "w_a_pos": int((w2 > 0).sum()),
    "budget_k": per_cell_k_a,
    "selected": int(sel.sum()),
    "info": {k: (int(v) if isinstance(v, (int, np.integer)) else v) for k, v in info.items()},
}

out = ROOT / "evidence" / "adjdis_ir28_04_diagnostic.json"
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "cells"}, indent=2))
print("cells:", {k: v["a_elig"] for k, v in report["cells"].items()})
print("wrote", out)
