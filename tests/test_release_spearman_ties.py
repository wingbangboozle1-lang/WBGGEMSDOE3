"""Regression tests for the tie handling in the uniqueness rank correlation.

The first version of ``gems_release.validate._spearman`` used
``np.argsort(np.argsort(x))``.  For binary rasters (millions of ties) that is not a
rank transform: NumPy resolves ties by index order, which fabricates a monotone
trend.  Measured effect: two *independent* 2 %-density dot fields returned
rho ~ 0.92, above the 0.90 uniqueness bar, and a legitimate candidate was rejected.

These tests pin the correct behaviour so the bug cannot come back:
  * tied binary fields that are independent must measure ~0;
  * identical fields must measure exactly 1;
  * the value must equal ``scipy.stats.spearmanr`` on the same data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release.validate import _spearman  # noqa: E402


def _binary_field(rng, n=400, density=0.02):
    return (rng.random(n) < density).astype(np.float32)


def test_independent_binary_fields_do_not_fabricate_correlation():
    rng = np.random.default_rng(7)
    rhos = [_spearman(_binary_field(rng), _binary_field(rng)) for _ in range(25)]
    worst = max(abs(r) for r in rhos)
    assert worst < 0.25, f"tie artefact: worst |rho| = {worst:.3f} on independent fields"


def test_identical_binary_faces_return_one():
    rng = np.random.default_rng(11)
    f = _binary_field(rng)
    assert _spearman(f, f) == pytest.approx(1.0)


def test_matches_scipy_on_tied_data():
    rng = np.random.default_rng(13)
    for _ in range(10):
        a, b = _binary_field(rng), _binary_field(rng)
        expected = spearmanr(a, b).statistic
        assert _spearman(a, b) == pytest.approx(expected, abs=1e-12)


def test_shifted_copy_of_a_smooth_field_is_flagged():
    """A one-pixel shift of a smooth field is still a near-copy and must be caught."""
    rng = np.random.default_rng(17)
    ramp = np.linspace(0, 1, 900) + rng.normal(0, 0.01, 900)
    assert _spearman(ramp, np.roll(ramp, 1)) > 0.9
