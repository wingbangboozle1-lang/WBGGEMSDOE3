#!/usr/bin/env python3
"""E1 — single-feature leakage canary on the vendored whole-segment holdout.

For every static field (and the two fold-legal dynamic geometry fields) compute
the pooled AUC distinguishing WITHHELD fault pixels from a random sample of the
same cell's active background.  AUC > 0.90 is leakage until proven otherwise.
No model is fitted and no dot is placed here.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import holdout as H
from hce import fields as F

RAW = ROOT / "data" / "raw"


def main():
    t0 = time.time()
    meta, X, fidx, foot = F.load()
    names = meta["names"]
    with rasterio.open(RAW / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    with rasterio.open(RAW / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc_all = ds.read(1) > 0
    ctx = H.load_holdout_context(RAW)
    Hh, Ww = foot.shape
    pos = np.full(Hh * Ww, -1, np.int32)
    pos[fidx] = np.arange(fidx.size, dtype=np.int32)
    rng = np.random.default_rng(20261027)

    truth_cols, bg_cols = [], []
    dyn = {}
    for cell in ctx.cells:
        sl = cell.bbox
        r0, c0 = int(sl[0].start), int(sl[1].start)
        ty, tx = cell.truth_coords
        tflat = (r0 + ty) * Ww + (c0 + tx)
        tc = pos[tflat]
        tc = tc[tc >= 0]
        bgmask = cell.active_sub.copy()
        bgmask[ty, tx] = False
        by, bx = np.nonzero(bgmask)
        pick = rng.choice(by.size, min(5000, by.size), replace=False)
        bflat = (r0 + by[pick]) * Ww + (c0 + bx[pick])
        bc = pos[bflat]
        bc = bc[bc >= 0]
        truth_cols.append(tc)
        bg_cols.append(bc)
        # fold-legal dynamic features computed from THIS cell's visible catalogue only
        vis = cell.visible_full
        d = F.dynamic_geometry(vis, foot, fidx)
        for k, arr in d.items():
            dyn.setdefault(k, []).append((arr[tc], arr[bc]))
    T = np.concatenate(truth_cols)
    B = np.concatenate(bg_cols)
    print(f"[canary] truth={T.size:,} background={B.size:,} cells={len(ctx.cells)} t={time.time()-t0:.0f}s", flush=True)

    rows = []
    for j, nm in enumerate(names):
        tv = np.asarray(X[j, T], dtype=np.float32)
        bv = np.asarray(X[j, B], dtype=np.float32)
        auc = float(roc_auc_score(np.r_[np.ones(tv.size), np.zeros(bv.size)], np.r_[tv, bv]))
        rows.append(dict(field=nm, family="static", auc=round(auc, 5)))
    for k, pairs in dyn.items():
        tv = np.concatenate([p[0] for p in pairs]).astype(np.float32)
        bv = np.concatenate([p[1] for p in pairs]).astype(np.float32)
        auc = float(roc_auc_score(np.r_[np.ones(tv.size), np.zeros(bv.size)], np.r_[tv, bv]))
        rows.append(dict(field=k, family="dynamic_fold_legal", auc=round(auc, 5)))
    rows.sort(key=lambda r: -r["auc"])
    thr = 0.90
    flagged = [r for r in rows if r["auc"] > thr]
    usable = [r["field"] for r in rows if r["auc"] <= thr]
    res = dict(evaluator_version=H.HIDE_RECOVER_EVALUATOR_VERSION,
               n_withheld_positives_pooled=int(T.size), n_background_sampled=int(B.size),
               n_cells=len(ctx.cells), threshold=thr, max_auc=rows[0]["auc"],
               flagged_fields=flagged, usable_fields=usable, all_pass=not flagged,
               top10=rows[:10], rows=rows,
               note="AUC computed on quantile-bin codes; a high value means the field alone separates withheld catalogue faults. AUC<=0.90 does not prove absence of leakage.")
    (ROOT / "evidence/hce_canary.json").write_text(json.dumps(res, indent=2) + "\n")
    print("[canary] max AUC", rows[0], "flagged", [r["field"] for r in flagged], "t=%.0fs" % (time.time() - t0))
    return 0 if not flagged else 2


if __name__ == "__main__":
    raise SystemExit(main())
