#!/usr/bin/env python3
"""Conservative byte-level GeoTIFF preflight; never authorizes a slot.

The default template is a pinned owner mirror, not an authenticated organizer
file. The local policy requires all raw cells finite in [0,1] and the footprint
represented by an internal mask. Organizer acceptance of that encoding remains
unverified; an unmasked all-finite file may still be accepted by the portal.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio

from github_bytes import sha256

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def validate(path: Path, template_path: Path, *, expected_template_sha256: str | None = TEMPLATE_SHA256) -> dict:
    path, template_path = Path(path), Path(template_path)
    template_hash, artifact_hash = sha256(template_path), sha256(path)
    errors: list[str] = []
    if expected_template_sha256 is not None and template_hash != expected_template_sha256:
        errors.append("template SHA-256 does not match the pinned mirror")
    if path.suffix.lower() != ".tif":
        errors.append("filename must end in .tif")
    counts = {"cells": 0, "footprint_cells": 0, "nonfinite_inside": 0,
              "out_of_range_inside": 0, "nonfinite_all": 0, "out_of_range_finite_all": 0,
              "invalid_inside_mask": 0, "valid_outside_mask": 0, "nonzero_outside": 0}
    minimum, maximum = math.inf, -math.inf
    with rasterio.open(template_path) as template, rasterio.open(path) as candidate:
        checks = {
            "geotiff_driver": candidate.driver == "GTiff" and template.driver == "GTiff",
            "one_band": candidate.count == 1,
            "float32": candidate.count == 1 and candidate.dtypes[0] == "float32",
            "shape_matches": candidate.shape == template.shape,
            "crs_matches": candidate.crs is not None and candidate.crs == template.crs,
            "transform_matches": candidate.transform == template.transform,
            "template_one_band": template.count == 1,
            "template_sha256_matches": expected_template_sha256 is None or template_hash == expected_template_sha256,
            "no_external_mask_sidecar": not any(str(p).lower().endswith(".msk") for p in candidate.files),
            "single_file_dataset": len(candidate.files) == 1 and Path(candidate.files[0]).resolve() == path.resolve(),
        }
        for name, ok in checks.items():
            if not ok:
                errors.append(name)
        if candidate.count == 1 and checks["shape_matches"] and template.count == 1:
            for _, window in template.block_windows(1):
                footprint = template.read_masks(1, window=window) > 0
                values = candidate.read(1, window=window)
                candidate_mask = candidate.read_masks(1, window=window) > 0
                finite = np.isfinite(values)
                bad_range = finite & ((values < 0) | (values > 1))
                counts["cells"] += int(values.size)
                counts["footprint_cells"] += int(footprint.sum())
                counts["nonfinite_inside"] += int(np.count_nonzero(footprint & ~finite))
                counts["out_of_range_inside"] += int(np.count_nonzero(footprint & bad_range))
                counts["nonfinite_all"] += int(np.count_nonzero(~finite))
                counts["out_of_range_finite_all"] += int(np.count_nonzero(bad_range))
                counts["invalid_inside_mask"] += int(np.count_nonzero(footprint & ~candidate_mask))
                counts["valid_outside_mask"] += int(np.count_nonzero(~footprint & candidate_mask))
                counts["nonzero_outside"] += int(np.count_nonzero(~footprint & finite & (values != 0)))
                inside = values[footprint & finite]
                if inside.size:
                    minimum = min(minimum, float(inside.min()))
                    maximum = max(maximum, float(inside.max()))
    checks["bytes_unchanged_during_validation"] = sha256(path) == artifact_hash
    if not checks["bytes_unchanged_during_validation"]:
        errors.append("bytes_unchanged_during_validation")
    if counts["footprint_cells"] == 0:
        errors.append("missing or unreadable footprint")
    for name in ("nonfinite_inside", "out_of_range_inside", "nonfinite_all", "out_of_range_finite_all",
                 "invalid_inside_mask", "valid_outside_mask", "nonzero_outside"):
        if counts[name]:
            errors.append(name)
    return {
        "validator_version": "wbggemsdoe3-format-v1",
        "artifact": str(path), "artifact_sha256": artifact_hash,
        "template_sha256": template_hash, "metadata_checks": checks, "counts": counts,
        "min_inside": minimum if math.isfinite(minimum) else None,
        "max_inside": maximum if math.isfinite(maximum) else None,
        "format_gate_pass": not errors, "failures": errors,
        "scope": "Conservative local format check only. Neither organizer acceptance, geological merit, uniqueness, nor slot permission is established.",
        "outside_policy": "All raw cells finite [0,1]; exact footprint encoded in a mask contained inside the TIFF; zero-valued outside. Portal behavior not confirmed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tif", type=Path)
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--output", type=Path, help="write JSON receipt")
    args = parser.parse_args()
    try:
        result = validate(args.tif, args.template)
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        result = {"validator_version": "wbggemsdoe3-format-v1", "format_gate_pass": False,
                  "failures": [str(exc)], "artifact": str(args.tif)}
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if result["format_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
