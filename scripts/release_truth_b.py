#!/usr/bin/env python3
"""Second truth axis: faults absent from the competition catalogue.

The hide-and-recover holdout (axis A) asks "can you recover a *catalogued* fault
you were not shown?". The competition target is the opposite kind of object: a
fault that is **not** in the catalogue. Axis B scores each candidate against
State Geologic Map Compilation faults that lie >300 m from every catalogue pixel,
using the official DTI formula with the official masking.

This is not hidden truth and not a leaderboard estimate. It is an independent
mapping lineage available to every candidate equally, and it is the only
available axis on which catalogue-mimicry is not rewarded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import shared, truth  # noqa: E402

EVID = ROOT / "evidence" / "release"


def dots_of(arr: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray) -> np.ndarray:
    return footprint & np.isfinite(arr) & (arr > 0) & ~catalogue


def main() -> int:
    import rasterio
    from scipy.ndimage import distance_transform_edt

    footprint, catalogue = shared.load_masks()
    metric = shared.shared_metric()
    sg = truth.sgmc_offcatalogue(catalogue)
    truth_b = sg["mask"] & footprint
    d_truth = distance_transform_edt(~truth_b)

    card = json.loads((EVID / "candidate_run_card.json").read_text())
    candidates = [{"site": "WBGGEMSDOE3 (this release)",
                   "path": str(ROOT / card["submission"]["path"]),
                   "owner_reported_score": None}]
    for row in json.loads((EVID / "comparators.json").read_text())["comparators"]:
        candidates.append({"site": row["site"], "path": row["path"],
                           "owner_reported_score": row["owner_reported_score"]})
    # Another lane in this repository. Scored here so that the two lanes can be
    # compared on one truth instead of on two different fold designs.
    extra = json.loads((EVID / "other_lanes.json").read_text())["lanes"]
    for row in extra:
        candidates.append({"site": row["site"], "path": row["path"],
                           "owner_reported_score": row.get("owner_reported_score")})

    rows = []
    for cand in candidates:
        path = Path(cand["path"])
        if not path.is_file():
            continue
        with rasterio.open(path) as src:
            arr = src.read(1)
        dots = dots_of(arr, footprint, catalogue)
        ev = metric.dti_binary(dots, truth_b, valid=footprint, known=catalogue)
        hit = float((d_truth[dots] <= 3.0).mean()) if dots.any() else 0.0
        rows.append(dict(site=cand["site"], file=path.name,
                         owner_reported_score=cand["owner_reported_score"],
                         dots=int(dots.sum()), dti_vs_offcatalogue=ev["dti"],
                         tp=ev["tp"], fp=ev["fp"], fn=ev["fn"],
                         recall=float(ev["tp"] / max(1, ev["n_truth"])),
                         hit_rate_within_3px=hit))
        print(f"{cand['site']:22s} dots={int(dots.sum()):7,d} "
              f"DTI_B={ev['dti']:.4f} recall={rows[-1]['recall']:.3f} h={hit:.3f}", flush=True)

    (EVID / "truth_b.json").write_text(json.dumps({
        "generated_by": "scripts/release_truth_b.py",
        "truth": {"n_cells": int(truth_b.sum()),
                  "definition": "sgmc_faults_100m.tif == 1 and distance to the "
                                "competition catalogue >= 3 px and inside the footprint",
                  "provenance": "USGS State Geologic Map Compilation raster shipped in "
                                "the pinned template; independent of the Qfault/INGENIOUS "
                                "lineage used for the competition labels"},
        "caveat": "State-map faults include bedrock structures that are not Quaternary; "
                  "this axis is a generalisation proxy, not hidden truth and not a "
                  "leaderboard estimate. Every candidate is scored identically.",
        "evaluator": "gems57.metric.dti_binary (official formula, alpha=0.2, beta=0.8, R=300 m)",
        "rows": rows,
    }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
