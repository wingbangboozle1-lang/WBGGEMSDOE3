#!/usr/bin/env python
"""Corridor / along-strike prior strategy: sweep on a tuning fold, confirm on others.

Two structural priors are built from the *visible* catalogue only:

  * ``kde``  -- isotropic Gaussian corridor density (fault systems are corridors);
  * ``ascp`` -- along-strike continuation prior: the catalogue shifted along its local
    strike at several distances (relay ramps, tip damage zones, en-echelon step-overs).

Emission is a binary dot map on the highest-prior pixels, restricted to the distance
band ``[t_min, t_max]`` from the visible catalogue (the masked band earns nothing and
the far field is nearly uniform), thinned to ``min_sep``.

Protocol: parameters are tuned on ``--tune-fold`` and then reported unchanged on the
confirmation folds.  No leaderboard score is read anywhere in this script.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsw import metric                        # noqa: E402
from src.newfaults import data, features, holdout, model  # noqa: E402


def score_cached(dots, hidden, active, w_truth, n_truth) -> dict:
    d = dots & active
    n_dots = int(d.sum())
    if n_dots == 0 or n_truth == 0:
        return {"dti": 0.0, "tp": 0.0, "fp": 0.0, "n_dots": n_dots}
    fp = float(np.sum(1.0 - w_truth[d]))
    dp = distance_transform_edt(~d)
    tp = float(metric.kernel(dp[hidden & active]).sum())
    return {"dti": float(metric.dti(tp, fp, n_truth - tp)), "tp": tp, "fp": fp, "n_dots": n_dots}


def _n(a: np.ndarray) -> np.ndarray:
    m = float(a.max())
    return a / m if m > 0 else a


def build_priors(fold: holdout.Fold) -> dict[str, np.ndarray]:
    out = {}
    vis = fold.visible
    for s in (10, 24):
        out[f"kde{s}"] = features.corridor_prior(vis, s)
    out["ascp"] = features.along_strike_prior(vis)
    out["offset"] = features.parallel_offset_prior(vis)
    out["ascp_kde24"] = out["ascp"] * (_n(out["kde24"]) + 0.05)
    out["offset_kde24"] = out["offset"] * (_n(out["kde24"]) + 0.05)
    out["offset_ascp"] = out["offset"] * (_n(out["ascp"]) + 0.05)
    out["offset_ascp_kde"] = out["offset"] * (_n(out["ascp"]) + 0.05) * (_n(out["kde24"]) + 0.05)
    return out


def sweep_prior(prior, fold, active, w_truth, n_truth, d_vis,
                t_mins=(2.0, 3.0, 5.0), t_maxes=(12.0, 20.0),
                ks=(200000, 600000, 1200000), seps=(1.0, 2.0, 3.0, 4.0)) -> list[dict]:
    rows = []
    for t_min, t_max in itertools.product(t_mins, t_maxes):
        if t_max <= t_min:
            continue
        legal = active & (d_vis >= t_min) & (d_vis < t_max)
        if not legal.any():
            continue
        v = np.where(legal, prior, -np.inf).ravel()
        order = np.argsort(-v, kind="stable")
        nvalid = int(np.isfinite(v[order]).sum())
        for k in ks:
            kk = min(nvalid, k)
            ys, xs = np.unravel_index(order[:kk], prior.shape)
            for sep in seps:
                dots = model._greedy_thin(ys, xs, prior[ys, xs], prior.shape, sep)
                s = score_cached(dots, fold.hidden, active, w_truth, n_truth)
                s.update({"t_min": float(t_min), "t_max": float(t_max), "k": int(k), "min_sep": float(sep)})
                rows.append(s)
    rows.sort(key=lambda r: -r["dti"])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune-fold", type=int, default=0)
    ap.add_argument("--confirm-folds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    shape = lab.shape
    res: dict = {"tune_fold": a.tune_fold, "confirm_folds": a.confirm_folds,
                 "sweeps": {}, "confirm": {}, "scored": {}}

    def prep(fi):
        fo = holdout.make_fold(cat, fi, hide_frac=0.2, buffer_px=2)
        act = foot & ~fo.known_mask
        dv = distance_transform_edt(~fo.visible)
        wt = metric.kernel(distance_transform_edt(~(fo.hidden & act)))
        nt = int((fo.hidden & act).sum())
        return fo, act, dv, wt, nt

    fold, active, d_vis, w_truth, n_truth = prep(a.tune_fold)
    res["tune_meta"] = fold.meta
    priors = build_priors(fold)
    best = None
    for name, pr in priors.items():
        rows = sweep_prior(pr, fold, active, w_truth, n_truth, d_vis)
        res["sweeps"][name] = rows[:15]
        print(f"{name:12s} best DTI {rows[0]['dti']:.5f} t=[{rows[0]['t_min']:g},{rows[0]['t_max']:g}] "
              f"k={rows[0]['k']} sep={rows[0]['min_sep']} dots={rows[0]['n_dots']} "
              f"TP={rows[0]['tp']:.0f}", flush=True)
        if best is None or rows[0]["dti"] > best[1]["dti"]:
            best = (name, rows[0])
    res["chosen"] = {"prior": best[0], **best[1]}
    print("chosen:", res["chosen"], flush=True)

    for f in a.confirm_folds:
        fo, act, dv, wt, nt = prep(f)
        pr = build_priors(fo)[best[0]]
        legal = act & (dv >= best[1]["t_min"]) & (dv < best[1]["t_max"])
        v = np.where(legal, pr, -np.inf).ravel()
        order = np.argsort(-v, kind="stable")
        ys, xs = np.unravel_index(order[:best[1]["k"]], pr.shape)
        dots = model._greedy_thin(ys, xs, pr[ys, xs], pr.shape, best[1]["min_sep"])
        s = score_cached(dots, fo.hidden, act, wt, nt)
        s["fold"] = f
        s["meta"] = fo.meta
        res["confirm"][f] = s
        res["scored"][f] = dots.sum()
        print(f"confirm fold {f}: DTI {s['dti']:.5f} TP {s['tp']:.1f} FP {s['fp']:.0f} dots {s['n_dots']}",
              flush=True)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, default=float))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
