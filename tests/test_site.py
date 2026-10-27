"""Contract tests for the fail-closed public release dashboard."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from build_site import human_age
from gems_project.release_gate import evaluate_release_gate

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "research.html", "evidence.html")
AUTHORITY = json.loads((ROOT / "evidence" / "run_card.json").read_text())
CANDIDATE = json.loads((ROOT / "evidence" / "gemsdoe_run_card.json").read_text())
GATE = json.loads((ROOT / "evidence" / "release_gate.json").read_text())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_feed_render_is_deterministic_and_does_not_claim_a_stale_snapshot_is_fresh():
    feed = {"last_success_utc": "2020-01-01T00:00:00+00:00", "last_attempt_error": None}
    assert human_age(feed) == "Last checked · 2020-01-01T00:00:00 UTC"
    assert "Observed" not in human_age(feed)
    feed["last_attempt_error"] = "Timeout"
    assert human_age(feed).startswith("Latest refresh failed")
    assert human_age({"last_success_utc": None}) == "No successful observation"
    assert human_age({"last_success_utc": "invalid"}) == "Invalid observation timestamp"


def test_release_gate_is_reproducible_and_fail_closed():
    fresh = evaluate_release_gate(AUTHORITY, CANDIDATE)
    for key in ("schema", "decision", "okay_to_submit", "candidate", "authority", "blocking_reasons"):
        assert GATE[key] == fresh[key]
    assert GATE["decision"] == "DO-NOT-SUBMIT"
    assert GATE["okay_to_submit"] is False
    assert len(GATE["blocking_reasons"]) >= 4
    assert "PROXY-DTI" in " ".join(GATE["blocking_reasons"])


def test_every_page_carries_the_global_negative_decision():
    for name in PAGES:
        body = (DOCS / name).read_text()
        assert '<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT">' in body, name
        assert "DO NOT SUBMIT" in body, name
        assert "OK TO DOWNLOAD AND SUBMIT" not in body, name


def test_research_download_is_published_but_not_advertised_as_cleared():
    name = Path(CANDIDATE["download"]["tif"]).name
    served = DOCS / "downloads" / name
    assert served.exists()
    assert sha256(served) == CANDIDATE["sha256"] == sha256(ROOT / CANDIDATE["download"]["tif"])
    index = (DOCS / "index.html").read_text()
    assert f'href="downloads/{name}"' in index
    assert "NOT for upload" in index
    summary = (DOCS / "executive-summary.html").read_text()
    assert name in summary and "DO NOT SUBMIT" in summary


def test_executive_summary_covers_all_nine_focus_sites_and_uses_not_estimable():
    body = (DOCS / "executive-summary.html").read_text()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in body, site
    assert "WBGGEMSDOE3" in body
    assert body.count("DO NOT SUBMIT — already scored / not unique") == 9
    assert body.count("NOT ESTIMABLE") >= 10


def test_local_format_pass_is_not_presented_as_portal_or_organizer_acceptance():
    body = " ".join((DOCS / name).read_text() for name in PAGES).lower()
    assert "portal acceptance remains unverified" in body
    assert "not organizer scores" in body
    assert "proxy-dti" in body


def test_downloads_index_is_research_only():
    index = (DOCS / "downloads" / "index.html").read_text()
    notice = (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").read_text()
    assert "DO NOT SUBMIT" in index and "DO NOT SUBMIT" in notice
    assert "Cleared file" not in index
    assert Path(CANDIDATE["download"]["tif"]).name in index


def test_pages_workflow_publishes_the_docs_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow
    assert "build_executive.py" in workflow


def test_parallel_lane_pages_do_not_override_global_release_gate():
    cspes = DOCS / "cspes"
    assert (cspes / "index.html").exists()
    assert "Not cleared for upload" in (cspes / "index.html").read_text()
    assert json.loads((cspes / "data" / "cspes_run_card.json").read_text())["verdict"] == "negative"

    hce = DOCS / "hce"
    for page in hce.glob("*.html"):
        assert "Global release gate: DO NOT SUBMIT" in page.read_text(), page.name

    readme = (ROOT / "README.md").read_text()
    assert "CURRENT DECISION: DO NOT SUBMIT" in readme
    assert "CSPES" in readme and "HCE-1" in readme
