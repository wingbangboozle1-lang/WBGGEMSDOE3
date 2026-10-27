"""RFL lane: Range-Front relief-discontinuity Lineaments (preregistered 2026-10-27,
knowledge/preregistration-2026-10-27-rfl.md, session arena/bd44f94b).

Label-independent surface from ONE cached band (det_elev, band 12 of the
hash-pinned 19-band mirror).  Physical target: the abrupt focal-relief step at a
Basin-and-Range mountain front, which persists where a younger alluvium-buried
normal fault has no scarp face for the USGS/INGENIOUS catalogue to map.

Frozen specification:
  relief   R2 = max5x5 - min5x5 (500 m), R5 = max11x11 - min11x11 (1.1 km)
  gradient Gk = |grad(Rk; sigma=1.5)|   (shared Gaussian-gradient code)
  ranks    empirical-CDF rank within footprint (shared code)
  surface  S  = min(rank G2, rank G5)   (multi-scale persistence)
  ablations rank G2 | rank G5 | S gated to 0.25<=rank R5<=0.90 | rank|grad det_elev|
  place    shared gemsw.cspes.place_dots (greedy top-K, 2 px NMS, K=37,654)

No catalogue-derived quantity enters the surface; catalogue pixels are excluded
only by the shared placer/writer.  Named non-fault mimic: lithologic range
fronts, alluvial-fan heads, pluvial shorelines.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi

from .cspes import _fill, _footprint_rank, grad_magnitude

BAND_DET_ELEV = 12
GRAD_SIGMA = 1.5
DEFAULT_BUDGET = 37_654


def focal_relief(elev: np.ndarray, radius: int) -> np.ndarray:
    """Local relief = focal max - focal min over a (2r+1)^2 window."""
    size = 2 * radius + 1
    mx = ndi.maximum_filter(elev, size=size, mode="nearest")
    mn = ndi.minimum_filter(elev, size=size, mode="nearest")
    return (mx - mn).astype(np.float32)


@dataclass
class RFLFields:
    surface: np.ndarray
    components: dict[str, np.ndarray]


def build_surface(det_elev_raw: np.ndarray, foot: np.ndarray) -> RFLFields:
    elev = _fill(det_elev_raw, foot)
    r2 = focal_relief(elev, 2)    # 500 m window
    r5 = focal_relief(elev, 5)    # 1.1 km window
    g2 = grad_magnitude(r2, GRAD_SIGMA)
    g5 = grad_magnitude(r5, GRAD_SIGMA)
    rk_g2 = _footprint_rank(g2, foot)
    rk_g5 = _footprint_rank(g5, foot)
    rk_r5 = _footprint_rank(r5, foot)

    surface = np.minimum(rk_g2, rk_g5)
    piedmont = ((rk_r5 >= 0.25) & (rk_r5 <= 0.90)).astype(np.float32)
    slope_ref = _footprint_rank(grad_magnitude(elev, GRAD_SIGMA), foot)

    comp = {
        "raw_det_elev": det_elev_raw.astype(np.float32),
        "relief_r2_500m": r2, "relief_r5_1100m": r5,
        "grad_relief_g2": g2, "grad_relief_g5": g5,
        "rank_g2": rk_g2, "rank_g5": rk_g5, "rank_r5": rk_r5,
        "rfl_full": surface.copy(),
        "abl_g500_only": rk_g2.copy(),
        "abl_g1100_only": rk_g5.copy(),
        "abl_piedmont_gate": (surface * piedmont).astype(np.float32),
        "abl_slope_reference": slope_ref,
    }
    # Rank fields are already 0 outside the footprint; raw/relief/gradient fields
    # are left untouched (canary samples only active in-footprint cells).
    surface = surface.copy()
    surface[~foot] = 0.0
    comp["rfl_full"] = surface.astype(np.float32)
    gate = comp["abl_piedmont_gate"].copy()
    gate[~foot] = 0.0
    comp["abl_piedmont_gate"] = gate
    return RFLFields(surface=surface.astype(np.float32), components=comp)
