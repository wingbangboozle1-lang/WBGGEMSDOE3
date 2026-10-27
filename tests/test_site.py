import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys_path_added = False


def test_every_published_page_states_its_evidence_class():
    for page in ("index.html", "executive-summary.html", "how-to-submit.html",
                 "research.html", "evidence.html"):
        body = (DOCS / page).read_text()
        assert "LEDGER-INVERSION ESTIMATE" in body, page


def test_front_page_advertises_a_download_that_matches_the_decision_and_the_card():
    decision = json.loads((DOCS / "data" / "decision.json").read_text())
    card = json.loads((ROOT / "evidence" / "candidate_run_card.json").read_text())
    front = (DOCS / "index.html").read_text()
    assert f"downloads/{decision['submission']}" in front
    target = DOCS / "downloads" / decision["submission"]
    assert target.is_file()
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert digest == decision["sha256"] == card["file"]["sha256"]
    assert (ROOT / "submission" / decision["submission"]).read_bytes() == target.read_bytes()


def test_submission_note_fits_the_portal_limit():
    card = json.loads((ROOT / "evidence" / "candidate_run_card.json").read_text())
    assert 0 < len(card["submission_note"]) <= 140


def test_front_page_does_not_claim_to_beat_the_champion_when_it_does_not():
    """The estimate must stay visibly below 0.2778 unless a future run really beats it."""
    decision = json.loads((DOCS / "data" / "decision.json").read_text())
    front = (DOCS / "index.html").read_text()
    if decision["ledger_inversion_estimate"] < 0.2778:
        assert "below the 0.2778" in front
    assert decision["focus_champion_owner_reported"] == 0.2778


def test_nine_site_table_reports_each_focus_site_with_a_uniqueness_verdict():
    table = json.loads((ROOT / "evidence" / "nine_site_table.json").read_text())
    sites = {row["site"] for row in table["rows"]}
    assert sites == {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                     "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    for row in table["rows"]:
        assert row["unique_vs_focus_set"] is False, row["site"]
        assert 0.0 <= row["max_overlap_fraction"] <= 1.0


def test_pages_publishers_use_the_same_docs_url_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow
