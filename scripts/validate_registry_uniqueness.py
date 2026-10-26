#!/usr/bin/env python3
"""Check pre-placement surface correlation and final-dot overlap against a registry.

This is a saved-raster comparison utility, not a holdout evaluator or submission
selector. It checks every entry in a caller-supplied registry manifest and reports
whether that manifest asserts complete coverage. The manifest's completeness assertion
must be sourced from the canonical shared registry; this script cannot discover omitted
or private registry files by itself. No lattice or other-raster exception is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


MAX_ABS_SPEARMAN = 0.90
MAX_DOT_OVERLAP = 0.70
DOT_RADIUS_PX = 3.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Compute 1-based average ranks for ties with stable NumPy sorting."""
    values = np.asarray(values)
    if values.ndim != 1:
        raise ValueError("rank input must be one-dimensional")
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = ((start + 1) + end) / 2.0
        start = end
    return ranks


def spearman_on_mask(candidate_surface: np.ndarray, registry_surface: np.ndarray, valid: np.ndarray) -> tuple[float | None, int]:
    candidate_surface = np.asarray(candidate_surface)
    registry_surface = np.asarray(registry_surface)
    valid = np.asarray(valid, dtype=bool)
    if candidate_surface.shape != registry_surface.shape or candidate_surface.shape != valid.shape:
        raise ValueError("surfaces and valid mask must share one grid")
    common = valid & np.isfinite(candidate_surface) & np.isfinite(registry_surface)
    n = int(common.sum())
    if n < 2:
        return None, n
    a = _average_ranks(candidate_surface[common].astype(np.float64, copy=False))
    b = _average_ranks(registry_surface[common].astype(np.float64, copy=False))
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.sqrt(np.dot(a, a) * np.dot(b, b)))
    if denominator == 0.0:
        return None, n
    return float(np.dot(a, b) / denominator), n


def dilate_euclidean(mask: np.ndarray, radius_px: float = DOT_RADIUS_PX) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2:
        raise ValueError("mask must be two-dimensional")
    if radius_px < 0:
        raise ValueError("radius_px must be nonnegative")
    height, width = mask.shape
    radius = int(np.ceil(radius_px))
    result = np.zeros_like(mask)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if np.hypot(dy, dx) > radius_px:
                continue
            sy0, sy1 = max(0, -dy), min(height, height - dy)
            sx0, sx1 = max(0, -dx), min(width, width - dx)
            if sy0 >= sy1 or sx0 >= sx1:
                continue
            result[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx] |= mask[sy0:sy1, sx0:sx1]
    return result


