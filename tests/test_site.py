"""Current repository-wide publication is fail-closed and evidence-bound."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
DOCS = ROOT / "docs"
CURRENT_CARD = ROOT / "evidence/session_c1e656ce_run_card.json"
AUTHORITY = ROOT / "evidence/session_9b794637_run_card.json"
CANDIDATE = ROOT / "evidence/session2_run_card.json"
WITNESS = ROOT / "evidence/session_c1e656ce_witness_recheck.json"
CURRENT_PAGES = (
    "index.html", "executive-summary.html", "how-to-submit.html", "research.html",
    "method.html", "evidence.html", "session-review.html", "submission.html",
    "downloads/index.html",
)


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_release_gate_is_negative_and_hash_bound():
    from gems_project.release_gate import evaluate_release_gate

    gate = _json("docs/data/release_gate.json")
    expected = evaluate_release_gate(_json("evidence/session_9b794637_run_card.json"),
                                    _json("evidence/session2_run_card.json"))
    assert gate["schema"] == "gems-release-gate-v1"
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert gate["okay_to_submit"] is False
    assert gate["candidate"] == expected["candidate"]
    assert gate["authority"] == expected["authority"]
    assert set(expected["blocking_reasons"]).issubset(set(gate["blocking_reasons"]))
    assert gate["okay_to_download_for_research"] is True
    for kind in ("authority", "candidate", "witness_audit"):
        source = ROOT / gate["source_cards"][kind]
        assert _sha(source) == gate["source_cards"][f"{kind}_sha256"]
    decision = _json("docs/data/decision.json")
    assert decision == {
        "decision": "DO-NOT-SUBMIT",
        "okay_to_submit": False,
        "candidate": None,
        "source": "release_gate.json",
    }
    assert (DOCS / "data/run_card.json").read_bytes() == AUTHORITY.read_bytes()


def test_current_review_card_records_null_candidate_and_no_holdout():
    card = json.loads(CURRENT_CARD.read_text(encoding="utf-8"))
    assert card["branch"] == "arena/c1e656ce-wbggemsdoe3"
    assert card["verdict"] == "negative"
    assert card["hypothesis"] and card["mechanism"] and card["named_non_fault_process"]
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["status"] == "NOT RUN"
    assert card["holdout_dti"]["evaluator_version"] is None
    assert card["holdout_dti"]["withheld_positives"] is None
    assert card["holdout_dti"]["value"] is None and card["holdout_dti"]["ci95"] is None
    assert card["registry_comparison"]["new_candidate_tested"] is False
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap_within_3px"] is None
    witness = card["registry_comparison"]["witness_measurement"]
    assert witness["evidence_class"].startswith("SAVED MIRRORED RASTER")
    assert witness["witness_positive_inside"] == witness["footprint_cells"]
    assert witness["conditional_directed_overlap_for_any_nonempty_in-footprint_candidate"] == 1.0
    assert card["raster_sha256"] is None
    assert card["validator_output"]["new_raster_generated"] is False
    assert card["validator_output"]["status"].startswith("NOT RUN")
    assert card["submission_name"] is None
    assert len(card["submission_note"]) <= 140
    assert card["selector_approval"] is False and card["weekly_slots_used"] == 0
    assert card["experiments_run"] == 0
    assert len(card["review_passes"]) == 3


def test_saved_witness_audit_is_conditional_and_negative():
    audit = json.loads(WITNESS.read_text(encoding="utf-8"))
    w, c = audit["witness"], audit["candidate"]
    assert audit["verdict"] == "negative"
    assert audit["approved_for_submission"] is False
    assert w["registered"] is True and w["universal_blocker"] is True
    assert w["witness_positive_inside"] == w["footprint_cells"]
    assert c["sha256"] == _sha(DOCS / "downloads" / c["file"].split("/")[-1])
    assert c["directed_overlap_within_3px_all_positive"] == 1.0
    assert "owner mirror" in audit["sample"]["provenance"]


def test_every_current_page_carries_the_negative_decision():
    for rel in CURRENT_PAGES:
        body = (DOCS / rel).read_text(encoding="utf-8")
        assert '<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT">' in body, rel
        folded = " ".join(body.lower().split())
        assert "do not submit" in folded or "no file is cleared" in folded, rel
        for phrase in (
            "ok to download and submit", "one file cleared for upload",
            "the only file cleared for upload",
        ):
            assert phrase not in folded, (rel, phrase)


def test_nine_site_table_uses_owner_reports_and_not_estimable_scores():
    body = (DOCS / "executive-summary.html").read_text(encoding="utf-8")
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in body
    assert "OWNER-REPORTED" in body
    assert "0.2778" in body
    assert "Not estimable" in body
    assert "DO NOT SUBMIT" in body
    assert "0.3047" not in body
    assert "0.2948" not in body


def test_gemsdoe32_explanation_stays_cautious_and_evidence_classed():
    body = (DOCS / "method.html").read_text(encoding="utf-8").lower()
    assert "owner-reported 0.2778" in body
    assert "2,545" in body
    assert "not established" in body or "cannot establish" in body
    assert "pair_identification.json" in body
    assert "hidden labels" in body


def test_ranked_hypotheses_are_explicitly_untested_and_qualitative():
    body = (DOCS / "research.html").read_text(encoding="utf-8")
    for phrase in ("Depth-consistent oblique", "Scale-conditioned magnetic", "Drainage-independent",
                   "Radiometric mixture-boundary", "Relative upside", "Cost:", "Named non-fault mimic"):
        assert phrase.lower() in body.lower(), phrase
    assert "No model experiment ran" in body
    assert "not verified" in body.lower()
    assert "geothermal vents" in body.lower()


def test_stale_machine_readable_approval_claims_are_quarantined():
    khd = _json("docs/data/khd_release.json")
    assert khd["decision"] == "DO-NOT-SUBMIT"
    assert khd["okay_to_submit"] is False
    assert "superseded publisher" in khd["archive_notice"]
    for name in ("candidate_run_card.json", "session2_run_card.json"):
        archived = _json(f"docs/data/{name}")
        assert archived["current_repository_decision"] == "DO-NOT-SUBMIT"
        assert archived["_archive_notice"]


def test_downloads_and_plain_text_notice_are_research_only():
    page = (DOCS / "downloads/index.html").read_text(encoding="utf-8")
    notice = (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text(encoding="utf-8")
    tifs = {p.name for p in (DOCS / "downloads").glob("*.tif")}
    assert tifs
    assert "DO NOT SUBMIT" in page
    assert "RESEARCH ONLY" in page
    assert "No TIFF in this directory is cleared" in notice
    for name in tifs:
        assert name in page and name in notice
    assert "CLEARED FOR SUBMISSION" not in notice


def test_all_site_wide_metadata_is_negative_and_site_checker_passes():
    from check_site import main

    assert main() == 0
    for page in DOCS.rglob("*.html"):
        body = page.read_text(encoding="utf-8")
        if 'name="gemsdoe-decision"' in body:
            assert 'name="gemsdoe-decision" content="DO-NOT-SUBMIT"' in body, page
        if 'name="gemsdoe-lane-decision"' in body:
            assert 'name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"' in body, page


def test_retired_positive_publishers_fail_without_mutating_pages():
    paths = ("build_site_v3.py", "build_release_gate_v2.py", "build_evidence_page.py",
             "build_dossier.py", "build_site_khd.py")
    protected = (DOCS / "index.html", DOCS / "data/release_gate.json", DOCS / "data/decision.json")
    before = {path: path.read_bytes() for path in protected}
    for name in paths:
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT,
                              capture_output=True, text=True, timeout=15)
        assert proc.returncode != 0, name
        assert "BLOCKED" in proc.stderr, (name, proc.stderr)
    assert {path: path.read_bytes() for path in protected} == before


def test_fail_closed_builder_is_deterministic():
    from build_site import main

    names = (*CURRENT_PAGES, "data/release_gate.json", "data/decision.json", "data/run_card.json",
             "data/pair_identification.json", "data/session_c1e656ce_run_card.json",
             "data/candidate_run_card.json", "data/session2_run_card.json", "data/khd_release.json",
             "data/ARCHIVE-NOT-SUBMIT.txt", "downloads/LEGACY-DO-NOT-SUBMIT.txt",
             "amdc/index.html", "fchd/index.html")
    before = {name: (DOCS / name).read_bytes() for name in names}
    assert main() == 0
    for name in names:
        assert (DOCS / name).read_bytes() == before[name], name
