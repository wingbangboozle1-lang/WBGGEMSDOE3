"""Prepare the competition data stack.

Catalogues rasters in data/raw/ and writes data/manifest.json with CRS, shape,
transform and dtype for each raster. Does not download anything (competition
data requires DrivenData login).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import rasterio

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_ROOT / "raw"
MANIFEST_PATH = DATA_ROOT / "manifest.json"

EXPECTED_FILES = {
    "training_features.tif": "stack of numerical predictor features",
    "labels.tif": "binary target / training labels",
    "sample_submission.tif": "submission format grid (CRS, shape, transform)",
    "existing_faults.tif": "mapped fault catalogue raster",
    "1m_DEM_links.csv": "DEM download links (JSON/CSV pointer)",
    "gems-geodawn-numerical-features.tif": "GEODAWN magnetic & radiometric features",
}


def describe_raster(path):
    with rasterio.open(path) as src:
        return {
            "path": str(path),
            "driver": src.driver,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtype": str(src.dtypes[0]) if src.count else None,
            "crs": str(src.crs) if src.crs else None,
            "transform": [round(v, 6) for v in src.transform.to_gdal()],
            "bounds": [round(v, 2) for v in src.bounds],
            "nodata": src.nodata,
        }


def main():
    if not RAW_DIR.exists():
        print(f"[prepare_data] raw data dir not found: {RAW_DIR}")
        print("[prepare_data] Place competition rasters in data/raw/ first.")
        print("[prepare_data] See scripts/download_competition_data.sh for sources.")
        return 1

    tifs = sorted(RAW_DIR.glob("*.tif")) + sorted(RAW_DIR.glob("*.TIF"))
    if not tifs:
        print(f"[prepare_data] no .tif files found in {RAW_DIR}")
        return 1

    manifest = {"data_root": str(DATA_ROOT), "rasters": {}}
    reference = None
    for tif in tifs:
        try:
            info = describe_raster(tif)
            info["description"] = EXPECTED_FILES.get(tif.name, "user-supplied raster")
            manifest["rasters"][tif.name] = info
            if tif.name == "sample_submission.tif":
                reference = tif
            print(f"[prepare_data] catalogued {tif.name}: "
                  f"{info['width']}x{info['height']}, bands={info['count']}, "
                  f"crs={info['crs']}, dtype={info['dtype']}")
        except Exception as exc:
            print(f"[prepare_data] WARNING: could not read {tif.name}: {exc}")
            manifest["rasters"][tif.name] = {"error": str(exc)}

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"[prepare_data] manifest written to {MANIFEST_PATH}")
    print(f"[prepare_data] {len(tifs)} raster(s) catalogued.")
    if reference:
        print(f"[prepare_data] reference grid: {reference.name}")
    else:
        print("[prepare_data] NOTE: sample_submission.tif not present; "
              "CRS/shape/transform matching cannot be verified until it is added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
