"""Contract tests for the 2026-10-27 session lane (arena/1f0b051d).

The lane's run card, TIF bytes, site downloads and verdict must stay mutually
consistent, and no projection may be labelled as an organizer score.
"""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence" / "session_1f0b051d_run_card.json").read_text())
NAME = CARD["submission_name"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_card_protocol_fields():
    for key in ("hypothesis", "mechanism", "named_non_fault_mimic", "holdout_dti",
                "correlation_overlap_vs_registry", "raster_sha256", "validator_output",
                "submission_name", "submission_note", "verdict"):
        assert key in CARD, key
    assert CARD["verdict"] in {"promote", "negative"}
    assert len(CARD["submission_note"]) <= 140
    assert CARD["organizer_confirmed_score"] is None
    assert CARD["experiments_run"] <= 3
    assert CARD["slots_used"] == 0
    h = CARD["holdout_dti"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] and h["n_withheld_positives"] > 0
    assert len(h["final_saved_file_static_readback"]["ci95"]) == 2


def test_tif_bytes_match_card_and_downloads():
    tif = ROOT / "submission" / NAME
    assert tif.exists()
    assert sha256(tif) == CARD["raster_sha256"]
    dl = ROOT / CARD["download"]["site_tif"]
    assert sha256(dl) == CARD["raster_sha256"]
    z = zipfile.ZipFile(ROOT / CARD["download"]["site_zip"])
    assert z.namelist() == [NAME]
    assert hashlib.sha256(z.read(NAME)).hexdigest() == CARD["raster_sha256"]


def test_tif_format_and_range():
    with rasterio.open(ROOT / "submission" / NAME) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        a = ds.read(1)
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert int((a > 0).sum()) == CARD["dots"]


def test_uniqueness_claims_within_protocol_limits():
    u = CARD["correlation_overlap_vs_registry"]
    assert u["n_comparators"] >= 122
    assert u["max_cand_within3_sparse"] <= 0.70
    assert abs(u["max_abs_density_spearman"]) <= 0.90
    assert CARD["canary"]["all_pass"] is True


def test_historical_lane_pages_do_not_recommend_submission():
    for name in ("index.html", "how-to-submit.html"):
        body = (ROOT / "docs/session-1f0b051d" / name).read_text()
        assert "Global release gate: DO NOT SUBMIT" in body
        assert "research only" in body.lower()
        assert "../data/session_1f0b051d_run_card.json" in body
        assert "submit it only as" not in body.lower()
    # The historical file and its actual hash remain available for reproducibility.
    assert (ROOT / "submission" / NAME).is_file()
