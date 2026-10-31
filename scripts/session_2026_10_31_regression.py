#!/usr/bin/env python3
"""Which targets does the public board reward?  Ridge regression with site-grouped CV.

Session 2026-10-31.  Reads data/work/ledger_covariates_2026_10_31.json.

Evidence class of every number produced here: OWNER-REPORTED scores regressed on
measured raster covariates.  There is no organizer receipt behind any score, so
the coefficients are measurements of an owner-reported ledger, not of the hidden
truth.  Reported as ESTIMATE, never as HOLDOUT-DTI or ORGANIZER-CONFIRMED.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"


def build_matrix(rows, prefix="lift_", controls=("n_dots", "mean_value", "mean_dots_within_3px",
                                                 "mean_dist_to_catalogue_px")):
    keys = [k for k in rows[0] if k.startswith(prefix)]
    others = [c for c in controls if c in rows[0]]
    names = list(others) + keys
    X = np.array([[r[n] for n in names] for r in rows], float)
    y = np.array([r["score"] for r in rows], float)
    return names, X, y


def standardize(X):
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return (X - mu) / sd, mu, sd


def ridge_fit(X, y, lam):
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * lam
    P[0, 0] = 0.0
    beta = np.linalg.solve(Xb.T @ Xb + P, Xb.T @ y)
    return beta


def cv_ridge(X, y, groups, lams, n_fold=6, seed=7):
    ug = np.unique(groups)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(ug))
    folds = {g: i % n_fold for i, g in enumerate(ug[perm])}
    gf = np.array([folds[g] for g in groups])
    best = None
    for lam in lams:
        pred = np.zeros_like(y)
        for f in range(n_fold):
            tr, te = gf != f, gf == f
            if te.sum() == 0:
                continue
            Xtr, _mu, _sd = standardize(X[tr])
            b = ridge_fit(Xtr, y[tr], lam)
            Xte = (X[te] - _mu) / _sd
            pred[te] = np.hstack([np.ones((te.sum(), 1)), Xte]) @ b
        mae = float(np.abs(pred - y).mean())
        rmse = float(np.sqrt(((pred - y) ** 2).mean()))
        if best is None or mae < best["mae"]:
            best = dict(lam=lam, mae=mae, rmse=rmse, pred=pred)
    return best


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    doc = json.loads((WORK / "ledger_covariates_2026_10_31.json").read_text())
    rows = doc["rows"]
    groups = np.array([r["site"] for r in rows])
    lams = np.geomspace(1e-2, 1e4, 40)

    print(f"n rasters = {len(rows)}; n sites = {len(np.unique(groups))}\n")

    # --- univariate screen -------------------------------------------------
    print("Univariate Spearman of owner-reported score vs covariate")
    y = np.array([r["score"] for r in rows])
    screen = []
    for k in rows[0]:
        if k.startswith(("lift_", "credit_")) or k in ("n_dots", "mean_value",
                                                       "mean_dots_within_3px",
                                                       "mean_dist_to_catalogue_px",
                                                       "fraction_on_catalogue", "mass"):
            x = np.array([r[k] for r in rows], float)
            if x.std() < 1e-12:
                continue
            screen.append((abs(spearman(x, y)), spearman(x, y), k))
    screen.sort(reverse=True)
    for a, s, k in screen:
        print(f"  {k:42s} rho = {s:+.3f}")

    # --- multivariate: lifts only -----------------------------------------
    for prefix in ("lift_", "credit_"):
        names, X, y = build_matrix(rows, prefix=prefix)
        Xs, mu, sd = standardize(X)
        best = cv_ridge(Xs, y, groups, lams)
        b = ridge_fit(Xs, y, best["lam"])
        print(f"\n=== {prefix}* ridge (site-grouped 6-fold CV) ===")
        print(f"  lambda* = {best['lam']:.3g}   CV MAE {best['mae']:.4f}  CV RMSE {best['rmse']:.4f}"
              f"  CV Spearman {spearman(best['pred'], y):+.3f}  (in-sample R2 "
              f"{1 - ((np.hstack([np.ones((len(y),1)),Xs])@b - y)**2).sum()/((y-y.mean())**2).sum():.3f})")
        order = np.argsort(-np.abs(b[1:]))
        for i in order:
            print(f"    {names[i]:42s} beta = {b[1+i]:+.4f}")

    # --- bootstrap stability of the lift model ------------------------------
    names, X, y = build_matrix(rows, prefix="lift_")
    Xs, mu, sd = standardize(X)
    best = cv_ridge(Xs, y, groups, lams)
    b_full = ridge_fit(Xs, y, best["lam"])
    rng = np.random.default_rng(11)
    B = []
    for _ in range(400):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(groups[idx])) < 8:
            continue
        B.append(ridge_fit(Xs[idx], y[idx], best["lam"])[1:])
    B = np.array(B)
    lo, hi = np.quantile(B, [0.025, 0.975], axis=0)
    print(f"\nBootstrap (400 resamples) 95% intervals, lambda={best['lam']:.3g}")
    order = np.argsort(-np.abs(b_full[1:]))
    for i in order:
        star = "  *" if (lo[i] > 0) == (hi[i] > 0) else ""
        print(f"    {names[i]:42s} beta {b_full[1+i]:+.4f}  [{lo[i]:+.4f}, {hi[i]:+.4f}]{star}")

    out = dict(session="2026-10-31",
               evidence_class="ESTIMATE (owner-reported scores regressed on measured covariates)",
               n_rasters=len(rows), n_sites=int(len(np.unique(groups))),
               lambda_selected=best["lam"], cv_mae=best["mae"], cv_rmse=best["rmse"],
               cv_spearman=spearman(best["pred"], y),
               coefficients={n: dict(beta=float(b_full[1 + i]),
                                     ci95=[float(lo[i]), float(hi[i])])
                             for i, n in enumerate(names)},
               univariate_spearman={k: float(s) for a, s, k in screen})
    (WORK / "ledger_regression_2026_10_31.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {WORK / 'ledger_regression_2026_10_31.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
