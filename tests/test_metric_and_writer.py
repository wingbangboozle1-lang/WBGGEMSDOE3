"""Synthetic metric checks and tests that the historical local writer is disabled."""
import math, sys
from pathlib import Path
import numpy as np, pytest, rasterio
from rasterio.transform import from_origin
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemsw import metric as M, writer as W, ledger as L


def brute(pred, truth, radius=3.0):
    p = np.asarray(pred, float); g = np.asarray(truth).astype(bool)
    h, w = p.shape; gt = np.argwhere(g); tp = 0.0
    for gy, gx in gt:
        best = 0.0
        for y in range(h):
            for x in range(w):
                d = math.hypot(y - gy, x - gx)
                if d <= radius:
                    best = max(best, p[y, x] * M.kernel(d))
        tp += best
    fp = 0.0
    for y in range(h):
        for x in range(w):
            if p[y, x] > 0:
                near = max((M.kernel(math.hypot(y - gy, x - gx)) for gy, gx in gt), default=0.0)
                fp += p[y, x] * (1.0 - near)
    return tp, fp, len(gt) - tp


def test_official_worked_example():
    # DrivenData page 967 scoring example: TP=3.00, FP=1.89, FN=2.00 -> 0.60
    assert round(M.dti(3.00, 1.89, 2.00), 2) == 0.60


def test_metric_matches_literal_equations():
    rng = np.random.default_rng(0)
    for _ in range(5):
        pred = (rng.random((14, 14)) < 0.12) * rng.random((14, 14))
        truth = rng.random((14, 14)) < 0.10
        c = M.components(pred, truth); tp, fp, fn = brute(pred, truth)
        assert c["TP_w"] == pytest.approx(tp, abs=1e-9) and c["FP_w"] == pytest.approx(fp, abs=1e-9)
        assert c["FN_w"] == pytest.approx(fn, abs=1e-9)


def test_ledger_credit_map_equals_metric_credit():
    rng = np.random.default_rng(3)
    p = ((rng.random((30, 30)) < 0.1) * 1.0).astype(np.float32)
    K, _ = L.credit_maps(p)
    truth = rng.random((30, 30)) < 0.15
    assert float(K[truth].sum()) == pytest.approx(M.components(p, truth)["TP_w"], abs=1e-4)


def _template(tmp_path, shape=(12, 14)):
    foot = np.ones(shape, bool); foot[:, :3] = False
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    t = tmp_path / "t.tif"
    with rasterio.open(t, "w", driver="GTiff", height=shape[0], width=shape[1], count=1, dtype="float32",
                       crs="EPSG:32611", transform=from_origin(243350, 4508550, 100, 100), nodata=np.nan) as d:
        d.write(arr, 1)
    return t, foot


def test_legacy_writer_and_validator_are_disabled(tmp_path):
    t, foot = _template(tmp_path)
    labels = np.zeros_like(foot)
    data = np.zeros(foot.shape, np.float32)
    with pytest.raises(RuntimeError, match='BLOCKED'):
        W.write_submission(data, foot, labels, t, tmp_path / 'out.tif', 'zeros')
    assert not (tmp_path / 'out.tif').exists()
    with pytest.raises(RuntimeError, match='BLOCKED'):
        W.validate(t, t, foot, labels)
