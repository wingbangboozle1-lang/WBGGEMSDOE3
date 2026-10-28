"""Safety regressions for the parallel session's independent diagnostics."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import verify_focus_uniqueness as focus
import verify_format_independent as fmt


def tif(path, shape=(4, 4), west=10):
    array = np.zeros(shape, dtype="float32")
    array[0, 0] = 1
    with rasterio.open(path, "w", driver="GTiff", height=shape[0], width=shape[1],
                       count=1, dtype="float32", crs="EPSG:32611",
                       transform=from_origin(west, 100, 100, 100)) as ds:
        ds.write(array, 1)
    return path


def test_cached_sample_is_rehashed(tmp_path, monkeypatch):
    monkeypatch.setattr(fmt, "CACHE", tmp_path)
    monkeypatch.setattr(fmt, "SAMPLE_SHA", "a" * 64)
    (tmp_path / (("a" * 64) + ".tif")).write_bytes(b"tampered cached sample")
    with pytest.raises(SystemExit, match="cached sample SHA-256 mismatch"):
        fmt.sample_path()


def test_format_shape_mismatch_reports_failure_instead_of_crashing(tmp_path, monkeypatch):
    sample = tif(tmp_path / "sample.tif")
    candidate = tif(tmp_path / "candidate.tif", shape=(3, 3))
    out = tmp_path / "result.json"
    monkeypatch.setattr(fmt, "sample_path", lambda: sample)
    monkeypatch.setattr(sys, "argv", ["format", str(candidate), "--out", str(out)])
    assert fmt.main() == 1
    result = json.loads(out.read_text())
    assert result["passed"] is False
    assert result["checks"]["shape_matches_sample"] is False
    assert result["checks"]["inside_footprint_all_finite"] is False


def test_focus_comparison_rejects_mismatched_grid(tmp_path, monkeypatch):
    sample = tif(tmp_path / "sample.tif")
    candidate = tif(tmp_path / "candidate.tif")
    reference = tif(tmp_path / "reference.tif", west=11)
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    (tmp_path / "registry").mkdir()
    (tmp_path / "evidence").mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / f"{digest}.tif").write_bytes(reference.read_bytes())
    (tmp_path / "evidence/nine_site_table.json").write_text(json.dumps({"rows": [{"site": "bad-grid", "sha256": digest}]}))
    (tmp_path / "registry/upstream_live_ledger_rasters.json").write_text(json.dumps({"rows": [{
        "sha256": digest, "status": "ok", "repo": "owner/repo", "path": "x.tif", "ref": "pinned"
    }]}))
    monkeypatch.setattr(focus, "ROOT", tmp_path)
    monkeypatch.setattr(focus, "CACHE", cache)
    monkeypatch.setattr(focus, "sample_path", lambda: sample)
    result = tmp_path / "result.json"
    assert focus.main(candidate, result) == 1
    report = json.loads(result.read_text())
    assert report["n_focus_files_checked"] == 0
    assert "grid mismatch" in report["errors"][0]
