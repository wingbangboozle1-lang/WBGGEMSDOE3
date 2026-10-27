#!/usr/bin/env python3
"""Owner-reported live-score projection model (PROJECTION, never a score).

Fits a small ridge regression from measurable raster geometry to the 117
SHA-verified OWNER-REPORTED scores in data/ledger/index.json, with leave-one-out
cross-validation.  The model is then used ONLY to produce an uncertain projection
for this lane's candidates and for the nine focus-site files.  It is not an
organizer receipt, not a leaderboard value, and cannot see the hidden test set.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_predict, LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import holdout as H
from hce import fields as F

DISC = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)
FEATURES = ["log10_n_dots", "sgmc_coverage", "catalogue_hidden_mean", "frac_near_h19_5",
            "frac_near_d28", "mean_dist_to_catalogue", "frac_near_catalogue", "block_occupancy",
            "frac_near_champion_b2"]


def mask_of(path, foot):
    with rasterio.open(path) as ds:
        a = ds.read(1)
        if ds.shape != foot.shape:
            return None
    return (np.isfinite(a) & (a > 0) & foot)


def features(m, ctx, foot, labels, d_cat, h_dots, d28, b2, blocks):
    m = m & foot & ~labels
    n = int(m.sum())
    if n == 0:
        return None
    ev = H.evaluate_candidate_holdout(m, ctx, name="f")
    out = [
        np.log10(n),
        ev["sgmc_off_catalogue_coverage"],
        ev["catalogue_hidden_mean"],
        float((m & h_dots).sum() / n),
        float((m & d28).sum() / n),
        float(d_cat[m].mean()),
        float((d_cat[m] <= 3).mean()),
        float(np.unique(blocks[m]).size / blocks.max()),
        float((m & b2).sum() / n),
    ]
    return np.asarray(out, np.float64)


def main():
    meta, X, fidx, foot = F.load()
    ctx = H.load_holdout_context(ROOT / "data" / "raw")
    labels = ctx.labels
    d_cat = ndi.distance_transform_edt(~labels)
    with rasterio.open(ROOT / "data/raw/scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif") as ds:
        h_raw = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    with rasterio.open(ROOT / "data/ledger/GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        d28_raw = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    with rasterio.open(ROOT / "data/focus/GEMSDOE32.tif") as ds:
        b2_raw = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    h_dots = ndi.binary_dilation(h_raw, structure=DISC)
    d28 = ndi.binary_dilation(d28_raw, structure=DISC)
    b2 = ndi.binary_dilation(b2_raw, structure=DISC)
    Hh, Ww = foot.shape
    blocks = (np.arange(Hh)[:, None] // 64 * 100 + np.arange(Ww)[None, :] // 64).astype(np.int16)

    idx = [r for r in json.load(open(ROOT / "data/ledger/index.json"))
           if r["status"] == "verified" and r.get("score") is not None]
    rows, ys, keep = [], [], []
    for r in idx:
        m = mask_of(ROOT / r["local"], foot)
        if m is None:
            continue
        f = features(m, ctx, foot, labels, d_cat, h_dots, d28, b2, blocks)
        if f is None:
            continue
        rows.append(f); ys.append(float(r["score"])); keep.append(r)
    A = np.stack(rows); y = np.array(ys)
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    loo = cross_val_predict(model, A, y, cv=LeaveOneOut())
    model.fit(A, y)
    resid = y - loo
    mae = float(np.mean(np.abs(resid)))
    q90 = float(np.quantile(np.abs(resid), 0.90))
    print(f"[score-model] n={len(y)} LOO MAE={mae:.4f} abs_err_q90={q90:.4f} "
          f"corr={np.corrcoef(y, loo)[0,1]:.3f}", flush=True)

    # ---- nine focus-site files ----
    pins = json.load(open(ROOT / "research/input_manifest.json"))[:9]
    claims = {s["site"]: float(s["owner_reported"])
              for s in json.load(open(ROOT / "registry/focus_sites.json"))["sites"]}
    focus = []
    for e in pins:
        m = mask_of(ROOT / "data/focus" / e["dest"], foot)
        f = features(m, ctx, foot, labels, d_cat, h_dots, d28, b2, blocks)
        focus.append(dict(site=e["id"], file=e["dest"], n_dots=int(m.sum()),
                          sgmc_coverage=float(f[1]), catalogue_hidden_mean=float(f[2]),
                          projection_p50=float(model.predict(f[None, :])[0]),
                          projection_p10=float(model.predict(f[None, :])[0] - q90),
                          projection_p90=float(model.predict(f[None, :])[0] + q90),
                          owner_reported_unverified=claims.get(e["id"], None)))
    # ---- candidates from the full-catalogue HCE susceptibility field ----
    p = np.load(ROOT / "data/work/hce_p_full.npy")
    active = foot & ~labels
    cand = []
    for s in (3, 4):
        rr = (np.arange(Hh) % s == 0)[:, None]
        cc = (np.arange(Ww) % s == 0)[None, :]
        lat = rr & cc
        for q in (0.08, 0.12, 0.16, 0.20, 0.25, 0.30):
            thr = float(np.quantile(p[active], 1.0 - q))
            m = active & lat & (p >= thr)
            f = features(m, ctx, foot, labels, d_cat, h_dots, d28, b2, blocks)
            pred = float(model.predict(f[None, :])[0])
            cand.append(dict(q=q, spacing=s, n_dots=int(m.sum()), sgmc_coverage=float(f[1]),
                             catalogue_hidden_mean=float(f[2]), projection_p50=pred,
                             projection_p10=pred - q90, projection_p90=pred + q90))
    res = dict(kind="PROJECTION from OWNER-REPORTED scores — NOT an organizer-confirmed score",
               n_training=int(len(y)), features=FEATURES, loo_mae=mae, loo_abs_err_q90=q90,
               loo_spearman=float(np.corrcoef(y, loo)[0, 1]),
               ridge_coefficients=dict(zip(FEATURES, model[-1].coef_.tolist())),
               focus_sites=focus, candidates=cand,
               caution="Off-network, dense or physically novel rasters are out of distribution; intervals use the LOO 90th-percentile absolute error and can still under-cover.")
    (ROOT / "evidence/hce_score_model.json").write_text(json.dumps(res, indent=2, default=float) + "\n")
    print("[score-model] candidate projections:")
    for c in cand:
        print(f"  q={c['q']:.2f} s={c['spacing']} dots={c['n_dots']:,} sgmc={c['sgmc_coverage']:.3f} "
              f"proj={c['projection_p50']:.4f} [{c['projection_p10']:.4f},{c['projection_p90']:.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
