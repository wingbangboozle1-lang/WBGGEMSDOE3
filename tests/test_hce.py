"""Historical HCE evidence and current fail-closed publication contract."""
from __future__ import annotations
import hashlib
import json
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "hce"
TIF = DOCS / "downloads" / "wbggems3-hce1-latest.tif"
ZIP = DOCS / "downloads" / "wbggems3-hce1-latest.zip"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in {"href", "src"} and v:
                self.targets.append(v)


def test_deliverable_tif_matches_run_card_and_official_format():
    rc = json.loads((ROOT / "evidence/hce_run_card.json").read_text())
    assert TIF.exists() and ZIP.exists()
    assert _sha(TIF) == rc["raster"]["sha256"]
    assert _sha(ZIP) == rc["raster"]["zip_sha256"]
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs is not None and ds.crs.to_epsg() == 32611
        assert ds.transform.to_gdal() == (243350.0, 100.0, 0.0, 4508550.0, 0.0, -100.0)
    assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0
    assert not np.isnan(a).any() and not (a < -1e30).any()
    assert int((a > 0).sum()) == rc["raster"]["dots"]
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        assert len(names) == 1 and names[0].endswith(".tif")
        assert hashlib.sha256(z.read(names[0])).hexdigest() == rc["raster"]["sha256"]


def test_run_card_labels_every_number_and_reports_both_uniqueness_readings():
    rc = json.loads((ROOT / "evidence/hce_run_card.json").read_text())
    for key in ("hypothesis", "mechanism", "named_non_fault_mimic", "holdout_dti",
                "registry", "raster", "validator", "submission_name", "submission_note", "verdict"):
        assert key in rc
    h = rc["holdout_dti"]
    assert h["evaluator_version"] and h["n_withheld_positives"] > 0 and len(h["candidate_ci95"]) == 2
    assert h["paired_delta_vs_champion_proxy"]["ci95"][0] > 0
    assert rc["validator"]["passed"] is True
    assert rc["validator"]["no_nan_inside_footprint"] is True
    assert rc["validator"]["values_in_0_1_inside_footprint"] is True
    assert rc["validator"]["crs_shape_transform_match"] is True
    assert len(rc["submission_note"]) <= 140
    assert len(rc["submission_name"]) <= 140
    assert rc["organizer_confirmed_score"] is None
    assert rc["weekly_slots_used"] == 0
    assert any("NOT_A_SCORE" in k for k in rc)
    assert rc["registry"]["content_aware_pass"] is True
    assert rc["registry"]["literal_pass"] is False
    assert "literal FAIL" in rc["verdict"]["uniqueness"]
    assert "NOT an organizer-confirmed score" in rc["verdict"]["overall"]


def test_uniqueness_and_canary_thresholds_are_unchanged():
    u = json.loads((ROOT / "evidence/hce_uniqueness.json").read_text())["audit"]
    t = u["thresholds"]
    assert t["max_abs_spearman"] == 0.90 and t["max_dot_overlap"] == 0.70
    assert u["U2_max_abs_spearman"] <= 0.90
    assert u["U3_max_overlap_sparse"] <= 0.70
    assert u["U3_space_filling_max_excess"] <= t["max_excess_over_random_null"]
    assert u["n_comparable"] > 100
    c = json.loads((ROOT / "evidence/hce_canary.json").read_text())
    assert c["threshold"] == 0.90 and c["all_pass"] and c["max_auc"] <= 0.90


def test_site_marks_hce_artifact_research_only_and_has_no_candidate_links():
    pages = ["index.html", "how-to-submit.html", "why-0.2778.html", "hypotheses.html",
             "evidence.html", "sources.html", "limitations.html"]
    assert all((DOCS / p).exists() for p in pages)
    idx = (DOCS / "index.html").read_text()
    gate = json.loads((ROOT / "docs/data/release_gate.json").read_text())
    # The lane page keeps its own negative verdict and points at the project gate.
    assert 'name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"' in idx
    assert f'>{gate["decision"]}</a>' in idx
    assert "DO NOT SUBMIT this lane" in idx
    assert "DOWNLOAD RESEARCH TIF" not in idx
    assert "downloads/wbggems3-hce1-latest.tif" not in idx
    for p in pages:
        text = (DOCS / p).read_text()
        assert "DO NOT SUBMIT this lane" in text
        assert "this lane: DO NOT SUBMIT" in text
        parser = _Links()
        parser.feed(text)
        for link in parser.targets:
            if link.startswith(("http", "mailto:", "#", "data:")):
                continue
            target = (DOCS / p).parent / link.split("#")[0]
            assert target.exists(), (p, link, target)
    root = (ROOT / "docs" / "index.html").read_text()
    assert "hce/index.html" in root


def test_site_builder_is_deterministic_and_fail_closed():
    from build_site import main
    before = {p.relative_to(ROOT / "docs"): _sha(p) for p in (ROOT / "docs").rglob("*.html")}
    assert main() == 0
    after = {p.relative_to(ROOT / "docs"): _sha(p) for p in (ROOT / "docs").rglob("*.html")}
    assert before == after
    idx = (DOCS / "index.html").read_text()
    gate = json.loads((ROOT / "docs/data/release_gate.json").read_text())
    assert f'>{gate["decision"]}</a>' in idx
    assert "DOWNLOAD RESEARCH TIF" not in idx
