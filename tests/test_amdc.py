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


def test_governing_gate_is_verified_v2_with_historical_sources_intact():
    gate = _load("docs/data/release_gate.json")
    if gate["schema"] == "gems-release-gate-v1":
        # historical negative mode remains a supported fail-closed state
        assert gate["decision"] == "DO-NOT-SUBMIT"
        assert gate["okay_to_submit"] is False
        assert gate["authority"]["selector_approval"] is False
        assert gate["candidate"]["sha256"] == SGCE_SHA
        assert gate["blocking_reasons"]
        keys = ("authority", "candidate", "witness_audit")
    else:
        # current mode: preregistered content-aware gates promoted ONE new file
        assert gate["schema"] == "gems-release-gate-v2"
        assert gate["decision"] == "SUBMIT"
        assert gate["okay_to_download_and_submit"] is True
        assert not gate["blocking_reasons"]
        assert gate["selector_slot_spend"]["authorized"] is False
        assert gate["selector_slot_spend"]["slots_used"] == 0
        assert "IR-01" in gate["historical_record"]
        assert gate["candidate"]["sha256"] != SGCE_SHA  # a NEW file, not the SGCE research TIFF
        keys = ("authority", "preregistration", "focus_overlap", "irregularities",
                "witness_audit", "historical_negative_authority")
    for key in keys:
        src = ROOT / gate["source_cards"][key]
        assert hashlib.sha256(src.read_bytes()).hexdigest() == gate["source_cards"][key + "_sha256"]
    # the AMDC lane itself must remain a negative dossier in either mode
    amdc_page = (ROOT / "docs" / "amdc" / "index.html").read_text()
    assert 'content="DO-NOT-SUBMIT"' in amdc_page
    assert "DO NOT SUBMIT" in amdc_page
    assert "OK TO DOWNLOAD AND SUBMIT" not in amdc_page


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


def test_readme_records_the_lane_and_binds_any_clearance_to_the_new_file():
    readme = (ROOT / "README.md").read_text()
    assert "Parallel lane: AMDC audit (2026-10-28, negative)" in readme
    assert "docs/amdc/index.html" in readme
    if "OK TO DOWNLOAD AND SUBMIT" in readme:
        # any clearance language must be tied to the gate-cleared LBCAL-K file
        assert "wbggems3-lbcalk" in readme
        assert "5e25d191abb79ac939d79c75cc99e7ebd0a61e32c6ef99351c7ee75f8a21fc1e" in readme
    assert "DO NOT SUBMIT" in readme  # historical research TIFFs stay negative


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
