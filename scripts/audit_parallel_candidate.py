#!/usr/bin/env python3
"""Audit a concurrently committed research TIFF against the registered lattice.

This is a read-only byte/overlap audit, not a model run or competition score.
The pinned sample is an owner mirror, not organizer-authenticated data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

from github_bytes import fetch_pinned, sha256
from validate_raster import validate

ROOT = Path(__file__).resolve().parents[1]
PRIOR_MAIN = "966b9ad722df057ca21ac5d6666c54e4626c957c"
REGISTRY_SHA = "846eddb9459f0e5b67f33da519bbd62c966bf5f539545ba3dad262fbfbc308c2"
RASTERS = [
    ("docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-zeros.tif",
     "5d4515665dc8f3f31aa0249a32a56002f86aef199c2033cb39d836bc41adb059"),
    ("docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-nan.tif",
     "58b34e2a24df99bc2857df2e6248075d65955592cd838e8e20dad2d1c1cfbd5a"),
    ("docs/downloads/wb-gems-doe-3-latest-submission-zeros.tif",
     "5d4515665dc8f3f31aa0249a32a56002f86aef199c2033cb39d836bc41adb059"),
]


def run(output: Path) -> dict:
    sources = json.loads((ROOT / "config/data-sources.json").read_text())
    hashes = {row["dest"]: row["sha256"] for row in sources["files"]}
    sample = ROOT / "data/raw/sample_submission.tif"
    lattice = ROOT / "data/raw/registry-lattice.tif"
    if sha256(sample) != hashes["sample_submission.tif"] or sha256(lattice) != hashes["registry-lattice.tif"]:
        raise ValueError("Sample or lattice hash mismatch; restore the pinned mirrors first")
    registry_path = ROOT / "data/cache/shared-registry-57.json"
    fetch_pinned("buffedlizard55-lab/57GEMSDOE", "822a0ce5546c7b6749cdd82eb145b6b3e616603d",
                 "docs/data/registry_refreshed.json", registry_path, REGISTRY_SHA, 339283)
    registry = json.loads(registry_path.read_text())
    if not any(row.get("sha256") == hashes["registry-lattice.tif"] for row in registry["rasters"]):
        raise ValueError("Witness missing from pinned registry")

    with rasterio.open(sample) as template, rasterio.open(lattice) as witness:
        if (template.shape, template.crs, template.transform) != (witness.shape, witness.crs, witness.transform):
            raise ValueError("Template/witness grid mismatch")
        footprint = template.read_masks(1) > 0
        grid = (template.shape, template.crs, template.transform)
        witness_dots = footprint & (witness.read(1) > 0)
    yy, xx = np.ogrid[-3:4, -3:4]
    halo = binary_dilation(witness_dots, structure=yy * yy + xx * xx <= 9)
    outputs = []
    for relative, digest in RASTERS:
        path = ROOT / relative
        if sha256(path) != digest:
            raise ValueError(f"Candidate bytes changed: {relative}")
        with rasterio.open(path) as raster:
            if raster.count != 1 or (raster.shape, raster.crs, raster.transform) != grid:
                raise ValueError(f"Candidate grid mismatch: {relative}")
            a = raster.read(1)
            in_dots = footprint & np.isfinite(a) & (a > 0)
            out_dots = ~footprint & np.isfinite(a) & (a > 0)
            inside = int(in_dots.sum())
            covered = int((in_dots & halo).sum())
            if inside == 0:
                raise ValueError("No in-footprint positive pixels; overlap undefined")
            nodata = "NaN" if raster.nodata is not None and np.isnan(raster.nodata) else raster.nodata
        format_report = validate(path, sample)
        format_report["artifact"] = relative
        outputs.append({
            "file": relative, "sha256": digest, "nodata_metadata": nodata,
            "positive_pixels_inside_mirrored_footprint": inside,
            "positive_pixels_outside_mirrored_footprint": int(out_dots.sum()),
            "positive_pixels_inside_lattice_halo": covered,
            "directional_overlap_inside_footprint": covered / inside,
            "duplicate_stop": 10 * covered > 7 * inside,
            "local_format_validator": format_report,
        })
    report = {
        "evidence_class": "RASTER AUDIT; NOT HOLDOUT-DTI OR ORGANIZER SCORE",
        "source_main_commit": PRIOR_MAIN,
        "witness_sha256": hashes["registry-lattice.tif"],
        "registry_sha256": REGISTRY_SHA,
        "scope": "Measured final dots against one pinned registry witness; no surface replay or full-registry pass.",
        "radius_px_euclidean_inclusive": 3,
        "prior_claim": "A subset-only report claimed UNIQUE PASS; its result did not account for this registered lattice witness.",
        "qualification": "Footprint is from an owner mirror, not organizer-authenticated. Local mask failure is not proof of portal rejection.",
        "rasters": outputs,
        "verdict": "DUPLICATE STOP — all three files are research/audit only, not eligible for submission",
        "ok_to_submit": False,
        "holdout_dti": None,
        "organizer_receipt": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/concurrent-candidate-audit.json")
    args = parser.parse_args()
    report = run(args.output)
    for item in report["rasters"]:
        print(item["file"], "inside dots:", item["positive_pixels_inside_mirrored_footprint"],
              "outside dots:", item["positive_pixels_outside_mirrored_footprint"],
              "lattice overlap:", item["directional_overlap_inside_footprint"],
              "duplicate:", item["duplicate_stop"])
    print("Wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
