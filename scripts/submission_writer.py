"""Legacy parallel-session writer; NOT the pinned shared submission writer.

Retained for research only. Its original template was not authenticated and did
not encode the pinned mirrored footprint, so the associated candidate failed the
literal registry rule and conservative footprint check. A local format result
cannot prove portal acceptance or correct the cause of a past portal rejection.
Do not use this file to bypass the shared-template or selector requirements.
See evidence/concurrent-candidate-audit.json and scripts/validate_raster.py.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.transform import from_origin

# Competition grid (verified against the official template grid).
EXPECTED_HEIGHT = 3730
EXPECTED_WIDTH = 3292
EXPECTED_TOTAL_PIXELS = EXPECTED_HEIGHT * EXPECTED_WIDTH
EXPECTED_FOOTPRINT_PIXELS = 5_167_373  # non-null cells of the template
EXPECTED_CRS = "EPSG:32611"
EXPECTED_ORIGIN_X = 243350.0
EXPECTED_ORIGIN_Y = 4508550.0
EXPECTED_RESOLUTION = 100.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ValidationReport:
    path: str
    passed: bool
    checks: dict
    geometry: dict
    stats: dict

    def to_dict(self):
        return asdict(self)


def _open_template(template_tif: Path):
    with rasterio.open(template_tif) as src:
        return dict(
            crs=src.crs,
            shape=(src.height, src.width),
            transform=src.transform,
            bounds=src.bounds,
        )


def validate_geotiff(tif_path: Path, template_tif: Path,
                     strict_whole_array: bool = True) -> ValidationReport:
    """13-point strict audit of a saved submission GeoTIFF.

    All checks are evaluated on the bytes stored in `tif_path`.
    """
    tmpl = _open_template(template_tif)
    expected_crs = tmpl["crs"]
    expected_shape = tmpl["shape"]
    expected_transform = tmpl["transform"]

    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        crs = src.crs
        shape = (src.height, src.width)
        transform = src.transform
        dtype = src.dtypes[0]
        count = src.count
        nodata = src.nodata

    grid_match = (crs == expected_crs) and (shape == expected_shape) \
        and (transform == expected_transform)

    checks = {
        "single_band": count == 1,
        "dtype_float32": dtype == "float32",
        "dimensions_3730x3292": shape == expected_shape,
        "crs_epsg_32611": str(crs) == EXPECTED_CRS or crs == expected_crs,
        "transform_matches_template": transform == expected_transform,
        "crs_matches_template": crs == expected_crs,
        "exact_reference_grid_match": grid_match,
    }

    # Range / finite checks on the whole saved array (portal-safe) and footprint.
    finite_all = int(np.isfinite(arr).sum())
    nan_all = int(np.isnan(arr).sum())
    inf_all = int(np.isinf(arr).sum())
    sentinel_all = int((arr < -1e30).sum())
    whole_in_01 = bool(np.all((arr >= 0.0) & (arr <= 1.0)) & np.isfinite(arr).all())

    stats = {
        "height": int(shape[0]),
        "width": int(shape[1]),
        "total_cells": int(arr.size),
        "finite_cells_all": int(finite_all),
        "nan_cells_all": int(nan_all),
        "inf_cells_all": int(inf_all),
        "sentinel_cells_all": int(sentinel_all),
        "whole_array_min": float(np.nanmin(arr)) if arr.size else float("nan"),
        "whole_array_max": float(np.nanmax(arr)) if arr.size else float("nan"),
        "whole_array_in_01": whole_in_01,
    }
    checks.update({
        "whole_array_all_finite": finite_all == arr.size,
        "whole_array_zero_nan": nan_all == 0,
        "whole_array_zero_inf": inf_all == 0,
        "whole_array_zero_sentinel": sentinel_all == 0,
        "whole_array_in_01": whole_in_01,
        "validator_range_0_1_guaranteed": whole_in_01,
    })

    passed = all(checks.values())
    geometry = {
        "crs": str(crs),
        "transform": [round(float(v), 6) for v in transform],
        "shape": [int(shape[0]), int(shape[1])],
        "count": int(count),
        "dtype": dtype,
        "nodata": None if nodata is None else float(nodata),
        "template_match": grid_match,
    }
    return ValidationReport(
        path=str(tif_path), passed=passed, checks=checks,
        geometry=geometry, stats=stats,
    )


def write_submission(mask: np.ndarray, footprint: np.ndarray,
                     template_tif: Path, out_path: Path,
                     mode: str = "zeros") -> np.ndarray:
    """Write a validated single-band float32 submission GeoTIFF.

    `mask` is a boolean/float positive-dot mask in the same shape as the grid.
    Values are clipped to [0, 1]. Outside the footprint: 0.0 (zeros mode) or NaN
    (nan mode). Footprint cells are forced finite.
    """
    assert mode in {"zeros", "nan"}
    with rasterio.open(template_tif) as tpl:
        profile = tpl.profile.copy()
        foot_template = tpl.read(1)
        # Use the template's own non-null region as the scored footprint when the
        # caller does not supply one; otherwise intersect with caller's footprint.
        if footprint is None:
            footprint = np.isfinite(foot_template)
    footprint = np.asarray(footprint, dtype=bool)
    assert footprint.shape == (EXPECTED_HEIGHT, EXPECTED_WIDTH), footprint.shape

    arr = np.zeros((EXPECTED_HEIGHT, EXPECTED_WIDTH), dtype=np.float32)
    clean = np.clip(np.asarray(mask, dtype=np.float32), 0.0, 1.0)
    arr[footprint] = np.where(footprint, clean, 0.0)[footprint]
    arr[footprint] = np.clip(arr[footprint], 0.0, 1.0)
    # Guarantee finite in-footprint values.
    arr[footprint] = np.where(np.isfinite(arr[footprint]), arr[footprint], 0.0).astype(np.float32)

    if mode == "zeros":
        arr[~footprint] = 0.0
        nodata = None
    else:
        arr[~footprint] = np.nan
        nodata = np.nan

    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(
        driver="GTiff", dtype="float32", count=1, compress="deflate",
        predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
        nodata=nodata,
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr.astype(np.float32), 1)
    return arr


def audit_saved_file(tif_path: Path, template_tif: Path,
                     strict_whole_array: bool = True) -> dict:
    report = validate_geotiff(tif_path, template_tif,
                              strict_whole_array=strict_whole_array)
    out = {
        "filename": Path(tif_path).name,
        "sha256": sha256_file(tif_path),
        "size_bytes": Path(tif_path).stat().st_size,
        "all_checks_passed": report.passed,
        "checks": report.checks,
        "geometry": report.geometry,
        "stats": report.stats,
    }
    return out
