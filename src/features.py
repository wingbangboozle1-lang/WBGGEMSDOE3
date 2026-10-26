"""
Feature computation for GEMS geothermal favourability.

All functions operate on numpy arrays and return arrays of the same shape.
Features are derived only from visible (non-withheld) faults during holdout
evaluation, per the PARALLEL-RUN PROTOCOL. No feature uses the held-out
targets, so there is no target leakage by construction.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def _as_float(a):
    return np.asarray(a, dtype=np.float64)


def gaussian_smooth(a, sigma_px):
    a = _as_float(a)
    if sigma_px <= 0:
        return a
    return ndimage.gaussian_filter(a, sigma=sigma_px, mode="nearest")


def distance_to_faults(fault_mask, pixel_size_m):
    fault_mask = np.asarray(fault_mask, dtype=bool)
    if not fault_mask.any():
        return np.full(fault_mask.shape, np.inf, dtype=np.float64)
    return ndimage.distance_transform_edt(~fault_mask) * float(pixel_size_m)


def lineament_density(fault_mask, window_px):
    fault_mask = np.asarray(fault_mask, dtype=bool).astype(np.float64)
    if window_px < 1:
        return fault_mask.copy()
    kernel = np.ones((window_px, window_px), dtype=np.float64) / (window_px * window_px)
    return ndimage.convolve(fault_mask, kernel, mode="constant", cval=0.0)


def curvature_like(a, pixel_size_m):
    a = _as_float(a)
    lap = ndimage.laplace(a, mode="nearest")
    return np.abs(lap) * float(pixel_size_m)


def openness_proxy(a, pixel_size_m, reach_px=3):
    a = _as_float(a)
    if reach_px < 1:
        return np.zeros_like(a)
    size = 2 * reach_px + 1
    local_min = ndimage.minimum_filter(a, size=size, mode="nearest")
    local_max = ndimage.maximum_filter(a, size=size, mode="nearest")
    pos = a - local_min
    neg = local_max - a
    return (pos + neg) * float(pixel_size_m)


def combine_features(feature_dict, weights):
    names = list(feature_dict.keys())
    stacked = np.stack([_as_float(feature_dict[n]) for n in names], axis=0)
    norm = np.zeros_like(stacked)
    for i in range(stacked.shape[0]):
        band = stacked[i]
        lo = np.percentile(band, 1)
        hi = np.percentile(band, 99)
        if hi > lo:
            norm[i] = np.clip((band - lo) / (hi - lo), 0.0, 1.0)
        else:
            norm[i] = np.zeros_like(band)
    w = np.array([weights.get(n, 1.0) for n in names], dtype=np.float64)
    w = w / w.sum()
    out = np.tensordot(w, norm, axes=([0], [0]))
    return np.clip(out, 0.0, 1.0)


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    a = rng.standard_normal((100, 100))
    print("curvature shape:", curvature_like(a, 30.0).shape)
    print("openness shape:", openness_proxy(a, 30.0).shape)
