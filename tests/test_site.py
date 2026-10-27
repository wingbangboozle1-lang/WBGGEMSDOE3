"""Site contract tests (reconciled 2026-10-27, LBCAL session).

The site must (a) show one unambiguous decision that equals evidence/decision.json,
(b) never offer a download as cleared unless the decision card is `promote`, and
(c) never present a model estimate as an organizer score.
"""
import hashlib
import json
import re
from pathlib import Path

from build_site import human_age

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "sources.html")
CARD = json.loads((ROOT / "evidence" / "decision.json").read_text())
FOCUS = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")


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


def test_site_card_is_the_repository_decision_card():
    assert json.loads((DOCS / "data" / "run_card.json").read_text()) == CARD
    assert CARD["verdict"] in {"promote", "negative"}


def test_every_page_carries_the_same_decision_as_the_card():
    expected = "SUBMIT" if CARD["verdict"] == "promote" else "DO-NOT-SUBMIT"
    for name in PAGES:
        body = (DOCS / name).read_text()
        assert f'<meta name="gemsdoe-decision" content="{expected}">' in body, name


def test_negative_decision_offers_nothing_as_cleared_and_labels_the_artifact():
    if CARD["verdict"] == "promote":
        return
    assert CARD["ok_to_submit"] is False and CARD["download"]["cleared"] is False
    idx = (DOCS / "index.html").read_text()
    assert "NOT OK TO SUBMIT" in idx and "OK TO DOWNLOAD AND SUBMIT" not in idx
    name = Path(CARD["download"]["tif"]).name
    assert "DO-NOT-SUBMIT" in name
    served = DOCS / "downloads" / name
    assert sha256(served) == CARD["sha256"] == sha256(ROOT / CARD["download"]["tif"])
    dl = (DOCS / "downloads" / "index.html").read_text()
    assert "Cleared file: none" in dl
    assert dl.index("Cleared file: none") < dl.index("Research only")


def test_executive_summary_covers_all_nine_focus_sites_and_our_files():
    body = (DOCS / "executive-summary.html").read_text()
    for site in FOCUS:
        assert site in body, site
    assert body.count("NO — already scored") == 9
    assert "skarpline-union" in body and "lbcal" in body
    focus = json.loads((ROOT / "evidence" / "focus_sites_2026-10-27.json").read_text())
    assert [s["site"] for s in focus["sites"]] == list(FOCUS)
    assert all(s["lbcal_family_cv_estimate"] is not None for s in focus["sites"])
    assert all(not s["unique_vs_other_focus_sites"] for s in focus["sites"])


def test_estimates_are_never_presented_as_scores():
    body = " ".join((DOCS / name).read_text() for name in PAGES)
    assert not re.search(r"(our|this) (file|submission)[^.]{0,40}score[sd]? (of |is )?0\.[45]", body, re.I)
    assert "not an organizer score" in body.lower()
    assert "ESTIMATE" in body


def test_legacy_rasters_are_never_linked_as_downloads():
    dl = DOCS / "downloads"
    notice = dl / "LEGACY-DO-NOT-SUBMIT.txt"
    assert notice.exists() and "DO NOT SUBMIT" in notice.read_text()
    index = (dl / "index.html").read_text()
    legacy = sorted(p.name for p in dl.glob("wb-gems-doe-3-*.tif"))
    assert legacy
    for line in (ln for ln in index.splitlines() if "<a href" in ln):
        for name in legacy:
            assert f'href="{name}"' not in line, f"legacy raster linked as a download: {line}"


def test_pages_workflow_publishes_the_docs_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    root_redirect = (ROOT / "index.html").read_text()
    assert "url=docs/index.html" in root_redirect
    assert "cp -a docs .cache/pages-release/docs" in workflow
    assert "path: .cache/pages-release" in workflow
    assert "build_executive.py" in workflow


def test_parallel_lanes_keep_their_own_verdicts_and_carry_the_repo_decision():
    lane = DOCS / "cspes"
    text = (lane / "index.html").read_text()
    assert "Not cleared for upload" in text or "NOT OK TO SUBMIT" in text
    assert json.loads((lane / "data" / "cspes_run_card.json").read_text())["verdict"] == "negative"
    for sub in ("hce", "cspes", "lst1"):
        assert "REPO-DECISION:START" in (DOCS / sub / "index.html").read_text(), sub


def test_readme_and_cards_agree_on_one_decision():
    readme = (ROOT / "README.md").read_text()
    word = "SUBMIT" if CARD["verdict"] == "promote" else "DO NOT SUBMIT"
    assert f"CURRENT DECISION: {word}." in readme
    assert "CURRENT DECISION: SUBMIT." not in readme or CARD["verdict"] == "promote"
    assert "CSPES lane" in readme and "negative" in readme.lower()
    g = json.loads((ROOT / "evidence" / "gemsdoe_run_card.json").read_text())
    assert g["verdict"] == "negative" and g["verdict_history"][-1]["from_verdict"] == "promote"
    lb = json.loads((ROOT / "evidence" / "lbcal_run_card.json").read_text())
    assert lb["verdict"] == CARD["verdict"] == "negative"
    assert len(lb["note"]) <= 140 and len(lb["submission_name"]) <= 140
