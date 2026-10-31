"""2026-10-29 session guards: negative decision, dated leaderboard correction, witness stats, deadline."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_session_card_is_negative_and_does_not_change_gate():
    card = _json("evidence/session_2026-10-29_gate-recheck_run_card.json")
    assert card["verdict"] == "negative"
    assert card["okay_to_submit"] is False
    assert card["okay_to_download_for_submission"] is False
    assert card["raster"]["generated"] is False and card["raster"]["sha256"] is None
    assert card["holdout_dti"]["value"] is None and card["holdout_dti"]["label"] == "NOT-RUN"
    assert card["submission"]["name"] is None
    assert card["experiments"]["geological_experiments_completed"] == 0
    assert "does NOT change the decision" in card["relationship_to_gate_card"]


def test_leaderboard_2026_10_29_records_correct_public_high():
    obs = _json("evidence/leaderboard_observation_2026-10-29.json")
    scores = obs["visible_public_scores"]
    assert scores["rank_1"] == "0.4544"
    assert scores["rank_26"] == "0.3328"
    assert "not a submission receipt" in obs["evidence_class"].lower()
    assert obs["conflicts_with_prior_brief"]["0.4413"].startswith("Not visible")


def test_witness_independent_stats_match_footprint():
    stats = _json("evidence/witness_independent_stats_2026-10-29.json")
    assert stats["footprint_cells"] == 5167373
    w = stats["witness"]
    assert w["positive_cells_inside_footprint"] == stats["footprint_cells"]
    assert w["footprint_cells_not_positive"] == 0
    assert 0 < w["inside_min"] < w["inside_max"] <= 1.0
    assert stats["inputs"]["witness"]["sha256"] == (
        "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be")
    assert stats["inputs"]["sample"]["sha256"] == (
        "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc")


def test_official_deadline_resolution_is_conservative():
    src = _json("evidence/official_source_check_2026-10-29.json")
    assert src["deadline_resolution"]["earlier_cutoff_utc"] == "2026-12-03 22:00 UTC (5:00 p.m. EST, UTC-5)"
    ids = {s["id"] for s in src["sources"]}
    assert {"S1", "S2", "S3", "S6"} <= ids
    rules = next(s for s in src["sources"] if s["id"] == "S6")
    assert any("5:00 p.m. ET" in fact for fact in rules["verified_facts"])


def test_published_index_states_current_negative_and_public_feed():
    page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert "DO NOT DOWNLOAD OR SUBMIT" in page
    assert "no file is cleared" in page.lower()
    assert "0.4544" in page and "0.3925" in page and "0.3195" in page
    assert "data/decision.json" in page
    assert "Q1" not in page and "Q2" not in page
