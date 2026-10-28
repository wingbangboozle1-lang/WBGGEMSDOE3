"""The public dashboard must never turn historical lane claims into approval."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "session-review.html", "submission.html")


def test_every_current_page_is_explicitly_negative():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert gate["okay_to_submit"] is False
    assert gate["authority"]["selector_approval"] is False
    assert gate["blocking_reasons"]
    for page in PAGES:
        body = (DOCS / page).read_text()
        assert '<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT">' in body
        assert "DO NOT SUBMIT" in body
        assert "OK TO DOWNLOAD AND SUBMIT" not in body
        assert "assets/status.js" in body


def test_witness_audit_and_research_file_are_hash_bound():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    sources = gate["source_cards"]
    for key in ("authority", "candidate", "witness_audit"):
        assert hashlib.sha256((ROOT / sources[key]).read_bytes()).hexdigest() == sources[key + "_sha256"]
    audit = json.loads((ROOT / sources["witness_audit"]).read_text())
    assert audit["witness"]["universal_blocker"] is True
    assert audit["witness"]["witness_positive_inside"] == audit["witness"]["footprint_cells"]
    assert audit["candidate"]["literal_duplicate"] is True
    assert audit["candidate"]["directed_overlap_within_3px_all_positive"] == 1.0
    assert audit["local_format_diagnostic"]["format_ok"] is True
    assert not audit["local_format_diagnostic"]["approved_for_submission"]
    for key in ("file", "published_file"):
        assert hashlib.sha256((ROOT / audit["candidate"][key]).read_bytes()).hexdigest() == audit["candidate"]["sha256"]


def test_nine_site_table_distinguishes_claims_from_receipts():
    body = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in body
    assert "unverified owner/user report" in body
    assert "Not estimable" in body
    assert "not a current full-registry audit" in body
    assert "0.2778" in body and "not evidence of score causality" in body


def test_downloads_and_lane_pages_cannot_advertise_clearance():
    for page in (DOCS / "downloads/index.html", DOCS / "rfl/index.html", DOCS / "thcs/index.html", DOCS / "session-1f0b051d/index.html"):
        text = page.read_text()
        assert "DO NOT SUBMIT" in text
        assert "OK TO DOWNLOAD AND SUBMIT" not in text
    assert "research" in (DOCS / "downloads/index.html").read_text().lower()
    assert "DO NOT SUBMIT" in (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text()


def test_pages_publishers_use_the_same_docs_url_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow


def test_latest_review_is_published_and_labeled_as_a_negative_preflight():
    page = (DOCS / "session-review.html").read_text()
    source = json.loads((ROOT / "evidence/session_review_2026-10-28.json").read_text())
    published = json.loads((DOCS / "data/session_review_2026-10-28.json").read_text())
    assert page.startswith("<!doctype html>")
    assert "Latest review" in page and "DO NOT SUBMIT" in page
    assert "No HOLDOUT-DTI value or confidence interval" in page
    assert "224 passed, 4 skipped, 72 warnings" in page
    assert published == source
    assert 'href="session-review.html"' in (DOCS / "index.html").read_text()


def test_feed_does_not_claim_old_data_is_live():
    from build_site import human_age
    assert human_age({"last_success_utc": "2020-01-01T00:00:00+00:00"}) == "Last checked · 2020-01-01T00:00:00 UTC"
    assert human_age({"last_success_utc": None}) == "No successful observation"
    assert human_age({"last_success_utc": "invalid"}) == "Invalid observation timestamp"
    assert 'data-freshness' in (DOCS / "index.html").read_text()


def test_site_checker_passes_on_committed_pages():
    from check_site import main
    assert main() == 0
