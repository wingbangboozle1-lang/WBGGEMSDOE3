#!/usr/bin/env python
"""Screen every evidence layer against the withheld-segment holdout (one layer at a time).

This is the leakage/signal canary required by the protocol: a single layer is turned
into dots (top-K within the legal domain) and scored with the verified DTI.  A layer
only counts as evidence if it beats the matched random baseline at the same dot count.

Also emits the *distance profile*: dots placed on a lattice inside successive
distance-to-visible-catalogue bands, which measures where the withheld truth actually
lives relative to the published catalogue.

Usage:
    python scripts/screen_layers.py --fold 0 --topk 40000 --out evidence/newfaults/screen_fold0.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsw import metric                       # noqa: E402
from src.newfaults import data, features, holdout, model  # noqa: E402

FEAT = ROOT / "data" / "work" / "features_f16.npy"


def _score(dots, hidden, active) -> dict:
    d = np.asarray(dots, bool) & active
    g = np.asarray(hidden, bool) & active
    n = int(g.sum())
    if not d.any() or n == 0:
        return {"dti": 0.0, "tp": 0.0, "fp": 0.0, "n_dots": int(d.sum()), "n_truth": n}
    dp = distance_transform_edt(~d)
    tp = float(metric.kernel(dp[g]).sum())
    dg = distance_transform_edt(~g)
    fp = float((1.0 - metric.kernel(dg[d])).sum())
    return {"dti": float(metric.dti(tp, fp, n - tp)), "tp": tp, "fp": fp,
            "n_dots": int(d.sum()), "n_truth": n}


def topk_dots(layer: np.ndarray, allowed: np.ndarray, k: int, min_sep: float = 1.0,
              sign: float = 1.0) -> np.ndarray:
    v = np.where(allowed & np.isfinite(layer), sign * layer.astype(np.float64), -np.inf)
    flat = v.ravel()
    k = min(k, int(np.isfinite(flat).sum()))
    idx = np.argpartition(-flat, k - 1)[:k]
    ys, xs = np.unravel_index(idx, layer.shape)
    dots = np.zeros(layer.shape, bool)
    dots[ys, xs] = True
    if min_sep > 1.0:
        dots = model._greedy_thin(ys, xs, sign * layer[ys, xs], layer.shape, min_sep)
    return dots


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--hide-frac", type=float, default=0.2)
    ap.add_argument("--buffer-px", type=int, default=2)
    ap.add_argument("--topk", type=int, default=40000)
    ap.add_argument("--min-sep", type=float, default=1.0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    shape = lab.shape
    fold = holdout.make_fold(cat, a.fold, hide_frac=a.hide_frac, buffer_px=a.buffer_px)
    active = foot & ~fold.known_mask
    d_vis = distance_transform_edt(~fold.visible)
    legal = active & (d_vis > 3.0)
    print(f"fold {a.fold} {fold.meta}  legal cells {int(legal.sum())}", flush=True)

    out: dict = {"fold": a.fold, "meta": fold.meta, "topk": a.topk, "min_sep": a.min_sep,
                 "legal_cells": int(legal.sum()), "layers": {}, "distance_profile": {}}

    # random baseline at the same dot count inside the legal domain
    rng = np.random.default_rng(1)
    li = np.flatnonzero(legal.ravel())
    pick = rng.choice(li, min(a.topk, li.size), replace=False)
    rnd = np.zeros(shape, bool)
    rnd.ravel()[pick] = True
    out["layers"]["__random_baseline__"] = _score(rnd, fold.hidden, active)
    print("random baseline", out["layers"]["__random_baseline__"], flush=True)

    names = features.feature_plan()
    arr = np.lib.format.open_memmap(FEAT, mode="r")
    for i, (nm, _kind) in enumerate(names):
        layer = np.asarray(arr[i], np.float32)
        for sign, tag in ((1.0, "+"), (-1.0, "-")):
            t0 = time.time()
            dots = topk_dots(layer, legal, a.topk, a.min_sep, sign)
            s = _score(dots, fold.hidden, active)
            s["sign"] = tag
            s["seconds"] = round(time.time() - t0, 2)
            out["layers"][f"{nm}{tag}"] = s
            print(f"  {nm}{tag:1s} DTI {s['dti']:.5f} TP {s['tp']:8.1f} dots {s['n_dots']} ({s['seconds']}s)", flush=True)
    del arr

    # external u8 evidence layers
    ext = {"lidar_scarp": ("lidar_scarp_features_u8.tif", 12),
           "geodawn_rad": ("geodawn_rad_u8.tif", 4),
           "geodawn_ext": ("geodawn_extensions_u8.tif", 4)}
    for fam, (fn, nb) in ext.items():
        for b in range(1, nb + 1):
            layer = data.u8_layer(fn, b)
            for sign, tag in ((1.0, "+"), (-1.0, "-")):
                dots = topk_dots(layer, legal, a.topk, a.min_sep, sign)
                s = _score(dots, fold.hidden, active)
                s["sign"] = tag
                out["layers"][f"{fam}_b{b}{tag}"] = s
                print(f"  {fam}_b{b}{tag} DTI {s['dti']:.5f} TP {s['tp']:8.1f}", flush=True)

    # distance profile: lattice dots inside successive distance-to-visible-catalogue bands
    lattice = np.zeros(shape, bool)
    lattice[::2, ::2] = True
    edges = [3, 5, 8, 12, 18, 28, 45, 70, 10**6]
    lo = 3.0
    for hi in edges:
        band = legal & (d_vis >= lo) & (d_vis < hi)
        dots = lattice & band
        s = _score(dots, fold.hidden, active)
        s["band_px"] = [lo, hi]
        out["distance_profile"][f"{lo:g}-{hi:g}"] = s
        print(f"  band {lo:g}-{hi:g} px: DTI {s['dti']:.5f} TP {s['tp']:8.1f} dots {s['n_dots']}", flush=True)
        lo = hi

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
