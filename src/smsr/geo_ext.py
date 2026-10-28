"""Three new geophysical planes appended to the shared ``gems57.geo`` block.

Reuses ``gems57.geo``'s own robust-z scorer and sentinel-scrubbing technique
(same formula, same clip) instead of inventing a second one, and reuses
``gems57.strand_orientation.magnetic_geometry`` -- already a label-free,
catalogue-independent structure-tensor routine built for exactly this purpose
(it was written for the TMI band, but nothing in it is magnetics-specific) --
to build the anisotropy/ridge feature. No catalogue, holdout mask or label is
read anywhere in this module, so it cannot leak the withholding.

New planes
----------
``g_strain_ridge``   coherence * log(1+|grad|) of the geodetic strain-rate
                     second invariant (``geod_2ndinv``, band 4): high only
                     where the strain surface is both steep AND *linear*
                     (elongated), which an isotropic production/injection
                     bowl is not.
``g_seis_dist``      robust-z of ``deq_n100a15`` (band 10, distance-weighted
                     earthquake proximity term supplied by the organiser).
``g_seis_intensity`` robust-z of ``ieq_n100a15`` (band 16, earthquake
                     intensity/density term supplied by the organiser).

Neither seismicity band appears anywhere in the shipped ``gems57.geo``
9-plane set (``GEO_FEATURES``); this is the first lane to use them.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from gems57 import geo as G
from gems57.strand_orientation import magnetic_geometry

NEW_GEO_FEATURES = ("g_strain_ridge", "g_seis_dist", "g_seis_intensity")

_BAND = {"geod_2ndinv": 4, "deq_n100a15": 10, "ieq_n100a15": 16}


def _clean(a: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Scrub float32 GDAL sentinels/non-finite cells to the in-footprint median.

    Identical technique to ``gems57.geo.load_planes._clean`` (same sentinel
    test, same fallback), duplicated here only because that inner function is
    not exported -- this is feature engineering for a new lane, not a change
    to the shared evaluator/holdout/writer/metric files.
    """
    v = a.astype(np.float64)
    bad = ~np.isfinite(v) | (np.abs(v) > 1e18)
    good = fp & np.isfinite(v) & (np.abs(v) <= 1e18)
    fill = float(np.median(v[good])) if good.any() else 0.0
    v[bad] = fill
    return v


def load_new_planes(footprint: np.ndarray, path: Path | None = None) -> dict[str, np.ndarray]:
    """Load and robust-z score the three new SMSR planes."""
    p = Path(path) if path else G.FEATURES_PATH
    fp = np.asarray(footprint, bool)
    with rasterio.open(p) as src:
        if (src.height, src.width) != fp.shape:
            raise ValueError(f"feature stack grid {src.shape} != footprint {fp.shape}")
        raw = {name: src.read(bidx) for name, bidx in _BAND.items()}

    strain = _clean(raw["geod_2ndinv"], fp)
    geom = magnetic_geometry(strain, fp)
    ridge = geom["coherence"].astype(np.float64) * np.log1p(
        np.hypot(*np.gradient(strain)).astype(np.float64))
    seis_d = _clean(raw["deq_n100a15"], fp)
    seis_i = _clean(raw["ieq_n100a15"], fp)

    planes = {
        "g_strain_ridge": G._robust_z(ridge.astype(np.float32), fp),
        "g_seis_dist": G._robust_z(seis_d.astype(np.float32), fp),
        "g_seis_intensity": G._robust_z(seis_i.astype(np.float32), fp),
    }
    for k, v in planes.items():
        if v.shape != fp.shape or v.dtype != np.float32:
            raise ValueError(f"plane {k} has wrong shape/dtype")
    return planes


def load_combined_planes(footprint: np.ndarray, path: Path | None = None) -> dict[str, np.ndarray]:
    """Shipped 9-plane ``gems57.geo`` block plus the 3 new SMSR planes, in order."""
    out = dict(G.load_planes(footprint, path))
    out.update(load_new_planes(footprint, path))
    return out
