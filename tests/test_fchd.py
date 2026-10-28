"""Tests for Session 4 (`FCHD-NCM`), `IR-24` release-gate synchronization, and `IR-27` TIFF band order.

Designed to run offline in CI without requiring gitignored `data/` or `.cache/` directories.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import rasterio

from src.fchd.features import FEATURE_NAMES
from src.fchd.ncm_struct import STRUCT_FEATURE_NAMES, compute_ncm_structural_grid
from src.fchd.registry_full import celf_knapsack_allocate
from src.lbcal.data import BAND as LBCAL_OFFICIAL_BAND

ROOT = Path(__file__).resolve().parents[1]


def _j(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def test_ir27_band_indices_match_official_tiff_tags():
    """Guard against IR-27: every tf_ds.read(k) in src/fchd/features.py must match official TIFF tags."""
    src = (ROOT / "src" / "fchd" / "features.py").read_text()
    var_to_official = {
        "grav": "iso_grav_anom",
        "grav_hg": "iso_grav_anom_hg",
        "rtp": "rtp",
        "mag_hg0": "tmi_hg",
        "geod_i2": "geod_2ndinv",
        "rad_tc": "tc",
        "geod_sh": "geod_shearrate",
        "grav_vg": "iso_grav_anom_vg",
        "det_elev": "det_elev",
        "mag": "tmi",
        "base_d": "depth_to_base_surf",
        "eq_dens": "ieq_n100a15",
        "cond_s": "cond_surf",
        "det_slp": "det_elev_slope",
    }
    for var_name, tag in var_to_official.items():
        m = re.search(rf"\b{var_name}\s*=\s*_fill_outside\(tf_ds\.read\((\d+)\)", src)
        assert m is not None, f"missing tf_ds.read assignment for {var_name}"
        assert int(m.group(1)) == LBCAL_OFFICIAL_BAND[tag], (var_name, tag)
    assert len(FEATURE_NAMES) == 62
    assert len(STRUCT_FEATURE_NAMES) == 10


def test_ncm_structural_features_strictly_respect_visible_mask():
    """Withheld fault components must not leak into NCM structural continuation features."""
    comp_a = np.zeros((120, 120), dtype=bool)
    comp_b = np.zeros((120, 120), dtype=bool)
    comp_a[25, 20:45] = True  # visible fault
    comp_b[90, 60:85] = True  # withheld fault far away

    ones = np.ones((120, 120), dtype=np.float32) * 0.5
    s_vis_only = compute_ncm_structural_grid(comp_a, ones, ones, ones)
    s_with_leak = compute_ncm_structural_grid(comp_a | comp_b, ones, ones, ones)

    assert s_vis_only.shape == (10, 120, 120)
    assert s_vis_only.dtype == np.float32
    # Ahead of withheld comp_b's eastern tip (row 90, col 89), tip cone is 0 when withheld vs >0 when present
    assert float(s_vis_only[0, 90, 89]) < float(s_with_leak[0, 90, 89])
    assert float(s_vis_only[0, 90, 89]) == 0.0


def test_celf_knapsack_allocator_respects_budget_collar_and_comparator_cap():
    rng = np.random.default_rng(7)
    prob = rng.uniform(0.01, 0.20, size=(80, 80)).astype(np.float32)
    prob[10:70:8, 10:70:8] = 0.95
    foot = np.ones((80, 80), dtype=bool)
    eligible = foot.copy()
    eligible[:8, :] = False  # simulated catalogue collar

    # Synthetic comparator covering top half of footprint; cap overlap at <= 0.50
    comp_d3 = np.zeros((80, 80), dtype=bool)
    comp_d3[:40, :] = True
    reg = {"d3_packed": np.packbits(comp_d3[foot])[None, :]}

    dots, info = celf_knapsack_allocate(
        prob_2d=prob,
        eligible_2d=eligible,
        foot=foot,
        reg=reg,
        budget_k=16,
        max_overlap_cap=0.50,
    )
    assert dots.dtype == bool and dots.shape == (80, 80)
    assert int(dots.sum()) == 16 and info["selected"] == 16
    assert not bool(dots[~eligible].any())
    assert int((dots & comp_d3).sum()) <= int(np.floor(0.50 * 16))


def test_fchd_run_card_canary_and_saved_geotiff_contracts():
    rc = _j("evidence/fchd_run_card.json")
    canary = _j("evidence/fchd_leakage_canary.json")
    exps = _j("evidence/fchd_experiments.json")

    assert rc["lane_id"] == "FCHD-NCM"
    assert rc["verdict"] == "negative"
    assert rc["ok_to_download"] is False
    assert rc["selector_approval"] is False
    assert rc["organizer_receipt"] is None
    assert rc["slots_spent"] == 0
    assert rc["experiments_used"] == 3 and len(exps["experiments"]) == 3
    assert len(rc["submission_note"]) <= 140
    assert "b15" in rc["budget_disclosure"] and "1,653" in rc["budget_disclosure"]

    assert canary["all_passed"] is True
    assert canary["n_features_tested"] == 72
    assert canary["max_directional_auc"] <= 0.90

    assert rc["uniqueness"]["pre_placement_max_abs_spearman"] <= 0.90
    assert rc["uniqueness"]["U3_max_nonlattice_overlap_3px"] <= 0.70
    assert rc["uniqueness"]["max_u3_overlap_vs_oct27_peers"] <= 0.70

    tif_sub = ROOT / rc["submission_path"]
    tif_docs = ROOT / "docs" / "fchd" / "downloads" / rc["submission_file"]
    assert tif_sub.is_file() and tif_docs.is_file()
    sha = hashlib.sha256(tif_sub.read_bytes()).hexdigest()
    assert sha == rc["raster_sha256"]
    assert tif_docs.read_bytes() == tif_sub.read_bytes()

    with rasterio.open(tif_sub) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert arr.dtype == np.float32
        assert ds.shape == (3730, 3292)
        assert int(ds.crs.to_epsg()) == 32611
    assert np.isfinite(arr).all()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert int((arr > 0).sum()) == rc["emitted_dots"] == 38000


def test_governing_fail_closed_gate_and_fchd_dossier_consistency():
    """Ensure FCHD-NCM dossier aligns with the governing fail-closed DO-NOT-SUBMIT gate."""
    dec = _j("docs/data/decision.json")
    gate = _j("docs/data/release_gate.json")
    assert dec["decision"] == "DO-NOT-SUBMIT" and dec["okay_to_submit"] is False
    assert gate["decision"] == "DO-NOT-SUBMIT" and gate["okay_to_submit"] is False

    fchd_page = (ROOT / "docs" / "fchd" / "index.html").read_text()
    assert 'content="DO-NOT-SUBMIT"' in fchd_page
    assert "DO NOT SUBMIT" in fchd_page
    assert "OK TO DOWNLOAD AND SUBMIT" not in fchd_page
    assert (ROOT / "docs" / "data" / "fchd_run_card.json").is_file()
    assert (ROOT / "docs" / "data" / "master_audit_2026-10-27.json").is_file()
