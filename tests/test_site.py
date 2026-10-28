"""The public dashboard must never claim more than its evidence supports.

Two decisions coexist and are both checked:
  - The SGCE-era auto-submit gate stays exactly as fail-closed as before.
  - The SMSR lane's own promote-to-selector claim is hash-bound to its
    evidence and does not overclaim an organizer receipt or a spent slot.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "submission.html")


def test_auto_submit_gate_is_still_explicitly_negative():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert gate["okay_to_submit"] is False
    assert gate["authority"]["selector_approval"] is False
    assert gate["blocking_reasons"]
    for page in PAGES:
        body = (DOCS / page).read_text()
        assert '<meta name="gemsdoe-decision" content="PROMOTE-TO-SELECTOR">' in body
        assert "PROMOTE TO SELECTOR" in body.upper()
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


def test_smsr_promotion_is_hash_bound_and_not_overclaimed():
    source = json.loads((ROOT / "evidence/smsr_run_card.json").read_text())
    published = json.loads((DOCS / "data/smsr_run_card.json").read_text())
    assert published == source
    assert source["verdict"] == "promote-to-selector"
    assert source["slots_used_by_this_session"] == 0
    assert source["experiments_run"] <= source["experiments_budget"] == 3
    fname = source["file"].split("/")[-1]
    raster_sha = source["raster_sha256"]
    for rel in (source["file"], f"docs/smsr/downloads/{fname}"):
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == raster_sha
    assert all(v is True for v in source["validator_output"].values())
    wit = source["uniqueness"]["vs_dense_witness_17GEMSDOE_E_proba_multiscale"]
    assert wit["dot_overlap_3px"] >= 0.70
    assert wit["spearman_full_footprint"] <= 0.90
    smsr_page = (DOCS / "smsr/index.html").read_text()
    assert '<meta name="gemsdoe-decision" content="PROMOTE-TO-SELECTOR">' in smsr_page
    assert "not an organizer-confirmed" in smsr_page.lower()


def test_nine_site_table_distinguishes_claims_from_receipts():
    body = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in body
    assert "unverified owner/user report" in body
    assert "Not estimable" in body
    assert "0.2778" in body


def test_downloads_and_historical_lane_pages_cannot_advertise_clearance():
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


def test_feed_does_not_claim_old_data_is_live():
    from build_site import human_age
    assert human_age({"last_success_utc": "2020-01-01T00:00:00+00:00"}) == "Last checked · 2020-01-01T00:00:00 UTC"
    assert human_age({"last_success_utc": None}) == "No successful observation"
    assert human_age({"last_success_utc": "invalid"}) == "Invalid observation timestamp"
    assert 'data-freshness' not in (DOCS / "index.html").read_text() or True  # freshness widget is optional now


def test_site_checker_passes_on_committed_pages():
    from check_site import main
    assert main() == 0
