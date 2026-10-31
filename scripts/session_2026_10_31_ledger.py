#!/usr/bin/env python3
"""Measure which spatial targets the public leaderboard rewards.

Session 2026-10-31 (branch arena/69eaf63d-wbggemsdoe3).  Companion to
`session_2026_10_31_targets.py`.

Method
------
For every rasters in the hash-pinned sibling ledger (118 files, owner-reported
scores, `registry/upstream_live_ledger_rasters.json`) and every candidate target
map T we compute two numbers:

    mean_credit_T(P) = sum_x p(x) k(d(x,T)) / sum_x p(x)      (value-weighted)
    lift_T(P)        = mean_credit_T(P) - mean_{footprint} k(d(x,T))

where k is the official triangular kernel with 300 m support.  We then regress
the owner-reported score on those lifts plus dot-count/spacing controls.

The regression is a MEASUREMENT of what the public board rewards.  It uses only
the *support* of each sibling raster (a measurement operator), never its values,
and never a copied prediction.  Scores are OWNER-REPORTED: no organizer receipt
exists, so every downstream quantity inherits that status.

Outputs: data/work/ledger_covariates_2026_10_31.{npz,json}
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
LEDGER = ROOT / "data" / "ledger"


def load_pins():
    rows = json.loads((ROOT / "registry/upstream_live_ledger_rasters.json").read_text())["rows"]
    rows = [r for r in rows if r.get("status") == "ok"]
    idx = json.loads((LEDGER / "index.json").read_text())
    by_name = {r["submission"]: r for r in idx if r.get("status") == "verified"}
    out = []
    for r in rows:
        rec = by_name.get(r["submission"])
        if rec and rec.get("local"):
            out.append(dict(site=r["site"], submission=r["submission"], score=float(r["score"]),
                            path=ROOT / rec["local"], sha256=r["sha256"]))
    return out


def main() -> int:
    z = np.load(WORK / "targets_2026_10_31.npz")
    footprint = z["footprint"]
    catalogue = z["catalogue"]
    d_cat = z["d_catalogue"]
    tnames = [k[2:] for k in z.files if k.startswith("k_")]
    fp_idx = np.flatnonzero(footprint.ravel())
    fp_mean = {t: float(z["k_" + t].ravel()[fp_idx].mean()) for t in tnames}
    cat_arr = catalogue.ravel()
    dcat_fp = d_cat.ravel()[fp_idx]

    pins = load_pins()
    rows = []
    covs = []
    for p in pins:
        with rasterio.open(p["path"]) as src:
            a = src.read(1).astype(np.float32)
        if a.shape != footprint.shape:
            print(f"SKIP shape {p['submission']} {a.shape}")
            continue
        a = np.where(footprint, a, 0.0)
        a[~np.isfinite(a)] = 0.0
        w = a.ravel()
        mass = float(w.sum())
        nz = np.flatnonzero(w > 0)
        if nz.size == 0:
            continue
        ww = w[nz]
        rec = dict(site=p["site"], submission=p["submission"], score=p["score"],
                   sha256=p["sha256"], n_dots=int(nz.size), mass=mass,
                   mean_value=float(mass / nz.size))
        # spacing: how many dots sit within 3 px of another dot
        dots = np.zeros(w.size, np.float32)
        dots[nz] = 1.0
        nb = ndi.uniform_filter(dots.reshape(footprint.shape), size=7, mode="constant") * 49.0
        rec["mean_dots_within_3px"] = float(nb.reshape(-1)[nz].mean())
        rec["fraction_on_catalogue"] = float(ww[cat_arr[nz]].sum() / mass)
        rec["mean_dist_to_catalogue_px"] = float((d_cat.ravel()[nz] * ww).sum() / mass)
        for t in tnames:
            k = z["k_" + t].ravel()[nz]
            c = float((k * ww).sum() / mass)
            rec["credit_" + t] = c
            rec["lift_" + t] = c - fp_mean[t]
        rows.append(rec)
        covs.append(rec)
        print(f"  {p['site']:12s} {p['submission'][:46]:46s} score {p['score']:.4f} dots {nz.size:>7,}")

    out = WORK / "ledger_covariates_2026_10_31.json"
    out.write_text(json.dumps(dict(
        session="2026-10-31",
        evidence_class="OWNER-REPORTED scores + measured raster covariates (no organizer receipt)",
        n_rasters=len(covs),
        footprint_cells=int(footprint.sum()),
        target_footprint_mean_credit=fp_mean,
        rows=covs), indent=1))
    print(f"\nwrote {out} with {len(covs)} rasters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
