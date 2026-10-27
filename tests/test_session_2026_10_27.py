"""Offline checks on the 2026-10-27 evidence. They read committed files only, so CI can run them
without restoring the shared-data cache."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_verification_record_all_passed_and_no_candidate():
    v = _load("evidence/verification_2026-10-27.json")
    assert v["all_passed"] is True
    assert v["candidate_created"] is False
    assert len(v["checks"]) == 20
    assert all(c["pass"] for c in v["checks"])


def test_repo_tiff_survey_has_no_out_of_range_values():
    v = _load("evidence/verification_2026-10-27.json")
    survey = v["local_tiff_survey"]
    assert len(survey) >= 1
    assert any(r["file"] == "data/template_grid.tif" for r in survey)
    assert sum(r["out_of_range_finite_cells"] for r in survey) == 0


def test_h6_1_copy_matches_recorded_sha():
    rec = _load("evidence/verification_2026-10-27.json")
    expected = rec["holdout_h6_1"]["source_sha256"]
    data = (ROOT / "evidence/h6_1_proximity_pruning_holdout.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected


def test_session_run_card_is_negative_with_zero_budget_used():
    c = _load("evidence/session_run_card_2026-10-27.json")
    assert c["experiments_run"] == 0
    assert c["slots_used"] == 0
    assert c["okay_to_download"] is False
    assert c["okay_to_submit"] is False
    assert c["candidate_file"] is None
    assert c["submission_name"] is None
    assert c["local_validation"]["all_passed"] is True
    assert c["local_validation"]["checks"] == len(_load("evidence/verification_2026-10-27.json")["checks"])


def test_leaderboard_observation_is_labelled_public_split():
    obs = _load("evidence/leaderboard_observation_2026-10-27.json")
    text = json.dumps(obs).lower()
    assert "public" in text
    assert "0.4544" in text


def test_submission_comment_limit_is_documented_on_site():
    html = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
    assert "140" in html
    assert "Predicted values must be in range [0, 1]" in html or "range [0, 1]" in html
