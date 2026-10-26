#!/usr/bin/env python3
"""Reproduce the priority-raster lineage and literal-registry STOP witness.

This is an artifact audit, not a holdout experiment and not a leaderboard
scorer. It downloads only immutable, hash-checked public research artifacts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

from github_bytes import fetch_pinned, sha256

ROOT = Path(__file__).resolve().parents[1]


def min_overlap_bound(uncovered: int, budget: int, footprint: int) -> float:
    """Pigeonhole lower bound for a set of distinct in-footprint dots."""
    if not 0 <= uncovered <= footprint or not 1 <= budget <= footprint:
        raise ValueError("invalid footprint, uncovered count, or dot budget")
    return max(0.0, (budget - uncovered) / budget)


def binary_rank_correlation(a: np.ndarray, b: np.ndarray, footprint: np.ndarray) -> float | None:
    """Spearman with average ranks for two binary fields on the footprint."""
    n = int(footprint.sum())
    na = int(np.count_nonzero(a & footprint))
    nb = int(np.count_nonzero(b & footprint))
    nab = int(np.count_nonzero(a & b & footprint))
    denominator = math.sqrt(na * (n - na) * nb * (n - nb))
    return None if denominator == 0 else (n * nab - na * nb) / denominator


def read_checked(path: Path, grid: tuple, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError(f"wrong band count or grid: {path}")
        arr = ds.read(1)
        values = arr[footprint]
        if ds.dtypes[0] != "float32" or not np.isfinite(values).all():
            raise ValueError(f"non-finite footprint or dtype: {path}")
        if np.any((values < 0) | (values > 1)):
            raise ValueError(f"values outside [0,1]: {path}")
        if not np.all((values == 0) | (values == 1)):
            raise ValueError(f"this binary-rank audit cannot process continuous raster: {path}")
        mask = footprint & (arr > 0)
        details = {
            "sha256": sha256(path), "dots_inside": int(mask.sum()),
            "dtype": ds.dtypes[0], "finite_inside": True,
            "min_inside": float(values.min()), "max_inside": float(values.max()),
            "nonfinite_outside": int(np.count_nonzero(~np.isfinite(arr[~footprint]))),
            "valid_mask_outside": int(np.count_nonzero(ds.read_masks(1)[~footprint])),
        }
        return mask, details


def run(output: Path) -> dict:
    sources = json.loads((ROOT / "config/data-sources.json").read_text())
    for item in sources["files"]:
        fetch_pinned(sources["repo"], sources["ref"], item["path"],
                     ROOT / "data/raw" / item["dest"], item["sha256"], item["bytes"])
    sample = ROOT / "data/raw/sample_submission.tif"
    with rasterio.open(sample) as ds:
        # Use only the nodata mask. The mirror's sample values include labels.
        footprint = ds.read_masks(1) > 0
        grid = (ds.shape, ds.crs, ds.transform)
        grid_info = {"shape": list(ds.shape), "crs": str(ds.crs),
                     "transform": list(tuple(ds.transform)[:6]), "bands": ds.count,
                     "template_sha256": sha256(sample), "footprint_pixels": int(footprint.sum())}
    with rasterio.open(ROOT / "data/raw/existing_faults.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("catalogue grid mismatch")
        catalogue = (ds.read(1) == 1) & footprint
    with rasterio.open(ROOT / "data/raw/registry-lattice.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("lattice grid mismatch")
        witness = (ds.read(1) == 1) & footprint
    yy, xx = np.ogrid[-3:4, -3:4]
    disk = yy * yy + xx * xx <= 9  # Euclidean <= 3 pixels, inclusive.
    halo = binary_dilation(witness, structure=disk)
    uncovered = int(np.count_nonzero(footprint & ~halo))
    total = int(footprint.sum())
    registry_path = ROOT / "data/cache/shared-registry-57.json"
    registry_hash = "846eddb9459f0e5b67f33da519bbd62c966bf5f539545ba3dad262fbfbc308c2"
    fetch_pinned("buffedlizard55-lab/57GEMSDOE", "822a0ce5546c7b6749cdd82eb145b6b3e616603d",
                 "docs/data/registry_refreshed.json", registry_path, registry_hash, 339283)
    registry = json.loads(registry_path.read_text())
    witness_hash = sha256(ROOT / "data/raw/registry-lattice.tif")
    witness_entries = [r for r in registry["rasters"] if r.get("sha256") == witness_hash]
    if len(witness_entries) != 1:
        raise ValueError("pinned witness is not present exactly once in the shared registry")

    entries = json.loads((ROOT / "config/priority-rasters.json").read_text())
    masks, details = {}, {}
    for entry in entries:
        dest = ROOT / "data/cache/priority" / f"{entry['id']}.tif"
        fetch_pinned(entry["repo"], entry["ref"], entry["path"], dest, entry["sha256"], entry["size"])
        masks[entry["id"]], data = read_checked(dest, grid, footprint)
        data.update(id=entry["id"], source_url=entry["source_url"],
                    file=Path(entry["path"]).name, role=entry["role"],
                    claim=entry["score_claim"], claim_evidence=entry["claim_evidence"],
                    overlap_lattice_within_3px=float(np.count_nonzero(masks[entry["id"]] & halo) / data["dots_inside"]))
        details[entry["id"]] = data
    ids = [entry["id"] for entry in entries]
    priority = [entry["id"] for entry in entries if entry["role"] == "historical_priority"]
    overlap: dict[str, dict[str, float]] = {key: {} for key in ids}
    correlations: dict[str, dict[str, float | None]] = {key: {} for key in ids}
    for other in ids:
        other_halo = binary_dilation(masks[other], structure=disk)
        for candidate in ids:
            if candidate == other:
                continue
            overlap[candidate][other] = float(np.count_nonzero(masks[candidate] & other_halo) / details[candidate]["dots_inside"])
            correlations[candidate][other] = binary_rank_correlation(masks[candidate], masks[other], footprint)
    for candidate in priority:
        nearest = max((x for x in priority if x != candidate), key=lambda x: overlap[candidate][x])
        details[candidate]["max_overlap_other_priority"] = overlap[candidate][nearest]
        details[candidate]["nearest_priority_id"] = nearest
        details[candidate]["literal_unique"] = False  # witnessed by lattice; not an exhaustive all-registry audit
    dist_catalogue = distance_transform_edt(~catalogue)
    lineage = {
        "site25_equals_site30_inside_footprint": bool(np.array_equal(masks["25"], masks["30"])),
        "site31_equals_site25_with_distance_gt_1px": bool(np.array_equal(masks["31"], masks["25"] & (dist_catalogue > 1))),
        "site32_equals_site25_with_distance_gt_2px": bool(np.array_equal(masks["32"], masks["25"] & (dist_catalogue > 2))),
        "site32_subset_of_site36": bool(np.all(~masks["32"] | masks["36"])),
        "site36_extra_dots_vs_site32": int(np.count_nonzero(masks["36"] & ~masks["32"])),
        "removed_by_1px_prune": int(np.count_nonzero(masks["25"] & ~masks["31"])),
        "removed_by_2px_prune_after_1px": int(np.count_nonzero(masks["31"] & ~masks["32"])),
    }
    out = {
        "audit_version": "wbggemsdoe3-priority-artifact-v1",
        "computed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "Nine hash-pinned historical rasters and one GEMSDOE27 research candidate versus each other and one registered lattice; not a full-registry pass, surface replay, holdout, or organizer receipt.",
        "grid": grid_info, "catalogue_positive_pixels": int(catalogue.sum()),
        "witness": {
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
            "registry_url": "https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/docs/data/registry_refreshed.json",
            "registry_sha256": registry_hash,
            "registry_raster_count": len(registry["rasters"]),
            "registry_witness_sources": witness_entries[0]["sources"],
            "raster_sha256": witness_hash,
            "halo_radius_pixels_euclidean_inclusive": 3,
            "footprint_pixels_outside_halo": uncovered,
            "footprint_coverage_fraction": 1 - uncovered / total,
            "historical_budget": 37654,
            "minimum_overlap_at_historical_budget": min_overlap_bound(uncovered, 37654, total),
            "smallest_dot_budget_provably_above_70pct": (10 * uncovered) // 3 + 1,
            "qualification": "The bound assumes distinct dots inside the template footprint; it does not rule out every lower-budget candidate."
        },
        "lineage": lineage, "rasters": details,
        "directional_overlap": overlap, "binary_spearman": correlations,
        "surface_checks": "not available; no pre-placement surface was replayed",
        "experiments_run": 0,
        "warning": "Historical score claims are user/owner-reported, not organizer-confirmed; byte association has no submission-page receipt."
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/priority-audit.json")
    args = parser.parse_args()
    result = run(args.output)
    witness = result["witness"]
    print("uncovered footprint cells:", witness["footprint_pixels_outside_halo"])
    print("minimum overlap at 37,654 dots:", witness["minimum_overlap_at_historical_budget"])
    print("GEMSDOE27 candidate actual lattice overlap:", result["rasters"]["27candidate"]["overlap_lattice_within_3px"])
    print("Lineage:", result["lineage"])
    print("Wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