def directed_dot_overlap(candidate_dots: np.ndarray, registry_dots: np.ndarray, valid: np.ndarray, radius_px: float = DOT_RADIUS_PX) -> tuple[float | None, int, int]:
    candidate_dots = np.asarray(candidate_dots, dtype=bool)
    registry_dots = np.asarray(registry_dots, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    if candidate_dots.shape != registry_dots.shape or candidate_dots.shape != valid.shape:
        raise ValueError("dot masks and valid mask must share one grid")
    candidate_dots = candidate_dots & valid
    registry_dots = registry_dots & valid
    candidate_count = int(candidate_dots.sum())
    registry_count = int(registry_dots.sum())
    if candidate_count == 0:
        return None, candidate_count, registry_count
    near_registry = dilate_euclidean(registry_dots, radius_px=radius_px)
    fraction = float(np.count_nonzero(candidate_dots & near_registry) / candidate_count)
    return fraction, candidate_count, registry_count


def _grid_signature(dataset: rasterio.io.DatasetReader) -> tuple[Any, ...]:
    return (
        int(dataset.count),
        tuple(int(v) for v in dataset.shape),
        dataset.crs,
        tuple(float(v) for v in tuple(dataset.transform)[:6]),
    )


def _failure_report(message: str, manifest_path: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "validation_type": "registry uniqueness check; not a score or authorization",
        "registry_manifest": str(manifest_path) if manifest_path else None,
        "registry_coverage": {
            "manifest_claims_complete": False,
            "includes_literal_lattice": False,
            "includes_all_focus_site_winners": False,
            "independently_verified": False,
            "status": "NOT VERIFIED",
        },
        "preplacement_surface_check": {"status": "NOT RUN", "maximum_absolute_spearman": None, "comparisons": []},
        "final_dot_check": {"status": "NOT RUN", "maximum_directed_overlap": None, "comparisons": []},
        "comparisons_passed": False,
        "literal_all_registry_uniqueness_passed": False,
        "submission_authorized": False,
        "errors": [message],
    }


def validate_registry_uniqueness(
    candidate_surface_path: str | Path,
    candidate_path: str | Path,
    template_path: str | Path,
    manifest_path: str | Path,
    *,
    max_abs_spearman: float = MAX_ABS_SPEARMAN,
    max_dot_overlap: float = MAX_DOT_OVERLAP,
    radius_px: float = DOT_RADIUS_PX,
) -> dict[str, Any]:
    """Compare candidate pre-placement surface and saved dots to all manifest entries."""
    surface_path, candidate_path, template_path, manifest_path = map(
        Path, (candidate_surface_path, candidate_path, template_path, manifest_path)
    )
    missing = [str(p) for p in (surface_path, candidate_path, template_path, manifest_path) if not p.is_file()]
    if missing:
        return _failure_report("Missing required file(s): " + ", ".join(missing), manifest_path)
    if not (0.0 <= max_abs_spearman <= 1.0 and 0.0 <= max_dot_overlap <= 1.0 and radius_px >= 0.0):
        return _failure_report("Thresholds must be in [0,1] and radius must be nonnegative.", manifest_path)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("entries")
        required_top_level = (
            bool(manifest.get("complete")),
            bool(manifest.get("includes_literal_lattice")),
            bool(manifest.get("includes_all_focus_site_winners")),
            bool(manifest.get("registry_version")),
            bool(manifest.get("source")),
            isinstance(entries, list) and len(entries) > 0,
        )
        if not all(required_top_level):
            return _failure_report(
                "Registry manifest must assert complete coverage, include the literal lattice and all focus-site winners, "
                "name its version/source, and contain at least one entry.",
                manifest_path,
            )
        entry_ids = [str(entry.get("id", "")).lower() for entry in entries]
        if len(set(entry_ids)) != len(entry_ids):
            return _failure_report("Registry manifest contains duplicate entry IDs.", manifest_path)
        required_sites = ("gemsdoe24", "gemsdoe25", "gemsdoe27", "gemsdoe28", "gemsdoe30", "gemsdoe31", "gemsdoe32", "gemsdoe33", "gemsdoe36")
        missing_sites = [site for site in required_sites if not any(site in entry_id for entry_id in entry_ids)]
        has_lattice = any("lattice" in entry_id for entry_id in entry_ids)
        if missing_sites or not has_lattice:
            return _failure_report(
                "Registry entries must explicitly include every focus-site winner and at least one literal lattice raster; "
                f"missing sites={missing_sites}, lattice_entry_present={has_lattice}.",
                manifest_path,
            )

        with rasterio.open(template_path) as template:
            if template.count != 1:
                return _failure_report("Template must be a single-band raster.", manifest_path)
            template_array = template.read(1, masked=False)
            template_signature = _grid_signature(template)
            footprint = (template.read_masks(1) > 0) & np.isfinite(template_array)
            if not footprint.any():
                return _failure_report("Template has no finite valid-footprint cells.", manifest_path)

        with rasterio.open(surface_path) as surface_src, rasterio.open(candidate_path) as candidate_src:
            candidate_surface = surface_src.read(1, masked=False) if surface_src.count == 1 else None
            candidate_raw = candidate_src.read(1, masked=False) if candidate_src.count == 1 else None
            if candidate_surface is None or candidate_raw is None:
                return _failure_report("Candidate surface and final raster must each be single-band.", manifest_path)
            if _grid_signature(surface_src) != template_signature or _grid_signature(candidate_src) != template_signature:
                return _failure_report("Candidate surface/final raster grid does not exactly match the template.", manifest_path)

        if not np.isfinite(candidate_surface[footprint]).all():
            return _failure_report("Candidate pre-placement surface has non-finite values inside the template footprint.", manifest_path)
        if not np.isfinite(candidate_raw[footprint]).all():
            return _failure_report("Candidate final raster has non-finite values inside the template footprint.", manifest_path)
        candidate_dots = np.isfinite(candidate_raw) & (candidate_raw > 0)
        if not np.any(candidate_dots & footprint):
            return _failure_report("Candidate saved raster has no positive cells inside the template footprint.", manifest_path)

        surface_comparisons: list[dict[str, Any]] = []
        dot_comparisons: list[dict[str, Any]] = []
        errors: list[str] = []
        base = manifest_path.parent
        for entry in entries:
            registry_id = str(entry.get("id", ""))
            required = (registry_id, entry.get("surface_file"), entry.get("surface_sha256"), entry.get("dots_file"), entry.get("dots_sha256"))
            if not all(required):
                errors.append("Registry entry is missing id/path/SHA-256 fields.")
                continue
            registry_surface_path = Path(entry["surface_file"])
            registry_dots_path = Path(entry["dots_file"])
            if not registry_surface_path.is_absolute():
                registry_surface_path = base / registry_surface_path
            if not registry_dots_path.is_absolute():
                registry_dots_path = base / registry_dots_path
            if not registry_surface_path.is_file() or not registry_dots_path.is_file():
                errors.append(f"Registry files missing for {registry_id}.")
                continue
            actual_surface_hash = sha256_file(registry_surface_path)
            actual_dots_hash = sha256_file(registry_dots_path)
            if actual_surface_hash != entry["surface_sha256"] or actual_dots_hash != entry["dots_sha256"]:
                errors.append(f"SHA-256 mismatch for registry entry {registry_id}.")
                continue
            with rasterio.open(registry_surface_path) as registry_surface_src, rasterio.open(registry_dots_path) as registry_dots_src:
                if (
                    registry_surface_src.count != 1
                    or registry_dots_src.count != 1
                    or _grid_signature(registry_surface_src) != template_signature
                    or _grid_signature(registry_dots_src) != template_signature
                ):
                    errors.append(f"Registry grid/band mismatch for {registry_id}; no resampling is allowed.")
                    continue
                registry_surface = registry_surface_src.read(1, masked=False)
                registry_raw_dots = registry_dots_src.read(1, masked=False)
            if not np.isfinite(registry_surface[footprint]).all():
                errors.append(f"Registry surface has non-finite values inside the template footprint: {registry_id}.")
                continue
            if not np.isfinite(registry_raw_dots[footprint]).all():
                errors.append(f"Registry dot raster has non-finite values inside the template footprint: {registry_id}.")
                continue
            rho, common_cells = spearman_on_mask(candidate_surface, registry_surface, footprint)
            dot_fraction, candidate_count, registry_count = directed_dot_overlap(
                candidate_dots,
                np.isfinite(registry_raw_dots) & (registry_raw_dots > 0),
                footprint,
                radius_px=radius_px,
            )
            surface_passed = rho is not None and abs(rho) <= max_abs_spearman
            dot_passed = dot_fraction is not None and dot_fraction <= max_dot_overlap
            if rho is None:
                errors.append(f"Surface correlation was not measurable for {registry_id} (constant or <2 common cells).")
            if dot_fraction is None:
                errors.append(f"Directed dot overlap was not measurable for {registry_id} (no candidate dots).")
            surface_comparisons.append({
                "registry_id": registry_id,
                "registry_surface_sha256": actual_surface_hash,
                "spearman_rho": rho,
                "absolute_spearman": abs(rho) if rho is not None else None,
                "common_valid_cells": common_cells,
                "threshold": max_abs_spearman,
                "passed": bool(surface_passed),
            })
            dot_comparisons.append({
                "registry_id": registry_id,
                "registry_dots_sha256": actual_dots_hash,
                "candidate_positive_cells": candidate_count,
                "registry_positive_cells": registry_count,
                "directed_fraction_within_radius": dot_fraction,
                "radius_pixels": radius_px,
                "maximum_allowed_fraction": max_dot_overlap,
                "passed": bool(dot_passed),
            })

        all_entries_compared = len(surface_comparisons) == len(entries) and len(dot_comparisons) == len(entries)
        max_abs = max((row["absolute_spearman"] for row in surface_comparisons if row["absolute_spearman"] is not None), default=None)
        max_dot = max((row["directed_fraction_within_radius"] for row in dot_comparisons if row["directed_fraction_within_radius"] is not None), default=None)
        surface_pass = all_entries_compared and not errors and all(row["passed"] for row in surface_comparisons)
        dots_pass = all_entries_compared and not errors and all(row["passed"] for row in dot_comparisons)
        comparisons_passed = bool(surface_pass and dots_pass)
        coverage = {
            "manifest_claims_complete": True,
            "includes_literal_lattice": True,
            "includes_all_focus_site_winners": True,
            "independently_verified": False,
            "registry_version": manifest["registry_version"],
            "source": manifest["source"],
            "entry_count": len(entries),
            "status": "CLAIMED COMPLETE BY MANIFEST; completeness not independently verified",
        }
        return {
            "schema_version": 1,
            "validation_type": "registry uniqueness check; not a score or authorization",
            "candidate_surface": str(surface_path),
            "candidate_raster": str(candidate_path),
            "template": str(template_path),
            "registry_manifest": str(manifest_path),
            "registry_coverage": coverage,
            "thresholds": {
                "maximum_absolute_spearman_exclusive_stop": max_abs_spearman,
                "maximum_directed_dot_fraction_exclusive_stop": max_dot_overlap,
                "dot_radius_pixels": radius_px,
            },
            "preplacement_surface_check": {
                "status": "PASS" if surface_pass else "FAIL",
                "maximum_absolute_spearman": max_abs,
                "comparisons": surface_comparisons,
            },
            "final_dot_check": {
                "status": "PASS" if dots_pass else "FAIL",
                "maximum_directed_overlap": max_dot,
                "comparisons": dot_comparisons,
            },
            "comparisons_passed": comparisons_passed,
            "literal_all_registry_uniqueness_passed": comparisons_passed,
            "submission_authorized": False,
            "errors": errors,
            "authorization_reason": "This check only compares every listed registry entry; it cannot prove the manifest omitted no registry raster or authorize a weekly slot.",
        }
    except Exception as exc:
        return _failure_report(f"Unable to complete registry uniqueness check: {type(exc).__name__}: {exc}", manifest_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", type=Path, required=True, help="Continuous pre-placement surface GeoTIFF")
    parser.add_argument("--candidate", type=Path, required=True, help="Saved final emitted-dot GeoTIFF")
    parser.add_argument("--template", type=Path, required=True, help="Official sample_submission.tif")
    parser.add_argument("--registry-manifest", type=Path, required=True, help="Complete manifest with hashes for every registry surface and dot raster")
    parser.add_argument("--max-abs-spearman", type=float, default=MAX_ABS_SPEARMAN)
    parser.add_argument("--max-dot-overlap", type=float, default=MAX_DOT_OVERLAP)
    parser.add_argument("--radius-px", type=float, default=DOT_RADIUS_PX)
    parser.add_argument("--out", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)
    result = validate_registry_uniqueness(
        args.surface,
        args.candidate,
        args.template,
        args.registry_manifest,
        max_abs_spearman=args.max_abs_spearman,
        max_dot_overlap=args.max_dot_overlap,
        radius_px=args.radius_px,
    )
    text = json.dumps(result, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["literal_all_registry_uniqueness_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
