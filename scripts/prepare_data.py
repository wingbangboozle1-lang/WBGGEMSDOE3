#!/usr/bin/env python3
"""Verify, but do not rebuild, the shared inputs and cached feature stack.

The shared receipt contains hashes, not the 19 arrays. Exit 2 even if local
files match: official provenance and code reuse permission are not verified here.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

from github_bytes import sha256

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "config/data-sources.json").read_text())
    feature_receipt = json.loads((ROOT / "config/shared-feature-receipt.json").read_text())
    if sha256(ROOT / "config/shared-feature-receipt.json") != "9195d416f11a37d11aaf0980926e21b605c1993ac715a5fd8be824068e515639":
        raise ValueError("shared feature receipt hash mismatch")
    files = manifest["files"] + [manifest["training_features"]]
    checks = {}
    for item in files:
        path = ROOT / "data/raw" / item["dest"]
        checks[item["dest"]] = bool(path.is_file() and path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"])
    cache = []
    for band in feature_receipt["bands"]:
        path = ROOT / "data/cache/shared-features" / f"band-{band['band']:02}.npy"
        cache.append({"band": band["band"], "path": str(path.relative_to(ROOT)),
                      "verified": path.is_file() and sha256(path) == band["sha256"]})
    grid = None
    sample_matches_catalogue = None
    if checks["sample_submission.tif"] and checks["existing_faults.tif"]:
        with rasterio.open(ROOT / "data/raw/sample_submission.tif") as sample, rasterio.open(ROOT / "data/raw/existing_faults.tif") as fault:
            same_grid = (sample.shape, sample.crs, sample.transform) == (fault.shape, fault.crs, fault.transform)
            valid = sample.read_masks(1) > 0
            # One-time diagnostic only. Never use the sample's values for features.
            sample_positive = valid & (sample.read(1) > 0)
            mapped = valid & (fault.read(1) == 1)
            sample_matches_catalogue = bool(np.array_equal(sample_positive, mapped))
            grid = {"shape": list(sample.shape), "crs": str(sample.crs),
                    "transform": list(tuple(sample.transform)[:6]),
                    "footprint_pixels": int(valid.sum()), "grid_match": same_grid,
                    "sample_positive_pixels": int(sample_positive.sum()),
                    "known_fault_pixels": int(mapped.sum())}
    training_grid_matches = False
    if grid and checks["training_features.tif"]:
        with rasterio.open(ROOT / "data/raw/training_features.tif") as feature:
            training_grid_matches = (list(feature.shape) == grid["shape"] and
                                     str(feature.crs) == grid["crs"] and
                                     list(tuple(feature.transform)[:6]) == grid["transform"] and
                                     feature.count == 19)
    tools_dir = ROOT / "data/cache/shared-template/gems57"
    required = [x for x in json.loads((ROOT / "config/shared-template.json").read_text())["files"]
                if x["upstream_path"].startswith("src/gems57/")]
    tools_verified = all((tools_dir / Path(x["upstream_path"]).name).is_file() and
                         sha256(tools_dir / Path(x["upstream_path"]).name) == x["sha256"]
                         for x in required)
    cache_ready = len(cache) == 19 and all(item["verified"] for item in cache)
    local_files_ready = all(checks.values()) and bool(grid and grid["grid_match"]) and training_grid_matches and tools_verified and cache_ready
    # Integrity of public mirrors is not proof that these bytes were obtained
    # from the organizer or that the unlicensed shared code may be reused.
    # No authenticated-data or permission verification has been implemented.
    ready = False
    result = {
        "evidence_class": "DATA-READINESS; NOT A SCORE", "computed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "local_file_prerequisites_passed": local_files_ready,
        "ready_for_holdout": ready,
        "ready_for_holdout_reason": "Official provenance and authorization to reuse the shared code are not verified by this script.",
        "raw_owner_mirror_checks": checks, "grid": grid, "training_grid_matches": training_grid_matches,
        "shared_template_unchanged": tools_verified, "feature_cache": cache,
        "sample_equals_existing_faults": sample_matches_catalogue,
        "sample_warning": "The owner-mirrored 'sample' positives match known labels, unlike the official page's zero-sample wording. Use its mask/grid only; official provenance not verified.",
        "missing": manifest["missing"], "experiments_run": 0,
        "license_warning": "No license was identified for the shared owner code; confirm permission before reuse or redistribution.",
    }
    output = ROOT / "evidence/data-readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"ready_for_holdout": ready, "local_file_prerequisites_passed": local_files_ready,
                      "raw_inputs_verified": all(checks.values()),
                      "cache_bands_verified": sum(int(x["verified"]) for x in cache),
                      "template_code_verified": tools_verified, "receipt": str(output)}, indent=2))
    print("Blocked: shared feature cache, official provenance and code reuse permission must be established; "
          "do not rebuild the cache as a private fork.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
