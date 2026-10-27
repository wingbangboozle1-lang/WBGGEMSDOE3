"""Geological feature bins for the hidden-fault density model.

Every feature is computed only from competition rasters or public external
layers; none uses hidden labels.  The catalogue distance uses the public
catalogue, which the official problem page says the test faults are absent
from (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

Features (bin edges are fixed a priori, never tuned on scores):

=============  =====================================================  ======
name           physical meaning                                       levels
=============  =====================================================  ======
d_cat          distance to nearest catalogue fault pixel (px=100 m)   10
topo           Hessian curvature strength of detrended elevation      5
crest          Canny crest of the det-elev slope (scarp/range front)  2
lidar          2 m LiDAR scarp descriptor rank (or "no LiDAR")        5
mag            TMI horizontal-gradient rank (magnetic edge)           4
sgmc           distance to USGS SGMC geologic-map faults              3
slope          det-elev slope quantile (basin / piedmont / range)     4
=============  =====================================================  ======
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import data as D

D_CAT_EDGES = np.array([0.5, 1.5, 2.95, 4.95, 7.95, 12.95, 20.95, 33.95, 54.95])  # 10 bins
FEATURES = ("d_cat", "topo", "crest", "lidar", "mag", "sgmc", "slope")
LEVELS = {"d_cat": 10, "topo": 5, "crest": 2, "lidar": 5, "mag": 4, "sgmc": 3, "slope": 4}
LEVEL_NAMES = {
    "d_cat": ["0 (on catalogue)", "1-1.4 px", "2-2.8 px", "3-4.9 px", "5-7.9 px", "8-12.9 px",
              "13-20.9 px", "21-33.9 px", "34-54.9 px", ">=55 px"],
    "topo": ["top 1%", "1-3%", "3-10%", "10-30%", "rest"],
    "crest": ["not crest", "slope crest"],
    "lidar": ["no LiDAR", "top 3%", "3-10%", "10-30%", "rest"],
    "mag": ["top 5%", "5-20%", "20-50%", "rest"],
    "sgmc": ["0-1.9 px", "2-4.9 px", ">=5 px"],
    "slope": ["0-30% (flat)", "30-70%", "70-95%", "95-100% (steep)"],
}


def _rank01(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Empirical CDF rank in [0,1] over valid cells (ties share the mean rank); NaN elsewhere."""
    out = np.full(a.shape, np.nan, dtype=np.float32)
    v = a[valid]
    order = np.argsort(v, kind="mergesort")
    r = np.empty(v.size, dtype=np.float64)
    r[order] = (np.arange(v.size) + 0.5) / v.size
    out[valid] = r.astype(np.float32)
    return out


def _qbin(rank: np.ndarray, top_edges: list[float]) -> np.ndarray:
    """Bin a [0,1] rank by descending top fractions, e.g. [0.01, 0.03, 0.10, 0.30] -> 5 levels."""
    lvl = np.full(rank.shape, len(top_edges), dtype=np.int16)
    upper = 1.0 - np.asarray(top_edges)
    for i in range(len(top_edges) - 1, -1, -1):
        lvl[rank >= upper[i]] = i
    return lvl


def _smooth_nan(a: np.ndarray, sigma: float) -> np.ndarray:
    m = np.isfinite(a)
    num = ndi.gaussian_filter(np.where(m, a, 0.0).astype(np.float64), sigma, mode="nearest")
    den = ndi.gaussian_filter(m.astype(np.float64), sigma, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 1e-6, num / den, np.nan)


