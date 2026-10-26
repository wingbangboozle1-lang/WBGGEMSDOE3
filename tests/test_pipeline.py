"""End-to-end pipeline tests using synthetic stand-in data.

These tests verify the GEMS submission pipeline runs and produces a
format-valid GeoTIFF. They do NOT measure real competition performance.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dti import pooled_dti
from src.features import curvature_like, openness_proxy, combine_features, lineament_density
from src.validate import validate_submission


def test_pooled_dti_bounds():
    rng = np.random.default_rng(0)
    H = W = 100
    target = np.zeros((H, W), dtype=bool)
    target[40:60, 40:60] = True
    prediction = np.zeros((H, W), dtype=np.float64)
    prediction[40:60, 40:60] = 1.0
    res = pooled_dti(prediction, target, pixel_size_m=30.0)
    assert 0.0 <= res["dti"] <= 1.0
    assert res["beta_term"] == 1.0  # predictions exactly on targets
    assert res["alpha_term"] == 1.0


def test_pooled_dti_rejects_out_of_range():
    rng = np.random.default_rng(0)
    prediction = rng.standard_normal((10, 10)) * 2 - 1  # outside [0,1]
    target = np.zeros((10, 10), dtype=bool)
    target[0, 0] = True
    try:
        pooled_dti(prediction, target, pixel_size_m=30.0)
        assert False, "should have raised"
    except ValueError:
        pass


def test_feature_shapes():
    rng = np.random.default_rng(1)
    a = rng.standard_normal((50, 50))
    assert curvature_like(a, 30.0).shape == (50, 50)
    assert openness_proxy(a, 30.0).shape == (50, 50)


def test_combine_features_in_range():
    rng = np.random.default_rng(2)
    feats = {
        "a": rng.standard_normal((40, 40)),
        "b": rng.standard_normal((40, 40)),
    }
    out = combine_features(feats, {"a": 0.5, "b": 0.5})
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_validation_gates(tmp_path):
    # valid tif
    arr = np.random.default_rng(3).random((20, 30)).astype(np.float32)
    valid = tmp_path / "valid.tif"
    with rasterio.open(valid, "w", driver="GTiff", dtype="float32", width=30,
                       height=20, count=1, compress="deflate") as s:
        s.write(arr, 1)
    res = validate_submission(str(valid))
    assert res.ok is True
    assert res.metrics["value_min"] >= 0.0
    assert res.metrics["value_max"] <= 1.0

    # out-of-range tif
    bad = tmp_path / "bad.tif"
    arr2 = (np.random.default_rng(4).random((20, 30)) * 2).astype(np.float32)
    with rasterio.open(bad, "w", driver="GTiff", dtype="float32", width=30,
                       height=20, count=1, compress="deflate") as s:
        s.write(arr2, 1)
    res2 = validate_submission(str(bad))
    assert res2.ok is False


if __name__ == "__main__":
    test_pooled_dti_bounds()
    test_pooled_dti_rejects_out_of_range()
    test_feature_shapes()
    test_combine_features_in_range()
    import tempfile
    test_validation_gates(Path(tempfile.mkdtemp()))
    print("All pipeline tests passed.")
