#!/usr/bin/env python3
"""E4 (final experiment): physical-only susceptibility + saturated dotted coverage.

Config (q, lattice spacing) is selected ONLY on the independent off-catalogue SGMC
fault population.  The chosen config is then scored once on the shared whole-segment
hide-and-recover holdout, with per-cell models fitted on visible faults only.
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
from gemsw import holdout as H
from hce import fields as F

RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
QS = [0.08, 0.12, 0.16, 0.20, 0.25, 0.30]
SPACINGS = [3, 4]


def fit_static(X, pos_cols, neg_cols, rng):
    M = np.concatenate([X[:, pos_cols].T, X[:, neg_cols].T], axis=0)
    y = np.r_[np.ones(pos_cols.size), np.zeros(neg_cols.size)]
    w_neg = 5_100_000.0 / neg_cols.size
    w = np.r_[np.ones(pos_cols.size), np.full(neg_cols.size, w_neg)]
    clf = HistGradientBoostingClassifier(max_iter=120, max_depth=6, learning_rate=0.12,
                                         min_samples_leaf=80, l2_regularization=2.0,
                                         early_stopping=False, random_state=20261027)
    clf.fit(M, y, sample_weight=w)
    return clf


def predict_block(clf, X, cols, chunk=200_000):
    out = np.zeros(cols.size, np.float32)
    for k in range(0, cols.size, chunk):
        out[k:k + chunk] = clf.predict_proba(X[:, cols[k:k + chunk]].T)[:, 1]
    return out


def lattice(shape, r0, c0, s):
    rr = (np.arange(r0, r0 + shape[0]) % s == 0)[:, None]
    cc = (np.arange(c0, c0 + shape[1]) % s == 0)[None, :]
    return rr & cc


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
    active = foot & ~labels
    act_cols = pos[active.ravel().nonzero()[0]]
    act_cols = act_cols[act_cols >= 0]
    lab_cols = pos[labels.ravel().nonzero()[0]]
    lab_cols = lab_cols[lab_cols >= 0]
    neg_all = rng.choice(act_cols.size, min(150_000, act_cols.size), replace=False)

    # ---- full-catalogue static-only model: used ONLY for SGMC config selection ----
    clf_all = fit_static(X, lab_cols, act_cols[neg_all], rng)
    p_all = np.zeros(Hh * Ww, np.float32)
    vals = predict_block(clf_all, X, np.arange(fidx.size))
    p_all[fidx] = vals
    p_all = p_all.reshape(Hh, Ww)
    print(f"[E4] full model p_sum={p_all.sum():.1f} p_max={p_all.max():.4f} t={time.time()-t0:.0f}s", flush=True)

    # ---- config selection on SGMC (independent off-catalogue fault population) ----
    cfg_rows = []
    for s in SPACINGS:
        lat = lattice(foot.shape, 0, 0, s)
        for q in QS:
            thr = float(np.quantile(p_all[active], 1.0 - q))
            dots = active & lat & (p_all >= thr)
            ev = H.evaluate_candidate_holdout(dots, ctx, name=f"cfg_q{q}_s{s}")
            cfg_rows.append(dict(q=q, spacing=s, threshold=thr, n_dots=int(dots.sum()),
                                 sgmc_raw_dti=ev["sgmc_off_catalogue_raw_dti"],
                                 sgmc_coverage=ev["sgmc_off_catalogue_coverage"]))
    cfg_rows.sort(key=lambda r: -r["sgmc_raw_dti"])
    best = cfg_rows[0]
    print("[E4] SGMC config selection top5:", json.dumps(cfg_rows[:5], indent=1), flush=True)

    # ---- per-cell fold-legal models, chosen config ----
    q, s = best["q"], best["spacing"]
    cells, cells_rand = {}, {}
    info = []
    for cell in ctx.cells:
        sl = cell.bbox
        sh = (sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
        vis = cell.visible_full
        vc = pos[vis.ravel().nonzero()[0]]
        vc = vc[vc >= 0]
        sub = pos.reshape(foot.shape)[sl].ravel()
        ok = sub >= 0
        cols = sub[ok]
        # negatives: random footprint cells outside the visible catalogue
        nonvis = np.setdiff1d(np.arange(fidx.size, dtype=np.int32), vc, assume_unique=False)
        neg = rng.choice(nonvis, min(150_000, nonvis.size), replace=False)
        clf = fit_static(X, vc, neg, rng)
        pv = np.zeros(sub.size, np.float32)
        pv[np.flatnonzero(ok)] = predict_block(clf, X, cols)
        p = pv.reshape(sh)
        dom = cell.active_sub & ~cell.visible_sub
        thr = float(np.quantile(p[dom], 1.0 - q)) if dom.any() else 1.0
        lat = lattice(sh, sl[0].start, sl[1].start, s)
        dots = dom & lat & (p >= thr)
        # dot-count-matched random control (shuffle susceptibility inside the domain)
        prand = np.zeros_like(p)
        di = np.flatnonzero(dom.ravel())
        prand.ravel()[di] = rng.permutation(p.ravel()[di])
        thr_r = float(np.quantile(prand[dom], 1.0 - q)) if dom.any() else 1.0
        dots_r = dom & lat & (prand >= thr_r)
        cells[cell.key] = dots
        cells_rand[cell.key] = dots_r
        info.append(dict(cell=cell.key, n=int(dots.sum()), n_random=int(dots_r.sum()), thr=thr))
        print(f"[E4] {cell.key}: dots={int(dots.sum())} random={int(dots_r.sum())} t={time.time()-t0:.0f}s", flush=True)

    ev = H.evaluate_hide_and_recover(cells, ctx, name="E4_hce_physical_saturated", n_boot=1000)
    evr = H.evaluate_hide_and_recover(cells_rand, ctx, name="E4_random_control", n_boot=1000)
    res = dict(evaluator_version=H.HIDE_RECOVER_EVALUATOR_VERSION, score_label="HOLDOUT-DTI",
               config_selector="independent off-catalogue SGMC faults (sgmc_off_catalogue_raw_dti)",
               sgmc_config_rows=cfg_rows, selected_config=best,
               E4=dict(pooled_dti=ev["pooled_dti"], ci95=ev["ci95_cluster_bootstrap"],
                       n_withheld=ev["n_withheld_positives"], per_quadrant=ev["per_quadrant_dti"],
                       folds=ev["folds"], cells=info),
               random_control=dict(pooled_dti=evr["pooled_dti"], ci95=evr["ci95_cluster_bootstrap"],
                                   n_withheld=evr["n_withheld_positives"]),
               p_full_sha256=None)
    np.save(WORK / "hce_p_full.npy", p_all.astype(np.float32))
    import hashlib
    res["p_full_sha256"] = hashlib.sha256((WORK / "hce_p_full.npy").read_bytes()).hexdigest()
    np.savez_compressed(WORK / "hce_E4_cells.npz", **{k: np.packbits(v.ravel()) for k, v in cells.items()})
    (ROOT / "evidence/hce_e4.json").write_text(json.dumps(res, indent=2, default=float) + "\n")
    print("[E4] FINAL HOLDOUT-DTI", ev["pooled_dti"], ev["ci95_cluster_bootstrap"],
          "random control", evr["pooled_dti"], "t=%.0fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
