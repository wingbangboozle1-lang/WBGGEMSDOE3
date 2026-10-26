from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import json

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for attr in ("href", "src"):
            if attr in attrs:
                self.paths.append(attrs[attr])


def test_internal_site_links_resolve():
    for page in [ROOT / "index.html", ROOT / "docs/executive-summary.html", ROOT / "docs/research.html"]:
        parser = Links()
        parser.feed(page.read_text())
        for link in parser.paths:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path or link.startswith("#"):
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.exists(), (page, link)


def test_status_and_scope_are_fail_closed():
    card = json.loads((ROOT / "evidence/run-card.json").read_text())
    audit = json.loads((ROOT / "evidence/priority-audit.json").read_text())
    assert card["verdict"] == "negative" and not card["ok_to_submit"]
    assert card["raster_sha256"] is None and card["holdout_dti"]["value"] is None
    assert audit["witness"]["minimum_overlap_at_historical_budget"] > 0.70
    assert audit["rasters"]["27candidate"]["overlap_lattice_within_3px"] > 0.99
    home = (ROOT / "index.html").read_text()
    summary = (ROOT / "docs/executive-summary.html").read_text()
    assert "No file is ready" in home and "disabled" in home
    assert "Best new file to submit: none" in summary
    assert summary.count('data-site="gemsdoe') == 9
    for id in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
        assert f'data-site="gemsdoe{id}"' in summary


def test_public_feed_never_acts_as_selector():
    feed = json.loads((ROOT / "docs/data/public-feed.json").read_text())
    assert "cannot approve a submission" in feed["warning"].lower()
    assert "not a submission receipt" in feed["leaderboard"]["evidence_class"].lower()
