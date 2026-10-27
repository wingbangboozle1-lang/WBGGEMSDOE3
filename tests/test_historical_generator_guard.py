import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_historical_lst1_run_card_is_reclassified_as_not_submittable():
    card = json.loads((ROOT / "evidence/lst1_run_card.json").read_text())
    assert card["ready_to_submit"] is False
    assert card["selector_approval"] is False
    assert card["registry_audit"]["literal_rule_pass"] is False
    assert card["registry_audit"]["literal_scope_complete"] is False
    assert all(value is False for value in card["gates"].values())
    assert card["gate_status"]["G1_literal_overlap_le_0.70_for_every_registry_raster"] == "FAIL"
    assert card["gate_status"]["G3_current_shared_evaluator_result_available"] == "NOT RUN"
    assert "D1_historical_local_format_validator_pass" in card["legacy_diagnostics"]
    assert card["verdict"].startswith("NEGATIVE:")
    assert card["holdout"]["label"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator"] == "GEMSDOE32-HIDE-RECOVER-v3.0"
    assert card["holdout"]["withheld_positive_pixels"] == 22232
    assert card["label_of_numbers"]["LEADERBOARD_ESTIMATE"] == "NOT_ESTIMABLE"
    assert "lst_projection_band" not in card and "lst_calibrators" not in card
    assert card["archived_diagnostics"]["projection_status"] == "QUARANTINED_NOT_A_SCORE"
    raw = json.loads((ROOT / "evidence/build_result.json").read_text())
    assert raw["record_kind"] == "HISTORICAL_LST1_BUILD_DIAGNOSTIC"
    assert raw["approved_for_submission"] is False
    assert raw["leaderboard_estimate"] == "NOT_ESTIMABLE"
    assert raw["projection_status"] == "QUARANTINED_NOT_A_SCORE"


def test_retired_writers_and_verifier_exit_without_writing_files():
    protected = [ROOT / "submission", ROOT / "evidence"]
    before = {
        path.relative_to(ROOT): (path.stat().st_size, path.stat().st_mtime_ns)
        for directory in protected
        for path in directory.rglob("*") if path.is_file()
    }
    for script, phrase in (
        ("scripts/build_submission.py", "DISABLED / DO NOT SUBMIT"),
        ("scripts/verify_submission.py", "DISABLED / NOT AUTHORITATIVE"),
    ):
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 2
        assert phrase in result.stderr
    after = {
        path.relative_to(ROOT): (path.stat().st_size, path.stat().st_mtime_ns)
        for directory in protected
        for path in directory.rglob("*") if path.is_file()
    }
    assert before == after
