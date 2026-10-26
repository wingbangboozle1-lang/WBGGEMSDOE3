from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data/cache/shared-template"
pytestmark = pytest.mark.skipif(not (TEMPLATE / "gems57/metric.py").exists(), reason="unchanged upstream cache not restored")
sys.path.insert(0, str(TEMPLATE))


def test_shared_metric_counterexample_and_exact_agreement():
    from gems57 import metric
    truth = np.zeros((5, 5), bool)
    truth[2, 2:4] = True
    p = np.zeros((5, 5), np.float32)
    p[2, 2] = 1
    credit, self_credit, _ = metric.max_cover(p, truth)
    assert credit.sum() == pytest.approx(5 / 3)
    assert credit.sum() > self_credit[2, 2]
    assert metric.dti_exact(p, truth)["dti"] == pytest.approx(metric.dti_bruteforce(p, truth)["dti"])


def test_shared_evaluator_rejects_out_of_range_predictions():
    from gems57 import evaluate_holdout
    p = np.zeros((4, 4), np.float32)
    p[1, 1] = 1.1
    truth = np.zeros((4, 4), bool)
    truth[2, 2] = True
    region = np.ones((4, 4), bool)
    with pytest.raises(ValueError, match="finite"):
        evaluate_holdout.evaluate(p, {"truth": truth, "visible": np.zeros_like(truth), "region": region}, region)
