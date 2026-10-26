from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Hrefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "href" and value:
                self.hrefs.append(value)


def test_all_static_site_internal_links_resolve():
    missing: list[str] = []
    for html in DOCS.rglob("*.html"):
        parser = Hrefs()
        parser.feed(html.read_text(encoding="utf-8"))
        for href in parser.hrefs:
            parsed = urlparse(href)
            if parsed.scheme or parsed.netloc or href.startswith("#"):
                continue
            target = (html.parent / parsed.path).resolve()
            try:
                target.relative_to(DOCS.resolve())
            except ValueError:
                missing.append(f"{html.relative_to(DOCS)} -> {href} (outside published docs tree)")
                continue
            if not target.exists():
                missing.append(f"{html.relative_to(DOCS)} -> {href}")
    assert not missing, "Broken local links:\n" + "\n".join(missing)


def test_landing_page_exposes_fail_closed_download_decision():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "NOT READY — DO NOT SUBMIT" in html
    assert "Candidate TIFF — unavailable" in html
    assert "aria-disabled=\"true\"" in html


def test_focus_audit_keeps_score_provenance_and_uniqueness_limits_explicit():
    audit = json.loads((DOCS / "data/focus-site-audit.json").read_text(encoding="utf-8"))
    assert len(audit["sites"]) == 9
    assert all(row["score_label"].startswith("OWNER-REPORTED") for row in audit["sites"])
    assert all(row["competition_score_receipt_present"] is False for row in audit["sites"])
    assert audit["uniqueness_rule"]["all_9_focus_winners_unique_against_each_other"] is False
    assert audit["uniqueness_rule"]["minimum_pairwise_directed_fraction"] > 0.70
    assert audit["uniqueness_rule"]["preplacement_surface_rank_correlation"].startswith("NOT MEASURED")


def test_current_run_card_is_negative_and_does_not_offer_a_file():
    card = json.loads((DOCS / "data/run-card.json").read_text(encoding="utf-8"))
    assert card["verdict"] == "negative"
    assert card["raster_sha256"] is None
    assert card["submission"]["download_link"] is None
    assert card["submission"]["status"] == "NO FILE — DO NOT DOWNLOAD OR SUBMIT"
    assert card["holdout_dti"]["status"] == "NOT RUN"
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["budget"]["candidate_experiments_used"] == 0
    assert card["budget"]["maximum_candidate_experiments"] == 3


def test_public_repository_feed_does_not_claim_scores():
    feed = json.loads((DOCS / "data/focus-repo-feed.json").read_text(encoding="utf-8"))
    assert feed["repositories_checked"] == 9
    assert len(feed["items"]) == 9
    assert feed["score_values_added"] is False
    assert feed["official_leaderboard"]["status"] == "not checked"
    assert "not an official competition score feed" in feed["feed_type"]
