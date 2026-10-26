from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
import rasterio
from affine import Affine

from scripts.validate_registry_uniqueness import (
    _average_ranks,
    directed_dot_overlap,
    spearman_on_mask,
    validate_registry_uniqueness,
)

GRID = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36", "r13-lattice-s5"]


def write_tif(path, array):
    array = np.asarray(array, dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": GRID,
        "nodata": None,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(tmp_path, *, duplicate_surface=False, duplicate_dots=False, omit_lattice=False):
    surface = tmp_path / "candidate-surface.tif"
    candidate = tmp_path / "candidate-dots.tif"
    template = tmp_path / "sample-submission.tif"
    reference_surface = tmp_path / "registry-surface.tif"
    reference_dots = tmp_path / "registry-dots.tif"
    manifest_path = tmp_path / "manifest.json"

    candidate_surface = np.arange(25, dtype=np.float32).reshape(5, 5)
    if duplicate_surface:
        registry_surface = candidate_surface.copy()
    else:
        registry_surface = np.random.default_rng(20261026).permutation(25).astype(np.float32).reshape(5, 5)
    candidate_dots = np.zeros((5, 5), dtype=np.float32)
    candidate_dots[4, 4] = 1.0
    reference_dot_array = np.zeros((5, 5), dtype=np.float32)
    reference_dot_array[4 if duplicate_dots else 0, 4 if duplicate_dots else 0] = 1.0

    write_tif(surface, candidate_surface)
    write_tif(candidate, candidate_dots)
    write_tif(template, np.zeros((5, 5), dtype=np.float32))
    write_tif(reference_surface, registry_surface)
    write_tif(reference_dots, reference_dot_array)

    ids = SITES[:-1] if omit_lattice else SITES
    entries = [
        {
            "id": site,
            "surface_file": reference_surface.name,
            "surface_sha256": sha256(reference_surface),
            "dots_file": reference_dots.name,
            "dots_sha256": sha256(reference_dots),
        }
        for site in ids
    ]
    manifest = {
        "schema_version": 1,
        "registry_version": "synthetic-test-registry-v1",
        "source": "synthetic pytest fixture only",
        "complete": True,
        "includes_literal_lattice": True,
        "includes_all_focus_site_winners": True,
        "entries": entries,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return surface, candidate, template, manifest_path


def test_average_ranks_use_midranks_for_ties():
    ranks = _average_ranks(np.array([10, 10, 30, 20], dtype=np.float64))
    assert ranks.tolist() == [1.5, 1.5, 4.0, 3.0]


def test_spearman_handles_perfect_negative_and_constant_surface():
    x = np.arange(4, dtype=np.float32).reshape(2, 2)
    valid = np.ones((2, 2), dtype=bool)
    rho, n = spearman_on_mask(x, -x, valid)
    assert rho == pytest.approx(-1.0)
    assert n == 4
    rho, _ = spearman_on_mask(x, np.ones((2, 2)), valid)
    assert rho is None


def test_directed_dot_overlap_is_candidate_fraction_with_euclidean_radius():
    candidate = np.zeros((9, 9), dtype=bool)
    reference = np.zeros((9, 9), dtype=bool)
    valid = np.ones((9, 9), dtype=bool)
    candidate[4, 7] = True
    candidate[0, 0] = True
    reference[4, 4] = True
    fraction, n_candidate, _ = directed_dot_overlap(candidate, reference, valid)
    assert fraction == pytest.approx(0.5)
    assert n_candidate == 2


def test_complete_manifest_checks_both_surface_and_dot_gates(tmp_path):
    surface, candidate, template, manifest = make_fixture(tmp_path)

    report = validate_registry_uniqueness(surface, candidate, template, manifest)

    assert report["preplacement_surface_check"]["status"] == "PASS"
    assert report["final_dot_check"]["status"] == "PASS"
    assert report["literal_all_registry_uniqueness_passed"] is True
    assert report["registry_coverage"]["entry_count"] == 10
    assert report["registry_coverage"]["independently_verified"] is False
    assert report["submission_authorized"] is False


def test_surface_duplicate_fails_spearman_gate(tmp_path):
    surface, candidate, template, manifest = make_fixture(tmp_path, duplicate_surface=True)

    report = validate_registry_uniqueness(surface, candidate, template, manifest)

    assert report["preplacement_surface_check"]["maximum_absolute_spearman"] == pytest.approx(1.0)
    assert report["preplacement_surface_check"]["status"] == "FAIL"
    assert report["literal_all_registry_uniqueness_passed"] is False


def test_final_dot_duplicate_fails_overlap_gate(tmp_path):
    surface, candidate, template, manifest = make_fixture(tmp_path, duplicate_dots=True)

    report = validate_registry_uniqueness(surface, candidate, template, manifest)

    assert report["final_dot_check"]["maximum_directed_overlap"] == pytest.approx(1.0)
    assert report["final_dot_check"]["status"] == "FAIL"
    assert report["literal_all_registry_uniqueness_passed"] is False


def test_manifest_without_literal_lattice_fails_closed(tmp_path):
    surface, candidate, template, manifest = make_fixture(tmp_path, omit_lattice=True)

    report = validate_registry_uniqueness(surface, candidate, template, manifest)

    assert report["literal_all_registry_uniqueness_passed"] is False
    assert report["preplacement_surface_check"]["status"] == "NOT RUN"
    assert "literal lattice" in report["errors"][0]


def test_registry_hash_mismatch_fails_closed(tmp_path):
    surface, candidate, template, manifest = make_fixture(tmp_path)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["entries"][0]["surface_sha256"] = "0" * 64
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")

    report = validate_registry_uniqueness(surface, candidate, template, manifest)

    assert report["literal_all_registry_uniqueness_passed"] is False
    assert any("SHA-256 mismatch" in error for error in report["errors"])
