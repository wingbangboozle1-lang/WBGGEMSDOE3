"""RFL lane unit tests (session arena/bd44f94b): relief math, frozen surface
properties, run-card schema, banner + site wiring.  Synthetic data only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def test_focal_relief_step():
    from gemsw.rfl import focal_relief
    e = np.zeros((21, 21), np.float32)
    e[:, 11:] = 100.0  # vertical step (idealised range front)
    r = focal_relief(e, 2)
    assert r.shape == e.shape
    # Relief is 100 in windows straddling the step, 0 far from it.
    assert r[10, 10] == pytest.approx(100.0)
    assert r[10, 0] == pytest.approx(0.0)
    assert r[10, 20] == pytest.approx(0.0)


def test_rfl_surface_bounds_and_footprint():
    from gemsw.rfl import build_surface
    rng = np.random.default_rng(0)
    shape = (120, 140)
    elev = (rng.normal(size=shape) * 50).astype(np.float32)
    elev[:, 80:] += 300.0
    elev[0, 0] = np.nan
    foot = np.ones(shape, bool)
    foot[:8, :] = False
    f = build_surface(elev, foot)
    s = f.surface
    assert s.dtype == np.float32
    assert np.isfinite(s).all()
    assert float(s.min()) >= 0.0 and float(s.max()) <= 1.0
    assert (s[~foot] == 0).all()
    for k in ("rfl_full", "abl_g500_only", "abl_g1100_only", "abl_piedmont_gate", "abl_slope_reference"):
        v = f.components[k]
        assert np.isfinite(v[foot]).all(), k
        assert float(v[foot].min()) >= 0.0 and float(v[foot].max()) <= 1.0 + 1e-6, k
    # Persistence = min of the two scale ranks, by definition.
    assert np.allclose(f.components["rfl_full"][foot],
                       np.minimum(f.components["rank_g2"], f.components["rank_g5"])[foot])


def test_rfl_run_card_schema_and_verdict():
    card = json.loads((ROOT / "evidence/rfl_run_card.json").read_text())
    for k in ("hypothesis", "mechanism", "named_non_fault_mimic", "holdout_dti",
              "correlation_overlap_vs_registry", "validator_output", "verdict"):
        assert k in card, k
    assert card["verdict"] == "negative"
    assert card["raster_sha256"] is None and card["submission_name"] is None
    h = card["holdout_dti"]
    assert h["label"] == "HOLDOUT-DTI" and h["n_withheld_positives"] == 22232
    assert h["evaluator_version"] == "GEMSDOE32-HIDE-RECOVER-v3.0"
    assert card["canary"]["all_pass"] and card["canary"]["max_single_feature_auc"] <= 0.90
    assert card["slots_spent"] == 0


def test_rfl_banner_and_site_wiring():
    from rfl_banner import RFL_BANNER
    assert "rfl/index.html" in RFL_BANNER and "DO NOT SUBMIT" in RFL_BANNER
    for name in ("index.html", "how-to-submit.html"):
        body = (ROOT / "docs/rfl" / name).read_text()
        assert "DO NOT SUBMIT this lane" in body and "this lane: DO NOT SUBMIT" in body
        assert "research only" in body.lower()
        assert "../data/release_gate.json" in body
        assert "cleared upload" not in body.lower()


def test_recommended_file_validation_receipt():
    v = json.loads((ROOT / "evidence/rfl_recommended_validation.json").read_text())
    assert v["passed"] and all(v["checks"].values())
    assert v["whole_array_min"] >= 0.0 and v["whole_array_max"] <= 1.0
    tif = ROOT / "docs/hce/downloads" / v["file"]
    assert tif.exists()
