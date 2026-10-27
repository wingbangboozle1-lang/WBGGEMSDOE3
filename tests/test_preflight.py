import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit', ROOT/'scripts/audit_preflight.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)

def test_template_byte_identity():
    assert all(audit.template_integrity().values())

def test_preflight_never_approves():
    assert audit.preflight()['approved_for_submission'] is False

def write(p, a, **changes):
    profile = dict(driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,dtype='float32',crs='EPSG:32611',transform=from_origin(243350,4508550,100,100))
    profile.update(changes)
    with rasterio.open(p,'w',**profile) as dst: dst.write(a.astype('float32'),1)

@pytest.mark.parametrize('bad',[-1,1.001,np.nan,np.inf,-3.4028235e38])
def test_bad_values_rejected(tmp_path,bad):
    sample=tmp_path/'s.tif';candidate=tmp_path/'p.tif'
    a=np.zeros((8,8));write(sample,a);a[0,0]=bad;write(candidate,a)
    assert not audit.raster_report(candidate,sample)['format_ok']

@pytest.mark.parametrize('change',[{'crs':'EPSG:4326'},{'transform':from_origin(0,0,100,100)},{'nodata':-9999}])
def test_grid_and_nodata_rejected(tmp_path,change):
    a=np.zeros((8,8));s=tmp_path/'s.tif';p=tmp_path/'p.tif';write(s,a);write(p,a,**change)
    assert not audit.raster_report(p,s)['format_ok']

def test_shape_rejected(tmp_path):
    s=tmp_path/'s.tif';p=tmp_path/'p.tif';write(s,np.zeros((8,8)));write(p,np.zeros((7,8)))
    assert not audit.raster_report(p,s)['format_ok']

def test_format_pass_is_not_approval(tmp_path):
    s=tmp_path/'s.tif';p=tmp_path/'p.tif';write(s,np.zeros((8,8)));write(p,np.zeros((8,8)))
    report=audit.raster_report(p,s)
    assert report['format_ok'] and not report['approved_for_submission']

def test_duplicate_stops():
    a=np.arange(400).reshape(20,20)/399;d=np.zeros_like(a);d[10,10]=1
    result=audit.novelty(a,d,d,np.ones_like(a,bool))
    assert result['status']=='DUPLICATE_STOP' and result['directed_overlap_within_3px']==1

def test_constant_field_indeterminate():
    a=np.zeros((5,5));assert not audit.novelty(a,a,a,np.ones_like(a,bool))['passed']

def test_missing_common_footprint_rejected():
    a=np.zeros((5,5))
    with pytest.raises(ValueError):audit.novelty(a,a,a,a)

def test_negative_card_and_no_fake_download():
    card=json.loads((ROOT/'evidence/run-card.json').read_text())
    assert len(card['note'])<=140 and card['verdict']=='negative'
    assert card['raster_sha256'] is None and not card['approved_for_submission']
    rows=json.loads((ROOT/'knowledge/focus-sites.json').read_text())
    assert len(rows)==9 and all(r['estimate'] is None and not r['approved_for_submission'] for r in rows)
    # Parallel research artifacts are preserved, but no TIF is approved.
    concurrent=json.loads((ROOT/'evidence/concurrent_audit.json').read_text())
    assert not concurrent['artifacts']['step_zeros']['eligible_to_submit']
    authoritative=json.loads((ROOT/'evidence/run_card.json').read_text())
    assert authoritative['verdict']=='negative' and not authoritative['selector_approval']

def test_snapshot_blob_identity():
    import hashlib
    for entry in json.loads((ROOT/'evidence/source-index.json').read_text()):
        data=(ROOT/entry['local']).read_bytes()
        assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==entry['blob']

def test_shared_evaluator_pools_and_labels():
    from gems57.evaluate_holdout import pooled_summary
    terms=np.array([[1.,2.,3.,4.],[2.,1.,2.,4.]])
    r=pooled_summary({'candidate':terms,'incumbent':terms},candidate='candidate',draws=100)
    assert r['evidence_class']=='HOLDOUT-DTI' and r['pooled']
    assert r['scores']['candidate']['withheld_positive_pixels']==8
    assert r['paired_differences']['incumbent']['ci95']==[0.,0.]

