"""The published project site must be bound to the current negative evidence."""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html",
              "method.html", "evidence.html", "session-review.html", "submission.html")
CURRENT_CARD = "evidence/session_7393d521_run_card.json"


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.targets = []
        self.meta = {}
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[attrs["name"]] = attrs.get("content", "")
        for key, value in attrs.items():
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def test_project_release_gate_is_negative_and_hash_bound():
    gate = _json("docs/data/release_gate.json")
    assert gate["schema"] == "gems-release-gate-v1"
    assert gate["decision"] == "DO-NOT-SUBMIT"
    assert gate["okay_to_submit"] is False
    assert gate["candidate"] is None
    assert gate["authority"]["selector_approval"] is False
    assert any("witness" in reason.lower() for reason in gate["blocking_reasons"])
    for row in gate["source_cards"].values():
        path = ROOT / row["path"]
        assert path.is_file()
        assert _sha(path) == row["sha256"]

    decision = _json("docs/data/decision.json")
    assert decision["decision"] == "DO-NOT-SUBMIT"
    assert decision["okay_to_submit"] is False and decision["candidate"] is None
    assert decision["run_card_sha256"] == _sha(ROOT / CURRENT_CARD)


def test_current_run_card_is_a_complete_negative_not_a_fake_score():
    card = _json(CURRENT_CARD)
    assert card["verdict"] == "negative" and card["okay_to_submit"] is False
    assert card["raster"]["generated"] is False
    assert card["raster"]["sha256"] is None
    assert card["holdout_dti"]["label"] == "NOT-RUN"
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["holdout_dti"]["evaluator_version"] is None
    assert card["holdout_dti"]["withheld_positive_count"] is None
    assert card["registry"]["surface_rank_correlation"]["status"] == "NOT_RUN_NO_SURFACE"
    assert card["registry"]["final_dot_overlap"]["status"] == "NOT_RUN_NO_CANDIDATE"
    assert card["registry"]["literal_dense_witness"]["conditional_directed_overlap_for_any_nonempty_in_footprint_candidate"] == 1.0
    assert card["validator"]["status"] == "NOT_RUN_NO_CANDIDATE"
    assert card["submission"]["name"] is None
    assert len(card["submission"]["note"]) <= 140
    assert card["submission"]["note_characters"] == len(card["submission"]["note"])
    assert card["experiments"]["geological_experiments_completed"] == 0
    assert card["selector"]["weekly_slots_used"] == 0
    prior = card["preexisting_main_artifact"]
    assert prior["status"] == "UNAPPROVED_ARCHIVE_ONLY"
    assert prior["byte_identity_rechecked_against_upstream_record"] is True
    assert prior["scientific_or_format_validation_in_this_review"] is False
    prior_path = ROOT / prior["path"]
    assert prior_path.is_file() and _sha(prior_path) == prior["upstream_recorded_sha256"]


def test_preregistration_has_five_distinct_testable_hypotheses():
    prereg = _json("evidence/preregistration_2026-10-28.json")
    rows = prereg["hypotheses"]
    assert 3 <= len(rows) <= 5
    assert len({r["id"] for r in rows}) == len(rows)
    for row in rows:
        assert row["mechanism"]
        assert row["named_non_fault_mimic"]
        assert row["physical_signature"]
        assert row["difference_from_repository"]
        assert row["expected_dti"] is None
        assert row["validation_status"].startswith("NOT RUN")
    assert prereg["global_stop"]["active"] is True
    assert prereg["experiment_budget"]["experiments_completed_at_preregistration"] == 0


