import json
from pathlib import Path
from unittest.mock import patch
import pytest

from refresh_feed import parse_first_place, parse_public_scores, refresh


def test_parse_public_ranks_and_reject_ambiguous_rows():
    html = ('<table><tr><th>Rank</th><th>Team</th><th>Score</th></tr>'
            '<tr><td>#1</td><td>team</td><td>0.4437</td></tr>'
            '<tr><td>#25</td><td>other</td><td>0.3217</td></tr>'
            '<tr><td>#26</td><td>third</td><td>0.3195</td></tr></table>')
    assert parse_first_place(html) == "0.4437"
    assert parse_public_scores(html) == {1: "0.4437", 25: "0.3217", 26: "0.3195"}
    with pytest.raises(ValueError, match="ambiguous"):
        parse_first_place('<tr><td>#1</td><td>0.1234</td><td>0.4567</td></tr>')
    with pytest.raises(ValueError, match="missing"):
        parse_first_place('<h1>Please log in</h1>')
    with pytest.raises(ValueError, match="duplicate public rank"):
        parse_public_scores('<tr><td>#1</td><td>0.1234</td></tr><tr><td>#1</td><td>0.4567</td></tr>')


def test_failed_refresh_preserves_snapshot_and_marks_stale(tmp_path):
    path = tmp_path / 'leaderboard.json'
    path.write_text(json.dumps({'best_public_dti': '0.4437', 'last_success_utc': '2026-01-01T00:00:00+00:00'}))
    with patch('urllib.request.urlopen', side_effect=OSError('network unavailable')):
        result = refresh(path)
    assert result['best_public_dti'] == '0.4437'
    assert result['last_success_utc'] == '2026-01-01T00:00:00+00:00'
    assert result['last_attempt_error'].startswith('OSError')


def test_refresh_reads_public_htmx_fragment_and_rejects_redirect(tmp_path):
    from io import BytesIO
    from refresh_feed import PARTIAL_URL, URL
    markup = b'<table><tr><th>Rank</th><th>Score</th><th>Team</th></tr><tr><td>#1</td><td>0.4567</td><td>public team</td></tr><tr><td>#25</td><td>0.3125</td><td>rank 25</td></tr></table>'

    class Response(BytesIO):
        def __init__(self, target):
            super().__init__(markup)
            self.target = target
        def geturl(self):
            return self.target

    path = tmp_path / 'leaderboard.json'
    with patch('urllib.request.urlopen', return_value=Response(PARTIAL_URL)) as request:
        result = refresh(path)
    assert request.call_args.args[0].full_url == PARTIAL_URL
    assert result['source'] == URL and result['best_public_dti'] == '0.4567'
    assert result['rank_25_public_dti'] == '0.3125'
    assert result['captured_ranks'] == {'1': '0.4567', '25': '0.3125'}
    assert result['last_attempt_error'] is None and result['last_success_utc']
    assert "request start" in result["observation_time_precision"]
    with patch('urllib.request.urlopen', return_value=Response('https://www.drivendata.org/accounts/login/')):
        rejected = refresh(path)
    assert rejected['best_public_dti'] == '0.4567'
    assert rejected['rank_25_public_dti'] == '0.3125'
    assert rejected['last_attempt_error'].startswith('ValueError: leaderboard fragment redirected')
