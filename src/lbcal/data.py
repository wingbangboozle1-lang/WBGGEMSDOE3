"""Paths, grid loading and registry enumeration for the LBCAL lane.

All inputs are restored, SHA-checked caches (never committed):
  * shared 57GEMSDOE template (official rasters + cached 19-band feature stack),
    restored by ``scripts/restore_shared_data.sh``;
  * GEMSDOE24 external layers (LiDAR scarp descriptors, SGMC faults, TIGER roads),
    restored by ``scripts/restore_x24_external.py``;
  * scored/unscored registry rasters, restored by ``scripts/fetch_ledger_rasters.py``
    and ``scripts/fetch_addendum_rasters.py``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
BANDS_DIR = TEMPLATE / ".cache" / "features"
OFFICIAL = TEMPLATE / "data" / "official"
EXTERNAL_T = TEMPLATE / "data" / "external"
X24 = ROOT / ".cache" / "upstream" / "x24" / "data" / "external"
CACHE = ROOT / ".cache" / "lbcal"

SHAPE = (3730, 3292)
FOOTPRINT_PX = 5_167_373
CATALOGUE_PX = 60_988
SENTINEL_LIMIT = -1e30  # training_features nodata is float32 min (-3.4e38)

# Official band order of training_features.tif (descriptions read from the TIFF tags).
BAND = {
    "mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_anom_slope": 5,
    "tc": 6, "geod_shearrate": 7, "geod_dilaterate": 8, "tmi_vg": 9, "deq_n100a15": 10,
    "iso_grav_anom_vg": 11, "det_elev": 12, "iso_grav_anom": 13, "tmi": 14,
    "depth_to_base_surf": 15, "ieq_n100a15": 16, "cond_surf": 17, "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Grid:
    foot: np.ndarray        # bool, finite cells of the official sample submission
    cat: np.ndarray         # bool, catalogue (labels == 1) inside the footprint
    profile: dict
    sample_path: Path


def load_grid() -> Grid:
    sample = OFFICIAL / "sample_submission.tif"
    with rasterio.open(sample) as ds:
        s = ds.read(1)
        prof = ds.profile
    with rasterio.open(OFFICIAL / "labels.tif") as ds:
        lab = ds.read(1)
    foot = np.isfinite(s)
    cat = (lab == 1) & foot
    assert s.shape == SHAPE, s.shape
    assert int(foot.sum()) == FOOTPRINT_PX, int(foot.sum())
    assert int(cat.sum()) == CATALOGUE_PX, int(cat.sum())
    assert prof["crs"].to_epsg() == 32611
    return Grid(foot=foot, cat=cat, profile=prof, sample_path=sample)


def band(name: str) -> np.ndarray:
    """Cached float32 band with NaN for nodata (template cache, never modified)."""
    a = np.array(np.load(BANDS_DIR / f"band-{BAND[name]:02d}.npy", mmap_mode="r"), dtype=np.float32)
    a[~np.isfinite(a) | (a < SENTINEL_LIMIT)] = np.nan
    return a


def lidar() -> dict[str, np.ndarray]:
    with rasterio.open(X24 / "lidar_scarp_features_u8.tif") as ds:
        arr = ds.read()
    return {n: arr[i] for i, n in enumerate(LIDAR_BANDS)}


def read_binary_u8(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1) > 0


def read_prediction(path: Path) -> tuple[np.ndarray, dict]:
    """Prediction as float32 with non-finite -> 0; returns array and raw diagnostics."""
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
        nodata = ds.nodata
        info = dict(dtype=str(ds.dtypes[0]), count=ds.count, crs=str(ds.crs),
                    transform=tuple(ds.transform)[:6], shape=a.shape, nodata=nodata)
    finite = np.isfinite(a)
    info["n_nonfinite"] = int((~finite).sum())
    a = np.where(finite, a, 0.0).astype(np.float32)
    if nodata is not None and np.isfinite(nodata):
        a = np.where(a == np.float32(nodata), 0.0, a).astype(np.float32)
    info["min"] = float(a.min())
    info["max"] = float(a.max())
    return a, info


def registry_rows() -> list[dict]:
    """Every raster this lane must be unique against, with owner-reported score if any.

    Sources (all hash-pinned): the 118 verified ledger rasters, the 2026-10-27
    addendum, and this repository's own previously generated TIFFs.
    """
    rows: list[dict] = []
    led = ROOT / "data" / "ledger" / "index.json"
    if led.is_file():
        for r in json.loads(led.read_text()):
            if r.get("status") == "verified" and r.get("local"):
                rows.append(dict(site=r["site"], submission=r["submission"], score=r["score"],
                                 local=r["local"], sha256=r["sha256"], source="ledger-2026-10-26"))
    add = ROOT / "registry" / "ledger_addendum_2026-10-27.json"
    if add.is_file():
        for r in json.loads(add.read_text())["rows"]:
            rows.append(dict(site=r["site"], submission=r["submission"], score=r["score"],
                             local=r["local"], sha256=r["sha256"], source="addendum-2026-10-27"))
    own = [
        "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif",
        "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif",
        "submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif",
        "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif",
        "docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-zeros.tif",
        "docs/downloads/wb-gems-doe-3-latest-submission-zeros.tif",
        "archive/concurrent-8488b95/submissions/unique_submissions/gems-unique-h80-hydrothermal-conduit-20261026-000000Z-unique-sha.tif",
        "archive/site-legacy-2026-10-26/site/assets/downloads/gems-hnew01-stepper-dblind-unique.tif",
    ]
    for rel in own:
        p = ROOT / rel
        if p.is_file():
            rows.append(dict(site="WBGGEMSDOE3 (this repo)", submission=p.stem, score=None,
                             local=rel, sha256=sha256_file(p), source="this-repo"))
    return rows
