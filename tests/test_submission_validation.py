"""Regression tests for scripts/validate_submission.py (format + uniqueness gates).

Synthetic small grids keep these fast; one test runs the shipped primary file against the
repository's template grid (skipped if the shipped file is absent)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_submission as V  # noqa: E402


def _write(path: Path, arr: np.ndarray, *, crs="EPSG:32611", dtype="float32", nodata=None,
           transform=None) -> Path:
    h, w = arr.shape
    tr = transform or from_origin(243350.0, 4508550.0, 100.0, 100.0)
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype=dtype,
                       crs=CRS.from_string(crs), transform=tr, nodata=nodata) as ds:
        ds.write(arr.astype(dtype), 1)
    return path


@pytest.fixture()
def grid(tmp_path):
    sample = _write(tmp_path / "sample.tif", np.zeros((120, 150), np.float32))
    return sample, tmp_path


def _dots(seed: int, n: int = 60) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = np.zeros((120, 150), np.float32)
    idx = rng.choice(a.size, size=n, replace=False)
    a.flat[idx] = rng.uniform(0.2, 1.0, size=n).astype(np.float32)
    return a


def test_valid_zero_outside_file_passes_format(grid):
    sample, tmp = grid
    cand = _write(tmp / "ok.tif", _dots(1))
    fmt = V.format_gate(cand, sample)
    assert fmt["passed"], fmt["problems"]
    assert fmt["inside_nan_cells"] == 0 and fmt["inside_min"] >= 0 and fmt["inside_max"] <= 1


def test_nan_cell_fails_format(grid):
    sample, tmp = grid
    a = _dots(2)
    a[0, 0] = np.nan
    cand = _write(tmp / "nan.tif", a)
    fmt = V.format_gate(cand, sample)
    assert not fmt["passed"]
    assert "whole_array_all_finite" in fmt["problems"]


def test_out_of_range_value_fails_format(grid):
    sample, tmp = grid
    a = _dots(3)
    a[5, 5] = 1.5
    cand = _write(tmp / "hi.tif", a)
    fmt = V.format_gate(cand, sample)
    assert not fmt["passed"]
    assert "whole_array_range_0_1" in fmt["problems"]


def test_wrong_crs_fails_format(grid):
    sample, tmp = grid
    cand = _write(tmp / "crs.tif", _dots(4), crs="EPSG:4326")
    assert not V.format_gate(cand, sample)["passed"]


def test_wrong_transform_fails_format(grid):
    sample, tmp = grid
    cand = _write(tmp / "tr.tif", _dots(5), transform=from_origin(243360.0, 4508550.0, 100.0, 100.0))
    assert not V.format_gate(cand, sample)["passed"]


def test_float64_fails_format(grid):
    sample, tmp = grid
    cand = _write(tmp / "f64.tif", _dots(6), dtype="float64")
    assert not V.format_gate(cand, sample)["passed"]


def test_exact_duplicate_fails_uniqueness(grid):
    sample, tmp = grid
    cand = _write(tmp / "cand.tif", _dots(7))
    copy = tmp / "copy.tif"
    copy.write_bytes(cand.read_bytes())
    u = V.uniqueness_gate(cand, [copy])
    assert u["exact_duplicates"] == ["copy.tif"]
    assert not u["passed"]


def test_independent_design_passes_uniqueness(grid):
    sample, tmp = grid
    cand = _write(tmp / "cand.tif", _dots(8))
    other = _write(tmp / "other.tif", _dots(9, n=60))
    u = V.uniqueness_gate(cand, [other])
    assert u["n_compared"] == 1 and u["n_skipped"] == 0
    assert u["max_share_our_dots_within_3px"] <= V.LIMIT_OVERLAP
    assert u["passed"]


def test_near_copy_fails_overlap_gate(grid):
    sample, tmp = grid
    base = _dots(10, n=60)
    cand = _write(tmp / "cand.tif", base)
    # Shift every dot by one pixel: every dot is within 3 px of the comparator.
    shifted = np.zeros_like(base)
    shifted[:, 1:] = base[:, :-1]
    other = _write(tmp / "shift.tif", shifted)
    u = V.uniqueness_gate(cand, [other])
    assert u["max_share_our_dots_within_3px"] > V.LIMIT_OVERLAP
    assert not u["passed"]


def test_mismatched_grid_is_reported_as_skipped_not_passed(grid):
    sample, tmp = grid
    cand = _write(tmp / "cand.tif", _dots(11))
    odd = _write(tmp / "odd.tif", np.zeros((10, 10), np.float32))
    u = V.uniqueness_gate(cand, [odd])
    assert u["n_compared"] == 0 and u["n_skipped"] == 1
    assert not u["passed"], "no comparable comparator must not count as a pass"


def test_registry_dedupes_identical_bytes(grid, tmp_path_factory):
    sample, tmp = grid
    d = tmp_path_factory.mktemp("reg")
    cand = _write(tmp / "cand.tif", _dots(12))
    _write(d / "a.tif", _dots(13))
    (d / "b.tif").write_bytes((d / "a.tif").read_bytes())
    paths = V.registry_paths([d], include_repo=False, candidate=cand)
    assert len(paths) == 1


@pytest.mark.skipif(not (ROOT / "docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif").exists(),
                    reason="shipped primary file absent")
def test_shipped_primary_file_format_and_hash_binding():
    cand = ROOT / "docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif"
    fmt = V.format_gate(cand, ROOT / "data/template_grid.tif")
    assert fmt["passed"], fmt["problems"]
    assert fmt["positive_cells"] == 20000
    assert V.sha256(cand) == "283209b977bc1c4885b6e9936494575d324a3460f289312aeeef760528909dda"
