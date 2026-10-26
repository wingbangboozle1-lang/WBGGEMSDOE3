from __future__ import annotations

import numpy as np
import rasterio
from affine import Affine

from scripts.validate_submission import validate_submission


GRID = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def write_tif(path, array, *, nodata=None, transform=GRID, crs="EPSG:32611"):
    array = np.asarray(array, dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)


def make_inputs(tmp_path):
    template = tmp_path / "sample_submission.tif"
    labels = tmp_path / "labels.tif"
    candidate = tmp_path / "candidate.tif"
    template_arr = np.full((5, 6), np.nan, dtype=np.float32)
    template_arr[:4, :5] = 0.0
    label_arr = np.zeros((5, 6), dtype=np.float32)
    candidate_arr = np.zeros((5, 6), dtype=np.float32)
    candidate_arr[1, 2] = 1.0
    write_tif(template, template_arr, nodata=np.nan)
    write_tif(labels, label_arr)
    write_tif(candidate, candidate_arr)
    return candidate, template, labels


def test_valid_raster_passes_format_and_catalogue_checks_but_never_authorizes_upload(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)

    report = validate_submission(candidate, template, labels)

    assert report["format_passed"] is True
    assert all(report["format_checks"].values())
    assert report["catalogue_check"]["passed"] is True
    assert report["statistics"]["positive_pixels_inside_footprint"] == 1
    assert report["submission_authorized"] is False
    assert "HOLDOUT-DTI" in report["authorization_reason"]


def test_nonfinite_outside_footprint_fails_range_preflight(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.float32)
    arr[1, 2] = 1.0
    arr[4, 5] = np.nan
    write_tif(candidate, arr)

    report = validate_submission(candidate, template, labels)

    assert report["format_passed"] is False
    assert report["format_checks"]["finite_inside_footprint"] is True
    assert report["format_checks"]["finite_everywhere"] is False
    assert report["format_checks"]["values_in_range_0_1"] is False
    assert report["submission_authorized"] is False


def test_nonfinite_inside_footprint_fails_preflight(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.float32)
    arr[1, 2] = np.nan
    write_tif(candidate, arr)

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["finite_inside_footprint"] is False
    assert report["format_checks"]["finite_everywhere"] is False
    assert report["format_passed"] is False


def test_out_of_range_values_fail_even_when_finite(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.float32)
    arr[1, 2] = 1.01
    write_tif(candidate, arr)

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["finite_everywhere"] is True
    assert report["format_checks"]["values_in_range_0_1"] is False
    assert report["format_passed"] is False


def test_nonzero_outside_footprint_fails(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.float32)
    arr[4, 5] = 0.2
    write_tif(candidate, arr)

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["finite_everywhere"] is True
    assert report["format_checks"]["zero_outside_footprint"] is False
    assert report["format_passed"] is False


def test_transform_mismatch_fails_even_if_shape_and_crs_match(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.float32)
    write_tif(candidate, arr, transform=Affine(100, 0, 243450, 0, -100, 4508550))

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["shape_matches_template"] is True
    assert report["format_checks"]["crs_matches_template"] is True
    assert report["format_checks"]["transform_matches_template"] is False
    assert report["format_passed"] is False


def test_shape_mismatch_fails(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    write_tif(candidate, np.zeros((6, 6), dtype=np.float32))

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["shape_matches_template"] is False
    assert report["format_passed"] is False


def test_crs_mismatch_fails(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    write_tif(candidate, np.zeros((5, 6), dtype=np.float32), crs="EPSG:4326")

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["crs_matches_template"] is False
    assert report["format_checks"]["crs_is_epsg32611"] is False
    assert report["format_passed"] is False


def test_nodata_tag_is_rejected(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    write_tif(candidate, np.zeros((5, 6), dtype=np.float32), nodata=0.0)

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["nodata_tag_absent"] is False
    assert report["format_passed"] is False


def test_template_nodata_mask_defines_footprint_even_when_nodata_is_finite(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    template_arr = np.full((5, 6), -9999.0, dtype=np.float32)
    template_arr[:4, :5] = 0.0
    write_tif(template, template_arr, nodata=-9999.0)
    candidate_arr = np.zeros((5, 6), dtype=np.float32)
    candidate_arr[4, 5] = 0.2
    write_tif(candidate, candidate_arr)

    report = validate_submission(candidate, template, labels)

    assert report["template_metadata"]["footprint_cells"] == 20
    assert report["format_checks"]["zero_outside_footprint"] is False
    assert report["format_passed"] is False


def test_empty_template_footprint_is_rejected(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    write_tif(template, np.full((5, 6), np.nan, dtype=np.float32), nodata=np.nan)
    write_tif(candidate, np.zeros((5, 6), dtype=np.float32))

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["template_footprint_nonempty"] is False
    assert report["format_passed"] is False


def test_catalogue_overlap_is_reported_and_fails_full_preflight(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    label_arr = np.zeros((5, 6), dtype=np.float32)
    label_arr[1, 2] = 1.0
    write_tif(labels, label_arr)

    report = validate_submission(candidate, template, labels)

    assert report["format_passed"] is True
    assert report["catalogue_check"]["positive_prediction_overlap"] == 1
    assert report["catalogue_check"]["passed"] is False
    assert report["submission_authorized"] is False


def test_non_float32_candidate_fails(tmp_path):
    candidate, template, labels = make_inputs(tmp_path)
    arr = np.zeros((5, 6), dtype=np.uint8)
    profile = {
        "driver": "GTiff",
        "height": 5,
        "width": 6,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:32611",
        "transform": GRID,
    }
    with rasterio.open(candidate, "w", **profile) as dst:
        dst.write(arr, 1)

    report = validate_submission(candidate, template, labels)

    assert report["format_checks"]["float32"] is False
    assert report["format_passed"] is False
