#!/usr/bin/env python
"""Final HOLDOUT-DTI measurement for the shipped submission geometry, with 95 % CI.

Runs the exact shipped configuration (corridor KDE sigma 24 px, band 3 <= d_vis < 12 px,
4 px greedy separation) on three independent hide-and-recover folds.  On each fold the
prior is rebuilt from that fold's *visible* catalogue only, so no hidden pixel enters
the prediction.  Also reports the two reference geometries measured on the same folds
(matched random dots and the best owner-reported focus file) for scale.

Every number emitted here is a HOLDOUT-DTI (evaluator = src/gemsw/metric.py, alpha 0.2,
beta 0.8, R = 3 px), never a competition score.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsw import metric                        # noqa: E402
from src.newfaults import data, features, holdout, model  # noqa: E402

CFG = dict(sigma=24.0, t_min=3.0, t_max=12.0, min_sep=4.0)


def emit(fold: holdout.Fold, cfg=CFG) -> np.ndarray:
    d_vis = distance_transform_edt(~fold.visible)
    prior = features.corridor_prior(fold.visible, cfg["sigma"])
    # NOTE: the emission domain must NOT be intersected with fold.train_mask.  That mask
    # is a 3-px collar around the withheld segments used to keep training samples away
    # from hidden truth; intersecting it would forbid every dot within 3 px of the
    # withheld pixels and silently zero the measured DTI (fixed 2026-10-31).
    legal = (d_vis >= cfg["t_min"]) & (d_vis < cfg["t_max"])
    v = np.where(legal, prior, -np.inf).ravel()
    order = np.argsort(-v, kind="stable")
    n = int(np.isfinite(v[order]).sum())
    ys, xs = np.unravel_index(order[:n], prior.shape)
    return model._greedy_thin(ys, xs, prior[ys, xs], prior.shape, cfg["min_sep"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    rng = np.random.default_rng(4)
    with rasterio.open(ROOT / "data" / "compare" / "GEMSDOE25.tif") as ds:
        best_focus = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0) > 0

    rows = []
    for f in a.folds:
        fold = holdout.make_fold(cat, f, hide_frac=0.2, buffer_px=2)
        active = foot & ~fold.known_mask
        dots = emit(fold) & active
        dec = holdout.decompose(dots, fold.hidden, active)
        boot = holdout.block_bootstrap_dti(dec, lab.shape, block=256, n_boot=300)
        # matched random baseline at the same dot count
        li = np.flatnonzero(active.ravel())
        pick = rng.choice(li, int(dots.sum()), replace=False)
        rnd = np.zeros(lab.shape, bool)
        rnd.ravel()[pick] = True
        dec_r = holdout.decompose(rnd, fold.hidden, active)
        dec_f = holdout.decompose(best_focus, fold.hidden, active)
        pair_r = holdout.paired_bootstrap_delta(dec, dec_r, lab.shape, block=256, n_boot=300)
        pair_f = holdout.paired_bootstrap_delta(dec, dec_f, lab.shape, block=256, n_boot=300)
        row = {
            "fold": f, "meta": fold.meta,
            "corridor": {"dti": dec["dti"], "ci95": boot["ci95"], "tp": dec["tp"], "fp": dec["fp"],
                         "n_dots": dec["n_dots"], "n_truth": dec["n_truth"],
                         "recall": dec["tp"] / dec["n_truth"]},
            "random_matched": {"dti": dec_r["dti"], "tp": dec_r["tp"], "fp": dec_r["fp"],
                               "n_dots": dec_r["n_dots"]},
            "focus_GEMSDOE25_d2_8": {"dti": dec_f["dti"], "tp": dec_f["tp"], "fp": dec_f["fp"],
                                     "n_dots": dec_f["n_dots"]},
            "paired_delta_vs_random": pair_r,
            "paired_delta_vs_focus": pair_f,
        }
        rows.append(row)
        print(f"fold {f}: corridor DTI {dec['dti']:.5f} CI {boot['ci95']} | "
              f"random {dec_r['dti']:.5f} | focus d2-8 {dec_f['dti']:.5f} | "
              f"paired-vs-random {pair_r['delta']:+.5f} CI {pair_r['ci95']} | "
              f"paired-vs-focus {pair_f['delta']:+.5f} CI {pair_f['ci95']}", flush=True)

    pooled = {
        "dti_mean": float(np.mean([r["corridor"]["dti"] for r in rows])),
        "dti_min": float(np.min([r["corridor"]["dti"] for r in rows])),
        "dti_max": float(np.max([r["corridor"]["dti"] for r in rows])),
        "ci95_per_fold": [r["corridor"]["ci95"] for r in rows],
        "n_folds": len(rows),
        "withheld_positives_total": int(sum(r["corridor"]["n_truth"] for r in rows)),
        "withheld_positives_per_fold": [int(r["corridor"]["n_truth"]) for r in rows],
        "paired_delta_vs_random_ci95_per_fold": [r["paired_delta_vs_random"]["ci95"] for r in rows],
        "paired_delta_vs_best_focus_ci95_per_fold": [r["paired_delta_vs_focus"]["ci95"] for r in rows],
        "paired_delta_min_lower_bound": float(min(
            min(r["paired_delta_vs_random"]["ci95"][0], r["paired_delta_vs_focus"]["ci95"][0])
            for r in rows)),
        "n_dots": int(rows[0]["corridor"]["n_dots"]),
    }
    out = {"evaluator": "src/gemsw/metric.py dti_binary (alpha 0.2, beta 0.8, R=3 px)",
           "config": CFG, "folds": rows, "pooled": pooled,
           "evaluator_version": "gemsw.metric.dti_binary alpha=0.2 beta=0.8 R=3px (2026-10-31 build)",
           "fold_local_catalogue_features": True,
           "matched_incumbent_folds": True,
           "label": "HOLDOUT-DTI: hide-and-recover, 20 % of catalogue segments withheld, "
                    "2 px buffer, visible catalogue masked as known"}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(pooled, indent=1))


if __name__ == "__main__":
    main()
