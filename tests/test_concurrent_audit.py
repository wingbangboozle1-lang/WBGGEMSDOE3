"""Contracts on measured parallel work; not a new geological experiment."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_parallel_step_candidate_fails_witness_and_mirrored_footprint():
    audit = json.loads((ROOT / 'evidence/concurrent_audit.json').read_text())
    step = audit['artifacts']['step_zeros']
    assert step['positive_cells'] == 35000
    assert step['outside_mirrored_footprint'] == 747
    assert step['on_mirrored_catalogue_inside_footprint'] == 463
    assert step['inside_footprint_overlap_registered_witness'] == 1.0
    assert step['forward_overlap_registered_witness'] == 34492 / 35000
    assert not step['shared_format_report']['ok']
    assert not step['eligible_to_submit']


def test_nan_twin_is_not_a_distinct_positive_mask_and_standins_fail_grid():
    audit = json.loads((ROOT / 'evidence/concurrent_audit.json').read_text())
    twin = audit['artifacts']['step_nan_tag']
    assert twin['same_decoded_positive_mask_as_zeros']
    assert twin['nodata'] == 'NaN' and twin['nan_cells'] == 0
    for key in ('standin', 'h80_archive'):
        assert not audit['artifacts'][key]['matches_mirrored_sample_grid']
        assert not audit['artifacts'][key]['eligible_to_submit']


def test_unsafe_parallel_entrypoints_fail_closed_without_overwriting_card():
    import subprocess
    import sys
    before = (ROOT / 'evidence/run_card.json').read_bytes()
    for script in ('generate_submission.py', 'finalize_submission.py'):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode != 0
        assert 'DISABLED / DO NOT SUBMIT' in result.stderr
    assert (ROOT / 'evidence/run_card.json').read_bytes() == before


def test_incomplete_parallel_uniqueness_checker_is_disabled():
    import pytest
    from uniqueness_audit import audit_uniqueness
    with pytest.raises(RuntimeError, match='incomplete historical registry'):
        audit_uniqueness(ROOT / 'not-a-candidate.tif', [])


def test_all_legacy_publication_and_generation_entrypoints_are_disabled():
    import subprocess
    import sys
    before = (ROOT / 'evidence/run_card.json').read_bytes()
    for script in ('assess_sites.py', 'build_design.py', 'build_readme.py',
                   'build_submission.py', 'finalize.py', 'run_holdout.py', 'verify_submission.py'):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode != 0, script
        assert 'BLOCKED' in result.stderr, script
    assert (ROOT / 'evidence/run_card.json').read_bytes() == before


def test_legacy_exempted_uniqueness_audit_is_disabled(tmp_path):
    import numpy as np
    import pytest
    from gemsw.uniq import audit
    a=np.zeros((4,4),bool)
    with pytest.raises(RuntimeError, match='unauthorized registry exemptions'):
        audit(a, None, tmp_path, a)
