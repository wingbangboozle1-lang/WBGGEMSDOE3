"""Fail-closed, full-registry novelty audit.

A final TIFF cannot stand in for its pre-placement continuous surface. The
surface must be supplied separately, and a complete registry plus reference
grid must be explicitly identified. Missing, incompatible, or constant
comparisons are indeterminate and cannot pass.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

RADIUS_PX = 3.0
RHO_CAP = 0.90
OVERLAP_CAP = 0.70


def _read(path: Path):
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        grid = (src.crs, src.transform, src.shape)
        mask = (src.read_masks(1) > 0) & np.isfinite(data)
    return data, mask, grid


def _spearman(a: np.ndarray, b: np.ndarray, valid: np.ndarray,
              max_pixels: int = 200_000, rng_seed: int = 20261026) -> Optional[float]:
    """Deterministic, common-footprint Spearman; constants are indeterminate."""
    mask = valid & np.isfinite(a) & np.isfinite(b)
    if int(mask.sum()) < 2:
        return None
    ra, rb = a[mask], b[mask]
    if np.ptp(ra) == 0.0 or np.ptp(rb) == 0.0:
        return None
    if ra.size > max_pixels:
        rng = np.random.RandomState(rng_seed)
        selected = rng.choice(ra.size, size=max_pixels, replace=False)
        ra, rb = ra[selected], rb[selected]
    rho = spearmanr(ra, rb).statistic
    return float(rho) if np.isfinite(rho) else None


def _overlap_within_px(candidate_dots: np.ndarray, registry_dots: np.ndarray,
                       valid: np.ndarray, px: float) -> Optional[float]:
    selected = candidate_dots & valid
    reference = registry_dots & valid
    if not selected.any() or not reference.any():
        return None
    distance = distance_transform_edt(~reference)
    return float((distance[selected] <= px).mean())


@dataclass
class UniquenessResult:
    candidate: str
    candidate_surface: Optional[str]
    reference_grid: Optional[str]
    registry_complete_declared: bool
    n_registry_rasters: int
    n_comparable_rasters: int
    incompatible_rasters: list[str]
    max_abs_rho_surface: Optional[float]
    max_abs_rho_final_dots: Optional[float]
    max_overlap_within_3px: Optional[float]
    surface_check_status: str
    registry_check_status: str
    lane_rule_1_pass: bool
    lane_rule_2_pass: bool
    unique: bool

    def to_dict(self):
        return asdict(self)


def audit_uniqueness(candidate_tif: Path, registry_tifs: list[Path], *,
                     candidate_surface_tif: Optional[Path],
                     reference_grid_tif: Optional[Path],
                     registry_complete: bool = False) -> UniquenessResult:
    """Compare a separate continuous surface and final dots against a registry.

    `registry_complete` must only be true when the manifest has been frozen and
    includes every required submission and calibration/null raster. Without a
    separate surface, authenticated grid, or explicit completeness assertion,
    `unique` is always false even if the available dot overlaps look small.
    """
    candidate_tif = Path(candidate_tif)
    registry_tifs = [Path(p) for p in registry_tifs]
    candidate_values, candidate_mask, candidate_grid = _read(candidate_tif)
    candidate_dots = np.isfinite(candidate_values) & (candidate_values > 0.5)

    surface_values = None
    surface_mask = None
    surface_status = "NOT_PROVIDED"
    surface_path = None
    if candidate_surface_tif is not None:
        surface_path = Path(candidate_surface_tif)
        surface_values, surface_mask, surface_grid = _read(surface_path)
        if surface_grid != candidate_grid:
            surface_status = "GRID_MISMATCH"
            surface_values = None
            surface_mask = None
        else:
            surface_status = "READY"

    reference_mask = None
    reference_grid = None
    reference_path = None
    reference_grid_valid = False
    if reference_grid_tif is not None:
        reference_path = Path(reference_grid_tif)
        with rasterio.open(reference_path) as src:
            ref_data = src.read(1)
            reference_mask = (src.read_masks(1) > 0) & np.isfinite(ref_data)
            reference_grid = (src.crs, src.transform, src.shape)
        reference_grid_valid = bool(
            reference_grid == candidate_grid and reference_mask.shape == candidate_mask.shape
        )
        if not reference_grid_valid:
            reference_mask = None
            surface_status = "REFERENCE_GRID_MISMATCH" if surface_values is not None else surface_status
    elif surface_values is not None:
        surface_status = "REFERENCE_GRID_REQUIRED"

    max_surface = None
    max_final_rho = None
    max_overlap = None
    rho_surface_values: list[float] = []
    rho_final_values: list[float] = []
    overlaps: list[float] = []
    incompatible: list[str] = []
    comparable = 0

    for registry_path in registry_tifs:
        try:
            reg_values, reg_mask, reg_grid = _read(registry_path)
        except Exception:
            incompatible.append(str(registry_path))
            continue
        if reg_grid != candidate_grid or reg_values.shape != candidate_values.shape:
            incompatible.append(str(registry_path))
            continue
        comparable += 1
        valid = candidate_mask & reg_mask
        if reference_mask is not None:
            valid &= reference_mask

        rho_final = _spearman(candidate_dots.astype(np.float64),
                              (reg_values > 0.5).astype(np.float64), valid)
        overlap = _overlap_within_px(candidate_dots, reg_values > 0.5, valid, RADIUS_PX)
        if rho_final is not None:
            rho_final_values.append(abs(rho_final))
        if overlap is not None:
            overlaps.append(overlap)

        if (surface_values is not None and surface_mask is not None
                and reference_mask is not None and reference_grid_valid):
            surface_valid = valid & surface_mask
            rho_surface = _spearman(surface_values, reg_values, surface_valid)
            if rho_surface is not None:
                rho_surface_values.append(abs(rho_surface))

    if rho_surface_values:
        max_surface = max(rho_surface_values)
        surface_status = "MEASURED"
    elif candidate_surface_tif is None:
        surface_status = "NOT_PROVIDED"
    elif surface_status == "READY":
        surface_status = "INDETERMINATE_NO_VALID_SURFACE_COMPARISONS"

    if rho_final_values:
        max_final_rho = max(rho_final_values)
    if overlaps:
        max_overlap = max(overlaps)

    registry_valid = bool(
        registry_complete and registry_tifs and comparable == len(registry_tifs)
        and not incompatible and reference_grid_valid
    )
    registry_status = "COMPLETE_DECLARED_AND_COMPARABLE" if registry_valid else "INCOMPLETE_OR_INCOMPATIBLE"
    if surface_values is not None and not reference_grid_valid and not rho_surface_values:
        surface_status = "REFERENCE_GRID_REQUIRED_OR_MISMATCH"
    surface_complete = bool(surface_status == "MEASURED" and registry_valid and reference_grid_valid)
    lane1 = bool(
        surface_complete and max_surface is not None and max_surface <= RHO_CAP
        and max_final_rho is not None and max_final_rho <= RHO_CAP
    )
    lane2 = bool(registry_valid and max_overlap is not None and max_overlap <= OVERLAP_CAP)
    unique = bool(lane1 and lane2)

    return UniquenessResult(
        candidate=str(candidate_tif),
        candidate_surface=str(surface_path) if surface_path else None,
        reference_grid=str(reference_path) if reference_path else None,
        registry_complete_declared=bool(registry_complete),
        n_registry_rasters=len(registry_tifs),
        n_comparable_rasters=comparable,
        incompatible_rasters=incompatible,
        max_abs_rho_surface=round(max_surface, 4) if max_surface is not None else None,
        max_abs_rho_final_dots=round(max_final_rho, 4) if max_final_rho is not None else None,
        max_overlap_within_3px=round(max_overlap, 4) if max_overlap is not None else None,
        surface_check_status=surface_status,
        registry_check_status=registry_status,
        lane_rule_1_pass=lane1,
        lane_rule_2_pass=lane2,
        unique=unique,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Saved final-dot TIFF")
    parser.add_argument("--surface", type=Path, required=True,
                        help="Separate pre-placement continuous surface TIFF")
    parser.add_argument("--template", type=Path, required=True,
                        help="Authenticated reference/sample grid")
    parser.add_argument("--registry", type=Path, action="append", required=True,
                        help="A registry TIFF; repeat for every manifest entry")
    parser.add_argument("--registry-complete", action="store_true",
                        help="Assert only after verifying the frozen manifest includes controls")
    args = parser.parse_args()
    result = audit_uniqueness(
        args.candidate,
        args.registry,
        candidate_surface_tif=args.surface,
        reference_grid_tif=args.template,
        registry_complete=args.registry_complete,
    )
    print(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    return 0 if result.unique else 2


if __name__ == "__main__":
    raise SystemExit(main())
