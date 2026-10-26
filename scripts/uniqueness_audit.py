"""WB-GEMS-DOE-3 lane-uniqueness audit.

Two mandatory lane rules (parallel-run protocol):

  1. Surface rank-correlation (Spearman |rho|) <= 0.90 vs every registry raster,
     checked on the pre-placement surface AND on the final dots.
  2. <= 70% of final dots fall within 3 px of any one registry raster's dots.

A raster that trips either rule has drifted into another lane: log as duplicate
and stop. Values are computed on saved bytes, so the audit is reproducible
without human inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from scipy.stats import spearmanr
from scipy.ndimage import distance_transform_edt

RADIUS_PX = 3.0
RHO_CAP = 0.90
OVERLAP_CAP = 0.70


def _load_binary(tif_path: Path) -> np.ndarray:
    with rasterio.open(tif_path) as src:
        arr = src.read(1).astype(np.float64)
    return np.isfinite(arr) & (arr > 0.5)


def _load_surface(tif_path: Path) -> np.ndarray:
    with rasterio.open(tif_path) as src:
        arr = src.read(1).astype(np.float64)
    return np.where(np.isfinite(arr), arr, 0.0)


def _spearman(a: np.ndarray, b: np.ndarray, max_pixels: int = 200_000,
              rng_seed: int = 20261026) -> float:
    """Spearman rank correlation of two flattened surfaces (subsampled for speed).

    Subsampling preserves the correlation ranking well enough for the lane gate
    (|rho| <= 0.90) while avoiding an O(N log N) sort over 12M pixels per raster.
    Constant inputs return 0.0 (no defined correlation).
    """
    ra = a.ravel()
    rb = b.ravel()
    mask = np.isfinite(ra) & np.isfinite(rb)
    if mask.sum() < 2:
        return 0.0
    ra, rb = ra[mask], rb[mask]
    if ra.size > max_pixels:
        rng = np.random.RandomState(rng_seed)
        sel = rng.choice(ra.size, size=max_pixels, replace=False)
        ra, rb = ra[sel], rb[sel]
    if ra.std() == 0.0 or rb.std() == 0.0:
        return 0.0
    rho, _ = spearmanr(ra, rb)
    return float(rho) if np.isfinite(rho) else 0.0


def _overlap_within_px(dots_a: np.ndarray, dots_b: np.ndarray, px: float) -> float:
    """Fraction of dots_a within `px` pixels of any dot in dots_b (Euclidean)."""
    if dots_a.size == 0 or dots_b.size == 0:
        return 0.0
    # distance transform of dots_b gives distance from every pixel to nearest b-dot
    dist = distance_transform_edt(~dots_b)
    return float(dist[dots_a].mean() <= px) if False else float(
        (dist[dots_a] <= px).mean())


@dataclass
class UniquenessResult:
    raster: str
    max_abs_rho_surface: float
    max_abs_rho_final_dots: float
    max_overlap_within_3px: float
    lane_rule_1_pass: bool   # |rho| <= 0.90
    lane_rule_2_pass: bool   # <= 70% within 3 px
    unique: bool
    n_registry_rasters: int

    def to_dict(self):
        return asdict(self)


def audit_uniqueness(candidate_tif: Path, registry_tifs: list[Path]) -> UniquenessResult:
    # This historical checker is not the shared tool: it excludes positive
    # values <= 0.5, skips mismatched grids, permits an empty registry, and
    # substitutes final dots for a pre-placement surface. It cannot clear a file.
    raise RuntimeError(
        "DISABLED: incomplete historical registry check cannot authorize a file; "
        "use the verified shared template after the documented protocol/tool issues are resolved."
    )
    candidate_surface = _load_surface(candidate_tif)
    candidate_dots = _load_binary(candidate_tif)

    max_rho_surface = 0.0
    max_rho_dots = 0.0
    max_overlap = 0.0
    n = 0
    for rt in registry_tifs:
        n += 1
        reg_surface = _load_surface(rt)
        reg_dots = _load_binary(rt)
        if reg_surface.shape != candidate_surface.shape:
            continue  # different grid: cannot compare directly
        max_rho_surface = max(max_rho_surface, abs(_spearman(candidate_surface, reg_surface)))
        max_rho_dots = max(max_rho_dots, abs(_spearman(candidate_dots.astype(float),
                                                       reg_dots.astype(float))))
        max_overlap = max(max_overlap, _overlap_within_px(candidate_dots, reg_dots, RADIUS_PX))

    rule1 = max_rho_surface <= RHO_CAP and max_rho_dots <= RHO_CAP
    rule2 = max_overlap <= OVERLAP_CAP
    return UniquenessResult(
        raster=str(candidate_tif),
        max_abs_rho_surface=round(max_rho_surface, 4),
        max_abs_rho_final_dots=round(max_rho_dots, 4),
        max_overlap_within_3px=round(max_overlap, 4),
        lane_rule_1_pass=bool(rule1),
        lane_rule_2_pass=bool(rule2),
        unique=bool(rule1 and rule2),
        n_registry_rasters=n,
    )
