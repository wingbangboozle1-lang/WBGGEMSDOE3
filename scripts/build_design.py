#!/usr/bin/env python3
"""EXP0 (shared): bins for every independent field + leakage canary + ledger design matrices.

Outputs (git-ignored cache): data/work/bins.npz, data/work/design.npz ; committed: evidence/field_canary.json
"""
from __future__ import annotations
import json, sys, time, hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw.grid import load_grid, read_band
from gemsw import features as F, ledger as L

W = ROOT / "data" / "work"; W.mkdir(parents=True, exist_ok=True)
NB = 64   # bins per field in the design arrays (rank-bin fields use codes 0..9; product stratum uses < 64)


def auc_two_pol(a_pos, a_neg):
    x = np.r_[a_pos, a_neg]; ok = np.isfinite(x)
    y = np.r_[np.ones(len(a_pos)), np.zeros(len(a_neg))][ok]; x = x[ok]
    r = rankdata(x); n1 = y.sum(); n0 = len(y) - n1
    auc = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return float(max(auc, 1 - auc)), float(auc)


def main() -> None:
    t0 = time.time()
    g = load_grid()
    active = g.foot & ~g.labels
    aidx = np.flatnonzero(active.ravel())
    rng = np.random.default_rng(7)
    neg_idx = rng.choice(aidx, 200_000, replace=False)
    pos_idx = np.flatnonzero(g.labels.ravel())
    sel = active[g.foot]            # active pixels expressed in footprint-order
    bins, canary = {}, []
    for name, fam, fld in F.iter_fields(g):
        fl = fld.ravel()
        a2, araw = auc_two_pol(fl[pos_idx], fl[neg_idx])
        bins[name] = F.to_bins(fld, active, g.foot)
        canary.append(dict(field=name, family=fam, auc_two_polarity=round(a2, 4), auc_raw=round(araw, 4),
                           missing_frac=round(float((bins[name][sel] == 0).mean()), 4)))
        print(f"{len(bins):3d} {name:34s} {fam:22s} AUC2={a2:.3f}  t={time.time()-t0:.0f}s", flush=True)
    worst = max(canary, key=lambda c: c["auc_two_polarity"])
    # nuisance controls (NOT features): distance to catalogue, H19-5 network membership
    def digitize(d, edges, codes):
        return np.asarray(codes, np.uint8)[np.digitize(d, edges, right=True)]
    d_cat = ndi.distance_transform_edt(~g.labels)
    cat_code = digitize(d_cat[g.foot], [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
    bins["NUIS_d_catalogue"] = cat_code
    h = read_band(ROOT / "data/raw/scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
    hm = np.isfinite(h) & (h > 0) & g.foot
    d_h = ndi.distance_transform_edt(~hm)
    h_code = digitize(d_h[g.foot], [0.01, 1.01, 2.01, 3.01, 5.01, 10.01], [0, 1, 2, 3, 4, 5, 6])
    bins["NUIS_d_H19-5"] = h_code
    bins["NUIS_catxH"] = (cat_code * 8 + h_code).astype(np.uint8)   # 8 x 7 product stratum, codes < 64
    np.savez_compressed(W / "bins.npz", **bins)       # footprint-order codes (NOT active-order)
    bins = {k: v[sel] for k, v in bins.items()}      # active-order for the design matrices
    json.dump(dict(n_fields=len(canary), worst=worst, threshold=0.90, all_pass=worst["auc_two_polarity"] <= 0.90,
                   fields=canary), open(ROOT / "evidence/field_canary.json", "w"), indent=1)
    print("canary worst:", worst, "all pass:", worst["auc_two_polarity"] <= 0.90)

    # ---- ledger design ----
    idx = json.load(open(ROOT / "data/ledger/index.json"))
    names = list(bins)
    rows, meta, digests = [], [], {}
    for r in idx:
        if r["status"] != "verified":
            continue
        a = read_band(ROOT / r["local"]).astype(np.float32)
        a = np.where(np.isfinite(a), a, 0.0)
        a[~active] = 0.0
        a = np.clip(a, 0.0, 1.0)
        dig = hashlib.sha256(np.round(a[active], 5).tobytes()).hexdigest()[:16]
        if dig in digests:
            digests[dig]["aliases"].append(dict(submission=r["submission"], score=r["score"]))
            continue
        row = L.design_row(a, active, bins, NB)
        rec = dict(site=r["site"], submission=r["submission"], score=r["score"], digest=dig, N=row["N"], dots=row["dots"],
                   aliases=[])
        digests[dig] = rec; rows.append(row); meta.append(rec)
        print(f"design {len(rows):3d} {r['submission'][:50]:50s} s={r['score']:.4f} N={row['N']:.0f} t={time.time()-t0:.0f}s", flush=True)
    s = np.array([np.mean([m["score"]] + [al["score"] for al in m["aliases"]]) for m in meta])
    np.savez_compressed(W / "design.npz", A=np.stack([r["A"] for r in rows]), B=np.stack([r["B"] for r in rows]),
                        N=np.array([r["N"] for r in rows]), s=s, S=L.sizes(bins, NB), names=np.array(names))
    json.dump(meta, open(W / "design_meta.json", "w"), indent=1)
    print("done", len(rows), "unique ledger rasters", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
