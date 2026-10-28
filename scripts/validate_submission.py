#!/usr/bin/env python3
"""Project-side submission validator: format gate + uniqueness gate, no human inspection.

Why this exists: the official rules (NLR, Sept 2026, s.3.2 and the DrivenData page
"Submission format") define what the portal accepts; the user's parallel-run protocol
defines the duplicate rule. This script applies both to one GeoTIFF and writes a JSON
record, exiting non-zero on any failure, so acceptance is decided by code and not by a
person looking at a map.

Format gate (official text + the project's stricter zeros policy):
  * one band, float32, GTiff driver;
  * CRS EPSG:32611, shape and affine transform identical to the sample grid;
  * every cell finite and inside [0, 1]. The official text allows "null or nan" outside
    the bounds; the project deliberately writes zeros instead, because the portal once
    rejected a NaN-outside file with "Predicted values must be in range [0, 1]". This is
    stricter than the rules, so it cannot make a file pass that the rules would fail.
  The format checks reuse ``gems_project.format_preflight.raster_report`` (shared code).

Uniqueness gate (user protocol, rules 1):
  * exact SHA-256 duplicate of any comparator -> FAIL;
  * share of this raster's positive cells within 3 px (kernel > 0) of one comparator's
    positive cells must be <= 0.70, for every comparator;
  * |Spearman| of the two rasters (sampled every 6th cell, as in check_uniqueness.py)
    must be <= 0.90.
  Comparators whose grid differs cannot be compared cell-by-cell; they are listed as
  ``skipped`` and counted, never silently treated as passing.

This is a PROJECT VALIDATOR. It is not organizer validation, does not prove portal
acceptance, does not measure the score, and does not select a submission slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import exact as EX  # noqa: E402  (shared 3-px triangular kernel)
from gems_project.format_preflight import raster_report  # noqa: E402  (shared format preflight)

SCHEMA = "gems-submission-validation-v1"
EVIDENCE_CLASS = "PROJECT VALIDATOR - not organizer validation; no score; no portal acceptance"
DEFAULT_SAMPLE = ROOT / "data" / "template_grid.tif"
LIMIT_OVERLAP = 0.70
LIMIT_ABS_SPEARMAN = 0.90
STRIDE = 6


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def format_gate(candidate: Path, sample: Path) -> dict:
    report = raster_report(candidate, sample)
    rep_checks = dict(report["checks"])
    with rasterio.open(candidate) as ds:
        rep_checks["gtiff_driver"] = ds.driver == "GTiff"
    return {
        "passed": bool(report["format_ok"]) and rep_checks["gtiff_driver"],
        "checks": rep_checks,
        "problems": report["problems"],
        "crs": report["crs"],
        "shape": report["shape"],
        "transform": report["transform"],
        "dtype": report["dtype"],
        "footprint_cells": report["footprint_cells"],
        "inside_min": report["inside_min"],
        "inside_max": report["inside_max"],
        "inside_nan_cells": report["inside_nan_cells"],
        "positive_cells": report["positive_inside"],
        "sample_sha256": report["sample_sha256"],
    }


def load_unit_raster(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
    return np.where(np.isfinite(arr), np.clip(arr, 0.0, 1.0), 0.0)


def uniqueness_gate(candidate: Path, comparators: list[Path]) -> dict:
    with rasterio.open(candidate) as ds:
        shape = ds.shape
    cand = load_unit_raster(candidate)
    ours = cand > 0
    cand_kernel = EX.kernel_credit_field(ours)
    cand_sha = sha256(candidate)
    rows, skipped = [], []
    for comp in comparators:
        comp = Path(comp)
        try:
            with rasterio.open(comp) as ds:
                if ds.shape != shape or ds.count != 1:
                    skipped.append({"file": str(comp), "reason": f"grid {ds.shape} x{ds.count} != candidate {shape}"})
                    continue
        except Exception as exc:  # unreadable comparator is reported, not ignored
            skipped.append({"file": str(comp), "reason": f"unreadable: {exc}"})
            continue
        other = load_unit_raster(comp)
        theirs = other > 0
        if not theirs.any():
            skipped.append({"file": str(comp), "reason": "no positive cells"})
            continue
        overlap = float((EX.kernel_credit_field(theirs)[ours] > 0).mean())
        reverse = float((cand_kernel[theirs] > 0).mean())
        rho = spearmanr(other[::STRIDE, ::STRIDE].ravel(), cand[::STRIDE, ::STRIDE].ravel()).statistic
        rho = float(rho) if np.isfinite(rho) else 0.0
        rows.append({
            "file": comp.name,
            "sha256": sha256(comp),
            "exact_duplicate": sha256(comp) == cand_sha,
            "n_positive_comparator": int(theirs.sum()),
            "share_our_dots_within_3px": round(overlap, 6),
            "share_their_dots_within_3px": round(reverse, 6),
            "spearman": round(rho, 6),
            "violates_overlap": overlap > LIMIT_OVERLAP,
            "violates_spearman": abs(rho) > LIMIT_ABS_SPEARMAN,
        })
    rows.sort(key=lambda r: -r["share_our_dots_within_3px"])
    max_overlap = rows[0]["share_our_dots_within_3px"] if rows else None
    max_abs_rho = max((abs(r["spearman"]) for r in rows), default=None)
    any_dup = any(r["exact_duplicate"] for r in rows)
    passed = bool(rows) and not any_dup and not any(r["violates_overlap"] or r["violates_spearman"] for r in rows)
    return {
        "passed": passed,
        "limit_share_within_3px": LIMIT_OVERLAP,
        "limit_abs_spearman": LIMIT_ABS_SPEARMAN,
        "n_compared": len(rows),
        "n_skipped": len(skipped),
        "max_share_our_dots_within_3px": max_overlap,
        "max_abs_spearman": max_abs_rho,
        "exact_duplicates": [r["file"] for r in rows if r["exact_duplicate"]],
        "closest_comparators": rows[:5],
        "skipped": skipped,
        "all_comparators": rows,
    }


def registry_paths(extra_dirs: list[Path], include_repo: bool, candidate: Path) -> list[Path]:
    found: dict[str, Path] = {}
    if include_repo:
        for p in ROOT.rglob("*.tif"):
            if ".venv" in p.parts or ".git" in p.parts or p.resolve() == candidate.resolve():
                continue
            found.setdefault(str(p.resolve()), p)
    for d in extra_dirs:
        for p in sorted(Path(d).glob("*.tif")):
            if p.resolve() != candidate.resolve():
                found.setdefault(str(p.resolve()), p)
    # Identical bytes in two places are one comparator; keep the first path (sorted).
    by_hash: dict[str, Path] = {}
    for k in sorted(found):
        by_hash.setdefault(sha256(found[k]), found[k])
    return sorted(by_hash.values(), key=lambda q: str(q))


def validate(candidate: Path, sample: Path, comparators: list[Path]) -> dict:
    fmt = format_gate(candidate, sample)
    uniq = uniqueness_gate(candidate, comparators)
    verdict = "PASS" if fmt["passed"] and uniq["passed"] else "FAIL"
    return {
        "schema": SCHEMA,
        "evidence_class": EVIDENCE_CLASS,
        "candidate": str(candidate.resolve().relative_to(ROOT)) if candidate.resolve().is_relative_to(ROOT) else str(candidate),
        "candidate_sha256": sha256(candidate),
        "candidate_bytes": candidate.stat().st_size,
        "sample": str(sample.resolve().relative_to(ROOT)) if sample.resolve().is_relative_to(ROOT) else str(sample),
        "format_gate": fmt,
        "uniqueness_gate": uniq,
        "verdict": verdict,
        "verdict_scope": "format + uniqueness only; the score is unknown until an organizer receipt exists",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--registry-dir", type=Path, action="append", default=[],
                    help="directory of comparator .tif files (repeatable)")
    ap.add_argument("--include-repo-tifs", action="store_true",
                    help="also compare against every other .tif in this repository")
    ap.add_argument("--out", type=Path, help="write the JSON record here")
    args = ap.parse_args(argv)
    comps = registry_paths(args.registry_dir, args.include_repo_tifs, args.candidate)
    record = validate(args.candidate, args.sample, comps)
    text = json.dumps(record, indent=1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    summary = {k: record[k] for k in ("candidate_sha256", "verdict")}
    summary["format_passed"] = record["format_gate"]["passed"]
    summary["uniqueness_passed"] = record["uniqueness_gate"]["passed"]
    summary["n_compared"] = record["uniqueness_gate"]["n_compared"]
    summary["n_skipped"] = record["uniqueness_gate"]["n_skipped"]
    summary["max_share_our_dots_within_3px"] = record["uniqueness_gate"]["max_share_our_dots_within_3px"]
    print(json.dumps(summary, indent=1))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
