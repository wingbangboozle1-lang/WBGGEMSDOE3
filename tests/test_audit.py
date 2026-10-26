import numpy as np
import pytest

from audit_priority import binary_rank_correlation, min_overlap_bound
from preflight import exceeds_overlap_limit


def test_lattice_lower_bound_and_boundary():
    assert min_overlap_bound(6649, 37654, 5167373) == pytest.approx(0.8234184947150369)
    assert min_overlap_bound(6649, 22163, 5167373) <= 0.70
    assert min_overlap_bound(6649, 22164, 5167373) > 0.70
    assert min_overlap_bound(10, 5, 20) == 0
    with pytest.raises(ValueError):
        min_overlap_bound(1, 0, 20)
    with pytest.raises(ValueError):
        min_overlap_bound(21, 5, 20)
    with pytest.raises(ValueError):
        min_overlap_bound(1, 21, 20)


def test_strict_overlap_limit_uses_exact_integer_boundary():
    assert not exceeds_overlap_limit(3, 10)  # exactly 70% is not >70%
    assert exceeds_overlap_limit(2, 10)
    assert not exceeds_overlap_limit(4, 10)
    assert not exceeds_overlap_limit(100, 10)
    with pytest.raises(ValueError):
        exceeds_overlap_limit(0, 0)


def test_binary_spearman_with_ties_and_constant():
    footprint = np.ones((2, 3), bool)
    a = np.array([[1, 0, 1], [0, 0, 1]], bool)
    assert binary_rank_correlation(a, a, footprint) == pytest.approx(1)
    assert binary_rank_correlation(a, ~a, footprint) == pytest.approx(-1)
    assert binary_rank_correlation(a, np.zeros_like(a), footprint) is None
    # Pixels outside the footprint must not influence the statistic.
    footprint[0, 0] = False
    changed = a.copy()
    changed[0, 0] = not changed[0, 0]
    assert binary_rank_correlation(a, changed, footprint) == pytest.approx(1)


def test_one_dot_can_cover_multiple_truth_pixels():
    # This is a synthetic arithmetic counterexample, not a holdout score.
    nearest_credit = 1.0
    marginal_truth_credit = 1.0 + (1.0 - 1.0 / 3.0)
    assert marginal_truth_credit > nearest_credit