@pytest.mark.parametrize('change', [
    {'dtype': 'float64'}, {'dtype': 'uint8'}, {'count': 2}, {'crs': None},
])
def test_wrong_dtype_bands_and_missing_crs_rejected(tmp_path, change):
    s=tmp_path/'s.tif';p=tmp_path/'p.tif';a=np.zeros((8,8))
    write(s,a);write(p,a,**change)
    assert not audit.raster_report(p,s)['format_ok']


def test_outside_footprint_positive_and_nan_are_not_silently_fixed(tmp_path):
    sample=tmp_path/'sample.tif'; candidate=tmp_path/'p.tif'
    a=np.zeros((8,8)); a[:,0]=np.nan
    write(sample,a,nodata=np.nan)
    p=np.zeros((8,8));p[1,0]=1;write(candidate,p)
    report=audit.raster_report(candidate,sample)
    assert not report['format_ok'] and report['positive_outside']==1
    p[1,0]=np.nan;write(candidate,p)
    report=audit.raster_report(candidate,sample)
    assert not report['format_ok'] and not report['checks']['whole_array_all_finite']
    assert not report['approved_for_submission']  # NaN outside is an unresolved policy, not known portal rejection


def test_inside_gdal_mask_and_empty_reference_fail_closed(tmp_path):
    s=tmp_path/'s.tif';p=tmp_path/'p.tif';a=np.zeros((8,8))
    write(s,a);write(p,a,nodata=0)
    assert not audit.raster_report(p,s)['checks']['inside_gdal_mask_valid']
    write(s,np.full((8,8),np.nan),nodata=np.nan)
    with pytest.raises(ValueError, match='empty'):
        audit.raster_report(p,s)


def test_negative_rank_correlation_alone_stops():
    peer=np.zeros((40,40));peer[0:4,0:4]=np.arange(1,17).reshape(4,4)
    surface=-peer;dots=np.zeros_like(peer);dots[35,35]=1
    result=audit.novelty(surface,dots,peer,np.ones_like(peer,bool))
    assert result['status']=='DUPLICATE_STOP'
    assert result['spearman'] == pytest.approx(-1)
    assert result['directed_overlap_within_3px'] == 0


def test_constant_positive_witness_still_stops_on_overlap():
    peer=np.ones((8,8));dots=np.zeros((8,8));dots[4,4]=1
    result=audit.novelty(peer,dots,peer,np.ones_like(peer,bool))
    assert result['status']=='DUPLICATE_STOP' and result['directed_overlap_within_3px']==1


def test_check_candidate_cli_requires_real_template_and_rejects_float64(tmp_path):
    import subprocess, sys
    sample=tmp_path/'sample.tif';candidate=tmp_path/'candidate.tif';a=np.zeros((8,8))
    write(sample,a);write(candidate,a,dtype='float64')
    run=subprocess.run([sys.executable,str(ROOT/'scripts/check_candidate.py'),str(candidate),'--template',str(sample)],
                       capture_output=True,text=True)
    assert run.returncode == 2
    result=json.loads(run.stdout)
    assert not result['format_ok'] and not result['checks']['dtype_float32']
    assert not result['approved_for_submission']
    run=subprocess.run([sys.executable,str(ROOT/'scripts/check_candidate.py'),str(candidate)],
                       capture_output=True,text=True)
    assert run.returncode == 2


def test_all_retired_local_writers_refuse_to_generate(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT))
    import src.submission_writer as legacy
    import scripts.submission_writer as older
    a=np.zeros((8,8))
    with pytest.raises(RuntimeError,match='BLOCKED'):
        legacy.conform_to_reference(a,tmp_path/'sample.tif',tmp_path/'bad.tif')
    with pytest.raises(RuntimeError,match='BLOCKED'):
        legacy.write_submission(a,tmp_path/'bad.tif')
    with pytest.raises(RuntimeError,match='BLOCKED'):
        older.validate_geotiff(tmp_path/'bad.tif',tmp_path/'sample.tif')
    assert not (tmp_path/'bad.tif').exists()