def test_literal_witness_is_recorded_as_a_stop_not_a_clearance():
    witness = _json("evidence/registry_witness_recheck_2026-10-27.json")["witness"]
    assert witness["universal_blocker"] is True
    assert witness["witness_positive_inside"] == witness["footprint_cells"] == 5_167_373
    assert witness["sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert "owner mirrors" in _json("evidence/preregistration_2026-10-28.json")["global_stop"]["provenance_caveat"]


def test_every_current_page_is_tagged_negative_and_has_no_clearance_claim():
    for rel in CORE_PAGES:
        page = DOCS / rel
        assert page.is_file(), rel
        parser = Links()
        parser.feed(page.read_text())
        assert parser.meta.get("gemsdoe-decision") == "DO-NOT-SUBMIT", rel
        text = " ".join(" ".join(parser.text).lower().split())
        assert "do not submit" in text or "no file is cleared" in text or "global stop is active" in text, rel
        assert "ok to download and submit" not in text, rel
        assert "one new file cleared" not in text, rel


def test_nine_site_table_and_gemsdoe32_explanation_are_caveated():
    page = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in page
    assert "OWNER-REPORTED" in page
    assert "0.2778" in page
    assert "not a verified causal account" in page.lower()
    assert "not estimable" in page.lower()
    assert "DO NOT SUBMIT" in page


def test_visible_peer_freshness_feed_distinguishes_drift_from_score_updates():
    freshness = _json("docs/freshness.json")
    published = _json("docs/data/source-freshness.json")
    assert published == freshness
    page = (DOCS / "executive-summary.html").read_text()
    review_page = (DOCS / "session-review.html").read_text()
    assert "Peer-source freshness" in page
    assert "does not tell us that a reported score or TIFF changed" in page
    assert "Latest repository review · 2026-10-29" in review_page
    assert "2026-10-28 research / release review (historical)" in review_page
    evidence_page = (DOCS / "evidence.html").read_text()
    assert "dot definition under review" in evidence_page.lower()
    assert "not a candidate-specific duplicate measurement" in evidence_page.lower()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in page


def test_current_repository_review_card_is_negative_and_bound_to_source_feed():
    card = _json("evidence/repo_review_2026-10-29.json")
    assert card["decision"] == "DO-NOT-SUBMIT"
    assert card["okay_to_download_for_submission"] is False
    assert card["verdict"] == "negative"
    assert card["holdout_dti"]["label"] == "NOT-RUN"
    assert card["raster"]["generated"] is False and card["raster"]["sha256"] is None
    assert card["experiment_and_selector_accounting"]["submission_slots_used"] == 0
    assert card["submission"]["note_characters"] == len(card["submission"]["note"]) <= 140
    assert card["source_freshness"]["focus_repositories_changed_since_pinned_audit"] == 9


def test_current_leaderboard_and_official_source_captures_are_labeled():
    obs = _json("evidence/leaderboard_observation_2026-10-28.json")
    assert obs["visible_public_scores"]["rank_1"] == "0.4544"
    assert obs["visible_public_scores"]["rank_25"] == "0.3217"
    assert obs["visible_public_scores"]["rank_26"] == "0.3195"
    assert "not a submission receipt" in obs["evidence_class"].lower()
    source = _json("evidence/official_source_check_2026-10-28.json")
    ids = {row["id"] for row in source["sources"]}
    assert {"competition_problem_and_format", "official_rules", "public_leaderboard", "submission_portal", "geodawn_usgs", "gdr_1391", "usgs_3dep", "landsat_collection_2"} <= ids
    assert any("homepage lists" in row.get("irregularity", "") for row in source["sources"])


def test_downloads_index_has_no_direct_tiff_and_legacy_inventory_is_negative():
    page = DOCS / "downloads/index.html"
    parser = Links()
    parser.feed(page.read_text())
    assert parser.meta.get("gemsdoe-decision") == "DO-NOT-SUBMIT"
    assert not any(Path(urlparse(url).path).suffix.lower() == ".tif" for url in parser.targets)
    notice = (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text()
    listed = {line.strip() for line in notice.splitlines() if line.startswith("  ") and line.strip().endswith(".tif")}
    present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
    assert listed == present
    assert "No TIFF in this directory is cleared" in notice
    assert "DO NOT SUBMIT" in notice
    prior = _json(CURRENT_CARD)["preexisting_main_artifact"]
    assert Path(prior["path"]).name in notice


def test_all_site_links_resolve_inside_docs():
    for page in DOCS.rglob("*.html"):
        parser = Links()
        parser.feed(page.read_text())
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(DOCS.resolve()) and target.is_file(), (page, link)


def test_retired_positive_builders_stop_before_writing_docs():
    before = (DOCS / "index.html").read_bytes()
    for name in ("build_site_v3.py", "build_release_gate_v2.py", "build_evidence_page.py"):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT,
                              capture_output=True, text=True, timeout=15)
        assert proc.returncode != 0, name
        assert "BLOCKED" in proc.stderr, (name, proc.stderr)
    assert (DOCS / "index.html").read_bytes() == before


def test_active_site_builder_is_deterministic():
    from build_site import main
    names = [*CORE_PAGES, "downloads/index.html", "downloads/LEGACY-DO-NOT-SUBMIT.txt",
             "data/release_gate.json", "data/decision.json", "data/session_7393d521_run_card.json",
             "data/preregistration_2026-10-28.json", "data/official_source_check_2026-10-28.json",
             "data/source-freshness.json", "data/repo-review-2026-10-29.md",
             "data/repo_review_2026-10-29.json", "data/witness_definition_check_2026-10-29.json",
             "data/session-review-2026-10-29-witness.md", "data/leaderboard.json",
             "data/fchd_run_card.json", "data/amdc_run_card.json",
             "fchd/index.html", "amdc/index.html"]
    before = {name: (DOCS / name).read_bytes() for name in names}
    assert main() == 0
    for name in names:
        assert (DOCS / name).read_bytes() == before[name], name


def test_pages_workflow_still_runs_the_active_builder_and_checker():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    checks = (ROOT / ".github/workflows/checks.yml").read_text()
    assert "python scripts/refresh_feed.py" in workflow
    assert "python scripts/check_freshness.py" in workflow
    assert "python scripts/build_site.py && python scripts/check_site.py" in workflow
    assert "python scripts/build_site.py" in checks
    assert "python scripts/check_site.py" in checks
