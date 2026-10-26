import json
from urllib.error import URLError
from urllib.request import Request

import pytest
from refresh_feed import SafeRedirect, parse_top_score, refresh


def test_leaderboard_parser_uses_rank_one_and_tversky_column():
    html = """<table><tr><th>Other</th></tr><tr><td>0.9999</td></tr></table>
    <table><thead><tr><th>Rank</th><th>Team members</th><th>Participant</th>
    <th>Best<br>public<br>DW-Tversky<br>(in descending order)</th><th>Shared work</th></tr></thead>
    <tbody><tr><td>#1</td><td></td><td>someone</td><td>0.4437</td><td></td></tr>
    <tr><td>#2</td><td></td><td>other</td><td>0.3916</td><td></td></tr></tbody></table>"""
    assert parse_top_score(html) == "0.4437"


@pytest.mark.parametrize("html", ["<p>Login</p>",
    "<table><tr><th>Rank</th><th>DW-Tversky</th></tr><tr><td>#1</td><td>evil</td></tr></table>",
    "<table><tr><th>Rank</th><th>DW-Tversky</th></tr><tr><td>#2</td><td>0.999</td></tr></table>"])
def test_parser_never_guesses(html):
    with pytest.raises(ValueError):
        parse_top_score(html)


def test_failure_preserves_last_observation_as_stale(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("network unavailable")
    monkeypatch.setattr("refresh_feed.retrieve", fail)
    result = refresh({"leaderboard": {"top_value": "0.4437", "observed_utc": "2026-10-26 UTC"}})
    assert result["leaderboard"]["status"] == "stale"
    assert result["leaderboard"]["observed_utc"] == "2026-10-26 UTC"
    assert result["leaderboard"]["top_value"] == "0.4437"
    assert all(r["status"] == "unavailable" for r in result["repositories"])
    assert "network unavailable" not in json.dumps(result)  # no server response text/credentials


def test_cross_host_redirect_is_rejected():
    handler = SafeRedirect()
    req = Request("https://api.github.com/repos/x/y", headers={"Authorization": "Bearer secret"})
    with pytest.raises(ValueError):
        handler.redirect_request(req, None, 302, "", {}, "https://www.drivendata.org/")
    with pytest.raises(ValueError):
        handler.redirect_request(req, None, 302, "", {}, "http://api.github.com/")
