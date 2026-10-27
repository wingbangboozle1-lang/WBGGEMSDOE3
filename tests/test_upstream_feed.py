"""The HEAD monitor is independent, fail-closed, and never implies score freshness."""
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import refresh_upstream as monitor


def fixtures(tmp_path):
    sites = ['GEMSDOE24', 'GEMSDOE25', 'GEMSDOE27']
    repo = lambda s: f'buffedlizard55-lab/{s}'
    baseline = {'checked_at': '2026-10-26T00:00:00+00:00', 'repositories': [
        {'repo': repo(s), 'commit': str(i) * 40, 'status': 'FETCHED'}
        for i, s in enumerate(sites, 1)]}
    manifest = {'sites': [{'site': s, 'ref': 'a' * 40} for s in sites]}
    b, m, out = tmp_path/'base.json', tmp_path/'focus.json', tmp_path/'out.json'
    b.write_text(json.dumps(baseline));m.write_text(json.dumps(manifest))
    return b, m, out


def test_head_changes_and_per_repo_failures_preserve_last_known_snapshot(tmp_path):
    base, manifest, out = fixtures(tmp_path)
    def first(repo):
        return ('1'*40, 'a'*40) if repo.endswith('24') else ('f'*40, 'b'*40)
    with patch.object(monitor, '_fetch_head', side_effect=first):
        assert monitor.refresh(out, base, manifest) == 0
    result = json.loads(out.read_text()); rows = {r['site']:r for r in result['repositories']}
    assert rows['GEMSDOE24']['comparison_to_baseline'] == 'UNCHANGED'
    assert rows['GEMSDOE25']['comparison_to_baseline'] == 'CHANGED'
    last_success = rows['GEMSDOE25']['last_success_utc']
    def next_check(repo):
        if repo.endswith('25'): raise OSError('test failure')
        return first(repo)
    with patch.object(monitor, '_fetch_head', side_effect=next_check):
        assert monitor.refresh(out, base, manifest) == 1
    result = json.loads(out.read_text()); rows = {r['site']:r for r in result['repositories']}
    failed = rows['GEMSDOE25']
    assert failed['fetch_status'] == 'FAILED' and failed['comparison_to_baseline'] == 'UNKNOWN'
    assert failed['observed_head'] == 'f'*40 and failed['last_success_utc'] == last_success
    assert 'OSError' in failed['last_attempt_error']
    assert not result['approved_for_submission']
    assert 'not proof' in result['scope']


def test_initial_failure_has_no_fabricated_observation(tmp_path):
    base, manifest, out = fixtures(tmp_path)
    with patch.object(monitor, '_fetch_head', side_effect=OSError('offline')):
        assert monitor.refresh(out, base, manifest) == 1
    rows = json.loads(out.read_text())['repositories']
    assert all(r['observed_head'] is None and r['last_success_utc'] is None for r in rows)


def test_head_parser_rejects_redirects_and_malformed_identifiers():
    class Response(BytesIO):
        def __init__(self, url, data): super().__init__(json.dumps(data).encode());self.url=url
        def geturl(self): return self.url
    repo='buffedlizard55-lab/GEMSDOE24'
    good_url=f'https://api.github.com/repos/{repo}/commits/main'
    with patch('urllib.request.urlopen', return_value=Response('https://github.com/login', {})):
        with pytest.raises(ValueError, match='redirected'): monitor._fetch_head(repo)
    with patch('urllib.request.urlopen', return_value=Response(good_url, {'sha':'oops','commit':{'tree':{'sha':'b'*40}}})):
        with pytest.raises(ValueError, match='malformed'): monitor._fetch_head(repo)


def test_unexpected_monitor_setup_failure_marks_prior_rows_unknown(tmp_path):
    base, manifest, out = fixtures(tmp_path)
    with patch.object(monitor, '_fetch_head', return_value=('f'*40, 'b'*40)):
        assert monitor.refresh(out, base, manifest) == 0
    before = json.loads(out.read_text())['repositories'][0]
    assert monitor.mark_monitor_failure(out, ValueError('bad setup'))
    rows = json.loads(out.read_text())['repositories']
    assert all(r['fetch_status']=='FAILED' and r['comparison_to_baseline']=='UNKNOWN' for r in rows)
    assert rows[0]['observed_head'] == before['observed_head']
    assert rows[0]['last_success_utc'] == before['last_success_utc']
    assert not monitor.mark_monitor_failure(tmp_path/'missing.json', ValueError('bad setup'))
