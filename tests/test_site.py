"""The published site must consistently honor the literal negative release decision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "method.html", "evidence.html")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_release_gate_is_negative_and_hash_bound():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    decision = json.loads((DOCS / "data/decision.json").read_text())
    assert gate["schema"] == "gems-release-gate-v1"
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert gate["okay_to_submit"] is False
    assert gate["okay_to_download_for_research"] is True
    assert gate["authority"]["verdict"] == "negative"
    assert gate["authority"]["selector_approval"] is False
    assert gate["candidate"]["lane_verdict"] == "negative"
    assert gate["candidate"]["literal_registry_pass"] is False
    assert gate["blocking_reasons"]
    assert decision == {
        "decision": "DO-NOT-SUBMIT", "okay_to_submit": False,
        "candidate": None, "source": "release_gate.json",
    }
    for key in ("authority", "candidate", "witness_audit"):
        source = gate["source_cards"][key]
        assert _sha(ROOT / source) == gate["source_cards"][key + "_sha256"]


def test_witness_is_registered_and_universal_on_the_mirrored_footprint():
    witness = json.loads((ROOT / "evidence/registry_witness_recheck_2026-10-27.json").read_text())
    w = witness["witness"]
    assert w["registered"] is True
    assert w["universal_blocker"] is True
    assert w["witness_positive_inside"] == w["footprint_cells"] == 5_167_373
    assert witness["approved_for_submission"] is False
    assert witness["verdict"] == "negative"


def test_all_current_pages_are_negative_and_not_submission_ctas():
    for name in PAGES:
        body = (DOCS / name).read_text()
        assert '<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT">' in body
        assert "DO NOT SUBMIT" in body
        lower = body.lower()
        assert "submit this file" not in lower
        assert "the portal should accept" not in lower
    assert "no file is currently cleared" in (DOCS / "submission.html").read_text().lower()


def test_nine_site_table_is_present_and_not_fabricating_new_estimates():
    body = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in body
    assert "OWNER-REPORTED" in body
    assert "0.2778" in body
    assert "not estimable" in body.lower()
    assert "DO NOT SUBMIT" in body
    for tif in ("wbggems3-invdesign-anchor-20k-zeros.tif",):
        assert tif not in body


def test_downloads_are_research_only_and_sites_label_their_role():
    notice = (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text()
    index = (DOCS / "downloads/index.html").read_text().lower()
    assert "DO NOT SUBMIT" in notice
    assert "CLEARED FOR SUBMISSION" not in notice
    assert "research" in index and "do not submit" in index
    assert "prior research file" in (DOCS / "how-to-submit.html").read_text()
    home = (DOCS / "index.html").read_text()
    assert "PRIOR PARALLEL-LANE RESEARCH ARTIFACT" in home
    assert "not authorized for submission" in home


def test_candidate_queue_has_four_hypotheses_and_explicit_blocker():
    review = (ROOT / "knowledge/repo-review-followup-2026-10-28.md").read_text()
    page = (DOCS / "research.html").read_text()
    assert review.count("| 1 |") == 1
    for label in ("Replicated cross-catchment offsets", "Radiometric mixing-manifold residual",
                  "Cross-height edge trajectory", "Strain–potential-field phase coherence"):
        assert label in review
    assert "all blocked" in page.lower()
    assert "3DEP" in page and "GeoDAWN" in page


def test_retired_positive_builders_fail_without_mutating_published_gate():
    gate = DOCS / "data/release_gate.json"
    before = gate.read_bytes()
    for name in ("build_site_v3.py", "build_release_gate_v2.py", "build_evidence_page.py", "build_session_site.py"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / name)],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 2, (name, result.stdout, result.stderr)
        assert "BLOCKED" in result.stderr
        assert gate.read_bytes() == before


def test_site_checker_passes_on_committed_pages():
    from check_site import main
    assert main() == 0


def test_pages_publisher_uses_the_negative_builder():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    assert "scripts/build_site.py && python scripts/check_site.py" in workflow
    assert "url=docs/index.html" in (ROOT / "index.html").read_text()
