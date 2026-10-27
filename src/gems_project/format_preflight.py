"""Conservative, read-only inspection of saved TIFF bytes against a sample grid.

This is a project-local diagnostic, not the shared competition writer, an
organizer validator, a uniqueness audit, or authorization to submit. The
sample's provenance must be checked separately. The current all-finite,
zero-outside policy is conservative and *not* known to satisfy the organizer's
outside-bounds wording; it must not be used to infer portal acceptance.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .sources import sha256_file


def raster_report(candidate: str | Path, sample: str | Path) -> dict:
    """Inspect every saved pixel, GDAL validity mask and grid metadata.

    Raises for unreadable files or an invalid reference. An invalid candidate is
    reported with ``format_ok=False`` rather than repaired. No tolerance is
    applied to affine equality or the [0, 1] range.
    """
    candidate, sample = Path(candidate), Path(sample)
    problems: list[str] = []
    with rasterio.open(sample) as ref, rasterio.open(candidate) as pred:
        if ref.count != 1 or ref.crs is None or ref.crs.to_epsg() != 32611:
            raise ValueError("reference must be one band in EPSG:32611")
        if (ref.transform.a != 100 or ref.transform.e != -100
                or ref.transform.b != 0 or ref.transform.d != 0):
            raise ValueError("reference must have an unrotated 100 m grid")
        checks = {
            "driver_geotiff": pred.driver == "GTiff",
            "single_band": pred.count == 1,
            "dtype_float32": pred.count == 1 and pred.dtypes[0] == "float32",
            "crs_matches_reference": pred.crs is not None and pred.crs == ref.crs,
            "shape_matches_reference": pred.shape == ref.shape,
            "transform_matches_reference": pred.transform == ref.transform,
            "nodata_unset_for_local_zero_policy": pred.nodata is None,
        }
        grid_ok = all(checks[k] for k in (
            "crs_matches_reference", "shape_matches_reference", "transform_matches_reference"))
        finite_all = in_range_all = True
        no_inside_nonfinite = in_range_inside = no_masked_inside = outside_zero = True
        fp_count = positive_inside = positive_outside = nan_inside = inf_inside = 0
        inside_min, inside_max = None, None
        for _, window in pred.block_windows(1):
            values = pred.read(1, window=window)
            finite_all &= bool(np.isfinite(values).all())
            in_range_all &= bool(np.isfinite(values).all() and
                                 ((values >= 0) & (values <= 1)).all())
            if not grid_ok:
                continue
            reference = ref.read(1, window=window)
            foot = np.isfinite(reference) & (ref.read_masks(1, window=window) > 0)
            inside = values[foot]
            outside = values[~foot]
            fp_count += int(foot.sum())
            positive_inside += int(np.count_nonzero(np.isfinite(inside) & (inside > 0)))
            positive_outside += int(np.count_nonzero(np.isfinite(outside) & (outside > 0)))
            nan_inside += int(np.count_nonzero(np.isnan(inside)))
            inf_inside += int(np.count_nonzero(np.isinf(inside)))
            no_inside_nonfinite &= bool(np.isfinite(inside).all())
            in_range_inside &= bool(np.isfinite(inside).all() and
                                    ((inside >= 0) & (inside <= 1)).all())
            no_masked_inside &= bool((pred.read_masks(1, window=window)[foot] > 0).all())
            outside_zero &= bool((outside == 0).all())
            finite = inside[np.isfinite(inside)]
            if finite.size:
                lo, hi = float(finite.min()), float(finite.max())
                inside_min = lo if inside_min is None else min(inside_min, lo)
                inside_max = hi if inside_max is None else max(inside_max, hi)
        if grid_ok and not fp_count:
            raise ValueError("reference has an empty finite, unmasked footprint")
        checks.update({
            "whole_array_all_finite": finite_all,
            "whole_array_range_0_1": in_range_all,
            "inside_all_finite": no_inside_nonfinite if grid_ok else False,
            "inside_range_0_1": in_range_inside if grid_ok else False,
            "inside_gdal_mask_valid": no_masked_inside if grid_ok else False,
            "outside_zero_for_local_policy": outside_zero if grid_ok else False,
        })
        problems = [name for name, passed in checks.items() if not passed]
        return {
            "format_ok": not problems,
            "checks": checks,
            "problems": problems,
            "sha256": sha256_file(candidate),
            "sample_sha256": sha256_file(sample),
            "crs": str(pred.crs),
            "shape": list(pred.shape),
            "transform": list(pred.transform)[:6],
            "dtype": pred.dtypes[0] if pred.count else None,
            "footprint_cells": fp_count if grid_ok else None,
            "inside_min": inside_min,
            "inside_max": inside_max,
            "inside_nan_cells": nan_inside if grid_ok else None,
            "inside_infinity_cells": inf_inside if grid_ok else None,
            "positive_inside": positive_inside if grid_ok else None,
            "positive_outside": positive_outside if grid_ok else None,
            "approved_for_submission": False,
            "note": ("Local all-finite/zero-outside diagnostic only; sample provenance, "
                     "organizer outside-bounds interpretation, performance, uniqueness, "
                     "and a separate slot selection are not established."),
        }
