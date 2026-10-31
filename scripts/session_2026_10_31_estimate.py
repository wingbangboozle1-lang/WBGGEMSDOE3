#!/usr/bin/env python3
"""Estimate the leaderboard score of any raster from the owner-reported ledger.

Session 2026-10-31.  Two independent estimators, both trained on the 118
hash-pinned sibling rasters whose scores are OWNER-REPORTED (no organizer
receipt exists for any of them):

  E1  covariate ridge: score ~ lifts of the official 300 m kernel credit against
      24 candidate target maps + dot-count/spacing controls.  Site-grouped
      6-fold CV.
  E2  calibrated E1: leave-one-site-out predictions regressed on the observed
      score, which removes the systematic bias of E1 at the top of the range and
      gives an honest residual spread.

Both are ESTIMATES.  They are not HOLDOUT-DTI and not ORGANIZER-CONFIRMED.  The
reported interval is the residual standard deviation of the leave-one-site-out
calibration, which is the honest error scale for a raster from a new design.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
CONTROLS = ("n_dots", "mean_value", "mean_dots_within_3px", "mean_dist_to_catalogue_px")


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def ridge_fit(X, y, lam):
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * lam
    P[0, 0] = 0.0
    return np.linalg.solve(Xb.T @ Xb + P, Xb.T @ y)


def standardize(X):
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return (X - mu) / sd, mu, sd


def measure(path: Path, z, footprint, catalogue, fp_idx, tnames, fp_mean) -> dict:
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
    a = np.where(footprint & np.isfinite(a), a, 0.0)
    w = a.ravel()
    nz = np.flatnonzero(w > 0)
    if nz.size == 0:
        raise ValueError("empty emission")
    ww = w[nz]
    mass = float(ww.sum())
    dots = np.zeros(w.size, np.float32)
    dots[nz] = 1.0
    nb = ndi.uniform_filter(dots.reshape(footprint.shape), size=7, mode="constant") * 49.0
    rec = dict(n_dots=int(nz.size), mass=mass, mean_value=float(mass / nz.size),
               mean_dots_within_3px=float(nb.reshape(-1)[nz].mean()),
               mean_dist_to_catalogue_px=float(
                   (ndi.distance_transform_edt(~catalogue).ravel()[nz] * ww).sum() / mass))
    for t in tnames:
        k = z["k_" + t].ravel()[nz]
        c = float((k * ww).sum() / mass)
        rec["lift_" + t] = c - fp_mean[t]
    return rec


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", action="append", default=[],
                    help="LABEL=PATH to score an additional raster with the same estimator")
    ap.add_argument("--out", default=None, help="write the record here instead of data/work")
    a = ap.parse_args()
    doc = json.loads((WORK / "ledger_covariates_2026_10_31.json").read_text())
    rows = doc["rows"]
    fp_mean = doc["target_footprint_mean_credit"]
    tnames = sorted(fp_mean)
    names = list(CONTROLS) + ["lift_" + t for t in tnames]
    X = np.array([[r[n] for n in names] for r in rows], float)
    y = np.array([r["score"] for r in rows], float)
    sites = np.array([r["site"] for r in rows])
    Xs, mu, sd = standardize(X)

    lam = 0.0838  # selected by site-grouped 6-fold CV (scripts/session_2026_10_31_regression.py)
    # leave-one-site-out predictions
    loo = np.zeros(len(y))
    for s in np.unique(sites):
        tr = sites != s
        te = sites == s
        Xtr, m, d = standardize(X[tr])
        b = ridge_fit(Xtr, y[tr], lam)
        loo[te] = np.hstack([np.ones((te.sum(), 1)), (X[te] - m) / d]) @ b
    cal_a, cal_b = np.polyfit(loo, y, 1)
    resid = y - (cal_a * loo + cal_b)
    sd_res = float(resid.std(ddof=2))
    print(f"E1 site-grouped LOO: MAE {np.abs(loo - y).mean():.4f} Spearman {spearman(loo, y):+.3f}")
    print(f"E2 calibrated LOO:   MAE {np.abs(resid).mean():.4f} Spearman "
          f"{spearman(cal_a * loo + cal_b, y):+.3f}  residual SD {sd_res:.4f}")
    print(f"    calibration: observed = {cal_a:.4f} * E1 + {cal_b:+.4f}")

    b_full = ridge_fit(Xs, y, lam)

    z = np.load(WORK / "targets_2026_10_31.npz")
    footprint = z["footprint"]
    catalogue = z["catalogue"]
    fp_idx = np.flatnonzero(footprint.ravel())

    targets = []
    diag = json.loads((WORK / "candidate_2026_10_31.json").read_text())
    targets.append(("CANDIDATE-2026-10-31 (floor 0.30, 35,235 dots)",
                    ROOT / "submission" / diag["file"], None))
    # the nine focus sites, best-scoring entry per site
    focus_sites = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                   "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    for r in sorted(rows, key=lambda r: -r["score"]):
        if r["site"] in focus_sites and not any(r["site"] == t[0] for t in targets):
            targets.append((r["site"], None, r))
    for spec in a.extra:
        label, path = spec.split("=", 1)
        targets.append((label, Path(path), None))
    out_rows = []
    for label, path, rec in targets:
        if rec is None:
            rec = measure(path, z, footprint, catalogue, fp_idx, tnames, fp_mean)
        x = np.array([[rec[n] for n in names]], float)
        e1 = float(np.ravel(np.hstack([np.ones((1, 1)), (x - mu) / sd]) @ b_full)[0])
        est = float(cal_a * e1 + cal_b)
        out_rows.append(dict(label=label, n_dots=rec["n_dots"],
                             mean_value=round(rec["mean_value"], 4),
                             owner_reported=None if path else rec.get("score"),
                             e1_raw=round(e1, 4),
                             estimate=round(max(est, 0.0), 4),
                             interval=[round(max(est - 1.96 * sd_res, 0.0), 4),
                                       round(est + 1.96 * sd_res, 4)]))
        print(f"  {label:44s} n={rec['n_dots']:>7,}  E1 {e1:.4f} -> estimate "
              f"{max(est,0):.4f} [{max(est-1.96*sd_res,0):.4f}, {est+1.96*sd_res:.4f}]"
              + (f"   (owner-reported {rec.get('score')})" if not path else ""))
    out_path = Path(a.out) if a.out else (WORK / "score_estimate_2026_10_31.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dict(
        session="2026-10-31",
        evidence_class="ESTIMATE from owner-reported scores (no organizer receipt)",
        estimator="site-grouped ridge on measured kernel-credit covariates, "
                  "leave-one-site-out calibrated",
        lambda_ridge=lam, n_train=len(rows),
        loo_mae=float(np.abs(resid).mean()), loo_spearman=spearman(cal_a * loo + cal_b, y),
        residual_sd=sd_res, calibration=[float(cal_a), float(cal_b)],
        rows=out_rows), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
