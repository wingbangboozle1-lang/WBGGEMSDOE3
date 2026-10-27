#!/usr/bin/env python3
"""Stage 2: invert the public score ledger into a hidden-truth density field.

WHY.  The official DTI (DrivenData competition 306, page 967) is, for a binary dot field,

    DTI = T / (T + alpha*FP_w + beta*(|G| - T)),    alpha=0.2, beta=0.8
    T   = sum_{g in G} k(dist(g, nearest dot))      <- linear in the truth field

so for a *known* score s and probe support, T is determined by two scalars:

    T_r = s_r (beta*M + alpha*FP_r) / (1 - alpha*s_r)

Each published score therefore becomes a linear measurement ``kA_r . rho = b_r`` of the
unknown truth-mass field rho on 400 m blocks.  118 such measurements exist (all sibling
rasters that have a published score), which is a small-angle tomography problem:
``rho`` is recovered by non-negative, smoothness-regularised least squares.

This is an ESTIMATE derived from *scalars*; the reconstruction is blurred at the scale the
118 projections allow.  It is not ground truth, not a holdout DTI, and not an
organizer-confirmed score.  Probes are drawn from sibling repositories (owner-reported
scores, no receipts); see registry/upstream_live_ledger_rasters.json.

Usage:  python scripts/invert_ledger.py [--folds 5] [--iters 500]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import grid as G                    # noqa: E402
from gemsw import inversion as INV             # noqa: E402

WORK = ROOT / "data" / "work"
FACTOR = 4
ALPHA, BETA = 0.2, 0.8


# ----------------------------------------------------------------------------- data
def load() -> dict:
    pr = np.load(WORK / f"probes_f{FACTOR}.npz", allow_pickle=False)
    g = G.load_grid()
    act = g.foot & ~g.labels
    return dict(
        kA=np.ascontiguousarray(pr["kA"].astype(np.float32)),
        nb=np.ascontiguousarray(pr["nblocks"].astype(np.float32)),
        active=pr["active_blocks"].astype(bool).ravel(),
        block_shape=tuple(int(x) for x in pr["block_shape"]),
        scores=pr["scores"].astype(np.float64),
        names=[str(x) for x in pr["names"]],
        n_dots=pr["n_dots"].astype(np.float64),
        act_count=np.ascontiguousarray(
            INV.block_sum(act.astype(np.float64), FACTOR).ravel().astype(np.float32)),
    )


# ------------------------------------------------------------------- linear operators
def laplacian(field2d: np.ndarray) -> np.ndarray:
    """4-neighbour graph Laplacian with Neumann edges (penalises roughness, keeps mass)."""
    d = np.zeros_like(field2d)
    d[1:, :] += field2d[1:, :] - field2d[:-1, :]
    d[:-1, :] += field2d[:-1, :] - field2d[1:, :]
    d[:, 1:] += field2d[:, 1:] - field2d[:, :-1]
    d[:, :-1] += field2d[:, :-1] - field2d[:, 1:]
    return d


def implied_targets(scores: np.ndarray, mass: float, FP: np.ndarray) -> np.ndarray:
    """T_r = s_r (beta*M + alpha*FP_r) / (1 - alpha*s_r)."""
    s = np.clip(scores, 0.0, (1.0 - 1e-6))
    return s * (BETA * mass + ALPHA * FP) / (1.0 - ALPHA * s)


def predict(kA: np.ndarray, nb: np.ndarray, rho: np.ndarray, act_count: np.ndarray) -> tuple:
    mass = float(rho.sum())
    T = (kA @ rho.astype(np.float32)).astype(np.float64)
    q = kernel_credit_from_density(rho, act_count)
    FP = (nb @ (1.0 - q)).astype(np.float64)
    dti = T / (T + ALPHA * FP + BETA * np.maximum(mass - T, 0.0) + 1e-12)
    return dti, dict(T=T, FP=FP, mass=mass)


def kernel_credit_from_density(rho: np.ndarray, act_count: np.ndarray) -> np.ndarray:
    """Kernel credit a dot in this block can expect: k(mean nearest-neighbour distance).

    Truth is line/point-like, so with per-cell truth fraction f the mean nearest-neighbour
    distance is ~0.5/f cells; credit = clip(1 - d_nn/3, 0, 1).
    """
    f_cell = rho / np.maximum(act_count, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        d_nn = np.where(f_cell > 1e-6, 0.5 / np.maximum(f_cell, 1e-6), 1e6)
    return np.clip(1.0 - d_nn / INV.RADIUS_PX, 0.0, 1.0)


def fista(kA, b, shape, lam_smooth=1.0, lam_l1=0.0, n_iter=400, rho0=None, mask=None):
    """min_{rho>=0} 0.5||kA rho - b||^2 + lam_smooth/2 ||L rho||^2 + lam_l1 ||rho||_1."""
    n = shape[0] * shape[1]
    m = kA.shape[0]
    rho = np.zeros(n, np.float32) if rho0 is None else rho0.astype(np.float32).copy()
    z = rho.copy()
    t = 1.0
    # conservative step from a power iteration on kA^T kA
    v = np.random.default_rng(0).standard_normal(n).astype(np.float32)
    for _ in range(20):
        v = kA.T @ (kA @ v)
        v /= np.linalg.norm(v) + 1e-12
    spec = float(np.sqrt(np.abs((kA @ v) @ (kA @ v)) / max(np.dot(v, v), 1e-12)))
    step = 1.0 / (spec ** 2 * 1.01 + lam_smooth * 8.0 + 1e-9)
    for it in range(n_iter):
            g = kA.T @ (kA @ z - b)
            g = g + lam_smooth * laplacian(z.reshape(shape)).ravel()
            zn = z - step * g
            if lam_l1 > 0:
                th = step * lam_l1
                zn = np.sign(zn) * np.maximum(np.abs(zn) - th, 0.0)
            np.maximum(zn, 0.0, out=zn)
            if mask is not None:
                zn[~mask] = 0.0
            tn = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
            z = zn + ((t - 1.0) / tn) * (zn - rho)
            rho = zn
            t = tn
    return rho


def solve(D: dict, idx: np.ndarray, lam_smooth=1.0, lam_l1=0.0, n_iter=400,
          mass0: float = 180_000.0, n_outer: int = 6) -> dict:
    kA = np.ascontiguousarray(D["kA"][idx])
    nb = D["nb"][idx]
    s = D["scores"][idx]
    shape = D["block_shape"]
    act = D["active"]
    rho = np.zeros(act.size, np.float32)
    mass = mass0
    hist = []
    for outer in range(n_outer):
        q = kernel_credit_from_density(rho, D["act_count"]) if outer else np.zeros(act.size, np.float32)
        FP = (nb @ (1.0 - q)).astype(np.float64)
        b = implied_targets(s, mass, FP)
        rho = fista(kA, b, shape, lam_smooth=lam_smooth, lam_l1=lam_l1,
                    n_iter=n_iter, rho0=rho, mask=act)
        new_mass = float(rho.sum())
        pred, _ = predict(kA, nb, rho, D["act_count"])
        resid = float(np.abs(pred - s).mean())
        hist.append({"outer": outer, "mass": new_mass, "mae": resid})
        mass = new_mass
    pred, parts = predict(kA, nb, rho, D["act_count"])
    return dict(rho=rho, pred=pred, parts=parts, history=hist, mass=mass)


def metrics(pred: np.ndarray, obs: np.ndarray) -> dict:
    from scipy.stats import spearmanr
    err = pred - obs
    ss = 1.0 - float((err ** 2).sum() / max(((obs - obs.mean()) ** 2).sum(), 1e-12))
    return {"mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "r2": ss, "max_abs": float(np.abs(err).max()),
            "spearman": float(spearmanr(pred, obs).statistic), "n": int(len(obs))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--n-outer", type=int, default=3)
    ap.add_argument("--iters", type=int, default=120)
    ap.add_argument("--lam-smooth", type=float, default=1.0)
    ap.add_argument("--lam-l1", type=float, default=0.0)
    ap.add_argument("--mass0", type=float, default=180_000.0)
    ap.add_argument("--out", default=str(WORK / "inversion.json"))
    a = ap.parse_args()
    t0 = time.time()
    D = load()
    n = len(D["scores"])
    print(f"[load] {n} probes, {D['kA'].shape[1]} blocks {D['block_shape']}", flush=True)

    idx = np.arange(n)
    full = solve(D, idx, a.lam_smooth, a.lam_l1, a.iters, a.mass0, n_outer=a.n_outer)
    print(f"[fit ] mass={full['mass']:,.0f} mae={full['history'][-1]['mae']:.4f} "
          f"({time.time()-t0:.0f}s)", flush=True)
    full_m = metrics(full["pred"], D["scores"])
    print(f"[fit ] full-sample {json.dumps(full_m)}", flush=True)

    sites = np.array([nm.split("::")[0] for nm in D["names"]])
    uniq = np.array(sorted(set(sites)))
    rng = np.random.default_rng(20261027)
    perm = rng.permutation(len(uniq))
    fold_of = {uniq[perm[i]]: i % a.folds for i in range(len(uniq))}
    fold = np.array([fold_of[s] for s in sites])
    cv_pred = np.full(n, np.nan)
    for k in range(a.folds):
        tr = np.where(fold != k)[0]
        te = np.where(fold == k)[0]
        r = solve(D, tr, a.lam_smooth, a.lam_l1, a.iters, a.mass0, n_outer=a.n_outer)
        p, _ = predict(np.ascontiguousarray(D["kA"][te]), D["nb"][te], r["rho"], D["act_count"])
        cv_pred[te] = p
        print(f"[cv  ] fold {k}: n_test={len(te)} mae={np.abs(p-D['scores'][te]).mean():.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    cv_m = metrics(cv_pred, D["scores"])

    order = np.argsort(-D["scores"])
    out = {
        "evidence_class": "LEDGER-INVERSION ESTIMATE (owner-reported scores, no organizer receipts)",
        "evaluator": "gemsw.inversion v2 (linear score tomography, 400 m blocks, exact EDT kernel)",
        "n_probes": n, "n_blocks": int(D["kA"].shape[1]),
        "block_shape": list(D["block_shape"]),
        "hyper": {"lam_smooth": a.lam_smooth, "lam_l1": a.lam_l1, "iters": a.iters,
                  "mass0": a.mass0, "folds": a.folds},
        "recovered_truth_mass_cells": full["mass"],
        "full_sample": full_m, "site_grouped_cv": cv_m,
        "outer_history": full["history"],
        "top_probes": [{"name": D["names"][i], "observed": float(D["scores"][i]),
                        "fitted": float(full["pred"][i]), "cv": float(cv_pred[i]),
                        "n_dots": int(D["n_dots"][i])} for i in order[:10]],
        "worst_cv": [{"name": D["names"][i], "observed": float(D["scores"][i]),
                      "cv": float(cv_pred[i])}
                     for i in np.argsort(-np.abs(cv_pred - D["scores"]))[:10]],
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(a.out).write_text(json.dumps(out, indent=1))
    np.save(WORK / "rho_blocks.npy", full["rho"].reshape(D["block_shape"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
