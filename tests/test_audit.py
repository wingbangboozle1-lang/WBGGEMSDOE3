import json
from pathlib import Path
import numpy as np
import pytest
from scipy.stats import spearmanr

from gems_project.audit import universal_witness, binary_spearman, violates_literal_protocol
from gems_project.run_card import make_card

ROOT = Path(__file__).resolve().parents[1]


def test_universal_witness_proves_overlap_for_arbitrary_nonempty_dot_sets():
    foot = np.array([[True, True, False], [True, True, True]])
    witness = foot.copy()
    proof = universal_witness(foot, witness)
    assert proof["universal_blocker"] and proof["uncovered_cells"] == 0
    # Every possible nonempty subset, not merely one hand-picked candidate.
    coordinates = np.argwhere(foot)
    for i in range(1, 1 << len(coordinates)):
        candidate = np.zeros_like(foot)
        for k, (y, x) in enumerate(coordinates):
            if (i >> k) & 1:
                candidate[y, x] = True
        assert witness[candidate].all()


def test_incomplete_witness_is_not_universal_and_empty_footprint_fails():
    a = np.ones((3, 3), bool)
    b = a.copy()
    b[1, 1] = False
    result = universal_witness(a, b)
    assert not result["universal_blocker"]
    assert result["uncovered_cells"] == 1
    with pytest.raises(ValueError, match="empty footprint"):
        universal_witness(np.zeros((2, 2), bool), np.ones((2, 2), bool))
    with pytest.raises(ValueError, match="grids must match"):
        universal_witness(a, b[:2])


def test_binary_rank_formula_exactly_matches_scipy_tied_spearman():
    rng = np.random.default_rng(8)
    for _ in range(25):
        valid = rng.random((17, 23)) > 0.1
        a = rng.random(valid.shape) < 0.13
        b = rng.random(valid.shape) < 0.25
        actual = binary_spearman(a, b, valid)
        expected = spearmanr(a[valid].astype(int), b[valid].astype(int)).statistic
        assert actual == pytest.approx(expected, abs=1e-12)
    assert binary_spearman(np.zeros((2, 2)), np.ones((2, 2)), np.ones((2, 2))) is None


def test_user_rank_stop_is_two_sided_and_thresholds_are_strict():
    assert violates_literal_protocol(0.1, -0.91)
    assert violates_literal_protocol(0.1, 0.91)
    assert violates_literal_protocol(0.701, 0.0)
    assert not violates_literal_protocol(0.70, -0.90)
    assert not violates_literal_protocol(0.0, None)
    with pytest.raises(ValueError, match="rank correlation"):
        violates_literal_protocol(0.0, float("nan"))
    with pytest.raises(ValueError, match="overlap"):
        violates_literal_protocol(-0.1, 0.0)


def test_recorded_negative_card_is_hash_bound_and_has_no_imaginary_raster():
    path = ROOT / "evidence/focus_audit.json"
    expected = make_card(path)
    card = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert card == expected
    assert card["verdict"] == "negative"
    assert card["holdout_dti"]["value"] is None
    assert card["raster_sha256"] is None
    assert card["validator_output"]["status"].startswith("NOT_RUN")
    assert card["submission_name"] is None
    assert len(card["submission_note"]) <= 140
    assert card["selector_approval"] is False


def test_recorded_focus_audit_has_nine_references_and_no_upload_approval():
    result = json.loads((ROOT / "evidence/focus_audit.json").read_text())
    assert len(result["focus_sites"]) == 9
    assert len({r["site"] for r in result["focus_sites"]}) == 9
    assert all(not r["ok_to_submit"] for r in result["focus_sites"])
    assert all(r["leaderboard_estimate"] is None for r in result["focus_sites"])
    assert result["witness"]["footprint_cells"] == result["witness"]["witness_positive_inside"]
    assert result["gems27_h31_conflicting_site_advice"]["literal_forward_overlap_vs_registered_witness"] == 1
    assert result["model_experiments_run"] == result["weekly_slots_used"] == 0
