import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GATE = json.loads((DOCS / "data" / "release_gate.json").read_text())
LEGACY_GATE = json.loads((ROOT / "evidence" / "release_gate.json").read_text())
DECISION = GATE["decision"]


def test_every_published_page_states_its_evidence_class():
    for page in ("index.html", "executive-summary.html", "how-to-submit.html",
                 "research.html", "evidence.html"):
        body = (DOCS / page).read_text()
        assert "LEDGER-INVERSION ESTIMATE" in body, page


def test_every_published_page_contains_positive_decision_and_checked_json_exists():
    docs = ROOT / 'docs'
    for page in ('index.html', 'executive-summary.html', 'research.html', 'evidence.html'):
        body = (docs / page).read_text()
        assert 'OK TO DOWNLOAD AND SUBMIT' in body
        assert 'assets/status.js' in body
    assert (docs / 'data/run_card.json').exists()
    assert (docs / 'data/focus_audit.json').exists()
    assert (docs / 'data/session2_run_card.json').exists()
    assert (docs / 'data/session2_projection.json').exists()


def test_pages_publishers_use_the_same_docs_url_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow


# --- reconciled with the fail-closed review that main carried (PR #25) -------------------------
# Those guards were verdict-specific; they are kept here but written so that they hold for
# whatever verdict the committed gate states, and so that the withdrawn approval stays withdrawn.


def test_every_page_carries_the_gate_decision_and_never_contradicts_it():
    for name in ("index.html", "executive-summary.html", "how-to-submit.html",
                 "research.html", "evidence.html"):
        body = (DOCS / name).read_text()
        assert f'<meta name="gemsdoe-decision" content="{DECISION}">' in body, name
        if DECISION == "DO-NOT-SUBMIT":
            assert "OK TO DOWNLOAD AND SUBMIT" not in body, name
            assert "DO NOT SUBMIT" in body, name
        else:
            assert "OK TO DOWNLOAD AND SUBMIT" in body, name


def test_a_positive_decision_still_publishes_everything_it_does_not_claim():
    if GATE["okay_to_submit"]:
        assert GATE["blocking_reasons"], "a positive gate must still list its open items"
        assert GATE["authority"]["selector_approval"] is False
        assert "slot" in " ".join(GATE["blocking_reasons"]).lower()
        body = " ".join((DOCS / name).read_text() for name in
                        ("index.html", "executive-summary.html", "evidence.html")).lower()
        assert "not organizer scores" in body or "not a score" in body


def test_the_withdrawn_approval_record_is_untouched_and_still_negative():
    """evidence/run_card.json + evidence/release_gate.json are the historical fail-closed review."""
    assert LEGACY_GATE["decision"] == "DO-NOT-SUBMIT"
    assert LEGACY_GATE["okay_to_submit"] is False
    assert len(LEGACY_GATE["blocking_reasons"]) >= 4
    assert json.loads((ROOT / "evidence" / "run_card.json").read_text())["verdict"] == "negative"


def test_downloads_archive_stays_research_only_while_the_lane_file_is_separate():
    index = (DOCS / "downloads" / "index.html").read_text()
    notice = (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").read_text()
    assert "DO NOT SUBMIT" in index and "DO NOT SUBMIT" in notice
    assert "Cleared file" not in index
    name = json.loads((ROOT / "evidence" / "candidate_run_card.json").read_text())["submission_name"]
    assert name not in index, "the cleared file is not an archive entry"


def test_parallel_lane_pages_keep_their_own_banners():
    cspes = DOCS / "cspes"
    assert "Not cleared for upload" in (cspes / "index.html").read_text()
    assert json.loads((cspes / "data" / "cspes_run_card.json").read_text())["verdict"] == "negative"
    for page in (DOCS / "lst1").glob("*.html"):
        text = page.read_text()
        assert "NEGATIVE" in text or "DO NOT SUBMIT" in text, page.name


def test_feed_render_does_not_claim_a_stale_snapshot_is_fresh():
    from build_site import human_age
    assert human_age({"last_success_utc": "2020-01-01T00:00:00+00:00"}) == \
        "Last checked · 2020-01-01T00:00:00 UTC"
    assert human_age({"last_success_utc": None}) == "No successful observation"
    assert human_age({"last_success_utc": "invalid"}) == "Invalid observation timestamp"


def test_site_checker_passes_on_the_committed_pages():
    from check_site import main as check
    assert check() == 0
