#!/usr/bin/env python3
"""Compute a literal-registry feasibility STOP before creating a surface.

A pass of this necessary test is NOT a uniqueness pass or permission to submit.
The witness and template are pinned owner mirrors, not organizer data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

from audit_priority import min_overlap_bound
from github_bytes import sha256

ROOT = Path(__file__).resolve().parents[1]


def exceeds_overlap_limit(uncovered: int, budget: int) -> bool:
    """Compare the 70% limit exactly, including its strict boundary."""
    if uncovered < 0 or budget < 1:
        raise ValueError("invalid uncovered count or budget")
    return 10 * max(0, budget - uncovered) > 7 * budget


def calculate(sample: Path, lattice: Path, budget: int) -> dict:
    src = json.loads((ROOT / "config/data-sources.json").read_text())
    hashes = {entry["dest"]: entry["sha256"] for entry in src["files"]}
    if sha256(sample) != hashes["sample_submission.tif"] or sha256(lattice) != hashes["registry-lattice.tif"]:
        raise ValueError("input hash mismatch")
    with rasterio.open(sample) as template, rasterio.open(lattice) as registered:
        if template.count != 1 or registered.count != 1 or (template.shape, template.crs, template.transform) != (registered.shape, registered.crs, registered.transform):
            raise ValueError("registered witness / template grid mismatch")
        footprint = template.read_masks(1) > 0
        pixels = registered.read(1)
        if not np.all(np.isfinite(pixels[footprint])) or not np.all((pixels[footprint] == 0) | (pixels[footprint] == 1)):
            raise ValueError("registered witness has invalid footprint values")
        dots = footprint & (pixels > 0)
    yy, xx = np.ogrid[-3:4, -3:4]
    halo = binary_dilation(dots, structure=yy * yy + xx * xx <= 9)
    total, uncovered = int(footprint.sum()), int(np.count_nonzero(footprint & ~halo))
    bound = min_overlap_bound(uncovered, budget, total)
    stopped = exceeds_overlap_limit(uncovered, budget)
    return {
        "version": "literal-preplacement-bound-v1", "candidate_dot_budget": budget,
        "footprint_pixels": total, "uncovered_pixels": uncovered,
        "witness_sha256": hashes["registry-lattice.tif"], "radius_px": 3,
        "minimum_possible_overlap_fraction": bound, "maximum_allowed_fraction": 0.70,
        "duplicate_stop": stopped, "eligible_for_selector": False, "ok_to_submit": False,
        "result": "DUPLICATE STOP" if stopped else "INCONCLUSIVE: further checks required",
        "scope": "Distinct in-footprint dots only; this lane generated no surface or final candidate. An inconclusive result is not a pass.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dots", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = calculate(ROOT / "data/raw/sample_submission.tif", ROOT / "data/raw/registry-lattice.tif", args.dots)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        print(json.dumps({"result": "ERROR — STOP", "ok_to_submit": False, "error": str(exc)}, indent=2))
        return 2
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 2 if result["duplicate_stop"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
