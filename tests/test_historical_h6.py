"""Historical H6-1 is cited as a limited proxy, not a live-score explanation."""
import hashlib
import json
from pathlib import Path

from build_site import historical_h6_section

ROOT = Path(__file__).resolve().parents[1]


def test_historical_receipt_is_pinned_and_carries_its_scope_limit():
    path = ROOT / 'evidence/h6_1_proximity_pruning_holdout.json'
    h = json.loads(path.read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'd477facac6ba82fe922e5cc075e17c644d9c946c5d192d16f9489238056c11dc'
    assert h['evaluator_version'] == 'gems57-pooled-hide-v2'
    assert h['scores']['unpruned']['withheld_positive_pixels'] == 11321
    assert h['verdict'] == 'negative'
    assert h['paired_differences']['random_prune']['ci95'][0] < 0 < h['paired_differences']['random_prune']['ci95'][1]
    assert h['holdout_scope_limitation']['nearest_visible_to_any_withheld_truth_px'] > 3


def test_dashboard_does_not_extrapolate_proxy_to_unseen_labels():
    body = historical_h6_section()
    assert 'not run or independently replayed here' in body
    assert '11,321 withheld positive pixels' in body
    assert 'cannot prove or disprove' in body
    assert 'no withheld truth within 3 pixels' in body
