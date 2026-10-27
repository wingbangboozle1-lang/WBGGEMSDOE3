"""Tests for Lane THCS-OOF, IR-20/IR-21/IR-23 fixes, CELF submodular placement, and byte-level GeoTIFF validity."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from src.gemsdoe.validation import SGMC_OFF_CATALOGUE_PX, score_from_profile
from src.thcs.celf import celf_select, optimal_dti_budget_from_gain_curve
from src.thcs.features import ALL_FEATURE_NAMES, BLOCK_AB_INDICES, BLOCK_A_INDICES

ROOT = Path(__file__).resolve().parents[1]


def test_ir21_validation_score_from_profile_is_bounded_and_respects_tp_le_g():
    """IR-21 fix: even a 206,895-dot lattice or 5.17M full-footprint mask cannot exceed TP_w <= |G|."""
    # Uniform lattice: h ~ 0.0872 on 62,122 SGMC proxy pixels, mass = 206,895, n_truth = 15,672.5
    s_lattice = score_from_profile(0.0872, 206_895.0, 15_672.5, n_proxy=SGMC_OFF_CATALOGUE_PX)
    assert 0.0 <= s_lattice < 0.16, f"Lattice score inflated: {s_lattice}"

    # Extreme full-footprint spam: mass = 5,167,373
    s_full = score_from_profile(0.50, 5_167_373.0, 12_691.0, n_proxy=SGMC_OFF_CATALOGUE_PX)
    assert 0.0 <= s_full <= 1.0
    assert s_full < 0.02

    # Edge cases: zero mass, zero truth, negative inputs
    assert score_from_profile(0.0, 38_000.0, 12_691.0) == 0.0
    assert score_from_profile(0.15, 0.0, 12_691.0) == 0.0
    assert score_from_profile(0.15, 38_000.0, 0.0) == 0.0


def test_celf_select_submodular_monotonicity_and_boundary_safety():
    rng = np.random.default_rng(7)
    prob = rng.uniform(0.0, 0.05, size=(40, 45)).astype(np.float32)
    # Plant a sharp synthetic fault trace including border pixels (row=0, col=44)
    for r in range(40):
        c = min(44, int(round(4 + 0.9 * r)))
        prob[r, c] = 0.95
    elig = np.ones((40, 45), dtype=bool)
    elig[10:13, :] = False  # Simulate visible-catalogue collar exclusion

    d0, m0 = celf_select(prob, elig, budget_k=0)
    assert int(d0.sum()) == 0 and m0["selected"] == 0

    d5, m5 = celf_select(prob, elig, budget_k=5)
    d12, m12 = celf_select(prob, elig, budget_k=12)
    assert int(d5.sum()) == 5
    assert int(d12.sum()) == 12
    assert not np.any(d12 & (~elig)), "CELF placed dots inside excluded collar"
    assert m12["covered_posterior_mass"] > m5["covered_posterior_mass"]
    assert m12["initial_max_gain"] >= m12["final_marginal_gain"] > 0.0

    k_opt, best_dti = optimal_dti_budget_from_gain_curve(np.linspace(1.2, 0.01, 50), expected_n_truth=20.0)
    assert 1 <= k_opt <= 50 and 0.0 < best_dti <= 1.0


def test_thcs_features_module_is_strictly_zero_catalogue():
    """Verify via AST & string literals that src/thcs/features.py never touches catalogue labels."""
    assert len(BLOCK_A_INDICES) == 38
    assert len(BLOCK_AB_INDICES) == 48
    assert len(ALL_FEATURE_NAMES) == 48
    assert "rad_tc_f32" in ALL_FEATURE_NAMES
    assert "mag_tilt_angle" in ALL_FEATURE_NAMES
    assert "probe2m_dab_3km" in ALL_FEATURE_NAMES

    src = (ROOT / "src" / "thcs" / "features.py").read_text()
    tree = ast.parse(src)
    string_literals = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    # Ignore module/function docstrings; check actual code string constants
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ds = ast.get_docstring(node, clean=False)
            if ds is not None:
                docstrings.add(ds)
    code_strings = [s for s in string_literals if s not in docstrings]
    forbidden = ("existing_faults.tif", "labels.tif", "derived_sgmc_faults_100m_u8.tif", "dist_known_fault_px")
    for bad in forbidden:
        assert all(bad not in s for s in code_strings), f"Forbidden catalogue token in code: {bad}"


def test_thcs_run_card_canary_and_saved_geotiff_bytes():
    rc = json.loads((ROOT / "evidence" / "thcs_run_card.json").read_text())
    canary = json.loads((ROOT / "evidence" / "thcs_leakage_canary.json").read_text())
    exps = json.loads((ROOT / "evidence" / "thcs_experiments.json").read_text())
    comp = json.loads((ROOT / "evidence" / "focus_and_lane_comparison.json").read_text())

    # Rule 4: Leakage canary
    assert canary["all_passed"] is True
    assert canary["n_features_tested"] == 48
    assert canary["max_directional_auc"] <= 0.90

    # Rule 6: 3-experiment budget honored and GDR #1391 ablation positive
    assert rc["experiments_used"] == 3
    assert len(exps["experiments"]) == 3
    e1, e2, e3 = exps["experiments"]
    assert e2["pooled_dti"] > e1["pooled_dti"], "GDR #1391 hydrothermal block must show positive ablation lift"
    assert e3["pooled_dti"] >= e2["pooled_dti"]

    # Rule 5: Run card completeness & <=140-char note
    note = rc["artifact"]["submission_note_140c"]
    assert 1 <= len(note) <= 140
    assert rc["verdict"] in {"promote", "negative"}

    # Portal [0, 1] & byte-identity check on saved GeoTIFF
    tif_path = ROOT / rc["artifact"]["submission_tif"]
    docs_tif = ROOT / rc["artifact"]["docs_download_tif"]
    assert tif_path.exists() and docs_tif.exists()
    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    assert sha == rc["artifact"]["raster_sha256"]
    assert hashlib.sha256(docs_tif.read_bytes()).hexdigest() == sha

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs is not None and ds.crs.to_epsg() == 32611
    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert int((arr > 0).sum()) == rc["artifact"]["emitted_dots"]

    # Focus-site comparison covers all 9 focus sites + THCS-OOF
    sites = {r["site"] for r in comp["rows"]}
    for s in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
              "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36", "WBGGEMSDOE3 (THCS-OOF)"):
        assert s in sites

    # IR-23 fix: no conflicting dual HCE banner injected at top of docs/index.html
    idx_html = (ROOT / "docs" / "index.html").read_text()
    assert idx_html.count('class="hero') == 1
