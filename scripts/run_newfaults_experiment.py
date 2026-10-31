#!/usr/bin/env python
"""Run the new-fault holdout experiments (2026-10-31 lane).

Experiments (each is a *holdout* measurement, never a competition score):

  E0  reference points: zero map, catalogue copy, random dots at the champion dot
      count, and a 3-px ribbon around the visible catalogue (the geometry used by the
      best owner-reported family: dots just outside the catalogue).
  E1  supervised multiscale model (hist gradient boosting) on the 68-channel evidence
      stack + fold-specific distance-to-visible-catalogue; emission sweep over
      threshold quantile and minimum dot separation.
  E2  geothermal-conditioned emission: keep only model dots within a distance of the
      GDR 1391 geothermal evidence (springs >= 30 C, vents), swept over the radius.

Usage
-----
    python scripts/run_newfaults_experiment.py --fold 0 --experiments E0 E1 E2 \
        --out evidence/newfaults/exp_fold0.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsw import metric                                     # noqa: E402
from src.newfaults import data, features, holdout, model          # noqa: E402

FEAT = ROOT / "data" / "work" / "features_f16.npy"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def reference_points(fold, foot, shape, n_champ=37654, seed=5) -> dict:
    """Cheap reference geometries scored on the same holdout."""
    rng = np.random.default_rng(seed)
    out = {}
    active = foot & ~fold.known_mask
    zero = np.zeros(shape, bool)
    out["E0_zero"] = holdout.score_dots(zero, fold.hidden, foot, fold.known_mask)
    # catalogue copy: emit the *visible* catalogue (what "submit the labels" earns once
    # known faults are masked out of the scored domain)
    out["E0_catalogue_copy"] = holdout.score_dots(fold.visible, fold.hidden, foot, fold.known_mask)
    # random dots at the champion dot count
    idx = np.flatnonzero(active.ravel())
    pick = rng.choice(idx, min(n_champ, idx.size), replace=False)
    rnd = np.zeros(shape, bool)
    rnd.ravel()[pick] = True
    out["E0_random_37654"] = holdout.score_dots(rnd, fold.hidden, foot, fold.known_mask)
    # ribbon: dots 3 px outside the visible catalogue, 2.8 px apart (champion geometry family)
    d_vis = distance_transform_edt(~fold.visible)
    ribbon = active & (d_vis > 2.0) & (d_vis <= 4.0)
    ys, xs = np.nonzero(ribbon)
    keep = ((ys.astype(np.int64) * 7919 + xs.astype(np.int64) * 104729) % 3) == 0
    rib = np.zeros(shape, bool)
    rib[ys[keep], xs[keep]] = True
    out["E0_ribbon_2to4px"] = holdout.score_dots(rib, fold.hidden, foot, fold.known_mask)
    out["E0_ribbon_2to4px"]["n_dots"] = int(rib.sum())
    return out


def run_fold(fold_idx: int, hide_frac: float, buffer_px: int, n_pos: int, n_neg: int,
             quantiles: list[float], seps: list[float], geothermal_radii: list[float],
             experiments: list[str], seed: int = 0, max_iter: int = 220) -> dict:
    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    shape = lab.shape
    fold = holdout.make_fold(cat, fold_idx, hide_frac=hide_frac, buffer_px=buffer_px)
    _log(f"fold {fold_idx}: {fold.meta}")

    res: dict = {"fold": fold_idx, "meta": fold.meta, "experiments": {}}

    if "E0" in experiments:
        res["experiments"]["E0"] = reference_points(fold, foot, shape)
        for k, v in res["experiments"]["E0"].items():
            _log(f"  {k}: DTI {v['dti']:.5f} TP {v['tp']:.1f} FP {v['fp']:.0f} n_dots {v.get('n_dots', '')}")

    need_model = ("E1" in experiments) or ("E2" in experiments)
    if not need_model:
        return res

    # ---- training set -------------------------------------------------------------
    t0 = time.time()
    pos_flat = np.flatnonzero((fold.visible).ravel())
    if pos_flat.size > n_pos:
        pos_flat = np.random.default_rng(seed).choice(pos_flat, n_pos, replace=False)
    neg_flat = model.balanced_negative_sample(fold.train_mask, fold.visible, n_neg, seed=seed + 1)
    idx = np.concatenate([pos_flat, neg_flat])
    y = np.concatenate([np.ones(pos_flat.size), np.zeros(neg_flat.size)])

    # fold-specific channel: distance to the *visible* catalogue (available at inference)
    d_vis = np.clip(distance_transform_edt(~fold.visible), 0, 60).astype(np.float32)
    X = model.design(FEAT, idx, shape, extra=[d_vis])
    _log(f"  design matrix {X.shape} in {time.time()-t0:.1f}s  positives={pos_flat.size} negatives={neg_flat.size}")

    t0 = time.time()
    clf = model.fit(X, y, seed=seed, max_iter=max_iter)
    _log(f"  model fitted in {time.time()-t0:.1f}s")
    t0 = time.time()
    prob = model.predict_surface(clf, FEAT, [d_vis], shape)
    _log(f"  surface predicted in {time.time()-t0:.1f}s")

    active = foot & ~fold.known_mask
    if "E1" in experiments:
        sweep = []
        for q in quantiles:
            t1 = time.time()
            cands = model.candidates(prob, active, quantile=q)
            _log(f"  E1 candidates q={q:.4f}: {cands[0].size} px in {time.time()-t1:.1f}s")
            for sep in seps:
                dots = model.select_dots(prob, active, min_sep=sep, cands=cands)
                s = holdout.score_dots(dots, fold.hidden, foot, fold.known_mask)
                s.update({"quantile": q, "min_sep": sep, "n_dots": int(dots.sum()),
                          "n_cand": int(cands[0].size)})
                sweep.append(s)
                _log(f"  E1 q={q:.4f} sep={sep}: DTI {s['dti']:.5f} dots {s['n_dots']} TP {s['tp']:.1f} FP {s['fp']:.0f}")
        res["experiments"]["E1"] = {"sweep": sweep}

    if "E2" in experiments:
        geo = features._geo_points()
        pts = np.concatenate([geo["spring_thermal30"].T, geo["vent"].T], axis=0) if geo["spring_thermal30"].size else geo["vent"].T
        d_geo = features.point_distance(shape, pts[:, 0], pts[:, 1]).astype(np.float32)
        best = max(res.get("experiments", {}).get("E1", {}).get("sweep", [{"quantile": 0.995, "min_sep": 1.0}]),
                   key=lambda r: r["dti"])
        sweep = []
        for rad in geothermal_radii:
            allowed_g = active & (d_geo <= rad)
            dots = model.select_dots(prob, allowed_g, quantile=best["quantile"], min_sep=best["min_sep"])
            s = holdout.score_dots(dots, fold.hidden, foot, fold.known_mask)
            s.update({"quantile": best["quantile"], "min_sep": best["min_sep"],
                      "geothermal_radius_px": rad, "n_dots": int(dots.sum())})
            sweep.append(s)
            _log(f"  E2 radius={rad}: DTI {s['dti']:.5f} dots {s['n_dots']} TP {s['tp']:.1f} FP {s['fp']:.0f}")
        res["experiments"]["E2"] = {"sweep": sweep, "base": {"quantile": best["quantile"], "min_sep": best["min_sep"]}}

    res["prob_stats"] = {"min": float(prob.min()), "max": float(prob.max()),
                         "mean": float(prob.mean()), "p999": float(np.quantile(prob[foot], 0.999))}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--hide-frac", type=float, default=0.2)
    ap.add_argument("--buffer-px", type=int, default=2)
    ap.add_argument("--n-pos", type=int, default=30000)
    ap.add_argument("--n-neg", type=int, default=120000)
    ap.add_argument("--quantiles", type=float, nargs="+", default=[0.99, 0.995, 0.998, 0.999])
    ap.add_argument("--seps", type=float, nargs="+", default=[1.0, 1.5, 2.0, 2.8])
    ap.add_argument("--geothermal-radii", type=float, nargs="+", default=[10, 20, 40, 80])
    ap.add_argument("--experiments", nargs="+", default=["E0", "E1"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-iter", type=int, default=220)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    res = run_fold(a.fold, a.hide_frac, a.buffer_px, a.n_pos, a.n_neg, a.quantiles, a.seps,
                   a.geothermal_radii, a.experiments, a.seed, a.max_iter)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1))
        _log(f"wrote {a.out}")


if __name__ == "__main__":
    main()
