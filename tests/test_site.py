"""The public dashboard must never turn historical lane claims into approval.

Since 2026-10-28 the repository decision can be either:
* ``SUBMIT`` (schema v2) — the LBCAL-K candidate passed the preregistered
  content-aware gates; clearance is hash-bound to the saved bytes and must
  carry every disclosure (IR-01, IR-11, ESTIMATE labelling, untouched slots), or
* ``DO-NOT-SUBMIT`` (schema v1) — the historical literal-registry negative.

In BOTH modes historical research TIFFs and lane pages must stay DO NOT SUBMIT.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "submission.html")
CLEARANCE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "submission.html")


def test_published_gate_is_verified_and_internally_consistent():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    decision = json.loads((DOCS / "data/decision.json").read_text())
    if gate["schema"] == "gems-release-gate-v2":
        assert gate["decision"] == "SUBMIT"
        assert gate["okay_to_download_and_submit"] is True
        assert not gate["blocking_reasons"]
        slot = gate["selector_slot_spend"]
        assert slot["authorized"] is False and slot["slots_used"] == 0
        sources = gate["source_cards"]
        for key in ("authority", "preregistration", "focus_overlap", "irregularities",
                    "witness_audit", "historical_negative_authority"):
            assert hashlib.sha256((ROOT / sources[key]).read_bytes()).hexdigest() == sources[key + "_sha256"], key
        # re-run the gate evaluator against the published authority
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from gems_project.release_gate_v2 import evaluate_release_gate_v2
        card = json.loads((ROOT / sources["authority"]).read_text())
        v2 = evaluate_release_gate_v2(card, ROOT, prereg_path=ROOT / sources["preregistration"])
        assert v2["decision"] == "SUBMIT" and v2["blocking_reasons"] == []
        # bytes: workspace + published copies
        tif = ROOT / card["raster"]["path"]
        assert hashlib.sha256(tif.read_bytes()).hexdigest() == gate["candidate"]["sha256"] == card["raster"]["sha256"]
        assert hashlib.sha256((DOCS / "downloads" / tif.name).read_bytes()).hexdigest() == gate["candidate"]["sha256"]
        assert decision == {"decision": "SUBMIT", "okay_to_download_and_submit": True, "okay_to_submit": True,
                            "candidate": gate["candidate"], "selector_slot_spend": gate["selector_slot_spend"],
                            "source": "release_gate.json"}
        assert "IR-01" in gate["historical_record"]
    else:
        assert gate["schema"] == "gems-release-gate-v1"
        assert gate["decision"] == "DO-NOT-SUBMIT"
        assert gate["okay_to_submit"] is False
        assert gate["authority"]["selector_approval"] is False
        assert gate["blocking_reasons"]
        assert decision["decision"] == "DO-NOT-SUBMIT" and decision["okay_to_submit"] is False
        sources = gate["source_cards"]
        for key in ("authority", "candidate", "witness_audit"):
            assert hashlib.sha256((ROOT / sources[key]).read_bytes()).hexdigest() == sources[key + "_sha256"], key


def test_clearance_pages_carry_file_hash_and_all_disclosures():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    if gate["schema"] != "gems-release-gate-v2":
        return  # negative mode: clearance pages must not exist
    sha = gate["candidate"]["sha256"]
    name = gate["candidate"]["submission"]
    for page in CLEARANCE_PAGES:
        body = (DOCS / page).read_text()
        folded = " ".join(body.lower().split())
        assert '<meta name="gemsdoe-decision" content="SUBMIT">' in body, page
        assert "assets/status.js" in body, page
        assert "ok to download and submit" in folded, page
        assert sha in body, page
        assert "ir-01" in folded, page
        assert "estimates are estimates" in folded, page
        assert "context only" in folded, page
        assert "do not submit" in folded, page  # historical TIFFs stay negative
        assert "organizer-confirmed" in folded, page  # labelled what it is not
        if page in ("index.html", "submission.html"):
            assert name in body, page
    # E2 cross-model disagreement must be disclosed on every clearance page
    e2 = json.loads((DOCS / "data" / "lbcal_k_run_card_e2.json").read_text())
    assert e2["verdict"] == "negative"  # the disagreement record exists
    for page in CLEARANCE_PAGES:
        folded = " ".join((DOCS / page).read_text().lower().split())
        assert "cross-model" in folded or "second opinion" in folded, page
        assert "0.195" in folded, page
    for page in PAGES:
        body = (DOCS / page).read_text()
        assert "DO NOT SUBMIT" in body, page  # lane/historical quarantine visible everywhere


def test_witness_audit_and_research_file_are_hash_bound():
    audit = json.loads((ROOT / "evidence/registry_witness_recheck_2026-10-27.json").read_text())
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
    assert "0.2778" in body
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    if gate["schema"] == "gems-release-gate-v2":
        assert "ESTIMATE" in body
        assert gate["candidate"]["submission"] in body
        assert "OK TO DOWNLOAD AND SUBMIT" in body
        assert "research only" in body  # historical claims still labelled
    else:
        assert "Not estimable" in body
        assert "not a current full-registry audit" in body
        assert "OK TO DOWNLOAD AND SUBMIT" not in body


def test_downloads_and_lane_pages_cannot_advertise_clearance_for_history():
    lane_pages = (DOCS / "rfl/index.html", DOCS / "thcs/index.html", DOCS / "session-1f0b051d/index.html",
                  DOCS / "lbcal/index.html", DOCS / "fchd/index.html", DOCS / "amdc/index.html")
    for page in lane_pages:
        text = page.read_text()
        assert "DO NOT SUBMIT" in text
        assert "OK TO DOWNLOAD AND SUBMIT" not in text
    downloads = (DOCS / "downloads/index.html").read_text()
    assert "DO NOT SUBMIT" in downloads  # historical archives stay negative
    assert "research" in downloads.lower()
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    if gate["schema"] == "gems-release-gate-v2":
        assert gate["candidate"]["sha256"] in downloads  # primary download is hash-bound
        assert "OK TO DOWNLOAD AND SUBMIT" in downloads
    else:
        assert "OK TO DOWNLOAD AND SUBMIT" not in downloads
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
    assert 'data-freshness' in (DOCS / "index.html").read_text()


def test_site_checker_passes_on_committed_pages():
    from check_site import main
    assert main() == 0
