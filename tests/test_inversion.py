"""Unit tests for the score-tomography instruments (gemsw.inversion + the emission helpers).

These tests are deliberately synthetic: they check the *algebra* on a grid small enough to
brute-force, so a bug in the fast distance-transform implementation cannot hide.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import inversion as INV  # noqa: E402


def brute_force_dti(dots: np.ndarray, truth: np.ndarray, active: np.ndarray) -> tuple[float, dict]:
    """Explicit official DTI: max over dots per truth cell, sum over dots for FP."""
    H, W = truth.shape
    k = lambda d: max(1.0 - d / 3.0, 0.0)
    T = 0.0
    for y, x in zip(*np.nonzero(truth & active)):
        best = 0.0
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and dots[yy, xx] and active[yy, xx]:
                    best = max(best, k(np.hypot(dy, dx)))
        T += best
    FP = 0.0
    ty, tx = np.nonzero(truth & active)
    for y, x in zip(*np.nonzero(dots & active)):
        if ty.size:
            d = np.min(np.hypot(ty - y, tx - x))
        else:
            d = np.inf
        FP += 1.0 - k(d)
    nG = float((truth & active).sum())
    dti = T / (T + 0.2 * FP + 0.8 * (nG - T) + 1e-12)
    return dti, {"T": T, "FP": FP, "nG": nG}


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_score_from_dots_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    shape = (60, 70)
    active = np.ones(shape, bool)
    active[:5, :] = False                      # a masked band, like the catalogue mask
    truth = active & (rng.random(shape) < 0.03)
    dots = active & (rng.random(shape) < 0.03)
    fast = INV.score_from_dots_full(dots, truth, active)
    slow, parts = brute_force_dti(dots, truth, active)
    assert fast["dti"] == pytest.approx(slow, rel=1e-9, abs=1e-12)
    assert fast["T"] == pytest.approx(parts["T"], rel=1e-9, abs=1e-9)
    assert fast["FP_w"] == pytest.approx(parts["FP"], rel=1e-9, abs=1e-9)


def test_kernel_is_zero_beyond_three_pixels_and_one_at_zero():
    d = np.array([0.0, 1.5, 3.0, 3.0001, 10.0])
    k = INV.kernel_from_distance(d)
    assert k[0] == 1.0
    assert k[1] == pytest.approx(0.5)
    assert k[2] == pytest.approx(0.0)
    assert np.all(k[3:] == 0.0)


def test_dots_on_the_mask_earn_nothing_and_still_cost():
    """A dot inside the masked band must add FP mass without adding credit."""
    shape = (40, 40)
    active = np.ones(shape, bool)
    active[:, :20] = False                      # left half masked
    truth = np.zeros(shape, bool)
    truth[20, 30] = True
    on_mask = np.zeros(shape, bool)
    on_mask[20, 2] = True
    r = INV.score_from_dots_full(on_mask, truth, active)
    assert r["T"] == 0.0
    assert r["FP_w"] == pytest.approx(1.0)
    assert r["dti"] == pytest.approx(0.0)


def test_dense_dots_on_truth_score_one_and_extra_dots_only_add_cost():
    shape = (30, 30)
    active = np.ones(shape, bool)
    truth = np.zeros(shape, bool)
    truth[10, 10:20] = True
    dots = truth.copy()
    perfect = INV.score_from_dots_full(dots, truth, active)
    assert perfect["dti"] == pytest.approx(1.0, abs=1e-9)
    wasteful = dots.copy()
    wasteful[25, 25] = True                     # one useless dot far from truth
    worse = INV.score_from_dots_full(wasteful, truth, active)
    assert worse["dti"] < perfect["dti"]


def test_block_operators_round_trip_and_weight_by_active_cells():
    a = np.arange(64, dtype=np.float64).reshape(8, 8)
    mean = INV.block_mean(a, 4)
    total = INV.block_sum(a, 4)
    assert mean.shape == (2, 2)
    assert mean[0, 0] == pytest.approx(a[:4, :4].mean())
    assert total[1, 1] == pytest.approx(a[4:, 4:].sum())


def test_upsample_repeats_blocks_without_changing_shape():
    coarse = np.array([[1.0, 2.0], [3.0, 4.0]])
    full = INV.upsample(coarse, (8, 8), factor=4)
    assert full.shape == (8, 8)
    assert full[0, 0] == 1.0 and full[7, 7] == 4.0


def test_implied_targets_inverts_the_metric_exactly():
    """T = s(beta*M + alpha*FP)/(1 - alpha*s) must invert DTI = T/(T+alpha FP+beta(M-T))."""
    M, FP, alpha, beta = 27110.0, 41281.0, 0.2, 0.8
    for s in (0.05, 0.15, 0.25, 0.30):
        T = s * (beta * M + alpha * FP) / (1 - alpha * s)
        back = T / (T + alpha * FP + beta * (M - T))
        assert back == pytest.approx(s, rel=1e-12)
