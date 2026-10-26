"""Smoke contracts only, not certification of organizer metric equivalence."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor/template24/src'))
from gems.holdout import SegmentHoldout
from gems.submission import sanitize
from gems.metric import dti_score_fast


def test_shared_sanitizer_bounds():
    result = sanitize(np.array([-9999, np.nan, np.inf, -np.inf, .5, 2.0]))
    assert np.isfinite(result).all()
    assert np.all((result >= 0) & (result <= 1))
    assert result[4] == .5


def test_shared_whole_components_hidden_and_training_purged():
    fp = np.ones((80,80),bool)
    labels = np.zeros_like(fp)
    labels[10:15,10] = True
    labels[10:15,65] = True
    labels[65:70,10] = True
    labels[65:70,65] = True
    labels[38:43,20] = True  # crosses a block boundary
    context = SegmentHoldout(fp,labels,buffer_px=3)
    for fold in context.folds:
        assert not (fold['train'] & fold['valid']).any()
        assert not np.isin(context.components[fold['visible']], fold['hidden_component_ids']).any()
        assert not (fold['truth'] & fold['visible']).any()
        assert fold['truth'].any()


def test_shared_perfect_prediction():
    a = np.zeros((10,10));a[5,5]=1
    assert abs(dti_score_fast(a,a)['dti']-1) < 1e-6
