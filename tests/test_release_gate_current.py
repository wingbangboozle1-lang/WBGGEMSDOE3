"""Regression tests for the release contract; synthetic evidence never selects a slot."""
import json
from pathlib import Path

import pytest
from gems_project.release_gate import evaluate_release_gate

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64


def good():
    authority = {"verdict": "promote", "selector_approval": True, "raster_sha256": SHA}
    candidate = {
        "submission_name": "synthetic-fixture", "submission_note": "Synthetic test only.",
        "raster_sha256": SHA, "verdict": "promote",
        "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator_version": "fixture-v1",
                        "withheld_positives": 10, "value": 0.4, "ci95": [0.3, 0.5],
                        "fold_local_catalogue_features": True, "matched_incumbent_folds": True,
                        "matched_baseline_dti": 0.3, "paired_delta_ci95": [0.01, 0.2]},
        "canary": {"all_features_tested": True, "n_features": 2, "n_features_tested": 2, "max_auc": 0.90},
        "uniqueness": {"literal_pass": True, "complete_registry": True, "registry_expected": 2,
                       "registry_checked": 2,
                       "surface": {"passed": True, "max_abs_spearman": 0.90, "max_dot_overlap": 0.70},
                       "final": {"passed": True, "max_abs_spearman": 0.80, "max_dot_overlap": 0.69}},
        "validator": {"passed": True, "single_band": True, "no_nan_inside_footprint": True,
                      "values_in_0_1": True, "crs_shape_transform_match": True,
                      "saved_bytes_equal_audited_dots": True, "sha256": SHA},
    }
    return authority, candidate


def test_complete_synthetic_contract_is_internally_consistent():
    # This tests the pure schema function, not a real file or a selector action.
    authority, candidate = good()
    assert evaluate_release_gate(authority, candidate)["okay_to_submit"] is True


@pytest.mark.parametrize("section,key,value", [
    ("authority", "selector_approval", False), ("authority", "selector_approval", "true"),
    ("authority", "selector_approval", 1), ("authority", "raster_sha256", "b" * 64),
    ("candidate", "raster_sha256", "not-a-hash"), ("candidate", "submission_note", "x" * 141),
    ("candidate", "verdict", "promote-with-caveat"),
    ("holdout_dti", "label", "PROXY-DTI"), ("holdout_dti", "withheld_positives", 0),
    ("holdout_dti", "ci95", [0.1, 0.2]), ("holdout_dti", "ci95", [float('nan'), 0.9]),
    ("holdout_dti", "fold_local_catalogue_features", False),
    ("holdout_dti", "matched_incumbent_folds", "true"),
    ("holdout_dti", "matched_baseline_dti", 0.4),
    ("holdout_dti", "paired_delta_ci95", [-0.01, 0.2]),
    ("canary", "all_features_tested", False), ("canary", "n_features_tested", 1),
    ("canary", "max_auc", 0.90001), ("canary", "max_auc", float('nan')),
    ("uniqueness", "literal_pass", False), ("uniqueness", "complete_registry", False),
    ("uniqueness", "registry_checked", 1),
    ("validator", "values_in_0_1", 1), ("validator", "sha256", "b" * 64),
    ("validator", "no_nan_inside_footprint", False),
])
def test_each_missing_or_invalid_gate_blocks(section, key, value):
    authority, candidate = good()
    target = authority if section == "authority" else candidate if section == "candidate" else candidate[section]
    target[key] = value
    result = evaluate_release_gate(authority, candidate)
    assert result["okay_to_submit"] is False
    assert result["decision"] == "DO-NOT-SUBMIT"
    assert result["blocking_reasons"]


@pytest.mark.parametrize("phase,key,value", [
    ("surface", "passed", False), ("surface", "max_abs_spearman", 0.901),
    ("surface", "max_dot_overlap", 0.701), ("surface", "max_abs_spearman", float('nan')),
    ("final", "passed", False), ("final", "max_abs_spearman", 0.901),
    ("final", "max_dot_overlap", 0.701), ("final", "max_dot_overlap", None),
])
def test_both_registry_phases_must_pass(phase, key, value):
    authority, candidate = good()
    candidate["uniqueness"][phase][key] = value
    assert not evaluate_release_gate(authority, candidate)["okay_to_submit"]


def test_old_sgce_card_and_current_authority_cannot_self_approve():
    authority = json.loads((ROOT / "evidence/session_9b794637_run_card.json").read_text())
    candidate = json.loads((ROOT / "evidence/session2_run_card.json").read_text())
    result = evaluate_release_gate(authority, candidate)
    assert not result["okay_to_submit"]
    # A content-aware PASS cannot override a literal failure or selector omission.
    assert candidate["correlation_overlap_vs_registry"]["final_dots"]["literal_pass"] is False
    assert authority["selector_approval"] is False


def test_original_owner_claims_are_not_receipts():
    comparison = json.loads((ROOT / "evidence/focus_and_lane_comparison.json").read_text())
    assert "without a verified receipt" in comparison["score_labeling_rule"]
    assert all(r["organizer_confirmed_score"] is None for r in comparison["rows"])
    assert next(r for r in comparison["rows"] if r["site"] == "GEMSDOE32")["owner_reported_unverified"] == 0.2778
