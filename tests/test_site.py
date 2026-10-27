"""Site contract tests.

The site must (a) show one unambiguous decision, (b) only offer a download that the
run card cleared and whose bytes match the recorded hash, and (c) never present a
model estimate as an organizer score.
"""
import hashlib
import json
import re
from pathlib import Path

from build_site import human_age

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "research.html", "evidence.html")
CARD = json.loads((ROOT / "evidence" / "gemsdoe_run_card.json").read_text())


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


def test_every_page_carries_the_same_decision_as_the_run_card():
    verdict = CARD["verdict"]
    assert verdict in {"promote", "negative"}
    expected = "SUBMIT" if verdict == "promote" else "DO-NOT-SUBMIT"
    for name in PAGES:
        body = (DOCS / name).read_text()
        assert f'<meta name="gemsdoe-decision" content="{expected}">' in body, name


def test_cleared_download_is_published_and_byte_identical():
    assert CARD["verdict"] == "negative"
    name = Path(CARD["download"]["tif"]).name
    served = DOCS / "downloads" / name
    assert served.exists()
    assert sha256(served) == CARD["sha256"] == sha256(ROOT / CARD["download"]["tif"])
    for page in ("index.html", "executive-summary.html"):
        assert f'href="downloads/{name}"' in (DOCS / page).read_text(), page


def test_executive_summary_covers_all_nine_focus_sites_and_our_file():
    body = (DOCS / "executive-summary.html").read_text()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in body, site
    assert "WBGGEMSDOE3" in body
    # each historical veto must be visible, not just implied
    assert body.count("NO — already scored") == 9


def test_estimates_are_never_presented_as_scores():
    body = " ".join((DOCS / name).read_text() for name in PAGES)
    # no sentence may attach the word score directly to our estimate
    assert not re.search(r"(our|this) (file|submission)[^.]{0,40}score[sd]? (of |is )?0\\.4", body, re.I)
    assert "not an organizer" in body.lower() or "not an organizer score" in body.lower()
    assert "ESTIMATE" in body


def test_legacy_rasters_are_labelled_and_never_offered_as_cleared():
    dl = DOCS / "downloads"
    notice = dl / "LEGACY-DO-NOT-SUBMIT.txt"
    assert notice.exists() and "DO NOT SUBMIT" in notice.read_text()
    index = (dl / "index.html").read_text()
    cleared = Path(CARD["download"]["tif"]).name
    # the cleared file is the first download link; every other raster is named under the veto heading
    assert index.index(cleared) < index.index("Research only")
    legacy = sorted(p.name for p in dl.glob("wb-gems-doe-3-*.tif"))
    assert legacy, "expected legacy rasters to still be present"
    for name in legacy:
        assert "wb-gems-doe-3-" in index and name not in index.split("Research only")[0]
    linked = [line for line in index.splitlines() if "<a href" in line]
    for line in linked:
        for name in legacy:
            assert name not in line, f"legacy raster linked as a download: {line}"


def test_pages_workflow_publishes_the_docs_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow
    assert "build_executive.py" in workflow


def test_parallel_cspes_lane_keeps_its_own_negative_verdict():
    """Two lanes, two decisions: this repo clears the skarpline file only."""
    lane = DOCS / "cspes"
    assert (lane / "index.html").exists()
    text = (lane / "index.html").read_text()
    assert "Not cleared for upload" in text or "NOT OK TO SUBMIT" in text
    card = json.loads((lane / "data" / "cspes_run_card.json").read_text())
    assert card["verdict"] == "negative"
    readme = (ROOT / "README.md").read_text()
    assert "CSPES lane" in readme and "negative" in readme.lower()
    assert "CURRENT DECISION: DO NOT SUBMIT" in readme
    assert "conflict" in readme.lower()


def test_downloads_index_separates_the_two_lanes():
    index = (DOCS / "downloads" / "index.html").read_text()
    cleared = Path(CARD["download"]["tif"]).name
    assert index.index(cleared) < index.index("Research only")
    assert "wbggems3-cspes-" in index
    # the CSPES file is named under a veto heading, never as the cleared download
    assert index.index("wbggems3-cspes-") > index.index("Research only")


def test_promotion_requires_all_explicit_boolean_gates():
    from build_executive import approval_errors
    assert approval_errors({"verdict": "promote"})
    gates = {key: True for key in approval_errors({})}
    assert not approval_errors({"promotion_gates": gates})
    for key in gates:
        for bad in (False, None, "true", 1):
            changed = dict(gates, **{key: bad})
            assert key in approval_errors({"promotion_gates": changed})


def test_negative_pages_never_invite_upload():
    for name in PAGES:
        text = (DOCS / name).read_text()
        assert "DO NOT SUBMIT" in text
        assert "OK TO DOWNLOAD AND SUBMIT" not in text
        assert "Estimated leaderboard DTI" not in text
    assert CARD["promotion_gates"]["literal_registry_final_dots"] is False
