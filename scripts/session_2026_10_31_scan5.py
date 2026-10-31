#!/usr/bin/env python3
"""Resolve the lane-drift flag: floor sweep for the capacity-1 geometry.

The 0.20-floor candidate tripped the equal-N 70% / 3 px rule against exactly one
registry raster (GEMSDOE37 h6-physics-dotted-80k, measured forward overlap
0.7105, rank correlation 0.129).  This sweep measures, for a ladder of
probability floors, (a) the holdout DTI of the capacity-1 geometry on the same
cached folds and (b) the equal-N overlap of the FINAL-model emission against the
registry, so the floor can be chosen on evidence instead of by hand.

Selection rule (declared here, before the numbers are read): pick the smallest
floor whose worst equal-N forward overlap is <= 0.70 while its pooled HOLDOUT-DTI
95% CI still overlaps the CI of the best floor.  If no floor satisfies both, keep
0.20 and report the trip.
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
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(TEMPLATE / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from session_2026_10_31_scan3 import capacity_support  # noqa: E402

SEED = 20261031
FLOORS = (0.20, 0.25, 0.30, 0.35)
RADIUS_PX = 3.0

_Y, _X = np.mgrid[-3:4, -3:4]
_DISK3 = (np.hypot(_Y, _X) <= RADIUS_PX)


def holdout_part() -> dict:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    arms, per_fold = {}, {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        fold = dict(region=region, truth=catalogue & region,
                    visible=catalogue & ~region, masked_known=catalogue & ~region)
        for fl in FLOORS:
            m = capacity_support(prob, region, 3, 1, fl)
            vals = np.where(m, 1.0, 0.0).astype(np.float32)
            res, terms = eh.evaluate(vals, fold, footprint, block_side=200,
                                     origin=(0, 0), global_shape=shape)
            tag = f"cap3_c1_f{fl:.2f}"
            arms.setdefault(tag, np.zeros_like(terms))
            arms[tag] += terms
            per_fold.setdefault(tag, {})[f"fold{f}"] = dict(dti=round(res["dti"], 5),
                                                            emitted=int(m.sum()))
    names = sorted(arms, key=lambda n: -eh.from_terms(arms[n].sum(axis=0)))
    summ = eh.pooled_summary({n: arms[n] for n in names}, candidate=names[0],
                             draws=600, seed=SEED)
    for n, s in sorted(summ["scores"].items(), key=lambda kv: -kv[1]["dti"]):
        print(f"  HOLDOUT {n}: DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] "
              f"dots {sum(v['emitted'] for v in per_fold[n].values()):,}")
    return dict(pooled=summ["scores"], per_fold=per_fold,
                paired=summ.get("paired_differences"))


def overlap_part() -> dict:
    footprint = np.load(WORK / "footprint_mask_2026_10_31.npy")
    fp_lin = np.flatnonzero(footprint.ravel())
    shape = footprint.shape
    prob = np.load(WORK / "candidate_prob_2026_10_31.npy")
    with rasterio.open(ROOT / "data" / "raw" / "labels.tif") as src:
        catalogue = (src.read(1) > 0) & footprint
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    allowed = footprint & (d_cat > 2.0)
    idx = json.loads((LEDGER / "index.json").read_text())
    comps = [(r["site"], Path(r["path"]).name, ROOT / r["local"])
             for r in idx if r.get("status") == "verified" and r.get("local")]
    results = {}
    for fl in FLOORS:
        dots = capacity_support(np.where(allowed, prob, -np.inf).astype(np.float32),
                                allowed, 3, 1, fl)
        n_c = int(dots.sum())
        worst, detail = None, []
        for site, name, path in comps:
            with rasterio.open(path) as src:
                a = src.read(1).astype(np.float32)
            a = np.where(np.isfinite(a), a, 0.0)
            a[~footprint] = 0.0
            v = a.ravel()
            n_pos = int((v > 0).sum())
            del a
            if n_pos == 0:
                continue
            k = min(n_c, n_pos)
            vals = v[fp_lin]
            part = np.argpartition(-vals, k - 1)[:k]
            cm = np.zeros(v.size, bool)
            cm[fp_lin[part]] = True
            del v, vals, part
            cm = cm.reshape(shape)
            near = ndi.binary_dilation(cm, structure=_DISK3, iterations=1)
            fwd = float((dots & near).sum() / n_c)
            del cm, near
            detail.append(dict(site=site, name=name, n_positive=n_pos, overlap=round(fwd, 6)))
            if worst is None or fwd > worst["overlap"]:
                worst = dict(site=site, name=name, n_positive=n_pos, overlap=round(fwd, 6))
        results[f"{fl:.2f}"] = dict(n_dots=n_c, worst=worst,
                                    top5=sorted(detail, key=lambda r: -r["overlap"])[:5])
        print(f"  floor {fl:.2f}: {n_c:,} dots; worst equal-N overlap {worst['overlap']:.4f} "
              f"({worst['site']} {worst['name'][:40]})", flush=True)
    return results


def main() -> int:
    print("=== holdout (capacity 1, floor ladder) ===")
    h = holdout_part()
    print("\n=== registry overlap (final-model emission) ===")
    o = overlap_part()
    out = dict(session="2026-10-31", evidence_class="HOLDOUT-DTI + measured registry overlap",
               floors=list(FLOORS), holdout=h, overlap=o)
    (WORK / "holdout_scan5_2026_10_31.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
