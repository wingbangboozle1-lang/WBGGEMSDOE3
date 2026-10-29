"""Offline checks on the saved witness-definition evidence (no network, no raster needed)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence" / "witness_definition_check_2026-10-29.json"
RUN = ROOT / "evidence" / "session_2026-10-29_run_card.json"
GATE = ROOT / "docs" / "data" / "release_gate.json"
PINNED = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"


def test_witness_hash_and_registry_agree():
    d = json.loads(EV.read_text())
    assert d["sha256"] == PINNED
    assert d["sha256_matches_registry"] is True
    assert d["registry_dots_match_recount"] is True


def test_literal_rule_covers_footprint_and_threshold_is_sparse():
    d = json.loads(EV.read_text())
    assert d["literal_positive_support"]["fraction_of_finite"]["0.0"] == 1.0
    assert d["literal_positive_support"]["cells"]["0.5"] < 0.2 * d["footprint_finite_cells"]


def test_run_card_is_negative_and_creates_no_candidate():
    rc = json.loads(RUN.read_text())
    assert rc["verdict"] == "negative"
    assert rc["okay_to_submit"] is False
    assert rc["okay_to_download_for_submission"] is False
    assert rc["raster"]["generated"] is False
    assert rc["holdout_dti"]["value"] is None
    assert rc["selector"]["weekly_slots_used"] == 0


def test_release_gate_still_do_not_submit():
    g = json.loads(GATE.read_text())
    assert g["decision"] == "DO-NOT-SUBMIT"
    assert g["okay_to_submit"] is False
