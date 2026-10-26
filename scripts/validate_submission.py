#!/usr/bin/env python3
"""Strict saved-byte GeoTIFF preflight for the DOE GEMS submission format.

This tool checks raster geometry, one-band float32 data, finite values in [0, 1],
zero-valued cells outside the template footprint, an absent NoData tag, and zero overlap
with the provided known-fault label mask. A PASS means only that these byte-level
checks passed. This script never evaluates a spatial holdout, novelty, leakage, a
competition score, or weekly-slot eligibility, and it never authorizes submission.

Example:
    python scripts/validate_submission.py candidate.tif \
        --template data/sample_submission.tif --labels data/labels.tif
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


FORMAT_CHECKS = (
    "single_band",
    "float32",
    "shape_matches_template",
    "template_footprint_nonempty",
    "crs_matches_template",
    "crs_is_epsg32611",
    "transform_matches_template",
    "finite_inside_footprint",
    "finite_everywhere",
    "values_in_range_0_1",
    "zero_outside_footprint",
    "nodata_tag_absent",
)


def _transform_tuple(transform: Any) -> list[float]:
    return [float(v) for v in tuple(transform)[:6]]


def _nodata_label(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if np.isnan(value):
            return "NaN"
    except TypeError:
        pass
    return str(value)


def _failure_report(candidate: Path, template: Path, labels: Path, message: str) -> dict[str, Any]:
    checks = {name: None for name in FORMAT_CHECKS}
    return {
        "schema_version": 1,
        "validation_type": "saved-byte submission-format preflight; not a score",
        "candidate": str(candidate),
        "template": str(template),
        "labels": str(labels),
        "format_checks": checks,
        "format_passed": False,
        "catalogue_check": {"available": False, "passed": None},
        "errors": [message],
        "submission_authorized": False,
        "authorization_reason": (
            "Format validation alone cannot establish HOLDOUT-DTI superiority, leakage safety, "
            "registry uniqueness, or weekly-slot approval."
        ),
    }


def validate_submission(
    candidate_path: str | Path,
    template_path: str | Path,
    labels_path: str | Path,
) -> dict[str, Any]:
    """Validate a candidate against the exact template grid and known-fault mask.

    Every pixel is checked for finiteness and [0, 1] range, including pixels outside
    the template footprint, because non-finite samples have caused the competition
    portal's range error. Values outside the footprint must be exactly zero. The output
    can never authorize a competition upload.
    """
    candidate = Path(candidate_path)
    template = Path(template_path)
    labels = Path(labels_path)
    missing = [str(p) for p in (candidate, template, labels) if not p.is_file()]
    if missing:
        return _failure_report(candidate, template, labels, "Missing required file(s): " + ", ".join(missing))

    try:
        with rasterio.open(template) as reference:
            if reference.count != 1:
                return _failure_report(
                    candidate, template, labels,
                    f"Template must be single-band; found {reference.count} bands.",
                )
            reference_array = reference.read(1, masked=False)
            footprint = (reference.read_masks(1) > 0) & np.isfinite(reference_array)
            ref_shape = tuple(reference.shape)
            ref_crs = reference.crs
            ref_transform = _transform_tuple(reference.transform)

        with rasterio.open(candidate) as src:
            candidate_array = src.read(1, masked=False) if src.count >= 1 else np.empty((0, 0))
            metadata = {
                "bands": int(src.count),
                "dtype": src.dtypes[0] if src.count else None,
                "shape": [int(v) for v in src.shape],
                "crs": str(src.crs) if src.crs is not None else None,
                "transform": _transform_tuple(src.transform),
                "nodata": _nodata_label(src.nodata),
            }
            checks: dict[str, bool] = {
                "single_band": src.count == 1,
                "float32": src.count == 1 and src.dtypes[0] == "float32",
                "shape_matches_template": tuple(src.shape) == ref_shape,
                "template_footprint_nonempty": bool(footprint.any()),
                "crs_matches_template": src.crs == ref_crs,
                "crs_is_epsg32611": src.crs is not None and src.crs.to_epsg() == 32611,
                "transform_matches_template": _transform_tuple(src.transform) == ref_transform,
                "finite_inside_footprint": False,
                "finite_everywhere": False,
                "values_in_range_0_1": False,
                "zero_outside_footprint": False,
                "nodata_tag_absent": src.nodata is None,
            }

        errors: list[str] = []
        aligned = candidate_array.shape == footprint.shape
        if not aligned:
            errors.append(f"Candidate array shape {candidate_array.shape} does not match template {footprint.shape}.")
            minimum = maximum = None
        else:
            finite = np.isfinite(candidate_array)
            checks["finite_inside_footprint"] = bool(finite[footprint].all())
            checks["finite_everywhere"] = bool(finite.all())
            if finite.any():
                finite_values = candidate_array[finite]
                checks["values_in_range_0_1"] = bool(
                    float(finite_values.min()) >= 0.0 and float(finite_values.max()) <= 1.0
                ) and bool(finite.all())
                minimum = float(finite_values.min())
                maximum = float(finite_values.max())
            else:
                minimum = maximum = None
            outside = ~footprint
            checks["zero_outside_footprint"] = bool(
                finite[outside].all() and np.count_nonzero(candidate_array[outside]) == 0
            )
            if not checks["finite_inside_footprint"]:
                errors.append("At least one non-finite prediction occurs inside the template footprint.")
            if not checks["finite_everywhere"]:
                errors.append("At least one non-finite prediction occurs anywhere in the file; the portal may reject it.")
            if not checks["values_in_range_0_1"]:
                errors.append("Predictions are not all finite and within [0, 1].")
            if not checks["zero_outside_footprint"]:
                errors.append("Predictions outside the template footprint must be exactly zero.")

        for key, description in (
            ("single_band", "Candidate must have exactly one band."),
            ("float32", "Candidate band must be float32."),
            ("shape_matches_template", "Candidate dimensions do not match the template."),
            ("template_footprint_nonempty", "Template has no valid finite footprint cells."),
            ("crs_matches_template", "Candidate CRS does not match the template."),
            ("crs_is_epsg32611", "Candidate CRS must be EPSG:32611."),
            ("transform_matches_template", "Candidate affine transform does not match the template exactly."),
            ("nodata_tag_absent", "Candidate must not declare a NoData value; use finite zero outside the footprint."),
        ):
            if not checks[key]:
                errors.append(description)

        with rasterio.open(labels) as label_src:
            label_alignment = (
                label_src.count == 1
                and tuple(label_src.shape) == ref_shape
                and label_src.crs == ref_crs
                and _transform_tuple(label_src.transform) == ref_transform
            )
            if not label_alignment:
                catalogue = {
                    "available": False,
                    "passed": False,
                    "reason": "Known-fault label grid does not exactly match the template.",
                    "positive_prediction_overlap": None,
                }
            elif not aligned:
                catalogue = {
                    "available": False,
                    "passed": None,
                    "reason": "Candidate/template arrays are not aligned; overlap was not evaluated.",
                    "positive_prediction_overlap": None,
                }
            else:
                label_array = label_src.read(1, masked=False)
                known = np.isfinite(label_array) & (label_array > 0) & footprint
                predicted = np.isfinite(candidate_array) & (candidate_array > 0) & footprint
                overlap = int(np.count_nonzero(known & predicted))
                catalogue = {
                    "available": True,
                    "passed": overlap == 0,
                    "reason": "No predicted positive pixels overlap the provided known-fault mask."
                    if overlap == 0 else "Predicted positive pixels overlap the known-fault mask.",
                    "positive_prediction_overlap": overlap,
                }
            if not catalogue["passed"]:
                errors.append(str(catalogue.get("reason")))

        format_passed = all(checks[name] for name in FORMAT_CHECKS)
        return {
            "schema_version": 1,
            "validation_type": "saved-byte submission-format preflight; not a score",
            "candidate": str(candidate),
            "template": str(template),
            "labels": str(labels),
            "candidate_metadata": metadata,
            "template_metadata": {
                "shape": [int(v) for v in ref_shape],
                "crs": str(ref_crs) if ref_crs is not None else None,
                "transform": ref_transform,
                "footprint_cells": int(footprint.sum()),
            },
            "format_checks": checks,
            "format_passed": bool(format_passed),
            "catalogue_check": catalogue,
            "statistics": {
                "minimum_finite_value": minimum,
                "maximum_finite_value": maximum,
                "positive_pixels_inside_footprint": (
                    int(np.count_nonzero(np.isfinite(candidate_array) & (candidate_array > 0) & footprint))
                    if aligned else None
                ),
                "non_finite_pixels_total": (
                    int(np.count_nonzero(~np.isfinite(candidate_array))) if aligned else None
                ),
            },
            "errors": errors,
            "submission_authorized": False,
            "authorization_reason": (
                "This preflight does not run the shared spatially-blocked HOLDOUT-DTI, per-feature leakage canary, "
                "pre-placement surface-correlation check, final-dot registry check, or separate weekly-slot selector."
            ),
        }
    except Exception as exc:  # Rasterio emits several backend-specific errors for corrupt inputs.
        return _failure_report(candidate, template, labels, f"Unable to validate raster inputs: {type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Candidate single-band GeoTIFF")
    parser.add_argument("--template", type=Path, required=True, help="Official sample_submission.tif")
    parser.add_argument("--labels", type=Path, required=True, help="Known catalogue labels/fault mask on the template grid")
    parser.add_argument("--out", type=Path, help="Optional path for the JSON report")
    args = parser.parse_args(argv)

    result = validate_submission(args.candidate, args.template, args.labels)
    text = json.dumps(result, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.get("format_passed") and result.get("catalogue_check", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
