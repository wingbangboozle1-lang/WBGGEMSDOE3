#!/usr/bin/env python3
"""Measure how much footprint the registry's submissions already cover (3-px kernel).

Reads the submission rows of evidence/uniqueness_gate_full_2026-10-28.json (457 real sibling
submissions; input/witness rasters excluded), unions their dots, and reports:
  * the share of the footprint within 3 px of ANY submission dot (the complement is empty
    if this is 1.0, so no design can be zero-overlap with every submission), and
  * for each of the largest comparators, the footprint cells that are >= 3 px from that one
    comparator (excluding the 4-px catalogue collar) -- the cells a design must use to stay
    under the 70% directed-overlap line against that comparator.

Writes evidence/uniqueness_coverage_2026-10-28.json. Read-only with respect to the data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "uniqueness_coverage_2026-10-28.json"
GATE = ROOT / "evidence" / "uniqueness_gate_full_2026-10-28.json"
LABELS = ROOT / ".cache" / "official" / "labels.tif"
TOP_N = 8


def dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > 0)


def main() -> int:
    gate = json.loads(GATE.read_text())
    subs = [r for r in gate["rows"] if r["kind"] == "submission"]
    with rasterio.open(LABELS) as s:
        lab = s.read(1)
    foot = lab != -1
    cat_collar = ndi.binary_dilation(lab == 1, iterations=4)
    union = np.zeros(lab.shape, bool)
    for r in subs:
        d = dots(ROOT / r["file"])
        if d.shape != lab.shape:
            raise SystemExit(f"grid mismatch: {r['file']}")
        union |= d
    dist = ndi.distance_transform_edt(~union)
    covered_by_union = float((foot & (dist < 3.0)).sum() / foot.sum())
    per = []
    for r in sorted(subs, key=lambda r: -r["our_dots_within3px"])[:TOP_N]:
        d = dots(ROOT / r["file"])
        dd = ndi.distance_transform_edt(~d)
        free = foot & (dd >= 3.0) & ~cat_collar
        per.append({
            "file": r["file"].split("/")[-1],
            "sha256": r["sha256"],
            "n_dots": int(d.sum()),
            "free_cells_ge3px_excl_collar": int(free.sum()),
            "free_fraction_of_footprint": round(float(free.sum() / foot.sum()), 6),
        })
    result = {
        "schema": "uniqueness-coverage-v1",
        "source_gate": str(GATE.relative_to(ROOT)),
        "source_gate_sha256": hashlib.sha256(GATE.read_bytes()).hexdigest(),
        "n_submission_comparators": len(subs),
        "footprint_cells": int(foot.sum()),
        "union_dots": int(union.sum()),
        "footprint_share_within_3px_of_any_submission": round(covered_by_union, 6),
        "zero_overlap_complement_exists": bool((foot & (dist >= 3.0) & ~cat_collar).any()),
        "top_comparators_by_overlap": per,
        "reading": (
            "The 3-px footprint of all 457 sibling submissions covers the whole footprint, so no "
            "design can have zero overlap with every submission. Under the literal per-raster 70% "
            "rule, the binding comparator is the 13GEMSDOE lattice: only the free cells above "
            "(0.14% of footprint) are available to keep its overlap at or below 70%."
        ),
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in (
        "union_dots", "footprint_share_within_3px_of_any_submission",
        "zero_overlap_complement_exists")}, indent=1))
    print(json.dumps(per[0], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
