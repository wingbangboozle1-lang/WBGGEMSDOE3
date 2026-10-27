"""Production scoring pipeline for the WBGGEMSDOE3 discovery submission.

The emitted surface is the union of two statistically independent lineament
supports, both built only from catalogue-free data:

  A. 100 m topographic scarp morphology (competition bands)
     ridge = non-maximum-suppressed |curvature| field of the detrended-elevation
     surface, averaged over four complementary scarp descriptors
     (plan curvature s=2, profile curvature s=2, LoG s=1, paired-scarp relay
     detector), weighted by local ridge-density corroboration.

  B. 2 m LiDAR scarp descriptors (USGS 3DEP via the competition DEM link list,
     aggregated to 100 m by the owner CI; band semantics in
     lidar_scarp_features.json: ex_mean, upface_max, lappos_max, step_max),
     non-maximum-suppressed and rank-averaged.

Why a union: the metric takes the maximum kernel-weighted credit per truth pixel,
so two supports only add value when they are not redundant. Measured overlap of
the two top-N sets is ~1.6% of their pixels, i.e. they are nearly disjoint.

Why binary: for a fixed support, the official DTI is strictly increasing in the
surface level, so 1.0 on the support and 0.0 elsewhere is optimal (see emit.py).

Why catalogue suppression at radius 0: the scored faults are by construction not
in the public catalogue, so catalogue cells can never earn credit and only add
false-positive mass. A radius of 0 removes exactly those cells and nothing else.
"""

from __future__ import annotations

import json

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import config as C
from . import features as F
from . import io as gio

# Owner-derived USGS 3DEP product (public domain); semantics documented in the
# adjacent JSON and copied into the run card.
LIDAR_TIF = C.ROOT / ".cache" / "upstream" / "x24" / "data" / "external" / "lidar_scarp_features_u8.tif"
LIDAR_JSON = C.ROOT / ".cache" / "upstream" / "x24" / "data" / "external" / "lidar_scarp_features.json"

CORE_LAYERS = ("de_cplan_s2", "de_cprof_s2", "de_log_s1", "de_paired_scarp")
LIDAR_CHANNELS = ("ex_mean", "upface_max", "lappos_max", "step_max")

# Operating point selected on the external-catalogue proxy (see docs/executive-summary).
BASE_N = 60_000
LIDAR_N = 40_000


def _rank01(a: np.ndarray, valid: np.ndarray, lo_pct=0.5, hi_pct=99.5) -> np.ndarray:
    v = a[valid]
    lo, hi = np.percentile(v, [lo_pct, hi_pct])
    return np.clip((a - lo) / (hi - lo + 1e-12), 0, 1).astype(np.float32)


def ridge_nms(q: np.ndarray, valid: np.ndarray, smooth: float = 0.8) -> np.ndarray:
    """One-pixel-wide ridge crests: keep cells maximal across the local gradient."""
    s = ndi.gaussian_filter(np.nan_to_num(q, nan=0.0), smooth, mode="nearest")
    gy, gx = np.gradient(s)
    mag = np.hypot(gx, gy) + 1e-12
    dy = np.rint(gy / mag).astype(np.int32)
    dx = np.rint(gx / mag).astype(np.int32)
    H, W = q.shape
    r = np.arange(H)[:, None]
    c = np.arange(W)[None, :]
    a = np.abs(s)
    fwd = a[np.clip(r + dy, 0, H - 1), np.clip(c + dx, 0, W - 1)]
    bwd = a[np.clip(r - dy, 0, H - 1), np.clip(c - dx, 0, W - 1)]
    return (a >= fwd) & (a >= bwd) & (a > 0) & valid


def morphology_score(stack, names, valid) -> np.ndarray:
    idx = {n: i for i, n in enumerate(names)}
    ranks, ridges = {}, {}
    for L in CORE_LAYERS:
        q = _rank01(np.asarray(stack[idx[L]]), valid)
        ranks[L] = q
        ridges[L] = np.where(ridge_nms(q, valid), q, np.float32(0.0)).astype(np.float32)
    core = np.mean([ridges[L] for L in CORE_LAYERS], axis=0).astype(np.float32)
    dens = ndi.uniform_filter(((core > 0) & (core > 0.35)).astype(np.float32), size=21)
    return (core * (0.5 + 2.0 * dens)).astype(np.float32)


def lidar_score(valid) -> tuple[np.ndarray, dict]:
    meta = json.loads(LIDAR_JSON.read_text())
    bands = meta["bands"]
    with rasterio.open(LIDAR_TIF) as src:
        A = src.read()
    parts = []
    for nm in LIDAR_CHANNELS:
        i = bands.index(nm)
        xmax, tr = meta["quantisation"][nm]
        q = A[i].astype(np.float32)
        z = np.clip((q - 1.0) / 254.0, 0.0, 1.0)
        x = xmax * (z ** 2) if tr == "sqrt" else xmax * z
        x[q == 0] = np.nan
        parts.append(_rank01(np.nan_to_num(x, nan=np.nanmin(x)), valid))
    lid = np.mean(parts, axis=0).astype(np.float32)
    return np.where(ridge_nms(lid, valid), lid, np.float32(0.0)).astype(np.float32), meta


def select_top(score: np.ndarray, valid: np.ndarray, n: int, salt: int = 0) -> np.ndarray:
    """Deterministic top-N selection (ties broken by flat index)."""
    q = np.where(valid, score, np.float32(-1.0)).astype(np.float32).ravel()
    jitter = (np.arange(q.size, dtype=np.float32) / max(q.size, 1)) * np.float32(1e-7)
    q = q - jitter + np.float32(salt) * 0
    n = int(min(n, int((q > 0).sum())))
    sel = np.argpartition(q, -n)[-n:] if n > 0 else np.array([], dtype=np.int64)
    mask = np.zeros(q.size, dtype=bool)
    mask[sel] = True
    return mask.reshape(valid.shape)


def build_support(base_score, lid_score, valid, catalogue, n_base=BASE_N, n_lidar=LIDAR_N):
    s1 = select_top(base_score, valid, n_base)
    s2 = select_top(lid_score, valid, n_lidar)
    support = s1 | s2
    support = support & ~catalogue  # radius 0: provably zero-credit cells only
    return support, {"base_cells": int(s1.sum()), "lidar_cells": int(s2.sum()),
                     "overlap_cells": int((s1 & s2).sum()),
                     "union_cells": int((s1 | s2).sum()),
                     "after_catalogue_suppression": int(support.sum())}


def build_all(verbose: bool = True):
    stack, names = F.build_feature_stack(verbose=False)
    valid = gio.read_footprint()
    catalogue = gio.read_labels()
    base = morphology_score(stack, names, valid)
    lid, meta = lidar_score(valid)
    support, info = build_support(base, lid, valid, catalogue)
    if verbose:
        print(f"[pipeline] {info}", flush=True)
    return {"base": base, "lidar": lid, "support": support, "valid": valid,
            "catalogue": catalogue, "lidar_meta": meta, "info": info}
