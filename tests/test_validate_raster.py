from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from validate_raster import validate


def write_raster(path, array, *, nodata=None, mask=None, internal=True, transform=None, count=1, dtype="float32"):
    height, width = array.shape
    profile = dict(driver="GTiff", height=height, width=width, count=count, dtype=dtype,
                   crs="EPSG:32611", transform=transform or from_origin(0, 1000, 100, 100), nodata=nodata)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=internal):
        with rasterio.open(path, "w", **profile) as ds:
            for i in range(count):
                ds.write(array.astype(dtype), i + 1)
            if mask is not None:
                ds.write_mask(mask.astype(np.uint8) * 255)


@pytest.fixture
def rasters(tmp_path):
    footprint = np.array([[False, True, True, True, False], [False, True, True, True, False],
                          [False, True, True, True, False], [False, False, True, False, False]])
    sample = np.where(footprint, 0.0, np.nan).astype(np.float32)
    template = tmp_path / "template.tif"
    write_raster(template, sample, nodata=np.nan)
    return template, footprint


def test_internal_mask_and_finite_values_pass_local_format(rasters, tmp_path):
    template, footprint = rasters
    values = np.zeros(footprint.shape, np.float32)
    values[1, 2] = 1.0
    candidate = tmp_path / "candidate.tif"
    write_raster(candidate, values, mask=footprint)
    result = validate(candidate, template, expected_template_sha256=None)
    assert result["format_gate_pass"], result
    assert result["counts"]["nonfinite_inside"] == 0
    assert result["counts"]["valid_outside_mask"] == 0
    assert result["min_inside"] == 0 and result["max_inside"] == 1
    assert "not" in result["scope"].lower() or "neither" in result["scope"].lower()


@pytest.mark.parametrize("bad", [np.nan, np.inf, -0.01, 1.01, -9999.0])
def test_bad_inside_values_fail_without_clipping(rasters, tmp_path, bad):
    template, footprint = rasters
    values = np.zeros(footprint.shape, np.float32)
    values[1, 2] = bad
    path = tmp_path / "bad.tif"
    write_raster(path, values, mask=footprint)
    result = validate(path, template, expected_template_sha256=None)
    assert not result["format_gate_pass"]
    assert result["counts"]["nonfinite_inside"] or result["counts"]["out_of_range_inside"]


def test_allfinite_unmasked_outside_is_inconclusive_not_portal_rejection(rasters, tmp_path):
    template, footprint = rasters
    path = tmp_path / "unmasked.tif"
    write_raster(path, np.zeros(footprint.shape, np.float32))
    result = validate(path, template, expected_template_sha256=None)
    assert result["counts"]["nonfinite_all"] == 0
    assert result["counts"]["out_of_range_finite_all"] == 0
    assert result["counts"]["valid_outside_mask"] == int((~footprint).sum())
    assert not result["format_gate_pass"]
    assert "valid_outside_mask" in result["failures"]


def test_nan_outside_fails_strict_whole_array_check(rasters, tmp_path):
    template, footprint = rasters
    values = np.where(footprint, 0.0, np.nan).astype(np.float32)
    path = tmp_path / "nan-outside.tif"
    write_raster(path, values, nodata=np.nan)
    result = validate(path, template, expected_template_sha256=None)
    assert result["counts"]["nonfinite_inside"] == 0
    assert result["counts"]["nonfinite_all"] == int((~footprint).sum())
    assert not result["format_gate_pass"]


def test_wrong_grid_dtype_and_template_hash_fail(rasters, tmp_path):
    template, footprint = rasters
    path = tmp_path / "bad-grid.tif"
    write_raster(path, np.zeros(footprint.shape), mask=footprint,
                 transform=from_origin(1, 1000, 100, 100), dtype="float64")
    result = validate(path, template, expected_template_sha256="0" * 64)
    assert not result["format_gate_pass"]
    assert not result["metadata_checks"]["float32"]
    assert not result["metadata_checks"]["transform_matches"]
    assert not result["metadata_checks"]["template_sha256_matches"]


def test_external_mask_sidecar_does_not_pass_single_tif(rasters, tmp_path):
    template, footprint = rasters
    path = tmp_path / "sidecar.tif"
    write_raster(path, np.zeros(footprint.shape), mask=footprint, internal=False)
    assert Path(str(path) + ".msk").exists()
    result = validate(path, template, expected_template_sha256=None)
    assert not result["metadata_checks"]["no_external_mask_sidecar"]
    assert not result["format_gate_pass"]


def test_nonzero_outside_is_rejected_even_if_masked(rasters, tmp_path):
    template, footprint = rasters
    values = np.zeros(footprint.shape, np.float32)
    values[0, 0] = 0.5
    path = tmp_path / "outside.tif"
    write_raster(path, values, mask=footprint)
    result = validate(path, template, expected_template_sha256=None)
    assert result["counts"]["nonzero_outside"] == 1
    assert not result["format_gate_pass"]
