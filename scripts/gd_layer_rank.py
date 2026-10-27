#!/usr/bin/env python3
"""Per-layer ranking on the external-catalogue proxy.

For each of the 76 cached features (and each 2 m LiDAR channel), take the top-N cells by
absolute deviation from the footprint median (two-polarity, so a channel is never penalised
for sign), then measure how much of the external proxy that support captures:

    h         = kernel-weighted hit rate   (credit per unit of mass)
    DTI_proxy = the official metric with the proxy as truth

The point is to rank *families*, so the protocol's hypothesis order is decided by
measurement rather than by intuition. Output: evidence/layer_ranking.json

Run: .venv/bin/python scripts/gd_layer_rank.py [N] [--lidar]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsdoe import config as C      # noqa: E402
from src.gemsdoe import io as gio        # noqa: E402
from src.gemsdoe import validation as V  # noqa: E402

LIDAR_TIF = C.ROOT / ".cache" / "upstream" / "x24" / "data" / "external" / "lidar_scarp_features_u8.tif"
LIDAR_META = LIDAR_TIF.parent / "lidar_scarp_features.json"
# geomorphic channels only; 'strike' is circular and 'valid' is a coverage mask, so both are
# excluded from a two-polarity ranking (they would be meaningless, not merely weak).
LIDAR_SKIP = {"strike", "valid"}

FAMILY = {
    "mag": "magnetic", "rtp": "magnetic", "tmi": "magnetic",
    "iso_grav": "gravity",
    "depth": "depth-to-basement",
    "cond": "conductivity",
    "tc": "thermal-conductivity",
    "de_": "detrended topo", "det_elev": "detrended topo",
    "ieq": "seismicity (inter-event)", "deq": "seismicity (distance)", "des": "seismicity (distance)",
    "geod": "geodetic strain", "dist_": "catalogue distance",
    "lidar": "2 m LiDAR scarp",
}


def family_of(name: str) -> str:
    for k, v in FAMILY.items():
        if name.startswith(k):
            return v
    return "other"


def top_support(score: np.ndarray, valid: np.ndarray, n: int) -> np.ndarray:
    flat = np.where(valid, score, -np.inf).ravel()
    n = min(n, int(valid.sum()))
    idx = np.argpartition(flat, -n)[-n:]
    out = np.zeros(flat.size, dtype=bool)
    out[idx] = True
    return out.reshape(score.shape) & valid


def score_mask(mask: np.ndarray, ev, gt: np.ndarray) -> dict:
    r = ev.evaluate(mask.astype(np.float32))
    mass = float(r["mass"])
    return {"mass": mass, "hit_rate": r["tp"] / max(mass, 1e-9),
            "capture": r["tp"] / max(r["n_truth"], 1), "dti_proxy": r["dti"]}


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20000
    valid = gio.read_footprint()
    gt = V.sgmc_only_gt(valid)
    ev = V.M.FastDTI(gt, valid=valid)
    names = json.loads((C.CACHE / "feature_names.json").read_text()) if hasattr(C, "CACHE") else \
        json.loads((ROOT / ".cache" / "gemsdoe" / "feature_names.json").read_text())
    stack = np.load(ROOT / ".cache" / "gemsdoe" / "feature_stack.npy", mmap_mode="r")

    rows = []
    for i, name in enumerate(names):
        x = np.asarray(stack[i], dtype=np.float32)
        finite = valid & np.isfinite(x)
        med = float(np.nanmedian(x[finite])) if finite.any() else 0.0
        score = np.abs(np.where(finite, x - med, 0.0))
        mask = top_support(score, finite, n)
        rows.append({"feature": name, "family": family_of(name), **score_mask(mask, ev, gt)})
        print(f"{i:2d} {name:<24s} {rows[-1]['family']:<22s} h={rows[-1]['hit_rate']:.4f} "
              f"dti={rows[-1]['dti_proxy']:.4f}", flush=True)

    lidar_rows = []
    band_names = json.loads(LIDAR_META.read_text())["bands"] if LIDAR_META.exists() else []
    if LIDAR_TIF.exists():
        with rasterio.open(LIDAR_TIF) as src:
            arr = src.read()
        for b in range(arr.shape[0]):
            name = band_names[b] if b < len(band_names) else f"lidar_{b}"
            if name in LIDAR_SKIP:
                continue
            x = arr[b].astype(np.float32)
            q = x > 0                      # 0 is nodata in the dequantised channels
            finite = valid & q
            score = np.where(finite, x, 0.0)
            mask = top_support(score, finite, n)
            lidar_rows.append({"feature": name, "family": "2 m LiDAR scarp", **score_mask(mask, ev, gt)})
            print(f"L{b} {name:<23s} h={lidar_rows[-1]['hit_rate']:.4f} "
                  f"dti={lidar_rows[-1]['dti_proxy']:.4f}", flush=True)

    all_rows = rows + lidar_rows
    fam = {}
    for r in all_rows:
        fam.setdefault(r["family"], []).append(r["hit_rate"])
    family_best = {k: {"best_hit_rate": max(v), "median_hit_rate": float(np.median(v)), "n_features": len(v)}
                   for k, v in fam.items()}

    out = {
        "proxy": "USGS SGMC faults >300 m from every catalogue fault",
        "n_proxy_positives": int(gt.sum()),
        "n_dots_per_layer": n,
        "selection": "top-N by |value - footprint median| (two-polarity), within footprint",
        "evaluator_version": "gemsdoe-dti-v1.0",
        "label": "PROXY (not a competition score)",
        "rows": all_rows,
        "family_best": dict(sorted(family_best.items(), key=lambda kv: -kv[1]["best_hit_rate"])),
        "note": "One feature alone is never the submission; this ranks which physical observables "
                "carry off-catalogue fault information at all.",
    }
    path = ROOT / "evidence" / "layer_ranking.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {path}")
    for k, v in out["family_best"].items():
        print(f"  {k:<24s} best h={v['best_hit_rate']:.4f} median={v['median_hit_rate']:.4f} ({v['n_features']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
