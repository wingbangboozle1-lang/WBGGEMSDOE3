"""Tests for the 2026-10-27 SGCE release. No network and no large restored data required."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def _j(rel):
    return json.loads((ROOT / rel).read_text())


def test_run_card_is_promote_hash_bound_and_never_claims_a_receipt():
    card = _j("evidence/session2_run_card.json")
    build = _j("evidence/session2_build.json")
    assert card["verdict"] == "promote"
    assert card["ok_to_download"] is True
    assert card["selector_approval"] is False
    assert card["organizer_receipt"] is None
    assert card["slots_spent"] == 0
    assert len(card["submission_note"]) <= 140
    assert card["raster_sha256"] == build["files"][card["submission_name"] + "-zeros.tif"]["sha256"]
    assert card["holdout"]["paired_delta_vs_champion_proxy"]["ci95"][0] > 0
    assert card["holdout"]["candidate"]["dti"] > card["holdout"]["champion_proxy"]["dti"]


def test_released_tiff_bytes_match_the_card_and_validation():
    card = _j("evidence/session2_run_card.json")
    build = _j("evidence/session2_build.json")
    for fname, meta in build["files"].items():
        p = ROOT / "submission" / fname
        assert p.is_file()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"]
        q = ROOT / "docs" / "downloads" / fname
        assert q.is_file() and q.read_bytes() == p.read_bytes()
    for name, v in build["validation"].items():
        assert v["passed"], name
        assert v["checks"]["single_band"] and v["checks"]["dtype_float32"]
        assert v["checks"]["crs_epsg_32611"] and v["checks"]["shape_matches_template"]
        assert v["checks"]["transform_matches_template"]
        assert v["checks"]["in_footprint_no_nan"] and v["checks"]["in_footprint_range_0_1"]
        assert v["checks"]["zero_on_catalogue"]
    with rasterio.open(ROOT / "submission" / (card["submission_name"] + "-zeros.tif")) as ds:
        a = ds.read(1)
    assert a.dtype == np.float32 and ds.count == 1
    assert int(ds.crs.to_epsg()) == 32611
    assert np.isfinite(a).all() and float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert int((a > 0).sum()) == build["dots"]


def test_uniqueness_gates_and_literal_reading_are_both_reported():
    u = _j("evidence/session2_build.json")["uniqueness"]
    assert u["U1_exact_dot_duplicate"] is False
    assert u["U2_max_abs_spearman"] <= 0.90
    assert u["U3_max_overlap_nonlattice"] <= 0.70
    assert u["U3_lattice_excess_pass"] is True
    assert u["content_aware_pass"] is True
    assert u["literal_pass"] is False   # dense witness remains a flagged protocol conflict


def test_leakage_canary_and_budget_are_recorded():
    h = _j("evidence/session2_holdout.json")
    assert h["canary_max"]["auc"] <= 0.90
    assert h["budget"]["experiments_run"] == 3
    card = _j("evidence/session2_run_card.json")
    assert "exceeded" in card["budget_disclosure"] or "repair" in card["budget_disclosure"]


def test_nine_site_table_has_estimates_and_no_hallucinated_scores():
    p = _j("evidence/session2_projection.json")
    assert p["model"] in ("ridge", "forest")
    assert p["n_training"] >= 100
    assert len(p["focus_sites"]) == 9
    for site, row in p["focus_sites"].items():
        assert "owner_reported_unverified" in row
        assert row["projection"]["label"] == "PROJECTION"
    assert p["candidate"]["projection"]["label"] == "PROJECTION"
    assert p["evidence_class"].startswith("PROJECTION")