def compute(grid: D.Grid) -> dict[str, np.ndarray]:
    foot = grid.foot
    out: dict[str, np.ndarray] = {}

    # 1. catalogue distance (px)
    d_cat = ndi.distance_transform_edt(~grid.cat).astype(np.float32)
    out["d_cat_px"] = d_cat
    out["d_cat"] = np.searchsorted(D_CAT_EDGES, d_cat, side="right").astype(np.int16)

    # 2./3. topography from detrended elevation
    z = D.band("det_elev")
    zs = _smooth_nan(z, 1.0)
    zs_f = np.where(np.isfinite(zs), zs, np.nanmean(zs))
    gy, gx = np.gradient(zs_f)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    hxy = 0.5 * (gxy + gyx)
    tr = 0.5 * (gxx + gyy)
    disc = np.sqrt(np.maximum((0.5 * (gxx - gyy)) ** 2 + hxy ** 2, 0.0))
    curv = np.maximum(np.abs(tr + disc), np.abs(tr - disc)).astype(np.float32)
    valid_topo = foot & np.isfinite(zs)
    topo_rank = _rank01(curv, valid_topo)
    out["topo_rank"] = topo_rank
    out["topo"] = np.where(valid_topo, _qbin(topo_rank, [0.01, 0.03, 0.10, 0.30]), 4).astype(np.int16)

    gmag = np.hypot(gx, gy)
    ny = np.rint(gy / (gmag + 1e-12)).astype(np.int32)
    nx = np.rint(gx / (gmag + 1e-12)).astype(np.int32)
    H, W = gmag.shape
    r = np.arange(H)[:, None]
    c = np.arange(W)[None, :]
    fwd = gmag[np.clip(r + ny, 0, H - 1), np.clip(c + nx, 0, W - 1)]
    bwd = gmag[np.clip(r - ny, 0, H - 1), np.clip(c - nx, 0, W - 1)]
    slope_rank = _rank01(gmag.astype(np.float32), valid_topo)
    crest = (gmag >= fwd) & (gmag >= bwd) & (slope_rank >= 0.70) & valid_topo
    out["crest"] = crest.astype(np.int16)
    out["slope_rank"] = slope_rank
    out["slope"] = np.where(valid_topo, np.searchsorted([0.30, 0.70, 0.95], slope_rank, side="right"), 0).astype(np.int16)

    # 4. LiDAR scarp descriptors (USGS 3DEP 1 m, aggregated by the owner CI to 100 m)
    L = D.lidar()
    lv = (L["valid"] > 0) & foot
    ranks = [_rank01(L[n].astype(np.float32), lv) for n in ("step_max", "upface_max", "ex_mean")]
    lid = np.nanmean(np.stack(ranks), axis=0)
    lid_rank = _rank01(np.where(lv, lid, 0).astype(np.float32), lv)
    out["lidar_rank"] = np.where(lv, lid_rank, np.nan).astype(np.float32)
    lvl = _qbin(np.nan_to_num(lid_rank, nan=0.0), [0.03, 0.10, 0.30]) + 1
    out["lidar"] = np.where(lv, lvl, 0).astype(np.int16)

    # 5. magnetic edge strength
    hg = D.band("tmi_hg")
    vm = foot & np.isfinite(hg)
    mag_rank = _rank01(hg, vm)
    out["mag_rank"] = mag_rank
    out["mag"] = np.where(vm, _qbin(np.nan_to_num(mag_rank, nan=0.0), [0.05, 0.20, 0.50]), 3).astype(np.int16)

    # 6. SGMC geologic-map faults (USGS State Geologic Map Compilation, 100 m raster)
    sg = D.read_binary_u8(D.EXTERNAL_T / "sgmc_faults_100m.tif")
    d_sg = ndi.distance_transform_edt(~sg).astype(np.float32)
    out["d_sgmc_px"] = d_sg
    out["sgmc"] = np.searchsorted([1.95, 4.95], d_sg, side="right").astype(np.int16)

    # joint cell id (row-major over FEATURES)
    cid = np.zeros(foot.shape, dtype=np.int32)
    for f in FEATURES:
        cid = cid * LEVELS[f] + out[f].astype(np.int32)
    out["cell"] = np.where(foot, cid, -1).astype(np.int32)
    return out


def n_cells() -> int:
    n = 1
    for f in FEATURES:
        n *= LEVELS[f]
    return n


def decode_cells() -> dict[str, np.ndarray]:
    """Level index of every feature for every joint cell id."""
    ids = np.arange(n_cells())
    levels = {}
    rem = ids.copy()
    for f in reversed(FEATURES):
        levels[f] = rem % LEVELS[f]
        rem //= LEVELS[f]
    return levels
