"""Revoked historical paths cannot rebuild a release or republish approval."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', ['finalize.py', 'build_submission.py', 'build_site_lst1.py'])
def test_legacy_commands_stop_before_loading_inputs(name):
    card = ROOT / 'evidence/lst1_run_card.json'
    before = card.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'DISABLED / DO NOT SUBMIT' in result.stderr
    assert card.read_bytes() == before


def test_historical_approval_revoked_in_both_copies():
    for path in ['evidence/lst1_run_card.json', 'docs/lst1/lst1_run_card.json']:
        card = json.loads((ROOT / path).read_text())
        assert card['ready_to_submit'] is False
        assert card['file_integrity_and_uniqueness_pass'] is False
        assert card['historical_correction']['previous_ready_to_submit'] is True


def test_legacy_deep_links_do_not_recommend_upload():
    for page in (ROOT / 'docs/lst1').glob('*.html'):
        text = page.read_text()
        assert 'LST1 quarantined' in text
        assert 'DO NOT SUBMIT' in text
        assert 'Upload only if' not in text
