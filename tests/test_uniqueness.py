import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from uniqueness_audit import audit_uniqueness


def write(path: Path, values: np.ndarray, *, nodata=None, x0=0):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=from_origin(x0, 1000, 100, 100),
        nodata=nodata,
    ) as dst:
        dst.write(values.astype("float32"), 1)


def example_files(tmp_path):
    rng = np.random.RandomState(74)
    candidate = np.zeros((10, 10), dtype="float32")
    candidate[9, 9] = 1
    registry = np.zeros((10, 10), dtype="float32")
    registry[0, 0] = 1
    surface = rng.normal(size=(10, 10)).astype("float32")
    template = np.zeros((10, 10), dtype="float32")
    paths = {name: tmp_path / f"{name}.tif" for name in ("candidate", "registry", "surface", "template")}
    write(paths["candidate"], candidate)
    write(paths["registry"], registry)
    write(paths["surface"], surface)
    write(paths["template"], template)
    return paths


def test_separate_surface_and_complete_registry_can_pass(tmp_path):
    paths = example_files(tmp_path)
    result = audit_uniqueness(
        paths["candidate"],
        [paths["registry"]],
        candidate_surface_tif=paths["surface"],
        reference_grid_tif=paths["template"],
        registry_complete=True,
    )
    assert result.surface_check_status == "MEASURED"
    assert result.registry_check_status == "COMPLETE_DECLARED_AND_COMPARABLE"
    assert result.lane_rule_1_pass and result.lane_rule_2_pass and result.unique


def test_missing_surface_fails_closed_even_when_dots_are_separate(tmp_path):
    paths = example_files(tmp_path)
    result = audit_uniqueness(
        paths["candidate"],
        [paths["registry"]],
        candidate_surface_tif=None,
        reference_grid_tif=paths["template"],
        registry_complete=True,
    )
    assert result.max_overlap_within_3px == 0.0
    assert result.surface_check_status == "NOT_PROVIDED"
    assert not result.lane_rule_1_pass and not result.unique


def test_incomplete_registry_cannot_pass(tmp_path):
    paths = example_files(tmp_path)
    result = audit_uniqueness(
        paths["candidate"],
        [paths["registry"]],
        candidate_surface_tif=paths["surface"],
        reference_grid_tif=paths["template"],
        registry_complete=False,
    )
    assert result.lane_rule_2_pass is False
    assert result.unique is False
    assert result.registry_check_status == "INCOMPLETE_OR_INCOMPATIBLE"


def test_reference_grid_mismatch_cannot_pass(tmp_path):
    paths = example_files(tmp_path)
    bad_template = tmp_path / "wrong-template.tif"
    write(bad_template, np.zeros((10, 10), dtype="float32"), x0=25)
    result = audit_uniqueness(
        paths["candidate"],
        [paths["registry"]],
        candidate_surface_tif=paths["surface"],
        reference_grid_tif=bad_template,
        registry_complete=True,
    )
    assert result.registry_check_status == "INCOMPLETE_OR_INCOMPATIBLE"
    assert result.surface_check_status == "REFERENCE_GRID_REQUIRED_OR_MISMATCH"
    assert not result.unique


def test_constant_surface_is_indeterminate_not_a_pass(tmp_path):
    paths = example_files(tmp_path)
    write(paths["surface"], np.zeros((10, 10), dtype="float32"))
    result = audit_uniqueness(
        paths["candidate"],
        [paths["registry"]],
        candidate_surface_tif=paths["surface"],
        reference_grid_tif=paths["template"],
        registry_complete=True,
    )
    assert result.max_abs_rho_surface is None
    assert result.surface_check_status == "INDETERMINATE_NO_VALID_SURFACE_COMPARISONS"
    assert not result.unique
