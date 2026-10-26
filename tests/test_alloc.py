"""Allocator: the closed-form marginal gain must equal the brute-force change of J = (1-.2mu)TP + .2mu M - .2mu N."""
import sys
from pathlib import Path
import numpy as np, pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemsw import alloc as A, ledger as L, metric as M


def J(rho, dots, mu):
    K, C = L.credit_maps(dots.astype(np.float32))
    return (1 - .2 * mu) * float((rho * K).sum()) + .2 * mu * float((rho * C).sum()) / 3.0 - .2 * mu * float(dots.sum())


def test_marginal_gain_matches_bruteforce():
    rng = np.random.default_rng(5)
    rho = (rng.random((24, 24)) * 0.3).astype(np.float32)
    dots = rng.random((24, 24)) < 0.05
    K, _ = L.credit_maps(dots.astype(np.float32))
    mu = 0.27
    g = A.gain_map(rho, K, mu)
    for (y, x) in [(5, 5), (12, 9), (20, 3), (2, 21)]:
        if dots[y, x]:
            continue
        d2 = dots.copy(); d2[y, x] = True
        assert g[y, x] == pytest.approx(J(rho, d2, mu) - J(rho, dots, mu), abs=1e-4)


def test_expected_tp_equals_official_metric_for_binary_truth():
    rng = np.random.default_rng(9)
    truth = rng.random((26, 26)) < 0.08
    dots = rng.random((26, 26)) < 0.07
    e = A.expected_dti(truth.astype(np.float32), dots)
    assert e["tp"] == pytest.approx(M.components(dots.astype(float), truth)["TP_w"], abs=1e-4)


def test_allocate_respects_cap_and_candidates():
    rng = np.random.default_rng(1)
    rho = (rng.random((40, 40)) * 0.5).astype(np.float32)
    cand = np.zeros((40, 40), bool); cand[:, :20] = True
    r = A.allocate(rho, cand, 0.2, n_max=15, min_gain=-1e6)
    assert r["dots"].sum() <= 15 and not r["dots"][:, 20:].any()
