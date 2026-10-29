"""Regression checks for the 2026-10-29 focus-site verification.

These tests read saved evidence files and synthetic arrays only. They make no
network calls, so they run in CI and in the sandbox alike.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "focus_files_verification_2026-10-29.json"
OFFICIAL = ROOT / "evidence" / "official_source_check_2026-10-29_focus.json"
SCRIPT = ROOT / "scripts" / "verify_focus_files.py"

NINE = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


def _load_script():
    spec = importlib.util.spec_from_file_location("verify_focus_files", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def card():
    return json.loads(EVIDENCE.read_text())


@pytest.fixture(scope="module")
def official():
    return json.loads(OFFICIAL.read_text())


def test_all_nine_sites_present_and_hashes_match_audit(card):
    assert set(card["rasters"]) == NINE
    assert all(r["sha256_matches_focus_audit"] for r in card["rasters"].values())


def test_every_raster_is_single_band_float32_on_official_grid(card):
    for site, r in card["rasters"].items():
        f = r["format"]
        assert f["band_count"] == 1, site
        assert f["dtype"] == "float32", site
        assert f["epsg"] == 32611, site
        assert f["shape"] == [3730, 3292], site
        assert f["grid_matches_official_template"] is True, site
        assert f["inf_cells"] == 0, site
        assert f["finite_out_of_0_1_cells"] == 0, site
        assert 0.0 <= f["finite_min"] <= f["finite_max"] <= 1.0, site


def test_footprint_styles_are_as_measured(card):
    styles = {s: r["format"]["footprint_style"] for s, r in card["rasters"].items()}
    assert {s for s, v in styles.items() if v == "nan_outside"} == {
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE31"}
    assert {s for s, v in styles.items() if v != "nan_outside"} == {
        "GEMSDOE30", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


def test_gems32_is_exact_pruned_copy_of_gems28_base(card):
    m = card["mechanism_gems32_vs_gems28_h27_4"]
    assert m["target_is_subset_of_base"] is True
    assert m["target_cells_not_in_base"] == 0
    assert m["base_positive_cells"] == 40199
    assert m["target_positive_cells"] == 37654
    assert m["base_cells_removed"] == 2545
    assert m["rule_mismatch_cells"] == 0
    assert m["removed_min_dist_to_catalogue_px"] > 1.0
    assert m["removed_max_dist_to_catalogue_px"] <= 2.0
    assert m["kept_min_dist_to_catalogue_px"] > 2.0


def test_identity_findings(card):
    assert card["identities"]["GEMSDOE31_dot_set_identical_to_GEMSDOE28_H27_4_base"] is True
    assert card["identities"]["GEMSDOE25_dot_set_identical_to_GEMSDOE30"] is True


def test_every_focus_file_fails_literal_uniqueness_rule(card):
    for site, u in card["uniqueness_vs_focus_set"].items():
        assert u["passes_70pct_3px_rule"] is False, site
        assert u["literal_user_rule_status"] == "DUPLICATE-STOP", site


def test_top_two_owner_files_have_no_dots_within_2px_of_catalogue(card):
    cat = card["catalogue"]["per_site_fraction_of_dots_within_2px"]
    assert cat["GEMSDOE32"] == 0.0
    assert cat["GEMSDOE36"] == 0.0


def test_irregularities_are_recorded(card):
    sample = card["official_sample_submission_check"]
    assert sample["value_1_cells_identical_to_training_labels"] is True
    assert sample["value_1_cells"] == 60988
    assert "Flagged" in sample["irregularity"]
    template = card["repo_template_grid_check"]
    assert template["is_identical_to_sample_submission_footprint"] is False
    assert template["finite_cells"] == 12279160


def test_evidence_class_forbids_score_claims(card):
    assert "NOT organizer-confirmed" in card["evidence_class"]
    assert "NOT HOLDOUT-DTI" in card["evidence_class"]


def test_official_source_quotes_are_present(official):
    text = json.dumps(official)
    for quote in ("Dec. 3, 2026, 11:59 p.m. UTC",
                  "data outside the bounds is null or nan",
                  "three submissions per week",
                  "5:00 p.m. ET on the prize submission deadline date",
                  "Pixels corresponding to known USGS/INGENIOUS faults are masked"):
        assert quote in text, quote


def test_official_check_is_dated_and_labelled(official):
    assert official["checked_date_utc"] == "2026-10-29"
    assert official["evidence_class"].startswith("OFFICIAL-SOURCE-TEXT")


def test_overlap_and_phi_on_synthetic_arrays():
    mod = _load_script()
    a = np.zeros((10, 10), dtype=bool)
    b = np.zeros((10, 10), dtype=bool)
    a[2, 2] = a[5, 5] = True
    b[2, 4] = True          # 2 px from a[2,2]; 3.16 px from a[5,5]
    dist_b = mod.distance_transform_edt(~b)
    # a[2,2] within 3 px of b -> yes; a[5,5] -> dist sqrt(9+1)=3.16 -> no
    assert mod.directed_overlap(a, dist_b) == pytest.approx(0.5)
    # identical sets: phi = 1
    assert mod.phi(a, a) == pytest.approx(1.0)
    # complementary sets on a 2x2 pattern: phi = -1
    c = np.array([[1, 0], [0, 1]], dtype=bool)
    d = ~c
    assert mod.phi(c, d) == pytest.approx(-1.0)


def test_phi_is_nan_for_constant_arrays():
    mod = _load_script()
    z = np.zeros((4, 4), dtype=bool)
    assert np.isnan(mod.phi(z, z))
