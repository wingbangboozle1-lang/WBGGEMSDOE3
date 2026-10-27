"""Synthetic raster tests for the independent, read-only registry recheck."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("registry_recheck", ROOT / "scripts/recheck_registry_witness.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write(path, arr, transform=None, nodata=None):
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                       count=1, dtype="float32", crs="EPSG:32611", nodata=nodata,
                       transform=transform or from_origin(10, 1000, 100, 100)) as ds:
        ds.write(arr.astype("float32"), 1)


def test_universal_witness_measures_actual_research_dots(tmp_path):
    sample = tmp_path / "sample.tif"
    witness = tmp_path / "witness.tif"
    candidate = tmp_path / "candidate.tif"
    s = np.zeros((8, 8), np.float32)
    s[:, 0] = np.nan
    write(sample, s, nodata=np.nan)
    ref = np.ones_like(s); ref[:, 0] = np.nan
    write(witness, ref, nodata=np.nan)
    p = np.zeros_like(s); p[1, 1] = p[3, 4] = p[7, 7] = 1
    write(candidate, p)
    result = mod.observations(sample, witness, candidate)
    assert result["witness"]["universal_blocker"]
    assert result["witness"]["footprint_cells"] == 56
    assert result["candidate"]["positive_pixels_all"] == 3
    assert result["candidate"]["positive_pixels_outside"] == 0
    assert result["candidate"]["positive_pixels_coincident_with_witness"] == 3
    assert result["candidate"]["directed_overlap_within_3px_all_positive"] == 1.0


def test_three_pixel_boundary_and_empty_reference_are_handled(tmp_path):
    sample = tmp_path / "sample.tif"; witness = tmp_path / "witness.tif"; candidate = tmp_path / "p.tif"
    a = np.zeros((10, 10), np.float32); write(sample, a)
    ref = a.copy(); ref[5, 5] = 1; write(witness, ref)
    p = a.copy(); p[5, 8] = 1; p[1, 1] = 1; write(candidate, p)
    result = mod.observations(sample, witness, candidate)
    assert not result["witness"]["universal_blocker"]
    assert result["candidate"]["directed_overlap_within_3px_all_positive"] == .5
    write(witness, a)
    result = mod.observations(sample, witness, candidate)
    assert result["candidate"]["directed_overlap_within_3px_all_positive"] == 0


def test_bad_geometry_and_empty_candidate_are_rejected(tmp_path):
    sample = tmp_path / "sample.tif"; witness = tmp_path / "witness.tif"; candidate = tmp_path / "p.tif"
    a = np.zeros((5, 5), np.float32); write(sample, a); write(witness, np.ones_like(a))
    write(candidate, a)
    with pytest.raises(ValueError, match="empty research prediction"):
        mod.observations(sample, witness, candidate)
    a[1, 1] = 1; write(candidate, a, transform=from_origin(11, 1000, 100, 100))
    with pytest.raises(ValueError, match="candidate grid"):
        mod.observations(sample, witness, candidate)


def test_wrong_pins_refuse_to_write_evidence(tmp_path):
    a = np.zeros((5, 5), np.float32)
    s = tmp_path / "s.tif"; w = tmp_path / "w.tif"; c = tmp_path / "c.tif"
    write(s, a); write(w, a); write(c, a)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        mod.build_report(s, w, c, c, ROOT / "registry/registry_session2.json")


def test_retired_publishers_and_generators_stop_before_writing():
    paths = ("session2_site.py", "build_dossier.py", "build_site_thcs.py", "session2_release.py",
             "session2_final.py", "build_cspes_submission.py", "build_focus_and_lane_comparison.py")
    before = (ROOT / "docs/index.html").read_bytes()
    for name in paths:
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT,
                              capture_output=True, text=True, timeout=15)
        assert proc.returncode != 0, name
        assert "BLOCKED" in proc.stderr, (name, proc.stderr)
    assert (ROOT / "docs/index.html").read_bytes() == before
