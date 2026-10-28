"""The published site must stay bound to recorded evidence, never to a claim.

These tests encode the *genuine* invariant of this project: a page may only advertise an upload
when a hash-bound evidence card, a format validation and the uniqueness gate all pass — and even
then the number it shows must be labelled an ESTIMATE.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "method.html", "evidence.html")


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_release_gate_is_hash_bound_and_agrees_with_the_run_card():
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    card = json.loads((ROOT / gate["source_cards"]["run_card"]).read_text())
    assert gate["schema"] == "gems-release-gate-v2"
    assert gate["decision"] == card["verdict"].split()[0].upper().replace("PROMOTE", "SUBMIT")
    assert gate["okay_to_submit"] is True
    assert gate["blocking_reasons"], "irregularities must be published with the decision"
    for key in ("run_card", "design", "uniqueness", "pair"):
        assert _sha(ROOT / gate["source_cards"][key]) == gate["source_cards"][key + "_sha256"]


def test_published_bytes_pass_every_portal_gate():
    est = json.loads((ROOT / "evidence/design_estimate.json").read_text())
    v = est["validation"]
    assert _sha(ROOT / v["path"]) == v["sha256"]
    assert v["in_0_1"] and v["n_nonfinite"] == 0
    assert v["crs_match"] and v["shape_match"] and v["transform_match"]
    assert v["zeros_outside_footprint"]
    assert v["n_positive"] == est["stats"]["n_dots"] > 0


def test_uniqueness_gate_matches_the_user_rule():
    u = json.loads((ROOT / "evidence/uniqueness_gate.json").read_text())
    assert u["unique"] is True
    assert u["max_directed_overlap"] <= 0.70
    assert u["max_abs_spearman"] <= 0.90
    assert u["n_registry_compared"] >= 50


def test_pair_identification_is_reproducible_and_physical():
    p = json.loads((ROOT / "evidence/pair_identification.json").read_text())
    assert p["pair"]["champion_is_subset_of_base"] is True
    assert p["pair"]["removed_within_3px_of_catalogue_frac"] == 1.0
    M = p["identification"]["hidden_truth_cells_M"]
    T = p["identification"]["identity_covers_T"]
    assert 10_000 < M < 25_000 and 0 < T < M


def test_every_current_page_is_estimate_labelled_and_decision_tagged():
    for page in PAGES:
        body = (DOCS / page).read_text()
        assert '<meta name="gemsdoe-decision" content="SUBMIT">' in body
        assert "estimate" in body.lower()
        assert "organizer-confirmed score is" not in body.lower()


def test_nine_site_table_is_present_and_labelled():
    body = (DOCS / "executive-summary.html").read_text()
    for n in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f"GEMSDOE{n}" in body
    assert "OWNER-REPORTED" in body
    assert "0.2778" in body
    assert "Do not submit" in body
    assert "ESTIMATE" in body


def test_legacy_negative_lane_pages_stay_negative():
    for rel in ("downloads/index.html", "rfl/index.html", "thcs/index.html"):
        p = DOCS / rel
        if p.is_file():
            text = p.read_text().lower()
            assert "do not submit" in text, rel
    # the downloads index may advertise exactly one file, and must label it an estimate
    dl = (DOCS / "downloads/index.html").read_text()
    assert dl.count("wbggems3-invdesign-anchor-20k-zeros.tif") >= 1
    assert "estimate" in dl.lower()


def test_pages_publisher_uses_the_same_layout():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    assert "url=docs/index.html" in (ROOT / "index.html").read_text()
    assert "cp -a docs .cache/pages-release/docs" in workflow


def test_site_checker_passes_on_committed_pages():
    from check_site import main
    assert main() == 0


def test_figures_are_bound_to_the_published_bytes():
    """The two method.html figures must describe the *cleared* file, not an older lane."""
    figs = json.loads((ROOT / "evidence/design_figures.json").read_text())
    tif = ROOT / figs["deliverable"]
    assert _sha(tif) == json.loads((ROOT / "evidence/run_card_v3.json").read_text())["raster"]["sha256"]
    assert figs["design_dots"] == 20000
    for rel in figs["figures"]:
        assert (ROOT / rel).stat().st_size > 10_000, rel
        assert (ROOT / rel).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", rel
    method = (DOCS / "method.html").read_text()
    for rel in figs["figures"]:
        assert Path(rel).name in method
    # the gate numbers the caption quotes must be the measured ones, and must clear the gate
    assert figs["frac_design_on_public_catalogue"] < 0.01
    assert figs["frac_design_within_3px_of_champion"] <= 0.70


def test_downloads_notice_agrees_with_the_gate():
    """The plain-text notice shipped next to the TIFFs may not contradict the decision."""
    gate = json.loads((DOCS / "data/release_gate.json").read_text())
    notice = (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").read_text()
    cleared = Path(gate["decision_scope"].split(": ", 1)[1]).name
    assert f"CLEARED FOR SUBMISSION (1 file): {cleared}" in notice
    assert gate["submission_name"] in notice
    assert "No file in this directory is cleared" not in notice
    listed = {ln.strip() for ln in notice.splitlines()
              if ln.startswith("  ") and not ln.startswith("    ") and ln.strip().endswith(".tif")}
    present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
    assert listed == present - {cleared}, (listed ^ (present - {cleared}))
