#!/usr/bin/env python3
"""Build the 2026-10-31 candidate submission.

HYPOTHESIS (preregistered in knowledge/preregistration-2026-10-31.md)
---------------------------------------------------------------------
H-A: a gradient-boosted fault-ness model fitted on the PUBLIC fault catalogue
from catalogue-free geophysical, 1 m-DEM-scarp and radiometric evidence, emitted
OFF the mapped network with a capacity-limited spread geometry, recovers
unmapped faults better than (a) the same number of random dots and (b) the
family's "extend the mapped trace" geometry.

MECHANISM
---------
The official distance-weighted Tversky index takes a MAX over dots within 300 m
of each truth pixel and charges only 0.2 per false-positive unit, so redundant
adjacent dots buy nothing while a spread-out dot buys coverage of a truth pixel
nothing else covers.  The holdout (scan3/scan4) selected:
    * value 1.0 on the support (soft values were always worse),
    * probability floor p >= 0.20,
    * at most ONE dot per 3x3 window (no two dots within 1 px),
    * dots within 2 px of the public catalogue removed (the family's best
      score, GEMSDOE32 0.2778, came from pruning that annulus out of a
      0.2600 parent).

NAMED NON-FAULT MIMIC: any linear/curvilinear geophysical or topographic
texture that is not a fault - lithologic contacts, alluvial-fan and terrace
edges, road and canal cuts, drainage lineaments, flight-line levelling artefacts.

This script does NOT choose a submission slot.  It writes a locally validated
TIFF; promotion is a separate selector step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
OUT = ROOT / "submission"
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(TEMPLATE / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import grid as g57grid  # noqa: E402
from gems57 import submission_writer  # noqa: E402
from session_2026_10_31_scan3 import capacity_support  # noqa: E402

SEED = 20261031
FLOOR = 0.20
CAPACITY_BLOCK = 3
CAPACITY = 1
CATALOGUE_BUFFER_PX = 2.0
NEG_PER_POS = 6
ENSEMBLE = 2


def rows_in(mask: np.ndarray, fp_idx: np.ndarray) -> np.ndarray:
    lin = np.flatnonzero(mask.ravel())
    pos = np.searchsorted(fp_idx, lin)
    pos = np.clip(pos, 0, len(fp_idx) - 1)
    return pos[fp_idx[pos] == lin]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=FLOOR)
    ap.add_argument("--buffer", type=float, default=CATALOGUE_BUFFER_PX)
    ap.add_argument("--capacity", type=int, default=CAPACITY)
    ap.add_argument("--block", type=int, default=CAPACITY_BLOCK)
    ap.add_argument("--ensemble", type=int, default=ENSEMBLE)
    ap.add_argument("--tag", default="wbg3")
    a = ap.parse_args()

    footprint = np.load(WORK / "footprint_mask_2026_10_31.npy")
    fp_idx = np.load(WORK / "footprint_index_2026_10_31.npy")
    sidecar = json.loads((WORK / "features_2026_10_31.json").read_text())
    X = np.memmap(WORK / "features_2026_10_31.dat", dtype=np.float32, mode="r",
                  shape=(sidecar["footprint_cells"], sidecar["n_features"]))
    with rasterio.open(ROOT / "data" / "raw" / "labels.tif") as src:
        catalogue = (src.read(1) > 0) & footprint
    shape = footprint.shape

    pos_rows = rows_in(catalogue, fp_idx)
    neg_pool = rows_in(footprint & ~catalogue, fp_idx)
    probs = np.zeros(shape, np.float32)
    for k in range(a.ensemble):
        rng = np.random.default_rng(SEED + 100 * k)
        neg_rows = rng.choice(neg_pool, size=min(len(neg_pool), NEG_PER_POS * len(pos_rows)),
                              replace=False)
        rows = np.concatenate([pos_rows, neg_rows])
        y = np.concatenate([np.ones(len(pos_rows), np.uint8), np.zeros(len(neg_rows), np.uint8)])
        clf = HistGradientBoostingClassifier(
            max_iter=220, learning_rate=0.10, max_leaf_nodes=31, min_samples_leaf=40,
            l2_regularization=1.0, max_bins=128, early_stopping=False,
            random_state=SEED + 100 * k)
        clf.fit(X[rows], y)
        pred = np.empty(len(fp_idx), np.float32)
        step = 250_000
        for s in range(0, len(fp_idx), step):
            r = np.arange(s, min(s + step, len(fp_idx)))
            pred[r] = clf.predict_proba(X[r])[:, 1]
        p = np.zeros(shape, np.float32)
        p.ravel()[fp_idx] = pred
        probs += p / a.ensemble
        print(f"  ensemble member {k}: fitted on {len(rows):,} rows", flush=True)
    np.save(WORK / "candidate_prob_2026_10_31.npy", probs)

    # --- emission ---------------------------------------------------------
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    allowed = footprint & (d_cat > a.buffer)
    score = np.where(allowed, probs, -np.inf).astype(np.float32)
    dots = capacity_support(score, allowed, a.block, a.capacity, a.floor)
    n_dots = int(dots.sum())
    print(f"emission: {n_dots:,} dots ({n_dots / footprint.sum() * 100:.2f}% of footprint), "
          f"floor {a.floor}, capacity {a.capacity}/{a.block}x{a.block}, buffer {a.buffer} px")

    values = np.where(dots, np.float32(1.0), np.float32(0.0))
    # coverage diagnostics
    frac_fp = n_dots / footprint.sum()
    on_cat = int((dots & catalogue).sum())
    near_cat_1 = int((dots & (d_cat <= 1.0)).sum())

    name = (f"{a.tag}-offcat-spread-n{n_dots}-f{int(a.floor*100)}-"
            f"c{a.capacity}b{a.block}-buf{int(a.buffer)}-20261031-zeros")
    note = (f"GBM fault-ness on catalogue-free GeoDAWN+3DEP+GDR evidence; "
            f"{n_dots} dots, p>={a.floor}, 1 per 3x3, {a.buffer}px catalogue buffer")[:140]
    ts = "20261031T000000Z"
    fname = f"{name}.tif"
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / fname
    for stale in (target, target.with_suffix(".zip"), target.with_suffix(".json")):
        if stale.exists():
            stale.unlink()
    receipt = submission_writer.write_submission(
        target, values, ROOT / "data" / "raw" / "sample_submission.tif", footprint,
        note=note, name=name, catalogue=catalogue,
        metadata=dict(session="2026-10-31", hypothesis="H-A", floor=a.floor,
                      capacity=a.capacity, block=a.block,
                      catalogue_buffer_px=a.buffer, ensemble=a.ensemble,
                      feature_count=sidecar["n_features"],
                      footprint_fraction=round(frac_fp, 6),
                      dots_on_catalogue=on_cat, dots_within_1px_catalogue=near_cat_1,
                      evaluated_by="gems57-pooled-hide-v2 quadrant holdout"))
    diag = dict(session="2026-10-31", n_dots=n_dots,
                footprint_fraction=round(float(frac_fp), 6),
                dots_on_catalogue=on_cat, dots_within_1px_catalogue=near_cat_1,
                probability_floor=a.floor, capacity=a.capacity, block=a.block,
                catalogue_buffer_px=a.buffer, ensemble_members=a.ensemble,
                name=name, note=note, file=fname, sha256=receipt["sha256"],
                bytes=receipt["bytes"], zip_sha256=receipt["zip_sha256"],
                validator=receipt["validator"], template_report=receipt["template_report"])
    (WORK / "candidate_2026_10_31.json").write_text(json.dumps(diag, indent=1))
    print(json.dumps({k: v for k, v in diag.items()
                      if k not in ("validator", "template_report")}, indent=1))
    print("validator:", json.dumps(diag["validator"]["checks"], indent=1))
    print("all_checks_passed:", diag["validator"]["all_checks_passed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
