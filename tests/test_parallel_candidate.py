"""Fail-closed integration of the concurrent research artifact."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_parallel_tiffs_are_preserved_but_not_approved():
    report = json.loads((ROOT / "evidence/concurrent-candidate-audit.json").read_text())
    assert not report["ok_to_submit"] and "DUPLICATE STOP" in report["verdict"]
    assert len(report["rasters"]) == 3
    for row in report["rasters"]:
        path = ROOT / row["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        assert row["positive_pixels_inside_mirrored_footprint"] == 34253
        assert row["positive_pixels_outside_mirrored_footprint"] == 747
        assert row["directional_overlap_inside_footprint"] == pytest.approx(34205 / 34253)
        assert row["duplicate_stop"] and not row["local_format_validator"]["format_gate_pass"]
    assert not json.loads((ROOT / "evidence/run_card.json").read_text())["ok_to_submit"]


def test_legacy_subset_checker_cannot_pass_an_empty_registry():
    from uniqueness_audit import audit_uniqueness
    with pytest.raises(RuntimeError, match="DISABLED"):
        audit_uniqueness(Path("nonexistent.tif"), [])


@pytest.mark.parametrize("script", ["generate_submission.py", "finalize_submission.py"])
def test_legacy_entry_points_are_disabled(script):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script)],
                            cwd=ROOT, text=True, capture_output=True, timeout=20)
    assert result.returncode != 0 and "DISABLED" in result.stderr
