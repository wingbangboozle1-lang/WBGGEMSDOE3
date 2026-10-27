"""Raster I/O for the competition grid: labels, footprint, feature stack, blocks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from . import config as C


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_official_data(strict: bool = True) -> dict:
    """Check that the three official rasters on disk match their pinned SHA-256s."""
    out = {}
    for name, pin in C.SHA256.items():
        p = C.DATA_DIR / name
        if not p.exists():
            out[name] = {"present": False}
            if strict:
                raise FileNotFoundError(f"missing official raster: {p}")
            continue
        got = sha256_file(p)
        out[name] = {"present": True, "sha256": got, "matches_pin": got == pin}
        if strict and got != pin:
            raise ValueError(f"SHA-256 mismatch for {name}: {got} != {pin}")
    return out


def read_band(path, index: int) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(index).astype(np.float32)
        nod = src.nodata
        if nod is not None and np.isfinite(nod):
            a[a == np.float32(nod)] = np.nan
    return a


def read_labels() -> np.ndarray:
    with rasterio.open(C.LABELS_TIF) as src:
        lab = src.read(1)
        nod = src.nodata
    g = lab == 1
    if nod is not None:
        g &= lab != nod
    return g


def read_footprint() -> np.ndarray:
    """True where the official sample submission is finite (the scored domain)."""
    with rasterio.open(C.SAMPLE_TIF) as src:
        a = src.read(1)
    return np.isfinite(a)


def read_band(path, index: int) -> np.ndarray:  # noqa: F811  (documented above)
    with rasterio.open(path) as src:
        a = src.read(index).astype(np.float32)
        nod = src.nodata
        if nod is not None and np.isfinite(nod):
            a[a == np.float32(nod)] = np.nan
    a[a < -1e30] = np.nan
    return a


def read_features_block(band: int, r0: int, r1: int) -> np.ndarray:
    with rasterio.open(C.FEATURES_TIF) as src:
        a = src.read(band, window=((r0, r1), (0, C.WIDTH))).astype(np.float32)
    a[~np.isfinite(a) | (a < -1e30)] = np.nan
    return a


def iter_blocks(size: int, n_rows: int, n_cols: int):
    """Spatial block index grid; returns list of (index, row0, row1, col0, col1)."""
    out = []
    br = int(np.ceil(C.HEIGHT / size))
    bc = int(np.ceil(C.WIDTH / size))
    i = 0
    for r in range(br):
        for c in range(bc):
            r0, r1 = r * size, min(C.HEIGHT, (r + 1) * size)
            c0, c1 = c * size, min(C.WIDTH, (c + 1) * size)
            out.append((i, r0, r1, c0, c1))
            i += 1
    return out


def block_grid(size: int = 621) -> np.ndarray:
    """Integer label per pixel: which spatial block it belongs to (-1 outside)."""
    lab = np.full((C.HEIGHT, C.WIDTH), -1, dtype=np.int16)
    for i, r0, r1, c0, c1 in iter_blocks(size, 0, 0):
        lab[r0:r1, c0:c1] = i
    return lab


_META = Path(__file__).resolve().parents[2] / "registry" / "data_manifest.json"


def data_manifest() -> dict:
    return json.loads(_META.read_text())
