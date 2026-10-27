#!/usr/bin/env python3
"""SGCE lane: leakage canary + preregistered 3-experiment hide-and-recover holdout.

Uses the SAME vendored evaluator as the incumbent evidence (GEMSDOE32-HIDE-RECOVER-v3.0),
identical folds, and a recomputed champion proxy for the paired bootstrap.  No submission slot
is used and no hidden competition label is read.  Output: evidence/session2_holdout.json.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import sgce, grid as G, holdout as H  # noqa: E402

OUT = ROOT / "evidence" / "session2_holdout.json"


def auc(scores_pos: np.ndarray, scores_neg: np.ndarray) -> float:
    from scipy.stats import rankdata
    n1, n0 = scores_pos.size, scores_neg.size
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(np.concatenate([scores_pos, scores_neg]))
    return float((r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def canary_prepare(cells, bins, g, rng):
    """Collect sampled hidden-truth / background field values for single-field AUC canaries."""
    names = list(sgce.FIELDS) + ["GEOM_d_vis_neg", "GEOM_corridor", "GEOM_relay", "RHO_surface"]
    pos = {n: [] for n in names}
    neg = {n: [] for n in names}
    for cell in cells:
        vis = cell.visible_full
        geo = sgce.geometry(vis, g.foot, sgce.SIGMA_DEFAULT)
        rho, _ = sgce.density(bins, vis, g.foot, geo)
        sl = cell.bbox
        truth = np.zeros(cell.active_sub.shape, bool)
        truth[cell.truth_coords] = True
        bg = cell.active_sub & ~truth
        ty, tx = np.nonzero(truth)
        by, bx = np.nonzero(bg)
        if ty.size > 4000:
            i = rng.choice(ty.size, 4000, replace=False)
            ty, tx = ty[i], tx[i]
        if by.size > 20000:
            i = rng.choice(by.size, 20000, replace=False)
            by, bx = by[i], bx[i]
        ry, rx = ty + sl[0].start, tx + sl[1].start
        ny, nx = by + sl[0].start, bx + sl[1].start
        for k, name in enumerate(sgce.FIELDS):
            b = np.asarray(bins[k])
            pos[name].append(b[ry, rx].astype(np.float32))
            neg[name].append(b[ny, nx].astype(np.float32))
        extra = dict(
            GEOM_d_vis_neg=(-geo["d_vis"]).astype(np.float32),
            GEOM_corridor=geo["corridor"].astype(np.float32),
            GEOM_relay=geo["relay"].astype(np.float32),
            RHO_surface=rho,
        )
        for name, arr in extra.items():
            pos[name].append(arr[ry, rx])
            neg[name].append(arr[ny, nx])
    res = {}
    for name in names:
        p = np.concatenate(pos[name]); q = np.concatenate(neg[name])
        a = auc(p, q)
        res[name] = dict(auc=a, n_pos=int(p.size), n_neg=int(q.size), leakage_canary=bool(a > 0.90))
    return res


def paired(a, b, n_boot=4000, seed=7):
    tpa, fpa, fna, act = a
    tpb, fpb, fnb, _ = b
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = []
    for _ in range(n_boot):
        i = rng.choice(act, size=len(act), replace=True)
        ds.append(f(tpa[i], fpa[i], fna[i]) - f(tpb[i], fpb[i], fnb[i]))
    return dict(delta=float(d0), ci95=[float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
                p_delta_le_0=float(np.mean(np.array(ds) <= 0)))


def build_arm(cells, ctx, bins, g, sigma, n_cap, label, max_rounds=12):
    per_cell, info = {}, []
    for cell in cells:
        vis = cell.visible_full
        geo = sgce.geometry(vis, g.foot, sigma)
        rho, dinfo = sgce.density(bins, vis, g.foot, geo)
        r = sgce.place(rho, vis, g.foot, geo, n_cap=n_cap, mu=0.28, max_rounds=max_rounds,
                       iters=3, region=cell.bbox)
        per_cell[cell.key] = r["dots"]
        info.append(dict(cell=cell.key, n=r["n"], model_dti=r["expected"]["dti"], trace=r["trace"],
                         corridor_px=geo["corridor_px"], relay_px=geo["relay_px"]))
        print(f"  {label} {cell.key}: n={r['n']} t={time.time()-T0:.0f}s", flush=True)
    ev = H.evaluate_hide_and_recover(per_cell, ctx, name=label, n_boot=1000)
    return dict(pooled_dti=ev["pooled_dti"], ci95=ev["ci95_cluster_bootstrap"],
                per_quadrant=ev["per_quadrant_dti"], n_withheld=ev["n_withheld_positives"],
                evaluator=ev["evaluator_version"], score_label="HOLDOUT-DTI",
                n_clusters=ev["n_spatial_clusters"], cells=info,
                settings=dict(sigma=sigma, n_cap=n_cap, max_rounds=max_rounds,
                              mass=sgce.MASS, fields=sgce.FIELDS)), ev["_block_totals"]


def main() -> None:
    global T0
    T0 = time.time()
    g = G.load_grid()
    bins = sgce.load_bins(g)
    ctx = H.load_holdout_context(ROOT / "data/raw")
    cells = ctx.cells
    print(f"loaded grid/bins/ctx in {time.time()-T0:.0f}s", flush=True)

    rng = np.random.default_rng(20261027)
    can = canary_prepare(cells, bins, g, rng)
    individual = {k: v for k, v in can.items() if k != "RHO_surface"}
    worst = max(individual.items(), key=lambda kv: (kv[1]["auc"] if np.isfinite(kv[1]["auc"]) else -1))
    print("CANARY max single-field AUC:", worst[0], worst[1],
          "composite RHO_surface AUC (diagnostic, not a single feature):", can["RHO_surface"]["auc"], flush=True)
    if worst[1]["leakage_canary"]:
        print("LEAKAGE CANARY TRIGGERED (AUC > 0.90): STOP", flush=True)
        json.dump(dict(canary=can, stop="leakage_canary", experiments={}), open(OUT, "w"), indent=1)
        return

    # Fold-local champion proxy: dotted H19-5 d2.8 with the B2 visible-fault pruning.
    d28p = next((ROOT / "data" / "ledger").glob("*dotted-h19-5-d2-8-20261002-e56ea318af89*.tif"))
    with rasterio.open(d28p) as ds:
        a28 = ds.read(1)
    d28 = np.isfinite(a28) & (a28 > 0) & g.foot
    ch, ch_info = {}, []
    for cell in cells:
        vis = cell.visible_full
        d_vis = ndi.distance_transform_edt(~vis)
        dots = d28 & (d_vis > sgce.B_PX) & ~vis
        ch[cell.key] = dots
        ch_info.append(dict(cell=cell.key, n=int(dots.sum())))
    chev = H.evaluate_hide_and_recover(ch, ctx, name="champion_proxy", n_boot=1000)
    champ = dict(pooled_dti=chev["pooled_dti"], ci95=chev["ci95_cluster_bootstrap"],
                 per_quadrant=chev["per_quadrant_dti"], n_withheld=chev["n_withheld_positives"],
                 evaluator=chev["evaluator_version"], score_label="HOLDOUT-DTI",
                 source=str(d28p.relative_to(ROOT)), cells=ch_info)
    print(f"champion_proxy HOLDOUT-DTI {champ['pooled_dti']:.4f} CI {champ['ci95']}", flush=True)

    result = dict(canary=can, canary_max=dict(field=worst[0], **worst[1]),
                  champion_proxy=champ, experiments={}, budget=dict(experiments_run=0, max=3))
    blocks = {"champion_proxy": chev["_block_totals"]}

    specs = [("E1", 15.0, 45_000), ("E2", 25.0, 45_000)]
    for label, sigma, cap in specs:
        arm, blk = build_arm(cells, ctx, bins, g, sigma, cap, label)
        blocks[label] = blk
        arm["paired_vs_champion_proxy"] = paired(blk, blocks["champion_proxy"])
        result["experiments"][label] = arm
        result["budget"]["experiments_run"] += 1
        print(f"{label}: HOLDOUT-DTI {arm['pooled_dti']:.4f} CI {arm['ci95']} "
              f"paired {arm['paired_vs_champion_proxy']}", flush=True)

    best = max(specs, key=lambda s: result["experiments"][s[0]]["pooled_dti"])
    e3 = ("E3", best[1], 60_000)
    arm, blk = build_arm(cells, ctx, bins, g, e3[1], e3[2], e3[0])
    arm["paired_vs_champion_proxy"] = paired(blk, blocks["champion_proxy"])
    arm["paired_vs_best_prior"] = paired(blk, blocks[best[0]])
    result["experiments"]["E3"] = arm
    result["budget"]["experiments_run"] += 1
    result["budget"]["best_sigma"] = best[1]
    print(f"E3: HOLDOUT-DTI {arm['pooled_dti']:.4f} CI {arm['ci95']} "
          f"paired {arm['paired_vs_champion_proxy']}", flush=True)
    result["promotion_rule"] = dict(
        requires="paired delta vs champion_proxy lower 95% bound > 0 on identical folds",
        passed=bool(arm["paired_vs_champion_proxy"]["ci95"][0] > 0
                    or result["experiments"][best[0]]["paired_vs_champion_proxy"]["ci95"][0] > 0),
        measured_on="hide-and-recover catalogue proxy, NOT the hidden expert-labelled test set")
    json.dump(result, open(OUT, "w"), indent=1, default=float)
    print(f"wrote {OUT} in {time.time()-T0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
