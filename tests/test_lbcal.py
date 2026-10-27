"""Unit tests for the LBCAL lane (synthetic arrays; no caches needed)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import coverage as COV, design as DS, features as F, model as Mdl  # noqa: E402


def kernel(d):
    return np.maximum(1.0 - d / 3.0, 0.0)


def test_max_credit_equals_official_kernel_for_binary_masks():
    rng = np.random.default_rng(0)
    p = (rng.random((60, 70)) < 0.02).astype(np.float32)
    c = COV.max_credit(p)
    ref = kernel(distance_transform_edt(p == 0))
    assert np.allclose(c, ref, atol=1e-6)


def test_truth_side_credit_matches_exact_tp_when_pi_is_the_truth():
    rng = np.random.default_rng(1)
    p = (rng.random((50, 50)) < 0.03).astype(np.float32)
    gt = np.zeros((50, 50), bool)
    gt[10, 5:45] = True
    gt[5:40, 30] = True
    tp_exact = kernel(distance_transform_edt(p == 0))[gt].sum()
    assert np.isclose((COV.max_credit(p) * gt).sum(), tp_exact)


def test_marginal_tp_matches_brute_force():
    rng = np.random.default_rng(2)
    pi = (rng.random((30, 30)) * 0.05).astype(np.float32)
    dots = rng.random((30, 30)) < 0.03
    c = COV.max_credit(dots.astype(np.float32))
    g = DS.marginal_tp(pi, c)
    base = float((pi * c).sum())
    for y, x in [(5, 5), (15, 20), (0, 29), (29, 0), (12, 12)]:
        d2 = dots.copy()
        d2[y, x] = True
        brute = float((pi * COV.max_credit(d2.astype(np.float32))).sum()) - base
        assert np.isclose(g[y, x], brute, atol=1e-5)


def test_placement_respects_allowed_mask_and_never_lowers_expected_dti():
    rng = np.random.default_rng(3)
    pi = np.zeros((80, 80), np.float32)
    pi[20:40, 10:70] = 0.08
    pi += (rng.random(pi.shape) * 0.002).astype(np.float32)
    allowed = np.ones(pi.shape, bool)
    allowed[30, :] = False
    dots, hist = DS.place(pi, allowed, log=None, min_batch=5, max_batch=50)
    assert dots.any() and not (dots & ~allowed).any()
    vals = [h["expected_dti"] for h in hist[1:]]
    assert all(b >= a - 1e-4 for a, b in zip(vals, vals[1:]))


def test_model_predict_and_link_shapes():
    M, names = Mdl.design_matrix()
    assert M.shape == (F.n_cells(), len(names)) and names[0] == "intercept"
    beta = np.zeros(len(names))
    beta[0] = -5.0
    pi, dpi = Mdl.link(M @ beta, 0.2)
    assert np.all(pi <= 0.2) and np.all(dpi >= 0)
    C = np.ones((2, F.n_cells()))
    y, aux = Mdl.predict(beta, M, C, C, np.array([100.0, 200.0]), np.ones(F.n_cells()), pi_max=0.2)
    assert y.shape == (2,) and np.all((y >= 0) & (y <= 1))


def test_feature_levels_are_consistent():
    lv = F.decode_cells()
    assert set(lv) == set(F.FEATURES)
    for f in F.FEATURES:
        assert lv[f].max() == F.LEVELS[f] - 1 and len(F.LEVEL_NAMES[f]) == F.LEVELS[f]


def test_lbcal_run_card_is_complete_and_hash_bound():
    card = json.loads((ROOT / "evidence" / "lbcal_run_card.json").read_text())
    for k in ("hypothesis", "mechanism", "non_fault_mimic", "holdout", "registry", "file", "validator",
              "submission_name", "note", "verdict", "leakage_canary", "estimate"):
        assert k in card, k
    assert card["holdout"]["label"] == "HOLDOUT-DTI" and len(card["holdout"]["ci95"]) == 2
    assert card["estimate"]["label"].startswith("ESTIMATE")
    assert card["verdict"] in {"promote", "negative"}
    if card["verdict"] == "negative":
        assert card["failed_gates"] and "DO-NOT-SUBMIT" in card["submission_name"]
    tif = ROOT / card["file"]["path"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["file"]["sha256"]
    assert card["validator"]["passed"] is True and len(card["note"]) <= 140


def test_lbcal_lane_pages_are_scoped_and_hash_bound():
    lane = json.loads((ROOT / "evidence" / "lbcal_lane_decision.json").read_text())
    assert lane["verdict"] == "negative" and lane["ok_to_submit"] is False and lane["download"]["cleared"] is False
    docs = ROOT / "docs" / "lbcal"
    for page in ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "sources.html"):
        body = (docs / page).read_text()
        assert '<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT">' in body, page
        assert 'name="gemsdoe-decision"' not in body, page  # never competes with the repository decision meta
        assert "../index.html" in body, page
    name = Path(lane["download"]["tif"]).name
    assert "DO-NOT-SUBMIT" in name
    served = docs / "downloads" / name
    assert hashlib.sha256(served.read_bytes()).hexdigest() == lane["sha256"]
    readme = (ROOT / "README.md").read_text()
    assert "FOURTH PARALLEL LANE: LBCAL" in readme and "docs/lbcal/index.html" in readme


def test_lbcal_delta_scan_covers_the_rasters_merged_later():
    delta = json.loads((ROOT / "evidence" / "lbcal" / "registry_delta_main.json").read_text())
    files = {Path(r["file"]).name for r in delta["rows"]}
    assert any("tde30k" in f for f in files) and any("dipolehybrid" in f for f in files)
    assert all(0.0 <= r["my_dots_within_3px_of_theirs"] <= 1.0 for r in delta["rows"])
