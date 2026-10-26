"""Competition grid constants + loaders.  All numbers are re-measured from the data, then asserted."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_FOOT_PX = 5_167_373          # finite cells of sample_submission.tif (measured 2026-10-26)
EXPECTED_CATALOGUE_PX = 60_988        # labels==1
SENTINEL = -3.4028234663852886e38     # training_features.tif declared nodata (float32 min)


@dataclass
class Grid:
    foot: np.ndarray       # bool, scoring footprint = finite cells of the template
    labels: np.ndarray     # bool, known USGS/INGENIOUS catalogue pixels (masked by the organizer when scoring)
    profile: dict          # rasterio profile of the template


def load_grid(raw: Path = RAW) -> Grid:
    with rasterio.open(raw / "sample_submission.tif") as ds:
        tpl = ds.read(1)
        prof = ds.profile
    with rasterio.open(raw / "labels.tif") as ds:
        lab = ds.read(1)
    foot = np.isfinite(tpl)
    labels = (lab == 1) & foot
    assert tpl.shape == EXPECTED_SHAPE, tpl.shape
    assert int(foot.sum()) == EXPECTED_FOOT_PX, int(foot.sum())
    assert int(labels.sum()) == EXPECTED_CATALOGUE_PX, int(labels.sum())
    assert prof["crs"].to_epsg() == 32611
    return Grid(foot=foot, labels=labels, profile=prof)


def read_band(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(band)


def clean_feature(a: np.ndarray) -> np.ndarray:
    """float32 band -> float32 with the -3.4e38 sentinel and non-finite values turned into NaN."""
    a = a.astype(np.float32, copy=True)
    a[~np.isfinite(a) | (a < -1e30)] = np.nan
    return a
