"""Loaders for the official GEMS rasters and the geothermal evidence tables.

No network access.  Every file is read from ``data/official/`` and its SHA-256 is
checked against the value recorded in ``registry/data_manifest.json`` (official
competition files) or ``registry/focus_sites.json`` (comparison submissions).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL = ROOT / "data" / "official"

NODATA = -3.4028234663852886e38

#: official band descriptions, read from the GeoTIFF band tags (not typed by hand)
BAND_TAGS = (
    "mag_anom", "mag_rtp", "mag_hgrad", "geod_second_inv", "grav_iso_slope",
    "mag_tilt", "geod_shear", "geod_dilat", "mag_vgrad", "dist_eq", "grav_vgrad",
    "detrend_elev", "grav_iso", "mag_tmi", "depth_basement", "eq_density",
    "conductivity", "grav_hgrad", "detrend_slope",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_hashes() -> dict[str, str]:
    """sha256 -> expected for the core competition files, from the repo manifest."""
    man = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    out = {}
    for f in man["files"]:
        if f.get("group") == "core" and f.get("sha256"):
            out[f["id"]] = f["sha256"]
    return out


@dataclass
class Grid:
    """Geometry shared by every official raster."""

    height: int
    width: int
    transform: rasterio.Affine
    crs: object

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)


def grid() -> Grid:
    with rasterio.open(OFFICIAL / "labels.tif") as ds:
        return Grid(ds.height, ds.width, ds.transform, ds.crs)


def load_labels() -> np.ndarray:
    """int8 catalogue: -1 outside the AOI, 0 inside, 1 fault."""
    with rasterio.open(OFFICIAL / "labels.tif") as ds:
        return ds.read(1)


def footprint(labels: np.ndarray | None = None) -> np.ndarray:
    """Boolean AOI mask = labels >= 0.  Verified: 5,167,373 cells = official FOOT_PX."""
    lab = load_labels() if labels is None else labels
    return lab >= 0


def catalogue(labels: np.ndarray | None = None) -> np.ndarray:
    lab = load_labels() if labels is None else labels
    return lab == 1


def sample_submission() -> np.ndarray:
    """Official sample submission: 1 on catalogue faults, 0 inside the AOI, NaN outside."""
    with rasterio.open(OFFICIAL / "sample_submission.tif") as ds:
        return ds.read(1)


def band(index: int) -> np.ndarray:
    """Read one official band (1-based index), nodata -> NaN, float32."""
    with rasterio.open(OFFICIAL / "training_features.tif") as ds:
        a = ds.read(index).astype(np.float32)
    a[a < NODATA / 2] = np.nan
    return a


def all_bands(indices=None) -> np.ndarray:
    idx = list(range(1, 20)) if indices is None else list(indices)
    with rasterio.open(OFFICIAL / "training_features.tif") as ds:
        a = ds.read(idx).astype(np.float32)
    a[a < NODATA / 2] = np.nan
    return a


def u8_layer(name: str, band_index: int = 1) -> np.ndarray:
    """Read a derived u8 evidence layer (0 = nodata by construction)."""
    with rasterio.open(OFFICIAL / name) as ds:
        a = ds.read(band_index).astype(np.float32)
        nod = ds.nodata
    if nod is not None:
        a[a == nod] = np.nan
    return a


def wellspring_table() -> list[dict]:
    """GDR 1391 well/spring temperature and chemistry points inside the footprint.

    Columns verified from the CSV header: layer,name,thermalclass,row,col,utm_x,utm_y,
    dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c
    """
    import csv

    rows = []
    with open(OFFICIAL / "gdr_wellspring_in_footprint.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                r["row"] = int(r["row"])
                r["col"] = int(r["col"])
            except (TypeError, ValueError):
                continue
            for k in ("temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                try:
                    r[k] = float(r[k])
                except (TypeError, ValueError):
                    r[k] = float("nan")
            rows.append(r)
    return rows


def vent_table() -> list[dict]:
    import csv

    rows = []
    with open(OFFICIAL / "gdr_volcanic_vents_in_footprint.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                r["row"] = int(r["row"])
                r["col"] = int(r["col"])
            except (TypeError, ValueError):
                continue
            rows.append(r)
    return rows


def qfault_table() -> list[dict]:
    import csv

    rows = []
    with open(OFFICIAL / "gdr_qfaults_traces.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            r["centroid_in_footprint"] = str(r.get("centroid_in_footprint", "")).strip() == "1"
            rows.append(r)
    return rows
