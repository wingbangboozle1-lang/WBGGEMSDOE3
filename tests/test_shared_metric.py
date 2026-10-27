"""Cross-check the unchanged shared evaluator on synthetic arrays only."""
from pathlib import Path
import importlib
import os
import sys
import numpy as np
import pytest

from gems_project.template import COMMIT, verify_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(os.environ.get('GEMS_TEMPLATE_DIR', ROOT / '.cache' / f'57GEMSDOE-{COMMIT}'))
pytestmark = pytest.mark.skipif(not TEMPLATE.exists(), reason='shared pinned template not restored in this environment')


def modules():
    verify_template(TEMPLATE)
    sys.path.insert(0, str(TEMPLATE / 'src'))
    return importlib.import_module('gems57.metric'), importlib.import_module('gems57.evaluate_holdout')


def test_shared_metric_matches_bruteforce_for_soft_predictions():
    metric, _ = modules()
    rng = np.random.default_rng(29)
    for _ in range(10):
        g = rng.random((11, 13)) < .06
        g[2, 3] = True
        p = np.where(rng.random((11, 13)) < .08, rng.random((11, 13)), 0.)
        a = metric.dti_exact(p, g)
        b = metric.dti_bruteforce(p, g)
        assert a['dti'] == pytest.approx(b['dti'], abs=1e-12)
        assert a['tp'] == pytest.approx(b['tp'], abs=1e-12)
        assert a['fp'] == pytest.approx(b['fp'], abs=1e-12)


def test_shared_evaluator_masks_visible_pixels_exactly():
    metric, evaluator = modules()
    truth = np.zeros((7, 8), bool)
    truth[2, 3] = truth[5, 6] = True
    visible = np.zeros_like(truth)
    visible[2, 3] = True
    prediction = np.zeros(truth.shape, np.float32)
    prediction[2, 3] = 1.
    prediction[5, 6] = .75
    fold = {'truth': truth, 'visible': visible, 'region': np.ones_like(truth)}
    actual, terms = evaluator.evaluate(prediction, fold, np.ones_like(truth), block_side=3)
    expected = metric.dti_exact(prediction, truth, known=visible)
    assert actual['n_truth'] == 1
    assert actual['dti'] == pytest.approx(expected['dti'])
    assert np.allclose(terms.sum(axis=0), [actual['tpw'], actual['fpw'], actual['fnw'], 1.])


def test_shared_prose_counterexample_multiple_truth_pixels():
    metric, _ = modules()
    truth = np.zeros((7, 7), bool)
    truth[3, 3] = truth[3, 4] = True
    p = np.zeros((7, 7)); p[3, 3] = 1.
    assert metric.dti_exact(p, truth)['tp'] == pytest.approx(5 / 3)
    assert metric.kernel(0) == 1


def test_shared_uniqueness_is_signed_but_project_convention_is_conservative():
    """Record the stricter local convention, not a claimed violation of user wording."""
    from gems_project.audit import violates_literal_protocol
    modules()  # puts the verified template on sys.path
    uniqueness = importlib.import_module('gems57.uniqueness')
    rows = [{
        'submission': 'synthetic-opposite-ranks', 'repo': 'synthetic',
        'their_dots': 10, 'spearman_full_footprint': -1.0,
        'my_dots_within_3px_of_theirs': 0.0,
        'their_dots_within_3px_of_mine': 0.0, 'jaccard_dot_sets': 0.0,
    }]
    reported = uniqueness.two_phase_summary(rows, footprint_cells=100, expected_rasters=1)
    assert not reported['literal_reading']['duplicate']  # upstream tests signed rho > +0.90
    assert violates_literal_protocol(0.0, -1.0)  # stricter project convention; not explicit user wording
