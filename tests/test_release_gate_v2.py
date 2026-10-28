"""Unit tests for the gate-based release decision (v2).

Every field that could be tampered with must flip the decision to
DO-NOT-SUBMIT with an explicit blocking reason. A passing v2 gate authorises
download + submission readiness only — never a slot spend (always False).
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_project.release_gate_v2 import evaluate_release_gate_v2  # noqa: E402

PREREG = ROOT / "knowledge/preregistration-2026-10-28-lbcalk.md"


def _card() -> dict:
    return json.loads((ROOT / "evidence/lbcal_k_run_card.json").read_text())


def test_clean_card_passes_and_never_authorizes_a_slot_spend():
    gate = evaluate_release_gate_v2(_card(), ROOT, prereg_path=PREREG)
    assert gate["decision"] == "SUBMIT"
    assert gate["okay_to_download_and_submit"] is True
    assert gate["blocking_reasons"] == []
    assert gate["selector_slot_spend"]["authorized"] is False
    assert gate["selector_slot_spend"]["slots_used"] == 0
    assert gate["informational"]["holdout_n_withheld"] == 22232
    passed = {g["name"]: g["passed"] for g in gate["gates"]}
    assert passed["G0_leakage_canary"] and passed["G2_final_dot_uniqueness"]
    assert passed["G4_leaderboard_estimate_gt_0p2778"]
    assert passed["G5_holdout_context_reported"]


def test_tampered_bytes_fail_closed():
    card = _card()
    card["raster"]["sha256"] = "0" * 64
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert any("SHA-256" in r or "digest" in r for r in gate["blocking_reasons"])


def test_failed_core_gate_fails_closed():
    for name in ("G0_leakage_canary", "G1_preplacement_surface",
                 "G2_final_dot_uniqueness", "G3_format_portal_range",
                 "G4_leaderboard_estimate_gt_0p2778"):
        card = _card()
        for g in card["gates"]:
            if g["name"] == name:
                g["passed"] = False
        gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
        assert gate["decision"] == "DO-NOT-SUBMIT", name


def test_overlap_above_gate_fails_closed():
    card = _card()
    for g in card["gates"]:
        if g["name"] == "G2_final_dot_uniqueness":
            g["detail"]["U3_max_nonlattice_overlap_3px"] = 0.7001
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_repair_gutting_fails_closed():
    card = _card()
    for g in card["gates"]:
        if g["name"] == "G2_final_dot_uniqueness":
            g["detail"]["repair_gutted_over_25pct"] = True
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_slot_spend_or_budget_violation_fails_closed():
    card = _card()
    card["budget"]["weekly_slots_used"] = 1
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"
    card = _card()
    card["budget"]["experiments_run"] = 4
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_estimate_at_or_below_champion_fails_closed():
    card = _card()
    for g in card["gates"]:
        if g["name"] == "G4_leaderboard_estimate_gt_0p2778":
            g["detail"]["cross_fit_mean"] = 0.2778
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_unlabelled_holdout_or_estimate_fails_closed():
    card = _card()
    for g in card["gates"]:
        if g["name"] == "G4_leaderboard_estimate_gt_0p2778":
            g["detail"]["label"] = "projected score 0.99"
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"
    card = _card()
    card["holdout"]["label"] = "score"
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_note_and_name_length_limits():
    card = _card()
    card["note"] = "x" * 141
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"
    card = _card()
    card["submission_name"] = ""
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_missing_preregistration_fails_closed(tmp_path):
    gate = evaluate_release_gate_v2(_card(), ROOT, prereg_path=tmp_path / "nope.md")
    assert gate["decision"] == "DO-NOT-SUBMIT"


def test_negative_card_stays_negative():
    card = copy.deepcopy(_card())
    card["verdict"] = "negative"
    gate = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG)
    assert gate["decision"] == "DO-NOT-SUBMIT"
