"""Tests for the exact distance-weighted Tversky implementation (src/gemsw/exact.py).

The identities checked here are the ones the whole project leans on:
  * DTI = TP_w / (0.2(TP_w + FP_w) + 0.8 |G|)
  * adding one unit dot raises the denominator by exactly 0.2
  * a dot exactly on a truth cell earns credit 1 and costs 0
"""
import numpy as np
import pytest

from gemsw import exact as EX


def _grid(shape=(40, 40)):
    return np.zeros(shape, bool)


def test_perfect_single_pixel():
    t = _grid()
    t[10, 10] = True
    p = np.zeros_like(t, dtype=float)
    p[10, 10] = 1.0
    r = EX.exact_dti(p, t)
    assert r["dti"] == pytest.approx(1.0, abs=1e-9)
    assert r["fp_w"] == pytest.approx(0.0, abs=1e-12)
    assert r["fn_w"] == pytest.approx(0.0, abs=1e-12)


def test_one_pixel_offset_credit_two_thirds():
    t = _grid()
    t[10, 10] = True
    p = np.zeros_like(t, dtype=float)
    p[10, 11] = 1.0                      # distance 1 px, R = 3 px -> k = 2/3
    r = EX.exact_dti(p, t)
    assert r["tp_w"] == pytest.approx(2.0 / 3.0, abs=1e-9)
    assert r["fp_w"] == pytest.approx(1.0 / 3.0, abs=1e-9)
    assert r["dti"] == pytest.approx((2 / 3) / (0.2 * 1 + 0.8 * 1), abs=1e-9)


def test_denominator_grows_by_exactly_alpha_per_dot():
    t = _grid()
    t[5, 5] = True
    p1 = np.zeros_like(t, dtype=float)
    p1[30, 30] = 1.0                     # far from truth: zero credit
    r1 = EX.exact_dti(p1, t)
    p2 = p1.copy()
    p2[32, 32] = 1.0                     # one more, also far
    r2 = EX.exact_dti(p2, t)
    assert r2["tp_w"] == r1["tp_w"]
    assert (r2["tp_w"] + r2["fp_w"]) - (r1["tp_w"] + r1["fp_w"]) == pytest.approx(1.0, abs=1e-12)


def test_empty_prediction_scores_zero():
    t = _grid()
    t[1, 1] = True
    r = EX.exact_dti(np.zeros_like(t, dtype=float), t)
    assert r["dti"] == 0.0
    assert r["fn_w"] == 1.0


def test_soft_and_binary_agree_when_support_is_binary():
    rng = np.random.default_rng(0)
    t = rng.random((30, 30)) > 0.97
    p = np.zeros_like(t, dtype=float)
    p[rng.integers(0, 30, 20), rng.integers(0, 30, 20)] = 1.0
    a = EX.exact_dti(p, t)
    b = EX.exact_dti(np.where(p > 0, 1.0, 0.0), t)
    assert a["dti"] == pytest.approx(b["dti"], abs=1e-12)


def test_kernel_radius_is_three_pixels():
    assert EX.RADIUS_PX == 3.0
    assert EX.kernel_from_distance(np.array([0.0, 1.0, 3.0, 4.0])).tolist() == \
        pytest.approx([1.0, 2 / 3, 0.0, 0.0])
