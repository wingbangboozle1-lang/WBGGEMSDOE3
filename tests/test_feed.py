import json
from pathlib import Path
from unittest.mock import patch
import pytest

from refresh_feed import parse_first_place, refresh


def test_parse_first_place_and_reject_ambiguous_rows():
    html = '<table><tr><th>Rank</th><th>Team</th><th>Score</th></tr><tr><td>#1</td><td>team</td><td>0.4437</td></tr><tr><td>#2</td><td>other</td><td>0.3916</td></tr></table>'
    assert parse_first_place(html) == "0.4437"
    with pytest.raises(ValueError, match="ambiguous"):
        parse_first_place('<tr><td>#1</td><td>0.1234</td><td>0.4567</td></tr>')
    with pytest.raises(ValueError, match="missing"):
        parse_first_place('<h1>Please log in</h1>')


def test_failed_refresh_preserves_snapshot_and_marks_stale(tmp_path):
    path = tmp_path / 'leaderboard.json'
    path.write_text(json.dumps({'best_public_dti': '0.4437', 'last_success_utc': '2026-01-01T00:00:00+00:00'}))
    with patch('urllib.request.urlopen', side_effect=OSError('network unavailable')):
        result = refresh(path)
    assert result['best_public_dti'] == '0.4437'
    assert result['last_success_utc'] == '2026-01-01T00:00:00+00:00'
    assert result['last_attempt_error'].startswith('OSError')
