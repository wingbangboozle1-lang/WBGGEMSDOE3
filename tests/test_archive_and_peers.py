"""Contracts on existing research artifacts; no competition experiment is run."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def test_lst1_archive_hashes_zip_and_literal_stop():
    report = json.loads((ROOT/'evidence/archive_audit.json').read_text())
    assert report['approved_for_submission'] is False
    assert len(report['tiffs']) == 2
    for row in report['tiffs']:
        data = (ROOT/'submission'/row['filename']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert row['band_count'] == 1 and row['dtype'] == 'float32'
        assert row['positive_inside'] == 32810 and row['positive_outside'] == 0
        assert row['inside_nan'] == 0 and row['inside_finite_range_0_1']
        assert row['forward_overlap_witness_within_3px_all_positive'] == 1
    archive = ROOT/'submission'/report['zip']['filename']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report['zip']['sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and z.namelist() == [report['tiffs'][0]['filename']]
        assert hashlib.sha256(z.read(z.namelist()[0])).hexdigest() == report['tiffs'][0]['sha256']


def test_recent_peer_files_are_not_eligible_and_are_pinned():
    report = json.loads((ROOT/'evidence/recent_peer_audit.json').read_text())
    pins = json.loads((ROOT/'registry/recent_featured.json').read_text())
    assert report['approved_for_submission'] is False
    assert {r['site']:r['sha256'] for r in report['artifacts']} == {r['site']:r['sha256'] for r in pins['artifacts']}
    for row in report['artifacts']:
        assert row['positive_inside'] > 0 and row['positive_outside'] == 0
        assert row['forward_overlap_witness_within_3px_all_positive'] == 1
        assert row['literal_duplicate'] and not row['approved_for_submission']
        assert 'unknown' in row['score']


def test_old_lst1_pages_are_unambiguously_research_only():
    pages = ROOT/'docs/lst1'
    for name in ('index.html','summary.html','how-to-submit.html','why.html',
                 'hypotheses.html','evidence.html','limitations.html'):
        body = (pages/name).read_text()
        assert 'No competition file is cleared.' in body
        assert 'Do not submit' in body and '100% witness overlap' in body
        assert 'portal acceptance' in body
    assert not (pages/'downloads').exists()
    assert not (pages/'lst1_run_card.json').exists()
    assert (ROOT/'submission').exists()  # archival bytes have not been deleted
    historical = json.loads((ROOT/'evidence/lst1_run_card.json').read_text())
    assert not historical['ready_to_submit'] and historical['verdict'] == 'negative'
    assert historical['historical_original_readiness_claims']['ready_to_submit']
    assert 'SUPERSEDED' in historical['_archive_notice']
