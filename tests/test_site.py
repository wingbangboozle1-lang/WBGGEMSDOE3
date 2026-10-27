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


def test_pages_publishers_use_the_same_docs_url_layout():
    workflow = (ROOT / '.github/workflows/pages.yml').read_text()
    root_redirect = (ROOT / 'index.html').read_text()
    assert 'url=docs/index.html' in root_redirect
    assert 'cp -a docs .cache/pages-release/docs' in workflow
    assert 'path: .cache/pages-release' in workflow


def test_source_head_statuses_are_rendered_per_repository():
    import json
    from build_site import overview
    a = json.loads((ROOT/'evidence/focus_audit.json').read_text())
    feed = json.loads((ROOT/'registry/leaderboard.json').read_text())
    concurrent = json.loads((ROOT/'evidence/concurrent_audit.json').read_text())
    upstream = json.loads((ROOT/'evidence/latest-upstream-check.json').read_text())
    recent = json.loads((ROOT/'evidence/recent_peer_audit.json').read_text())
    upstream['repositories'][0].update(fetch_status='FAILED', comparison_to_baseline='UNKNOWN', last_attempt_error='test')
    body = overview(a, feed, concurrent, upstream, recent)
    assert 'UNKNOWN' in body and 'data-error="yes"' in body
    assert 'Current best files and scores are unverified' in body
    assert 'A changed HEAD is a drift warning' in body
    assert 'S22-CTXHGB' in body and 'KPL-36' in body


def test_future_upload_guide_uses_official_geotiff_without_assuming_zip():
    from build_site import guide
    body = guide()
    assert 'exact approved GeoTIFF' in body
    assert 'ZIP acceptance has not been independently verified' in body
    assert 'TIFF or single-TIFF ZIP' not in body
