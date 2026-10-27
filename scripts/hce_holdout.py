#!/usr/bin/env python3
"""E1/E2/E3 — fold-legal HCE candidate vs the shared hide-and-recover evaluator.

For EACH of the 8 spatial holdout cells we:
  * build every catalogue-derived field from that cell's VISIBLE faults only;
  * fit a gradient-boosted susceptibility model on visible fault pixels vs a
    background sample (no hidden segment is a positive, no hidden truth is used
    for tuning);
  * predict a probability field, turn it into a metric-optimal dot set with the
    shared Dinkelbach allocator (alpha=0.2, beta=0.8, 300 m triangular kernel);
  * score the per-cell dot mask with the UNMODIFIED vendored GEMSDOE32
    `evaluate_hide_and_recover` (pooled DTI + 256-block cluster bootstrap CI).

Three experiments only:
  E1  champion_proxy replay (not fold-legal, used as the reported incumbent)
  E2  HCE gamma=1.0, dot cap 40,000 per cell
  E3  HCE gamma=1.5, dot cap 60,000 per cell (prespecified variant)
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import holdout as H, alloc as A
from hce import fields as F

RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
GAMMA = {"E2_hce_g1_k40k": (1.0, 40000), "E3_hce_g15_k60k": (1.5, 60000)}


def build_matrix(X, cols, names, dyn_arrays):
    n = cols.size
    M = np.empty((n, len(names) + len(dyn_arrays)), np.uint8)
    for j in range(X.shape[0]):
        M[:, j] = X[j, cols]
    for j, (_, arr) in enumerate(dyn_arrays.items(), start=X.shape[0]):
        M[:, j] = arr[cols]
    return M


def fit_predict(cell, X, fidx, foot, pos, labels, rng, chunk=200_000):
    vis = cell.visible_full
    # visible-fault positives; background negatives sampled > 5 px from ANY visible trace
    pos_cols = pos[vis.ravel().nonzero()[0]]
    pos_cols = pos_cols[pos_cols >= 0]
    d_vis = ndi.distance_transform_edt(~vis)
    bg_pool = foot & (d_vis > 5.0)
    bg_idx = np.flatnonzero(bg_pool.ravel())
    take = rng.choice(bg_idx.size, min(150_000, bg_idx.size), replace=False)
    bg_cols = pos[bg_idx[take]]
    bg_cols = bg_cols[bg_cols >= 0]
    dyn = F.dynamic_geometry(vis, foot, fidx)
    names = [f"x{i}" for i in range(X.shape[0])]
    Xp = build_matrix(X, pos_cols, names, dyn)
    Xn = build_matrix(X, bg_cols, names, dyn)
    Xt = np.concatenate([Xp, Xn], axis=0)
    yt = np.r_[np.ones(Xp.shape[0]), np.zeros(Xn.shape[0])]
    # sample weights restore the real prior (~1 % of the footprint is a fault)
    w_neg = (foot.sum() - vis.sum()) / Xn.shape[0]
    wt = np.r_[np.ones(Xp.shape[0]), np.full(Xn.shape[0], w_neg)]
    clf = HistGradientBoostingClassifier(max_iter=120, max_depth=6, learning_rate=0.12,
                                         min_samples_leaf=80, l2_regularization=2.0,
                                         early_stopping=False, random_state=20261027)
    clf.fit(Xt, yt, sample_weight=wt)
    # predict every footprint cell of this cell's bbox
    sl = cell.bbox
    sub = pos.reshape(foot.shape)[sl].ravel()
    active = sub >= 0
    prob = np.zeros(sub.size, np.float32)
    cols = sub[active]
    for k in range(0, cols.size, chunk):
        cc = cols[k:k + chunk]
        M = build_matrix(X, cc, names, dyn)
        prob[np.flatnonzero(active)[k:k + chunk]] = clf.predict_proba(M)[:, 1].astype(np.float32)
    return prob.reshape(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start), dyn


def place(prob, cell, gamma, kcap, iters=3):
    """Dinkelbach allocation on the cropped cell grid; returns bool mask in bbox space."""
    p = np.clip(prob, 0.0, None)
    rho = np.power(p, gamma).astype(np.float32)
    cand = cell.active_sub.copy()
    # never emit on visible catalogue pixels (shared writer also enforces this)
    cand &= ~cell.visible_sub
    mu, out = 0.25, None
    for _ in range(iters):
        r = A.allocate(rho, cand.copy(), mu, n_max=kcap, max_rounds=10)
        e = A.expected_dti(rho, r["dots"])
        out = (r["dots"], e)
        if abs(e["dti"] - mu) < 5e-4:
            break
        mu = float(e["dti"])
    return out[0], out[1]


def paired(a, b, n_boot=4000, seed=17):
    tpa, fpa, fna, act = a
    tpb, fpb, fnb, _ = b
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = []
    for _ in range(n_boot):
        i = rng.choice(act, size=len(act), replace=True)
        ds.append(f(tpa[i], fpa[i], fna[i]) - f(tpb[i], fpb[i], fnb[i]))
    return dict(delta=float(d0), ci95=[float(np.quantile(ds, .025)), float(np.quantile(ds, .975))],
                p_delta_le_0=float(np.mean(np.asarray(ds) <= 0)))


def main():
    t0 = time.time()
    meta, X, fidx, foot = F.load()
    with rasterio.open(RAW / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    ctx = H.load_holdout_context(RAW)
    Hh, Ww = foot.shape
    pos = np.full(Hh * Ww, -1, np.int32)
    pos[fidx] = np.arange(fidx.size, dtype=np.int32)
    rng = np.random.default_rng(20261027)
    d28_path = next((ROOT / "data/ledger").glob("*dotted-h19-5-d2-8-20261002-e56ea318af89*.tif"))
    with rasterio.open(d28_path) as ds:
        d28 = (np.isfinite(ds.read(1))) & (ds.read(1) > 0) & foot
    print(f"[hce] setup {time.time()-t0:.0f}s; d28 dots {int(d28.sum()):,}", flush=True)

    # ---------------- E1: champion proxy (replay, same evaluator) ----------------
    cells_e1 = {}
    for cell in ctx.cells:
        vis = cell.visible_full
        d_vis = ndi.distance_transform_edt(~vis)
        dots = d28 & (d_vis > 2.01) & ~vis
        cells_e1[cell.key] = dots
    ev1 = H.evaluate_hide_and_recover(cells_e1, ctx, name="E1_champion_proxy", n_boot=1000)

    # ---------------- E2 / E3: HCE per-cell models ----------------
    probs, info = {}, []
    for cell in ctx.cells:
        p, _ = fit_predict(cell, X, fidx, foot, pos, labels, rng)
        probs[cell.key] = p
        info.append(dict(cell=cell.key, p_sum=float(p.sum()), p_max=float(p.max())))
        print(f"[hce] fitted {cell.key}: p_sum={p.sum():.1f} p_max={p.max():.4f} t={time.time()-t0:.0f}s", flush=True)

    results = {
        "evaluator_version": H.HIDE_RECOVER_EVALUATOR_VERSION,
        "score_label": "HOLDOUT-DTI",
        "alpha": 0.2, "beta": 0.8, "kernel_m": 300,
        "feature_fields": meta["n_fields"], "feature_names": meta["names"],
        "canary": "evidence/hce_canary.json",
        "experiments": {},
    }
    blocks = {}
    for tag, (gamma, kcap) in GAMMA.items():
        per_cell = {}
        for cell in ctx.cells:
            dots, exp = place(probs[cell.key], cell, gamma, kcap)
            per_cell[cell.key] = dots
            print(f"[hce] {tag} {cell.key}: dots={int(dots.sum())} model_dti={exp['dti']:.4f} t={time.time()-t0:.0f}s", flush=True)
        ev = H.evaluate_hide_and_recover(per_cell, ctx, name=tag, n_boot=1000)
        blocks[tag] = ev["_block_totals"]
        results["experiments"][tag] = dict(
            gamma=gamma, kcap=kcap, pooled_dti=ev["pooled_dti"], ci95=ev["ci95_cluster_bootstrap"],
            n_withheld=ev["n_withheld_positives"], per_quadrant=ev["per_quadrant_dti"],
            mean_dots=float(np.mean([int(v.sum()) for v in per_cell.values()])),
            folds={k: {kk: vv for kk, vv in v.items()} for k, v in ev["folds"].items()})
        np.savez_compressed(WORK / f"hce_{tag}_cells.npz", **{k: np.packbits(v.ravel()) for k, v in per_cell.items()})
    ev1c = ev1
    blocks["E1_champion_proxy"] = ev1c["_block_totals"]
    results["experiments"]["E1_champion_proxy"] = dict(
        pooled_dti=ev1c["pooled_dti"], ci95=ev1c["ci95_cluster_bootstrap"],
        n_withheld=ev1c["n_withheld_positives"], per_quadrant=ev1c["per_quadrant_dti"],
        mean_dots=float(np.mean([int((v & ctx.foot).sum()) for v in cells_e1.values()])),
        note="NOT fold-legal: the H19-5 / D2.8 network was built from the full catalogue, so hidden segments leak into the incumbent.")
    for tag in GAMMA:
        results["experiments"][tag]["paired_vs_E1_champion_proxy"] = paired(blocks[tag], blocks["E1_champion_proxy"])
    results["fit_info"] = info
    (ROOT / "evidence/hce_holdout.json").write_text(json.dumps(results, indent=2, default=float) + "\n")
    print(json.dumps({k: (v["pooled_dti"], v["ci95"], v.get("paired_vs_E1_champion_proxy", {}).get("delta"))
                      for k, v in results["experiments"].items()}, indent=2))
    print(f"[hce] done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
