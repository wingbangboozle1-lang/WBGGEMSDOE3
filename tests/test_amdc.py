"""2026-10-28 AMDC lane: shipped-bytes audit, run card v2, negative dossier.

No network, no heavy rasters: everything asserted here comes from committed
evidence/*.json, the generated docs/ bytes, and the served research download.
The lane verdict is negative and nothing here overrides the repository's
governing DO-NOT-SUBMIT decision.
"""
import hashlib
import json
import math
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SGCE_SHA = "0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09"
SGCE_NAME = "wbggems3-sgce-20261027-f52d35d8-zeros.tif"
FORBIDDEN = (
    "ok to download and submit", "one new file cleared", "one file cleared for upload",
    "approved submission download", "the repository's cleared upload", "submit it only as",
    "why this file will not trigger", "all automated local gates pass",
)


def _load(path: str):
    return json.loads((ROOT / path).read_text())


def test_run_card_v2_is_negative_and_fail_closed():
    card = _load("evidence/amdc_run_card.json")
    assert card["run_card_version"] == "amdc-2"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is False
    assert card["experiments"] == {"run": 3, "max": 3}
    assert card["slots_spent"] == 0 and card["organizer_receipt"] is None
    assert card["submission_name"] is None and card["submission_note"] is None
    assert card["holdout"]["promotion_gate_P2_lower_gt_0"] is True
    assert card["uniqueness"]["promotion_gate_P3_content_aware_pass"] is False
    assert card["uniqueness"]["dots_max_gated_overlap"] > 0.90
    assert card["uniqueness"]["literal_reading"]["dots_duplicate_count"] == 25
    assert len(card["duplicate_stop_log"]) >= 2
    assert card["holdout"]["all_arms"]["E1"]["dti"] > card["holdout"]["all_arms"]["E2"]["dti"]


def test_inversion_and_projection_are_recomputed_from_ranking():
    card = _load("evidence/amdc_run_card.json")
    rows = [r for r in _load("evidence/amdc/ranking.json") if r["id"].startswith("focus:")]
    assert len(rows) == 9
    owners = [float(r["owner_reported"]) for r in rows]
    holds = [r["holdout_dti"] for r in rows]
    n = len(rows)
    mo, mh = sum(owners) / n, sum(holds) / n
    cov = sum((o - mo) * (h - mh) for o, h in zip(owners, holds))
    pearson = cov / math.sqrt(sum((o - mo) ** 2 for o in owners) * sum((h - mh) ** 2 for h in holds))
    assert pearson < -0.8, pearson
    assert card["owner_vs_holdout_inversion"]["pearson"] == round(pearson, 3)
    assert card["owner_vs_holdout_inversion"]["spearman"] < -0.8
    p = card["projection"]
    assert abs(p["slope"] * 0.019 + p["intercept"] - 0.2726) < 0.001
    assert p["arms"]["SGCE_shipped_bytes"]["projection"] == 0.2726


def test_bytes_audit_corrects_the_headline_and_matches_served_bytes():
    audit = _load("evidence/amdc/sgce_bytes_audit.json")
    assert audit["correction"]["status"].startswith("CORRECTED")
    assert audit["audited_file"]["file_sha256"] == SGCE_SHA
    served = DOCS / "downloads" / SGCE_NAME
    assert hashlib.sha256(served.read_bytes()).hexdigest() == SGCE_SHA
    assert audit["evaluator_A_native"]["sgce_shipped_dti"] == 0.0191
    assert audit["evaluator_B_matched"]["sgce_fixed_dti"] == 0.019
    assert audit["evaluator_A_native"]["withheld_positives"] == 22232
    assert audit["evaluator_B_matched"]["withheld_positives"] == 22893
    assert audit["uniqueness_reaudit"]["gated_max_overlap"] < 0.70
    assert "SUBMITTABLE" in audit["validator_rerun"]["zeros_variant"]


def test_governing_gate_is_hash_bound_and_negative():
    """The project-level gate is negative and bound to the current review evidence."""
    gate = _load("docs/data/release_gate.json")
    assert gate["schema"] == "gems-release-gate-v1"
    assert gate["decision"] == "DO-NOT-SUBMIT" and gate["okay_to_submit"] is False
    assert gate["candidate"] is None and gate["authority"]["selector_approval"] is False
    assert gate["blocking_reasons"], "the reason for the negative decision must be published"
    for row in gate["source_cards"].values():
        src = ROOT / row["path"]
        assert hashlib.sha256(src.read_bytes()).hexdigest() == row["sha256"]
    current = _load("docs/data/session_3b056688_run_card.json")
    assert current["verdict"] == "negative" and current["raster"]["sha256"] is None
    amdc = _load("evidence/amdc_run_card.json")
    assert amdc["verdict"] == "negative"


def test_amdc_data_copies_match_evidence():
    for name in ("amdc_run_card.json", "sgce_bytes_audit.json", "amdc_ranking.json",
                 "amdc_paired.json", "amdc_projection.json", "amdc_exps.json",
                 "amdc_canary.json", "amdc_uniqueness_remeasured.json"):
        assert (DOCS / "data" / name).exists(), name
    assert (DOCS / "data/amdc_run_card.json").read_bytes() == (ROOT / "evidence/amdc_run_card.json").read_bytes()


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def test_amdc_lane_page_is_scoped_negative_with_working_links():
    page = DOCS / "amdc" / "index.html"
    assert page.exists()
    body = page.read_text()
    assert '<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT">' in body
    assert 'name="gemsdoe-decision"' not in body
    assert "DO NOT SUBMIT" in body and "../index.html" in body
    folded = " ".join(body.lower().split())
    for phrase in FORBIDDEN:
        assert phrase not in folded, phrase
    parser = _Links()
    parser.feed(body)
    for link in parser.targets:
        parsed = urlparse(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (page.parent / unquote(parsed.path)).resolve()
        assert target.is_relative_to(DOCS.resolve()) and target.is_file(), link


def test_readme_records_the_negative_lane_without_claiming_clearance():
    readme = (ROOT / "README.md").read_text()
    assert "docs/amdc/index.html" in readme
    assert "AMDC" in readme and "DO NOT SUBMIT" in readme
    assert "DO NOT SUBMIT" in readme.split("## Historical lane records")[0]
    assert "research only" in readme.lower() or "research-only" in readme.lower()
    # The original task is preserved as a brief, but it cannot override the current gate.
    assert "HOLDOUT-DTI" in readme and "Maximize P(Win)" in readme


def test_amdc_step_is_deterministic():
    from build_site import main
    names = ["index.html", "executive-summary.html", "research.html", "evidence.html",
             "how-to-submit.html", "submission.html", "data/release_gate.json",
             "data/decision.json", "amdc/index.html", "data/amdc_run_card.json",
             "data/sgce_bytes_audit.json"]
    before = {n: (DOCS / n).read_bytes() for n in names}
    assert main() == 0
    for n in names:
        assert (DOCS / n).read_bytes() == before[n], n
