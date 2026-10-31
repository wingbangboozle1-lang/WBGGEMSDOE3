#!/usr/bin/env python3
"""Head-to-head: this lane's raster vs the raster main's gate v2 cleared.

Two lanes worked 2026-10-31 on the same repository with different holdout
instruments, so their HOLDOUT-DTI numbers are not comparable. This script puts
every candidate on ONE instrument - the new-fault hide-and-recover folds that
produced docs/data/release_gate.json (src/newfaults/holdout.py, 3 folds, 20 %
of catalogue segments withheld, 2 px buffer, visible catalogue masked as
known) - and reports a paired bootstrap delta against the shipped corridor
raster, which is what a promotion decision actually needs.

Every number here is HOLDOUT-DTI, never a competition score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsw import metric                       # noqa: E402
from src.newfaults import data, holdout              # noqa: E402

FOLDS = (0, 1, 2)
RASTERS = [
    ("offcat_buf12_f0.15", ROOT / "submission/wbg3-offcat-spread-n38026-f15-c1b3-buf12-20261031-zeros.tif"),
    ("corridor_band3to12_s24", ROOT / "docs/downloads/wbg-corridor-band3to12-s24-sep4-20261031T030000Z-zeros.tif"),
    ("twr1r2_crestcore3px", ROOT / "docs/downloads/wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif"),
    ("offcat_buf2_f0.30", ROOT / "submission/wbg3-offcat-spread-n35235-f30-c1b3-buf2-20261031-zeros.tif"),
]
BASELINE = "corridor_band3to12_s24"


def read_dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.nan_to_num(a.astype(np.float32), nan=0.0) > 0


def main() -> int:
    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    shape = lab.shape
    rasters = [(n, p) for n, p in RASTERS if Path(p).is_file()]
    dots = {n: read_dots(p) for n, p in rasters}
    print("loaded:", {n: int(v.sum()) for n, v in dots.items()}, flush=True)

    rng = np.random.default_rng(4)
    per_fold = {n: [] for n in dots}
    per_fold["random_matched"] = []
    for f in FOLDS:
        fold = holdout.make_fold(cat, f, hide_frac=0.2, buffer_px=2)
        active = foot & ~fold.known_mask
        decs = {}
        li = np.flatnonzero(active.ravel())
        n_ref = int(dots[BASELINE].sum())
        for name, d in dots.items():
            decs[name] = holdout.decompose(d & active, fold.hidden, active)
        rnd = np.zeros(shape, bool)
        rnd.ravel()[rng.choice(li, min(n_ref, li.size), replace=False)] = True
        decs["random_matched"] = holdout.decompose(rnd, fold.hidden, active)
        for name, dec in decs.items():
            per_fold[name].append(dec)
        line = "  ".join(f"{n} {d['dti']:.5f}" for n, d in decs.items())
        print(f"fold {f} (truth {decs[BASELINE]['n_truth']:,}): {line}", flush=True)

    # Pool the three folds by summing per-pixel terms.
    pooled = {}
    for name, decs in per_fold.items():
        tp = sum(d["tp"] for d in decs)
        fp = sum(d["fp"] for d in decs)
        nt = sum(d["n_truth"] for d in decs)
        pooled[name] = dict(dti=float(metric.dti(tp, fp, nt - tp)), tp=tp, fp=fp,
                            n_truth=nt, n_dots=int(sum(d["n_dots"] for d in decs)))
    # Block bootstrap on the concatenated per-fold decompositions (folds are
    # disjoint in truth, so summing the block tables is the pooled resample).
    cis, deltas = {}, {}
    for name, decs in per_fold.items():
        lo_hi = []
        for d in decs:
            lo_hi.append(holdout.block_bootstrap_dti(d, shape, block=256, n_boot=300)["ci95"])
        cis[name] = [float(np.mean([c[0] for c in lo_hi])), float(np.mean([c[1] for c in lo_hi]))]
        dlt = [holdout.paired_bootstrap_delta(a, b, shape, block=256, n_boot=300)
               for a, b in zip(decs, per_fold[BASELINE])]
        deltas[name] = dict(delta=float(pooled[name]["dti"] - pooled[BASELINE]["dti"]),
                            ci95=[float(np.mean([d["ci95"][0] for d in dlt])),
                                  float(np.mean([d["ci95"][1] for d in dlt]))],
                            per_fold=[float(d["delta"]) for d in dlt])

    print("\npooled over 3 folds:")
    for name in sorted(pooled, key=lambda k: -pooled[k]["dti"]):
        p = pooled[name]
        d = deltas[name]
        print(f"  {name:24s} DTI {p['dti']:.5f}  CI~[{cis[name][0]:.5f},{cis[name][1]:.5f}]  "
              f"dots {p['n_dots']:,}  vs {BASELINE}: {d['delta']:+.5f} "
              f"[{d['ci95'][0]:+.5f},{d['ci95'][1]:+.5f}]", flush=True)

    out = dict(session="2026-10-31",
               evidence_class="HOLDOUT-DTI head-to-head on one shared instrument",
               evaluator="src/gemsw/metric.py dti_binary (alpha 0.2, beta 0.8, R=3 px)",
               protocol="hide-and-recover, 20% of catalogue segments withheld, 2 px buffer, "
                        "visible catalogue masked as known, folds 0-2",
               withheld_positives_total=int(pooled[BASELINE]["n_truth"]),
               pooled=pooled, ci95_mean_per_fold=cis, vs_baseline=deltas,
               note="CI rows are the mean of the three per-fold 95% block-bootstrap CIs, "
                    "not a pooled resample; the paired deltas are the decision statistic.")
    (ROOT / "evidence" / "versus_2026_10_31.json").write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
