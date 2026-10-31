#!/usr/bin/env python3
"""Which distance-to-catalogue band does the public leaderboard reward?

Session 2026-10-31.  Motivation: the single strongest univariate correlation in
the 118-raster ledger is between the owner-reported score and the mean distance
from the dots to the PUBLIC fault catalogue (Spearman +0.256; top-25 scorers sit
25.4 px from it, bottom-25 at 15.4 px, footprint average 30.8 px).  A new fault
cannot be a mapped fault, so mass spent near the mapped network is mass that
cannot earn true-positive credit.  This script measures the reward by BAND so
the catalogue buffer can be chosen on evidence instead of by habit.

Method: for every ledger raster compute the fraction of its emitted mass in each
distance-to-catalogue band (and, separately, in bands of distance to the SGMC
structures that are absent from the public catalogue).  Ridge-regress the
owner-reported score on the band fractions (one band dropped for the simplex
constraint) plus a dot-count control, with site-grouped cross-validation, and
bootstrap the coefficients.

Evidence class: ESTIMATE from OWNER-REPORTED scores.  Not HOLDOUT-DTI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
LEDGER = ROOT / "data" / "ledger"
sys.path.insert(0, str(ROOT / "scripts"))

BANDS = (0.0, 1.5, 3.0, 6.0, 12.0, 25.0, 50.0, 1e9)
BAND_LABELS = ["0-1.5", "1.5-3", "3-6", "6-12", "12-25", "25-50", ">50"]


def band_fractions(mass_by_band: np.ndarray) -> np.ndarray:
    s = mass_by_band.sum()
    return mass_by_band / s if s > 0 else mass_by_band


def measure_bands(path: Path, footprint, d_cat, d_sgmc) -> dict:
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
    a = np.where(footprint & np.isfinite(a), a, 0.0)
    w = a.ravel()
    nz = np.flatnonzero(w > 0)
    if nz.size == 0:
        raise ValueError("empty")
    ww = w[nz].astype(np.float64)
    mass = ww.sum()
    dc = d_cat.ravel()[nz].astype(np.float64)
    ds = d_sgmc.ravel()[nz].astype(np.float64)
    cat_bands = np.zeros(len(BANDS) - 1)
    sgmc_bands = np.zeros(len(BANDS) - 1)
    for i in range(len(BANDS) - 1):
        m = (dc >= BANDS[i]) & (dc < BANDS[i + 1])
        cat_bands[i] = ww[m].sum() / mass
        m2 = (ds >= BANDS[i]) & (ds < BANDS[i + 1])
        sgmc_bands[i] = ww[m2].sum() / mass
    return dict(n_dots=int(nz.size), mass=float(mass),
                cat_bands=cat_bands.tolist(), sgmc_bands=sgmc_bands.tolist())


def ridge(X, y, lam):
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * lam
    P[0, 0] = 0.0
    return np.linalg.solve(Xb.T @ Xb + P, Xb.T @ y)


def stdz(X):
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return (X - mu) / sd, mu, sd


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    z = np.load(WORK / "targets_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    with rasterio.open(ROOT / "data" / "raw" / "external" /
                       "derived_sgmc_faults_100m_u8.tif") as src:
        sgmc = (src.read(1) > 0) & footprint
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    d_sgmc = ndi.distance_transform_edt(~sgmc).astype(np.float32)

    idx = json.loads((LEDGER / "index.json").read_text())
    pins = json.loads((ROOT / "registry/upstream_live_ledger_rasters.json").read_text())["rows"]
    score_of = {r["submission"]: float(r["score"]) for r in pins}
    rows = []
    for r in idx:
        if r.get("status") != "verified" or not r.get("local"):
            continue
        m = measure_bands(ROOT / r["local"], footprint, d_cat, d_sgmc)
        m["score"] = score_of.get(r["submission"])
        m["site"] = r["site"]
        m["name"] = Path(r["path"]).name
        rows.append(m)
    rows = [r for r in rows if r["score"] is not None]
    print(f"measured {len(rows)} ledger rasters")

    y = np.array([r["score"] for r in rows])
    names = [f"cat[{BAND_LABELS[i]}]" for i in range(len(BAND_LABELS) - 1)] + \
            [f"sgmc[{BAND_LABELS[i]}]" for i in range(1, len(BAND_LABELS))] + ["log_n_dots"]
    X = np.array([[*r["cat_bands"][:-1], *r["sgmc_bands"][1:], np.log(r["n_dots"])]
                  for r in rows], float)
    sites = np.array([r["site"] for r in rows])
    Xs, mu, sd = stdz(X)

    # site-grouped CV over lambda
    ug = np.unique(sites)
    rng = np.random.default_rng(7)
    perm = rng.permutation(len(ug))
    fold_of = {g: i % 6 for i, g in enumerate(ug[perm])}
    gf = np.array([fold_of[s] for s in sites])
    best = None
    for lam in np.geomspace(1e-2, 1e3, 30):
        pred = np.zeros_like(y)
        for f in range(6):
            tr, te = gf != f, gf == f
            Xtr, m, d = stdz(X[tr])
            b = ridge(Xtr, y[tr], lam)
            pred[te] = np.hstack([np.ones((te.sum(), 1)), (X[te] - m) / d]) @ b
        mae = float(np.abs(pred - y).mean())
        if best is None or mae < best[0]:
            best = (mae, lam, spearman(pred, y))
    print(f"site-grouped CV: MAE {best[0]:.4f}  lambda {best[1]:.3g}  Spearman {best[2]:+.3f}")
    b = ridge(Xs, y, best[1])
    boots = []
    for _ in range(400):
        i = rng.integers(0, len(y), len(y))
        boots.append(ridge(Xs[i], y[i], best[1])[1:])
    boots = np.array(boots)
    lo, hi = np.quantile(boots, [0.025, 0.975], axis=0)
    print(f"\n{'band':16s} {'beta':>8s} {'95% CI':>24s}")
    for i, n in enumerate(names):
        star = "*" if (lo[i] > 0) == (hi[i] > 0) else " "
        print(f"  {n:14s} {b[1+i]:+8.4f}  [{lo[i]:+.4f}, {hi[i]:+.4f}] {star}")

    diag = json.loads((WORK / "candidate_2026_10_31.json").read_text())
    cand = measure_bands(ROOT / "submission" / diag["file"], footprint, d_cat, d_sgmc)
    print("\ncandidate catalogue-distance band fractions:")
    for lab, v in zip(BAND_LABELS, cand["cat_bands"]):
        print(f"   {lab:6s} {v:.3f}")
    med = {lab: float(np.median([r["cat_bands"][i] for r in rows]))
           for i, lab in enumerate(BAND_LABELS)}
    top = sorted(rows, key=lambda r: -r["score"])[:20]
    med_top = {lab: float(np.median([r["cat_bands"][i] for r in top]))
               for i, lab in enumerate(BAND_LABELS)}
    print("\nband fractions: all-118 median vs top-20 median vs candidate")
    print(f"{'band':8s} {'all':>8s} {'top20':>8s} {'cand':>8s}")
    for lab in BAND_LABELS:
        i = BAND_LABELS.index(lab)
        print(f"{lab:8s} {med[lab]:8.3f} {med_top[lab]:8.3f} {cand['cat_bands'][i]:8.3f}")
    (WORK / "bands_2026_10_31.json").write_text(json.dumps(dict(
        session="2026-10-31", evidence_class="ESTIMATE (owner-reported scores)",
        n=len(rows), cv_mae=best[0], cv_spearman=best[2], lam=best[1],
        coefficients={n: dict(beta=float(b[1 + i]), ci95=[float(lo[i]), float(hi[i])])
                      for i, n in enumerate(names)},
        medians_all=med, medians_top20=med_top, candidate=cand), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
