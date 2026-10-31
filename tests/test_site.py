"""The published site must be bound to the release gate and to saved evidence.

2026-10-31: the site contract is gate-driven (schema v2). These tests check the two properties
that matter -- the gate re-verifies from bytes, and the pages say exactly what the gate says --
plus the fail-closed behaviour when any input is missing or altered.
"""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))

from gems_project.site_gate import compose_gate, verify_candidate  # noqa: E402

CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html",
              "method.html", "evidence.html", "session-review.html", "submission.html")
CLEARANCE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "submission.html")


def _json(path) -> dict:
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


def _page(rel: str) -> tuple[Links, str]:
    p = Links()
    p.feed((DOCS / rel).read_text())
    return p, " ".join(" ".join(p.text).split())


@pytest.fixture(scope="module")
def gate() -> dict:
    return _json("docs/data/release_gate.json")


def test_gate_is_v2_and_recomputes_clean(gate):
    assert gate["schema"] == "gems-release-gate-v2"
    assert gate["decision"] in {"SUBMIT", "DO-NOT-SUBMIT"}
    reasons, facts = verify_candidate(gate, ROOT)
    assert reasons == []
    assert facts["sha256"] == gate["candidate"]["sha256"]
    assert facts["raster"]["bands"] == 1 and facts["raster"]["dtype"] == "float32"
    assert facts["raster"]["crs"] == "EPSG:32611"
    assert facts["raster"]["min"] >= 0.0 and facts["raster"]["max"] <= 1.0
    assert facts["raster"]["nan_cells"] == 0 and facts["raster"]["inf_cells"] == 0
    assert gate["okay_to_submit"] is (gate["decision"] == "SUBMIT")
    assert gate["blocking_reasons"] == []


def test_scope_limit_is_declared_not_hidden(gate):
    assert gate["conditions"]["registry_audit_complete"] is False
    scope = gate["uniqueness"]["scope_statement"]
    assert "522" in scope and "296" in scope
    assert str(gate["uniqueness"]["n_references"]) in scope
    for rel in ("index.html", "executive-summary.html", "how-to-submit.html"):
        _, text = _page(rel)
        assert scope[:60] in text, rel


@pytest.mark.parametrize("field,value", [
    ("sha256", "0" * 64), ("zip_sha256", "1" * 64), ("tif", "docs/downloads/does-not-exist.tif"),
    ("n_positive", 1), ("submission_name", ""), ("note", "x" * 141),
])
def test_candidate_lies_block_the_gate(gate, field, value):
    bad = json.loads(json.dumps(gate))
    bad["candidate"][field] = value
    reasons, _ = verify_candidate(bad, ROOT)
    assert reasons


@pytest.mark.parametrize("section,field,value", [
    ("holdout", "label", "PROXY-DTI"),
    ("holdout", "mean_dti", 0.0),
    ("canary", "all_features_tested", False),
    ("canary", "max_auc", 0.95),
    ("canary", "canary_has_power", False),
    ("uniqueness", "max_cand_within_3px", 0.71),
    ("uniqueness", "max_abs_spearman", 0.95),
    ("uniqueness", "duplicates_exact", ["x.tif"]),
    ("uniqueness", "scope_statement", ""),
])
def test_evidence_lies_block_the_gate(gate, section, field, value):
    bad = json.loads(json.dumps(gate))
    bad[section][field] = value
    assert verify_candidate(bad, ROOT)[0]


def test_a_fold_that_loses_to_its_baseline_blocks(gate):
    bad = json.loads(json.dumps(gate))
    bad["holdout"]["folds"][0]["random_matched_dti"] = bad["holdout"]["folds"][0]["dti"] + 0.01
    assert any("random baseline" in r for r in verify_candidate(bad, ROOT)[0])
    bad = json.loads(json.dumps(gate))
    bad["holdout"]["folds"][1]["paired_delta_lower"] = -0.001
    assert any("paired" in r for r in verify_candidate(bad, ROOT)[0])


def test_compose_gate_republishes_the_evidence_verdict(gate):
    rebuilt = compose_gate(_json("evidence/newfaults/run_card_2026_10_31.json"),
                           _json("evidence/newfaults/holdout_final.json"),
                           _json("evidence/newfaults/uniqueness_20261031.json"),
                           _json("evidence/newfaults/leakage_canary.json"),
                           _json("submission/newfaults-2026-10-31/"
                                 "wbg-corridor-band3to12-s24-sep4-20261031T030000Z-manifest.json"),
                           ROOT)
    assert rebuilt["holdout"]["mean_dti"] == gate["holdout"]["mean_dti"]
    assert rebuilt["holdout"]["folds"] == gate["holdout"]["folds"]
    assert rebuilt["uniqueness"]["max_cand_within_3px"] == gate["uniqueness"]["max_cand_within_3px"]
    assert rebuilt["canary"]["max_auc"] == gate["canary"]["max_auc"]


def test_every_core_page_carries_the_gate_decision(gate):
    for rel in CORE_PAGES:
        p, text = _page(rel)
        assert p.meta.get("gemsdoe-decision") == gate["decision"], rel
        if gate["decision"] == "SUBMIT":
            assert "cleared" in text.lower() or "download" in text.lower(), rel


