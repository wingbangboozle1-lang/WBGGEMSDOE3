"""Revoked historical paths cannot rebuild a release or republish approval."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['finalize.py', 'build_submission.py'])
def test_legacy_commands_stop_before_loading_inputs(name):
    card = ROOT / 'evidence/lst1_run_card.json'
    before = card.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'BLOCKED' in result.stderr
    assert card.read_bytes() == before


def test_historical_approval_revoked_in_both_copies():
    card = json.loads((ROOT / 'evidence/lst1_run_card.json').read_text())
    assert card['ready_to_submit'] is False
    assert card['file_integrity_and_uniqueness_pass'] is False
    assert card['historical_original_readiness_claims']['ready_to_submit'] is True
    # The older approval-bearing public JSON was removed, not silently republished.
    assert not (ROOT / 'docs/lst1/lst1_run_card.json').exists()


def test_legacy_deep_links_do_not_recommend_upload():
    for page in (ROOT / 'docs/lst1').glob('*.html'):
        text = page.read_text()
        assert 'research only' in text.lower()
        assert 'DO NOT SUBMIT' in text
        assert 'Upload only if' not in text
