#!/usr/bin/env python3
"""Spatially-blocked, FOLD-LOCAL hold-out for the W1' candidate (label: HOLDOUT-DTI).

Every cell builds its candidate from ITS visible catalogue only (distance strata, modulation fit, B=2 pruning),
then is scored by the vendored GEMSDOE32 hide-and-recover evaluator (whole-segment hiding, 1.5 km collar,
256-block spatial cluster bootstrap CI).  The ledger-fitted stratum lambdas come from live scores, never from
the hidden catalogue segments.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import candidate as C, holdout as H, grid as G

VARIANTS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["champion_proxy", "stratum_quota", "lst_mod_quota", "lst_mod_noquota"]
ONE_CELL = len(sys.argv) > 2 and sys.argv[2] == "one"
t0 = time.time()
g = G.load_grid()
ctx = H.load_holdout_context(ROOT / "data/raw")
model = C.load_model(ROOT / "data/work/lst_model.npz")
bz = np.load(ROOT / "data/work/bins.npz")
need = set(C.MOD_FIELDS)
bins_foot = {k: bz[k] for k in need}
h = G.read_band(ROOT / "data/raw/scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
h_dots = np.isfinite(h) & (h > 0) & g.foot
h_dist = ndi.distance_transform_edt(~h_dots)
avoid_p = ROOT / "data/work/avoid_mask_packed.npy"
avoid = None
if avoid_p.exists() and "--no-avoid" not in sys.argv:
    avoid = np.unpackbits(np.load(avoid_p))[: g.foot.size].reshape(g.foot.shape).astype(bool)
print("avoid zone px:", 0 if avoid is None else int(avoid.sum()), flush=True)
d28 = G.read_band(next((ROOT / "data/ledger").glob("*dotted-h19-5-d2-8-20261002-e56ea318af89*.tif")))
d28 = np.isfinite(d28) & (d28 > 0) & g.foot
print(f"setup {time.time()-t0:.0f}s; d2.8 dots {int(d28.sum())}", flush=True)
cells = ctx.cells[:1] if ONE_CELL else ctx.cells
res, blocks = {}, {}
for v in VARIANTS:
    per_cell, info = {}, []
    for cell in cells:
        vis = cell.visible_full
        if v == "champion_proxy":                 # D2.8 + fold-local B2
            d_vis = ndi.distance_transform_edt(~vis)
            dots = d28 & (d_vis > 2.01) & ~vis
            info.append(dict(cell=cell.key, n=int(dots.sum())))
        else:
            mdl = dict(model, strat_lambda=model["strat_lambda_median"]) if v.endswith("_median") else model
            r = C.build(mdl, bins_foot, g.foot, vis, h_dots, h_dist, region=cell.bbox, avoid=avoid,
                        on_share=C.ON_SHARE_FINAL if ("_quota" in v) else 1.0 - 1e-9,
                        use_mod=v.startswith("lst_mod") , iters=2)
            dots = r["dots"]
            info.append(dict(cell=cell.key, n=r["n"], n_on=r["n_on"], n_off=r["n_off"], model_dti=r["expected"]["dti"],
                             model_dti_no_quota=r["expected_without_quota"]["dti"]))
        per_cell[cell.key] = dots
        print(f"  {v} {cell.key}: n={int(dots[cell.bbox].sum())} t={time.time()-t0:.0f}s", flush=True)
    if ONE_CELL:
        continue
    ev = H.evaluate_hide_and_recover(per_cell, ctx, name=v, n_boot=1000)
    blocks[v] = ev["_block_totals"]
    vkey = v + ("__DIAGNOSTIC_no_avoid_zone" if "--no-avoid" in sys.argv else "")
    res[vkey] = dict(pooled_dti=ev["pooled_dti"], ci95=ev["ci95_cluster_bootstrap"], per_quadrant=ev["per_quadrant_dti"],
                  n_withheld=ev["n_withheld_positives"], cells=info, score_label="HOLDOUT-DTI",
                  evaluator=ev["evaluator_version"])
    print(f"{v}: HOLDOUT-DTI {ev['pooled_dti']:.4f} CI {ev['ci95_cluster_bootstrap']}", flush=True)
def paired(a, b, n_boot=4000, seed=7):
    """Paired spatial-cluster bootstrap of pooled DTI(a) - pooled DTI(b) over the same 256-block resamples."""
    tpa, fpa, fna, act = a; tpb, fpb, fnb, _ = b
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = []
    for _ in range(n_boot):
        i = rng.choice(act, size=len(act), replace=True)
        ds.append(f(tpa[i], fpa[i], fna[i]) - f(tpb[i], fpb[i], fnb[i]))
    return dict(delta=float(d0), ci95=[float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
                p_delta_le_0=float(np.mean(np.array(ds) <= 0)))


if not ONE_CELL:
    if "champion_proxy" in blocks:
        for v in VARIANTS:
            if v != "champion_proxy":
                vk = v + ("__DIAGNOSTIC_no_avoid_zone" if "--no-avoid" in sys.argv else "")
                res[vk]["paired_vs_champion_proxy"] = paired(blocks[v], blocks["champion_proxy"])
                print(vk, "paired delta vs champion proxy:", res[vk]["paired_vs_champion_proxy"], flush=True)
    out = ROOT / "evidence/holdout_results.json"
    prev_ = {}
    prev = json.load(open(out)) if out.exists() else {}
    prev.update(res)
    json.dump(prev, open(out, "w"), indent=1)
