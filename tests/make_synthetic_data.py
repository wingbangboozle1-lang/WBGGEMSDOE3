"""Create a synthetic stand-in competition data grid for pipeline testing.

This is NOT real competition data. It exercises the full train/holdout/
validate/write pipeline so every script can be verified end-to-end before
real data is available.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SHAPE = (400, 600)  # rows, cols
PIXEL = 30.0
CRS = CRS.from_epsg(32611)
TRANSFORM = from_bounds(240000, 4300000, 240000 + SHAPE[1] * PIXEL,
                        4300000 - SHAPE[0] * PIXEL, SHAPE[1], SHAPE[0])


def write_tif(path, array, crs=CRS, transform=TRANSFORM, dtype=np.float32,
              count=1, nodata=None):
    profile = {"driver": "GTiff", "dtype": np.dtype(dtype).name, "width": array.shape[1],
               "height": array.shape[0], "count": count, "crs": crs,
               "transform": transform, "compress": "deflate"}
    if nodata is not None:
        profile["nodata"] = nodata
    dt = np.dtype(dtype)
    with rasterio.open(path, "w", **profile) as dst:
        for b in range(count):
            band = array[b] if count > 1 else array
            dst.write(band.astype(dt), b + 1)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    rows, cols = SHAPE
    y, x = np.mgrid[0:rows, 0:cols]

    # Synthetic "true faults": a few linear features
    faults = np.zeros((rows, cols), dtype=np.float32)
    # fault A: diagonal
    for i in range(cols):
        j = int(0.5 * rows + 0.3 * (i - cols / 2))
        if 0 <= j < rows:
            faults[j, i] = 1.0
            faults[max(0, j - 1):j + 2, i] = 1.0
    # fault B: curved
    for i in range(cols):
        j = int(0.3 * rows + 40 * np.sin((i / cols) * 2 * np.pi))
        if 0 <= j < rows:
            faults[j, i] = 1.0

    # synthetic target labels: fault zones + some blind cells not in faults
    labels = np.zeros((rows, cols), dtype=np.float32)
    from scipy import ndimage as ndi
    labels = ndi.binary_dilation(faults > 0, iterations=4).astype(np.float32)
    # add blind geothermal cells (not in catalogue faults)
    blind_cx, blind_cy = cols * 0.75, rows * 0.3
    d = np.hypot(x - blind_cx, y - blind_cy)
    blind = (d < 25).astype(np.float32)
    labels = np.clip(labels + blind, 0, 1)

    # feature stack: distance to fault + curvature-ish + noise
    dist = ndi.distance_transform_edt(faults == 0) * PIXEL
    feat_dist = np.clip(1.0 - dist / 600.0, 0, 1).astype(np.float32)
    feat_noise = rng.standard_normal((rows, cols)).astype(np.float32)
    feat_stack = np.stack([feat_dist, feat_noise], axis=0)

    # sample submission grid: zeros, same shape/transform/crs
    sample = np.zeros((rows, cols), dtype=np.float32)

    write_tif(RAW_DIR / "existing_faults.tif", faults)
    write_tif(RAW_DIR / "labels.tif", labels)
    write_tif(RAW_DIR / "training_features.tif", feat_stack, count=2)
    write_tif(RAW_DIR / "sample_submission.tif", sample)

    print(f"[make_synthetic_data] wrote {RAW_DIR}")
    print(f"  existing_faults.tif   shape={faults.shape}")
    print(f"  labels.tif            shape={labels.shape}, positives={int(labels.sum())}")
    print(f"  training_features.tif bands=2")
    print(f"  sample_submission.tif shape={sample.shape}")


if __name__ == "__main__":
    main()
