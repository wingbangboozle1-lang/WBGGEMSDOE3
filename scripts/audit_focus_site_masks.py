#!/usr/bin/env python3
"""Recompute the nine-site historical TIFF hash/grid/positive-mask overlap audit.

This script only reads already-downloaded historical TIFFs for forensic/educational
analysis. It does not generate, copy, score, or authorize a submission.

Expected local filenames are GEMSDOE24.tif, GEMSDOE25.tif, ... GEMSDOE36.tif, as
listed in docs/data/focus-site-audit.json. The report's pinned source hashes are checked
before metadata or overlap is accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "data" / "focus-site-audit.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dilate_euclidean(mask: np.ndarray, radius_px: float = 3.0) -> np.ndarray:
    """Return cells at Euclidean grid distance <= radius_px from any True cell."""
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2:
        raise ValueError("mask must be a 2-D array")
    height, width = mask.shape
    radius = int(np.ceil(radius_px))
    expanded = np.zeros_like(mask)
    offsets = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if np.hypot(dy, dx) <= radius_px
    ]
    for dy, dx in offsets:
        sy0, sy1 = max(0, -dy), min(height, height - dy)
        sx0, sx1 = max(0, -dx), min(width, width - dx)
        if sy0 >= sy1 or sx0 >= sx1:
            continue
        expanded[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx] |= mask[sy0:sy1, sx0:sx1]
    return expanded


def directed_overlap_within_radius(candidate: np.ndarray, reference: np.ndarray, radius_px: float = 3.0) -> float:
    candidate = np.asarray(candidate, dtype=bool)
    reference = np.asarray(reference, dtype=bool)
    if candidate.shape != reference.shape:
        raise ValueError("candidate and reference masks must share a grid")
    n_positive = int(candidate.sum())
    if n_positive == 0:
        return 0.0
    near_reference = dilate_euclidean(reference, radius_px=radius_px)
    return float(np.count_nonzero(candidate & near_reference) / n_positive)


def _nodata_value(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if np.isnan(value):
            return "NaN"
    except TypeError:
        pass
    return str(value)


def audit(raster_dir: Path, manifest_path: Path = AUDIT_PATH, radius_px: float = 3.0) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["sites"]
    masks: dict[str, np.ndarray] = {}
    profiles: dict[str, dict] = {}
    files: dict[str, dict] = {}

    for record in records:
        site = record["site"]
        path = raster_dir / f"{site}.tif"
        if not path.is_file():
            raise FileNotFoundError(f"Missing historical audit raster: {path}")
        digest = sha256_file(path)
        if digest != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {site}: expected {record['sha256']}, got {digest}")
        with rasterio.open(path) as dataset:
            if dataset.count != 1:
                raise ValueError(f"{site} must have one band; found {dataset.count}")
            array = dataset.read(1, masked=False)
            profile = {
                "crs": str(dataset.crs) if dataset.crs is not None else None,
                "shape": [int(v) for v in dataset.shape],
                "transform": [float(v) for v in tuple(dataset.transform)[:6]],
                "dtype": dataset.dtypes[0],
                "nodata": _nodata_value(dataset.nodata),
                "bands": int(dataset.count),
                "finite": int(np.isfinite(array).sum()),
                "nonfinite": int((~np.isfinite(array)).sum()),
                "positive": int((np.isfinite(array) & (array > 0)).sum()),
                "minimum_finite": float(np.nanmin(array)) if np.isfinite(array).any() else None,
                "maximum_finite": float(np.nanmax(array)) if np.isfinite(array).any() else None,
            }
            masks[site] = np.isfinite(array) & (array > 0)
            profiles[site] = profile
            files[site] = {
                "path": str(path),
                "sha256": digest,
                "expected_sha256": record["sha256"],
                "sha256_matches": True,
                "source_commit": record["source_commit"],
                "source_file_path": record["file_path"],
            }

    names = [record["site"] for record in records]
    first = profiles[names[0]]
    same_grid = all(
        (profiles[name]["crs"], profiles[name]["shape"], profiles[name]["transform"])
        == (first["crs"], first["shape"], first["transform"])
        for name in names
    )
    if not same_grid:
        raise ValueError("Historical raster CRS/shape/transform mismatch; do not compare masks without a reviewed reprojection.")

    pairwise: dict[str, float] = {}
    for candidate in names:
        for reference in names:
            if candidate == reference:
                continue
            pairwise[f"{candidate}__to__{reference}"] = directed_overlap_within_radius(
                masks[candidate], masks[reference], radius_px=radius_px
            )

    per_site = []
    for record in records:
        site = record["site"]
        comparisons = {
            reference: pairwise[f"{site}__to__{reference}"]
            for reference in names if reference != site
        }
        worst_reference = max(comparisons, key=comparisons.get)
        per_site.append({
            "site": site,
            "historical_submission": record["submission_id"],
            "score_label": record["score_label"],
            "historical_score": record["historical_score"],
            "sha256": record["sha256"],
            "positive_pixels": profiles[site]["positive"],
            "profile": profiles[site],
            "maximum_directed_within_radius_fraction": comparisons[worst_reference],
            "worst_reference_site": worst_reference,
            "unique_under_limit": comparisons[worst_reference] <= manifest["uniqueness_rule"]["maximum_allowed_fraction"],
            "all_pairwise_comparisons": comparisons,
        })

    all_values = list(pairwise.values())
    threshold = float(manifest["uniqueness_rule"]["maximum_allowed_fraction"])
    return {
        "schema_version": 1,
        "audit_type": "historical focus-site final-dot mask comparison; not a score",
        "scope": manifest["scope"],
        "source_method": "Local historical TIFF bytes; SHA-256 pinned; Euclidean disk dilation implemented on the unresampled raster grid.",
        "distance_pixels": float(radius_px),
        "maximum_allowed_fraction": threshold,
        "source_hashes_match": True,
        "all_grids_match": same_grid,
        "number_of_rasters": len(names),
        "directed_pairwise_comparisons": len(pairwise),
        "minimum_pairwise_directed_fraction": min(all_values) if all_values else None,
        "maximum_pairwise_directed_fraction": max(all_values) if all_values else None,
        "all_historical_winners_fail_uniqueness": all(not row["unique_under_limit"] for row in per_site),
        "files": files,
        "sites": per_site,
        "pairwise_directed_within_radius_fraction": pairwise,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raster_dir", type=Path, help="Directory holding <GEMSDOE site>.tif audit copies")
    parser.add_argument("--manifest", type=Path, default=AUDIT_PATH, help="Pinned source/hash manifest JSON")
    parser.add_argument("--radius-px", type=float, default=3.0)
    parser.add_argument("--out", type=Path, help="Optional JSON result path")
    args = parser.parse_args()
    result = audit(args.raster_dir, args.manifest, args.radius_px)
    text = json.dumps(result, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
