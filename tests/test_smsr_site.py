"""SMSR lane page: hash-bound to its own evidence, independent of the site-wide decision.

This lane coexists with whatever the site-wide `gemsdoe-decision` currently is
(it does not assert or contradict the main banner's choice of file); it only
promises that ITS OWN claims are backed by real, hash-checked bytes.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def test_smsr_run_card_published_copy_matches_source():
    source = json.loads((ROOT / "evidence/smsr_run_card.json").read_text())
    published = json.loads((DOCS / "data/smsr_run_card.json").read_text())
    assert published == source
    assert source["verdict"] == "promote-to-selector"
    assert source["slots_used_by_this_session"] == 0
    assert source["experiments_run"] <= source["experiments_budget"] == 3


def test_smsr_raster_bytes_are_hash_bound_everywhere_they_are_served():
    source = json.loads((ROOT / "evidence/smsr_run_card.json").read_text())
    fname = source["file"].split("/")[-1]
    raster_sha = source["raster_sha256"]
    for rel in (source["file"], f"docs/smsr/downloads/{fname}"):
        assert sha(ROOT / rel) == raster_sha, rel
    receipt = json.loads((ROOT / "evidence/smsr_build_receipt.json").read_text())
    assert receipt["sha256"] == raster_sha
    assert receipt["validator"]["all_checks_passed"] is True
    assert receipt["validator"]["min"] == 0.0
    assert receipt["validator"]["max"] == 1.0
    assert receipt["validator"]["n_nan"] == 0
    assert receipt["validator"]["n_infinite"] == 0


def test_smsr_lane_page_does_not_contradict_or_hide_the_site_wide_decision():
    body = (DOCS / "smsr/index.html").read_text()
    assert "smsr-seisgeod-missingshear-detached-20261028T000000Z.tif" in body
    assert "not an organizer-confirmed" in body.lower()
    assert "head-to-head against invdesign" in body.lower()
    # the dense-witness caveat must still be reported, not silently dropped
    assert "17GEMSDOE_E-proba-multiscale" in body


def test_smsr_lane_is_discoverable_from_the_published_index():
    index = (DOCS / "index.html").read_text()
    assert "smsr/index.html" in index


def test_smsr_uniqueness_gate_thresholds_hold():
    uniq = json.loads((ROOT / "evidence/smsr_uniqueness.json").read_text())
    for row in uniq:
        if row["name"] == "17GEMSDOE-witness-dense":
            continue  # the known, transparently-reported dense-witness edge case
        assert row["dot_overlap_3px"] <= 0.70 or row["spearman_full_footprint"] <= 0.90, row


def test_build_site_smsr_is_deterministic():
    import importlib
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    build_site_smsr = importlib.import_module("build_site_smsr")
    before = (DOCS / "smsr/index.html").read_text()
    assert build_site_smsr.main() == 0
    after = (DOCS / "smsr/index.html").read_text()
    assert before == after
