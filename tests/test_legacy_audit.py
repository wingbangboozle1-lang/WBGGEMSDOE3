import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit import inspect, overlap_bound


def write(path, a, transform=None):
    with rasterio.open(path, 'w', driver='GTiff', height=a.shape[0], width=a.shape[1], count=1,
                       dtype='float32', crs='EPSG:32611', transform=transform or from_origin(100, 100, 10, 10), nodata=np.nan) as r:
        r.write(a.astype('float32'), 1)


def test_strict_threshold_boundary():
    assert not overlap_bound(100, 97, 10)['guaranteed_duplicate']  # exactly 70%
    assert overlap_bound(100, 97, 11)['guaranteed_duplicate']
    assert overlap_bound(5167373, 5160724, 22164)['guaranteed_duplicate']
    assert not overlap_bound(5167373, 5160724, 22163)['guaranteed_duplicate']


@pytest.mark.parametrize('args', [(1,2,1), (1,0,0), (1,0,2), (1,-1,1)])
def test_invalid_bound(args):
    with pytest.raises(ValueError):
        overlap_bound(*args)


@pytest.mark.parametrize('bad', [-1, 1.01, np.nan, np.inf, -np.inf])
def test_inside_invalid(tmp_path, bad):
    t = tmp_path/'template.tif'; p = tmp_path/'p.tif'
    write(t, np.array([[0., np.nan],[0.,0.]]))
    write(p, np.array([[bad, np.nan],[0.,1.]]))
    _, _, report = inspect(p,t)
    assert not report['inside_values_in_0_1']


def test_outside_sentinel_rejected(tmp_path):
    t = tmp_path/'template.tif'; p = tmp_path/'p.tif'
    write(t, np.array([[0., np.nan],[0.,0.]]))
    write(p, np.array([[0., -9999.],[0.,1.]]))
    _, _, report = inspect(p,t)
    assert report['inside_values_in_0_1']
    assert not report['all_finite_values_in_0_1']


def test_grid_mismatch(tmp_path):
    t = tmp_path/'template.tif'; p = tmp_path/'p.tif'
    write(t, np.zeros((2,2)));write(p,np.zeros((2,2)),from_origin(101,100,10,10))
    with pytest.raises(ValueError, match='Grid mismatch'):
        inspect(p,t)


def test_pinned_shared_instruments_unchanged():
    for row in json.loads((ROOT/'vendor/pins.json').read_text()):
        path = ROOT/'vendor/template24'/row['local']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']


def test_sources_unchanged():
    for row in json.loads((ROOT/'research/source_hashes.json').read_text()):
        assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest() == row['sha256']


def test_decision_is_negative():
    card=json.loads((ROOT/'docs/run-card.json').read_text())
    assert card['verdict']=='negative' and card['ok_to_submit'] is False
    assert card['raster_sha256'] is None and card['holdout']['dti'] is None
    assert len(card['note']) <= 140
    audit=json.loads((ROOT/'docs/audit.json').read_text())
    assert len(audit['rows']) == 9
    assert all(not x['unique_among_focus9'] for x in audit['rows'].values())
    assert audit['champion_forensics']['equals_d28_euclidean_fault_distance_gt_2px']


def test_local_html_links_resolve():
    from html.parser import HTMLParser
    from urllib.parse import urlsplit
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            if tag=='a':
                for key, val in attrs:
                    if key=='href':
                        p=urlsplit(val)
                        if not p.scheme and p.path:
                            assert (ROOT/'docs'/p.path).is_file(), val
    for page in (ROOT/'docs').glob('*.html'):
        Links().feed(page.read_text())


def test_dossier_is_reproducible():
    """The published dossier must be a pure function of evidence/*.json.

    The earlier generator (scripts/build_site.py) is retained for the LST1 lane but no longer
    owns these pages; scripts/build_dossier.py does, and regenerating must be a no-op.
    """
    from build_dossier import pages
    published = pages()
    for name, text in published.items():
        assert (ROOT / 'docs' / name).read_text() == text, name
