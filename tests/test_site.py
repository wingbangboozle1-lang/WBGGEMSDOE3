from pathlib import Path

from build_site import human_age

ROOT = Path(__file__).resolve().parents[1]


def test_feed_render_is_deterministic_and_does_not_claim_a_stale_snapshot_is_fresh():
    feed = {'last_success_utc': '2020-01-01T00:00:00+00:00', 'last_attempt_error': None}
    assert human_age(feed) == 'Last checked · 2020-01-01T00:00:00 UTC'
    assert 'Observed' not in human_age(feed)
    feed['last_attempt_error'] = 'Timeout'
    assert human_age(feed).startswith('Latest refresh failed')
    assert human_age({'last_success_utc': None}) == 'No successful observation'
    assert human_age({'last_success_utc': 'invalid'}) == 'Invalid observation timestamp'


def test_every_published_page_contains_negative_decision_and_checked_json_exists():
    docs = ROOT / 'docs'
    for page in ('index.html', 'executive-summary.html', 'research.html', 'evidence.html'):
        body = (docs / page).read_text()
        assert 'No competition file is cleared.' in body
        assert 'assets/status.js' in body
    assert (docs / 'data/run_card.json').exists()
    assert (docs / 'data/focus_audit.json').exists()
