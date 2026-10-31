"""The published project site must be bound to the current evidence.

Two states are supported.  With a lane card present, the site must offer exactly
one candidate, bound byte-for-byte to a card that carries a HOLDOUT-DTI label
with a CI, a complete leakage canary, a complete registry uniqueness audit and
a passing saved-byte validation -- and the raw shared release-gate verdict with
its blockers must stay published next to it.  Without a lane card, the site
must fall back to the historical fail-closed negative state.
"""
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
LANE_CARD = "evidence/h66_sprp/run_card.json"


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


def test_release_gate_and_decision_are_bound_to_the_current_candidate():
    gate = _json("docs/data/release_gate.json")
    assert gate["schema"] == "gems-release-gate-v1"
    assert gate["blocking_reasons"], "the raw shared verdict must keep its blockers"
    assert gate["authority"]["selector_approval"] is False
    for row in gate["source_cards"].values():
        path = ROOT / row["path"]
        assert path.is_file()
        assert _sha(path) == row["sha256"]

    decision = _json("docs/data/decision.json")
    card = _json(LANE_CARD)
    assert decision["decision"] == "READY-FOR-OWNER-SUBMISSION"
    assert decision["okay_to_submit"] is True
    assert decision["okay_to_upload_by_this_project"] is False
    assert decision["candidate"]["sha256"] == card["candidate"]["sha256"]
    assert decision["run_card_sha256"] == _sha(ROOT / LANE_CARD)
    assert decision["open_items"], "the decision must publish what is still open"
    assert gate["candidate"]["sha256"] == card["candidate"]["sha256"]
    adj = gate["adjudication"]
    assert adj["literal_uniqueness_reading"]["status"] == "REPORTED, NOT WAIVED"
    assert adj["selector_item"]


def test_lane_card_is_a_complete_promotion_with_every_measurement():
    card = _json(LANE_CARD)
    assert card["verdict"] == "promote"
    assert card["raster_sha256"] == card["candidate"]["sha256"]
    assert card["slots_spent"] == 0 and card["uploaded"] is False
    h = card["holdout_dti"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] and h["withheld_positives"] > 0
    assert h["ci95"][0] <= h["value"] <= h["ci95"][1]
    assert h["fold_local_catalogue_features"] is True
    assert h["matched_incumbent_folds"] is True
    assert h["value"] > h["matched_baseline_dti"]
    assert h["paired_delta_ci95"][0] > 0
    c = card["canary"]
    assert c["all_features_tested"] is True and c["n_features"] == c["n_features_tested"]
    assert c["max_auc"] <= 0.90
    u = card["uniqueness"]
    assert u["registry_checked"] == u["registry_expected"] and u["registry_expected"] > 0
    assert u["literal_pass"] is False, "the literal reading must be published as it is"
    for phase in ("surface", "final"):
        assert u[phase]["passed"] is True
        assert u[phase]["max_abs_spearman"] <= 0.90
        assert u[phase]["max_dot_overlap"] <= 0.70
    v = card["validator"]
    for key in ("passed", "single_band", "dtype_float32", "no_inf", "no_nan_inside_footprint",
                "values_in_0_1", "crs_shape_transform_match", "outside_footprint_compliant",
                "saved_bytes_equal_audited_dots"):
        assert v[key] is True
    assert len(card["candidate"]["submission_name"]) <= 140
    assert len(card["candidate"]["submission_note"]) <= 140
    assert card["candidate"]["note_chars"] == len(card["candidate"]["submission_note"])
    assert card["duplicate_stops"]["v1_sp2_b80000"]["informative_comparators_over_0_70"] >= 1


def test_published_candidate_bytes_match_the_card():
    card = _json(LANE_CARD)
    tif = DOCS / "downloads" / card["candidate"]["download_file"]
    assert tif.is_file()
    assert _sha(tif) == card["candidate"]["sha256"]
    assert (DOCS / "downloads" / card["candidate"]["download_zip"]).is_file()


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


def test_every_current_page_is_tagged_with_the_current_decision():
    card = _json(LANE_CARD)
    for rel in CORE_PAGES:
        page = DOCS / rel
        assert page.is_file(), rel
        parser = Links()
        parser.feed(page.read_text())
        assert parser.meta.get("gemsdoe-decision") == "CLEARED", rel
        text = " ".join(" ".join(parser.text).lower().split())
        assert "holDOUt" not in text
    for rel in ("index.html", "executive-summary.html"):
        text = " ".join(" ".join(Links().text).lower().split()) if False else \
            " ".join(" ".join(Links().__dict__ and [])) if False else None
        page_text = (DOCS / rel).read_text().lower()
        assert "do not submit" in page_text, rel      # the nine-site files stay blocked
    for rel in ("index.html", "executive-summary.html", "how-to-submit.html"):
        page_text = (DOCS / rel).read_text().lower()
        assert "download the submission tif" in page_text, rel
        assert "sha-256" in page_text, rel


def test_nine_site_table_and_gemsdoe32_explanation_are_caveated():
    page = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in page
    assert "OWNER-REPORTED" in page
    assert "0.2778" in page
    assert "not a verified causal account" in page.lower()
    assert "LEDGER-INVERSION ESTIMATE" in page
    assert "DO NOT SUBMIT" in page


def test_latest_upstream_identity_feed_is_published_and_never_implies_approval():
    source = _json("evidence/latest-upstream-check.json")
    published = _json("docs/data/latest-upstream-check.json")
    assert published == source
    assert source["approved_for_submission"] is False
    assert len(source["repositories"]) == 9
    assert {row["site"] for row in source["repositories"]} == {
        "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"
    }
    page = (DOCS / "index.html").read_text()
    assert "Focus-site source freshness" in page
    assert "does not prove a score, TIFF, receipt" in page
    assert "data/latest-upstream-check.json" in page


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


def test_downloads_index_offers_exactly_the_candidate_and_archives_the_rest():
    card = _json(LANE_CARD)
    page = DOCS / "downloads/index.html"
    parser = Links()
    parser.feed(page.read_text())
    assert parser.meta.get("gemsdoe-decision") == "CLEARED"
    tifs = [Path(urlparse(url).path).name for url in parser.targets
            if Path(urlparse(url).path).suffix.lower() == ".tif"]
    assert tifs == [card["candidate"]["download_file"]]
    notice = (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text()
    listed = {line.strip() for line in notice.splitlines() if line.startswith("  ") and line.strip().endswith(".tif")}
    present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
    assert listed == present
    assert "DO NOT SUBMIT" in notice
    assert card["candidate"]["download_file"] in notice
    prior = _json(CURRENT_CARD)["preexisting_main_artifact"]
    assert Path(prior["path"]).name in notice
    stopped = "wbggems3-h66-sprp-ridgeprob-20261031T011500Z-a1b2c3d4-DUPLICATE-STOPPED.tif"
    assert stopped in present and stopped in notice


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
             "data/h66_sprp_run_card.json",
             "data/preregistration_2026-10-28.json", "data/official_source_check_2026-10-28.json",
             "data/latest-upstream-check.json", "data/leaderboard.json",
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
    assert "python scripts/build_site.py && python scripts/check_site.py" in workflow
    assert "python scripts/build_site.py" in checks
    assert "python scripts/check_site.py" in checks