def test_clearance_pages_name_the_exact_file(gate):
    name = Path(gate["candidate"]["tif"]).name
    for rel in CLEARANCE_PAGES:
        p, text = _page(rel)
        assert name in text, rel
    page, _ = _page("how-to-submit.html")
    text = _page("how-to-submit.html")[1]
    assert gate["candidate"]["sha256"] in text
    assert gate["candidate"]["note"] in text
    assert any(urlparse(t).path.endswith(name) for t in page.targets)


def test_executive_summary_labels_every_number(gate):
    _, text = _page("executive-summary.html")
    assert f"HOLDOUT-DTI {gate['holdout']['mean_dti']:.3f}" in text
    assert "OWNER-REPORTED" in text.upper()
    assert "not a leaderboard" in text.lower()
    assert "0.2778" in text
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in text


@pytest.mark.parametrize("phrase", ["organizer-confirmed 0.", "expected leaderboard score",
                                    "projected leaderboard score", "guaranteed score"])
def test_no_page_overclaims_a_score(phrase):
    for rel in CORE_PAGES:
        _, text = _page(rel)
        assert phrase not in text.lower(), rel


def test_downloads_offer_only_the_cleared_file(gate):
    p, _ = _page("downloads/index.html")
    assert p.meta.get("gemsdoe-decision") == gate["decision"]
    cleared = Path(gate["candidate"]["tif"]).name
    linked = {Path(urlparse(u).path).name for u in p.targets
              if Path(urlparse(u).path).suffix.lower() == ".tif"}
    assert linked == {cleared}
    published = DOCS / "downloads" / cleared
    assert _sha(published) == gate["candidate"]["sha256"]


def test_legacy_archive_is_still_marked_do_not_submit(gate):
    notice = (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").read_text()
    cleared = Path(gate["candidate"]["tif"]).name
    present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
    assert cleared in present
    lines = notice.splitlines()
    assert "DO NOT SUBMIT" in notice
    listed = {ln.strip() for ln in lines if ln.startswith("  ") and ln.strip().endswith(".tif")}
    assert present - {cleared} <= listed
    assert cleared in listed  # listed under CLEARED, not under the archive


def test_lane_archives_never_claim_the_repository_decision(gate):
    for page in sorted(DOCS.rglob("*.html")):
        rel = page.relative_to(DOCS)
        if len(rel.parts) < 2 or rel.parts[0] == "downloads":
            continue
        text = page.read_text()
        assert "Governing repository decision" not in text, rel
        assert "Global release gate: DO NOT SUBMIT" not in text, rel


def test_all_site_links_resolve_inside_docs():
    for page in DOCS.rglob("*.html"):
        p = Links()
        p.feed(page.read_text())
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(DOCS.resolve()) and target.is_file(), (page, link)


def test_run_card_is_complete_and_positive():
    card = _json("evidence/newfaults/run_card_2026_10_31.json")
    for field in ("hypothesis", "mechanism", "named_non_fault_process_that_could_mimic_it",
                  "leakage_canary", "registry_comparison", "raster", "validator", "submission",
                  "verdict"):
        assert card.get(field), field
    assert card["verdict"] == "promote" and card["okay_to_submit"] is True
    assert len(card["submission"]["note"]) <= 140
    assert card["submission"]["note_characters"] == len(card["submission"]["note"])
    assert card["holdout"]["label"] == "HOLDOUT-DTI"
    assert float(card["holdout"]["value"]) > float(sum(card["holdout"]["random_matched_baseline"]) / 3)
    assert card["raster"]["generated"] is True and len(card["raster"]["sha256"]) == 64
    assert (ROOT / card["raster"]["path"]).is_file()
    assert card["experiments_run"]["count"] <= 3


def test_canary_records_every_channel_and_can_fire():
    can = _json("evidence/newfaults/leakage_canary.json")
    assert can["all_features_tested"] is True
    assert can["n_features"] == can["n_features_tested"] > 0
    assert max(can["max_auc"], 1.0 - can["max_auc"]) <= 0.90
    assert can["auc_positive_control_distance_to_withheld_truth"] > 0.90
    assert can["leakage_detected"] is False


def test_holdout_never_carries_a_leaderboard_projection():
    hold = _json("evidence/newfaults/holdout_final.json")
    assert hold["fold_local_catalogue_features"] is True
    assert hold["matched_incumbent_folds"] is True
    assert "not a competition score" in hold["label"].lower() or "hide-and-recover" in hold["label"].lower()
    for f in hold["folds"]:
        assert f["corridor"]["ci95"][0] <= f["corridor"]["dti"] <= f["corridor"]["ci95"][1]
        assert f["corridor"]["dti"] > f["random_matched"]["dti"]
        assert f["corridor"]["dti"] > f["focus_GEMSDOE25_d2_8"]["dti"]


def test_nine_site_scores_are_never_presented_as_ours():
    focus = _json("evidence/focus_audit.json")
    assert len(focus["focus_sites"]) == 9
    for row in focus["focus_sites"]:
        assert row["organizer_confirmed_score"] is None if "organizer_confirmed_score" in row else True
        assert row["claimed_by_owner_not_receipt"]


def test_active_site_builder_is_deterministic():
    from build_site import main
    names = [*CORE_PAGES, "downloads/index.html", "downloads/LEGACY-DO-NOT-SUBMIT.txt",
             "data/release_gate.json", "data/decision.json", "data/run_card.json",
             "data/holdout_final.json", "data/uniqueness_20261031.json",
             "data/leakage_canary.json", "fchd/index.html", "amdc/index.html"]
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
