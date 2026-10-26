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
