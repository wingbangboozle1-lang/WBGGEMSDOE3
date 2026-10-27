#!/usr/bin/env python3
"""CSPES lane experiments 1-2 (label: HOLDOUT-DTI; no slot, no upload).

E1  leakage canary : single-field ROC-AUC for hidden fault pixels inside the eight
                     hide-and-recover cells. AUC > 0.90 is a leakage stop.
E2  holdout DTI    : CSPES dots (K=37,654, 2-px NMS) vs the matched D2.8 fold-local
                     champion proxy, same cells, same shared evaluator, paired block
                     bootstrap of the DTI difference. Frozen ablations included.

Usage: .venv/bin/python scripts/run_cspes.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import cspes as C, grid as G, holdout as H  # noqa: E402

T0 = time.time()
RNG = np.random.default_rng(20261027)
EVID = ROOT / "evidence"
EVID.mkdir(exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------- load
g = G.load_grid()
log("grid loaded")
ctx = H.load_holdout_context(ROOT / "data/raw")
log(f"holdout context: {len(ctx.cells)} cells, "
    f"{sum(c.n_truth for c in ctx.cells)} withheld positives")
bands = C.read_cspes_bands(ROOT / "data/raw/training_features.tif")
fields = C.build_surface(bands, g.foot)
log("CSPES surface built")

# ---------------------------------------------------------------- E1: canary
def canary_samples(per_cell_neg: int = 4_000):
    """Pooled hidden-truth positives and matched active-domain negatives per cell."""
    xs_pos, xs_neg, names = [], [], []
    for cell in ctx.cells:
        sl = cell.bbox
        active = cell.active_sub
        ty, tx = cell.truth_coords
        ys_pos, xs = np.nonzero(active)
        neg_choice = RNG.choice(ys_pos.size, size=min(per_cell_neg, ys_pos.size), replace=False)
        ny, nx = ys_pos[neg_choice], xs[neg_choice]
        names.append((sl, ty, tx, ny, nx))
    return names


canary_fields = {
    "raw_iso_grav_anom": bands["grav"],
    "raw_rtp": bands["rtp"],
    "raw_det_elev": bands["elev"],
    "P_grav_persist": fields.components["P_grav_persist"],
    "P_mag_persist": fields.components["P_mag_persist"],
    "align_collinear": fields.components["align"],
    "topo_rank": fields.components["topo_rank"],
    "cspes_full_surface": fields.surface,
}
canary = {}
cells_idx = canary_samples()
for name, arr in canary_fields.items():
    y_true, score = [], []
    for sl, ty, tx, ny, nx in cells_idx:
        sub = arr[sl]
        y_true.append(np.ones(ty.size, np.int8))
        score.append(sub[ty, tx])
        y_true.append(np.zeros(ny.size, np.int8))
        score.append(sub[ny, nx])
    y_true = np.concatenate(y_true)
    score = np.concatenate(score)
    finite = np.isfinite(score)
    auc = float(roc_auc_score(y_true[finite], score[finite]))
    canary[name] = {"auc": auc, "n_pos": int(y_true.sum()),
                    "n_neg": int((y_true == 0).sum()), "leakage_alarm": auc > 0.90}
    log(f"canary {name:22s} AUC={auc:.4f}{'  LEAKAGE ALARM' if auc > 0.90 else ''}")
if any(v["leakage_alarm"] for v in canary.values()):
    json.dump({"status": "STOP: leakage canary", "canary": canary},
              open(EVID / "cspes_canary.json", "w"), indent=1)
    raise SystemExit("E1 leakage stop")
json.dump({"status": "pass", "canary": canary}, open(EVID / "cspes_canary.json", "w"), indent=1)

# ---------------------------------------------------------------- E2: holdout
def evaluate(mask_full, name):
    ev = H.evaluate_hide_and_recover(mask_full, ctx, name=name, n_boot=1000)
    log(f"{name:28s} DTI={ev['pooled_dti']:.4f} CI={[round(x,4) for x in ev['ci95_cluster_bootstrap']]} "
        f"n_withheld={ev['n_withheld_positives']}")
    return ev


K = C.DEFAULT_BUDGET
results = {}
surfaces = {k: fields.components[k] for k in
            ("cspes_full", "abl_grav_only", "abl_mag_only", "abl_no_topo_conditioning")}
dots_by_name = {}
for name, surf in surfaces.items():
    dots = C.place_dots(surf, g.foot, g.labels, budget=K)
    dots_by_name[name] = dots
    results[name] = evaluate(dots, name)

# Same-count random-null baseline (one seeded draw; label-independent).
null_dots = np.zeros(g.foot.shape, bool)
elig = np.flatnonzero((g.foot & ~g.labels).ravel())
null_dots.ravel()[RNG.choice(elig, K, replace=False)] = True
results["random_null_k37654"] = evaluate(null_dots, "random_null_k37654")

# Matched incumbent: D2.8 champion proxy, rebuilt fold-locally exactly as in
# scripts/run_holdout.py (dots farther than 2.01 px from each cell's VISIBLE faults).
d28_path = next((ROOT / "data/ledger").glob("GEMSDOE25__*dotted-h19-5-d2-8*.tif"))
d28 = G.read_band(d28_path)
d28_dots = np.isfinite(d28) & (d28 > 0) & g.foot
log(f"incumbent D2.8 dots: {int(d28_dots.sum())} from {d28_path.name}")
champ_cells = {}
for cell in ctx.cells:
    vis = cell.visible_full
    d_vis = ndi.distance_transform_edt(~vis)
    champ_cells[cell.key] = d28_dots & (d_vis > 2.01) & ~vis
champ = H.evaluate_hide_and_recover(champ_cells, ctx, name="champion_proxy_d28_b2", n_boot=1000)
results["champion_proxy_d28_b2"] = {
    "pooled_dti": champ["pooled_dti"], "ci95_cluster_bootstrap": champ["ci95_cluster_bootstrap"],
    "n_withheld_positives": champ["n_withheld_positives"], "evaluator_version": champ["evaluator_version"],
    "score_label": champ["score_label"]}
log(f"{'champion_proxy_d28_b2':28s} DTI={champ['pooled_dti']:.4f} "
    f"CI={[round(x,4) for x in champ['ci95_cluster_bootstrap']]}")


def paired_delta(ev_a, ev_b, n_boot=4000, seed=7):
    """Paired spatial-cluster bootstrap of pooled DTI(a)-pooled DTI(b) on shared blocks."""
    tpa, fpa, fna, act = ev_a["_block_totals"]
    tpb, fpb, fnb, _ = ev_b["_block_totals"]
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.choice(act, size=act.size, replace=True)
        ds[i] = f(tpa[idx], fpa[idx], fna[idx]) - f(tpb[idx], fpb[idx], fnb[idx])
    return {"delta": float(d0), "ci95": [float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
            "p_delta_le_0": float(np.mean(ds <= 0.0))}


ev_full = H.evaluate_hide_and_recover(dots_by_name["cspes_full"], ctx, name="cspes_full_paired", n_boot=1000)
paired = paired_delta(ev_full, champ)
log(f"PAIRED CSPES - champion: delta={paired['delta']:+.4f} CI={[round(x,4) for x in paired['ci95']]} "
    f"P(delta<=0)={paired['p_delta_le_0']:.4f}")

summary = {
    "lane": "CSPES cross-scale potential-field edge stability",
    "spec": "knowledge/preregistration-2026-10-27.md",
    "budget_K": K,
    "n_withheld_positives": ev_full["n_withheld_positives"],
    "evaluator_version": ev_full["evaluator_version"],
    "canary_file": "evidence/cspes_canary.json",
    "results": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_") and kk != "folds"}
                for k, v in results.items()},
    "paired_cspes_minus_champion": paired,
    "elapsed_s": round(time.time() - T0, 1),
}
json.dump(summary, open(EVID / "cspes_holdout.json", "w"), indent=1)
np.save(ROOT / "data/work_cspes_dots.npy", np.packbits(dots_by_name["cspes_full"].ravel()))
log("wrote evidence/cspes_holdout.json and data/work_cspes_dots.npy")
