"""Unit tests for the CSPES lane (surface construction, placement, frozen spec)."""
from __future__ import annotations

import numpy as np
import pytest

from gemsw import cspes as C

rng = np.random.default_rng(42)
H, W = 120, 90


def _grid():
    foot = np.zeros((H, W), bool)
    foot[10:-10, 10:-10] = True
    catalogue = np.zeros((H, W), bool)
    catalogue[60, 30:34] = True
    bands = {
        "grav": rng.normal(size=(H, W)).astype(np.float32),
        "rtp": rng.normal(size=(H, W)).astype(np.float32),
        "elev": rng.normal(size=(H, W)).astype(np.float32),
    }
    bands["grav"][~foot] = np.nan
    return foot, catalogue, bands


def test_surface_bounds_and_components():
    foot, catalogue, bands = _grid()
    fields = C.build_surface(bands, foot)
    s = fields.surface
    assert s.shape == (H, W)
    assert np.isfinite(s[foot]).all()
    assert s[foot].min() >= 0.0 and s[foot].max() <= 1.0
    assert (s[~foot] == 0.0).all()
    # every rank component lives in [0,1]; collinearity is a cosine expression
    assert fields.components["align"].min() >= 0 and fields.components["align"].max() <= 1.0


def test_surface_is_deterministic():
    foot, catalogue, bands = _grid()
    a = C.build_surface(bands, foot).surface
    b = C.build_surface(bands, foot).surface
    assert np.array_equal(a, b)


def test_placement_respects_footprint_catalogue_and_nms():
    foot, catalogue, bands = _grid()
    fields = C.build_surface(bands, foot)
    dots = C.place_dots(fields.surface, foot, catalogue, budget=200, radius=2.0)
    assert dots.dtype == bool
    assert (dots & ~foot).sum() == 0, "no dots outside the footprint"
    assert (dots & catalogue).sum() == 0, "no dots on the catalogue"
    assert dots.sum() <= 200
    # min Euclidean distance >= 2 between any two placed dots
    ys, xs = np.nonzero(dots)
    if dots.sum() > 1:
        order = np.argsort(ys)
        ys, xs = ys[order], xs[order]
        from scipy.spatial import cKDTree
        d, _ = cKDTree(np.column_stack([ys, xs])).query(np.column_stack([ys, xs]), k=2)
        assert d[:, 1].min() >= 2.0


def test_placement_budget_when_eligible_runs_out():
    foot, catalogue, bands = _grid()
    fields = C.build_surface(bands, foot)
    # radius-5 NMS cannot fit 5,000 points on this small grid: must return a feasible set, not raise
    dots = C.place_dots(fields.surface, foot, catalogue, budget=5_000, radius=5.0,
                        candidate_pool=1_000)
    assert dots.sum() > 0 and (dots & ~foot).sum() == 0


def test_sentinel_cleaning_is_required():
    foot, catalogue, bands = _grid()
    bands["rtp"][20, 20] = np.float32(-3.4028234663852886e38)  # competition nodata sentinel
    fields = C.build_surface(bands, foot)
    assert np.isfinite(fields.surface[foot]).all(), "sentinel must never reach the surface"


def test_band_indices_match_verified_tif_order():
    # frozen in knowledge/preregistration-2026-10-27.md against the GeoTIFF descriptions
    assert C.BAND_RTP == 2 and C.BAND_DET_ELEV == 12 and C.BAND_ISO_GRAV == 13
    assert C.DEFAULT_BUDGET == 37_654 and C.NMS_RADIUS_PX == 2.0 and C.TOPO_PENALTY == 0.5
