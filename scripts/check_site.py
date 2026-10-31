#!/usr/bin/env python3
"""Fail-closed site contract for the current GEMS decision.

Two states are supported and both are checked hard:

* NO LANE CARD (the historical state): the publication must match the recorded
  no-candidate stop — no clearance, no direct TIFF link, negative meta tags.
* LANE CARD (2026-10-31 and later): exactly one candidate may be offered, it
  must be bound byte-for-byte to a machine-readable card that carries a
  HOLDOUT-DTI label with a CI, a complete leakage canary, a complete registry
  uniqueness audit and a passing saved-byte format validation; the raw shared
  release-gate verdict (which still blocks on the literal all-registry
  uniqueness reading and on the absence of a separate slot selector) must stay
  published next to it, and the weekly slot must remain unspent.

A passing check proves the publication is internally consistent and hash-bound.
It does not validate scientific performance, and it is not an organizer receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html",
              "research.html", "method.html", "evidence.html", "session-review.html",
              "submission.html")
FORBIDDEN_POSITIVE = (
    "the repository's cleared upload",
    "submit a unique file below",
    "meta name=\"gemsdoe-decision\" content=\"submit\"",
)
LEGACY_CARD = "evidence/session_7393d521_run_card.json"
LANE_CARD = "evidence/h66_sprp/run_card.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        if tag == "meta" and attrs_map.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[attrs_map["name"]] = attrs_map.get("content", "")
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def check_lane(lane: dict, errors: list[str]) -> dict:
    """Validate the published candidate against its card.  Returns the card."""
    c = lane.get("candidate", {})
    v = lane.get("validator", {})
    h = lane.get("holdout_dti", {})
    u = lane.get("uniqueness", {})
    canary = lane.get("canary", {})
    sha_hex = c.get("sha256", "")
    if not isinstance(sha_hex, str) or not SHA256_RE.fullmatch(sha_hex):
        errors.append("lane card candidate has no valid SHA-256")
    if lane.get("verdict") != "promote":
        errors.append("lane card verdict is not promote")
    if lane.get("slots_spent") not in (0, None) or lane.get("uploaded") is not False:
        errors.append("lane card claims a spent slot or an upload")
    # holdout
    if h.get("label") != "HOLDOUT-DTI":
        errors.append("lane holdout is not labelled HOLDOUT-DTI")
    ci = h.get("ci95")
    if (not isinstance(ci, list) or len(ci) != 2
            or not all(isinstance(x, (int, float)) for x in ci)
            or not ci[0] <= float(h.get("value", -1)) <= ci[1]):
        errors.append("lane holdout CI is missing or does not contain the reported value")
    if not isinstance(h.get("withheld_positives"), int) or h["withheld_positives"] <= 0:
        errors.append("lane holdout has no withheld-positive count")
    if not h.get("evaluator_version"):
        errors.append("lane holdout has no evaluator version")
    if h.get("fold_local_catalogue_features") is not True or h.get("matched_incumbent_folds") is not True:
        errors.append("lane holdout is not fold-local / matched-control")
    # canary
    if (canary.get("all_features_tested") is not True
            or canary.get("n_features") != canary.get("n_features_tested")
            or float(canary.get("max_auc", 1.0)) > 0.90):
        errors.append("lane leakage canary is incomplete or above threshold")
    # uniqueness
    if u.get("registry_checked") != u.get("registry_expected") or not u.get("registry_expected"):
        errors.append("lane uniqueness audit did not cover the whole indexed registry")
    for phase in ("surface", "final"):
        p = u.get(phase, {})
        if (p.get("passed") is not True
                or float(p.get("max_abs_spearman", 1.0)) > 0.90
                or float(p.get("max_dot_overlap", 1.0)) > 0.70):
            errors.append(f"lane uniqueness {phase} phase is not passing")
    if u.get("literal_pass") is not False and u.get("literal_firings") is None:
        errors.append("lane uniqueness must publish the literal reading explicitly")
    # validator
    for key in ("passed", "single_band", "dtype_float32", "no_inf", "no_nan_inside_footprint",
                "values_in_0_1", "crs_shape_transform_match", "outside_footprint_compliant",
                "saved_bytes_equal_audited_dots"):
        if v.get(key) is not True:
            errors.append(f"lane validator does not certify '{key}'")
    if v.get("sha256") != sha_hex:
        errors.append("lane validator is bound to different bytes than the candidate")
    # the published bytes
    tif = DOCS / "downloads" / c.get("download_file", "")
    zip_path = DOCS / "downloads" / c.get("download_zip", "")
    if not tif.is_file():
        errors.append(f"published candidate file missing: {tif}")
    elif sha(tif) != sha_hex:
        errors.append("published candidate file does not match the card SHA-256")
    if not zip_path.is_file():
        errors.append(f"published candidate ZIP missing: {zip_path}")
    else:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            if len(names) != 1 or not names[0].endswith(".tif"):
                errors.append("published ZIP does not contain exactly one GeoTIFF")
            elif tif.is_file() and z.read(names[0]) != tif.read_bytes():
                errors.append("published ZIP member differs from the published TIF")
    if len(c.get("submission_name", "")) > 140 or not c.get("submission_name"):
        errors.append("lane submission name is missing or too long")
    if len(c.get("submission_note", "")) > 140 or not c.get("submission_note"):
        errors.append("lane submission note is missing or too long")
    if c.get("note_chars") != len(c.get("submission_note", "")):
        errors.append("lane submission note character count is wrong")
    return lane


def main() -> int:
    errors: list[str] = []
    expected_sources = {
        "run_card": LEGACY_CARD,
        "witness_recheck": "evidence/registry_witness_recheck_2026-10-27.json",
        "preregistration": "evidence/preregistration_2026-10-28.json",
        "official_sources": "evidence/official_source_check_2026-10-28.json",
        "leaderboard_snapshot": "evidence/leaderboard_observation_2026-10-28.json",
    }
    lane_path = ROOT / LANE_CARD
    lane = None
    if lane_path.is_file():
        lane = json.loads(lane_path.read_text(encoding="utf-8"))
    gate_path = DOCS / "data/release_gate.json"
    current_card_path = ROOT / expected_sources["run_card"]
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        card = json.loads(current_card_path.read_text(encoding="utf-8"))
        decision = json.loads((DOCS / "data/decision.json").read_text(encoding="utf-8"))
        prereg = json.loads((ROOT / expected_sources["preregistration"]).read_text(encoding="utf-8"))
        sources = json.loads((ROOT / expected_sources["official_sources"]).read_text(encoding="utf-8"))
        snapshot = json.loads((ROOT / expected_sources["leaderboard_snapshot"]).read_text(encoding="utf-8"))
        witness = json.loads((ROOT / expected_sources["witness_recheck"]).read_text(encoding="utf-8"))
        upstream = json.loads((ROOT / "evidence/latest-upstream-check.json").read_text(encoding="utf-8"))
        published_upstream = json.loads((DOCS / "data/latest-upstream-check.json").read_text(encoding="utf-8"))

        if upstream.get("approved_for_submission") is not False:
            errors.append("upstream identity monitor must explicitly deny submission authorization")
        upstream_rows = upstream.get("repositories", [])
        if (len(upstream_rows) != 9 or
                {row.get("site") for row in upstream_rows} !=
                {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}):
            errors.append("upstream identity monitor must cover each of the nine focus sites exactly once")
        if published_upstream != upstream:
            errors.append("published upstream identity check is stale or differs from its source evidence")
        if gate.get("schema") != "gems-release-gate-v1":
            errors.append("release gate is not the fail-closed v1 schema")
        if not gate.get("blocking_reasons"):
            errors.append("release gate lacks documented blockers")

        if lane is not None:
            check_lane(lane, errors)
            sha_hex = lane["candidate"]["sha256"]
            if gate.get("candidate", {}).get("sha256") != sha_hex:
                errors.append("release gate is not bound to the published candidate")
            adj = gate.get("adjudication", {})
            if not adj.get("literal_uniqueness_reading"):
                errors.append("release gate does not publish the literal uniqueness reading")
            if not adj.get("selector_item"):
                errors.append("release gate does not publish the selector item")
            if gate.get("authority", {}).get("selector_approval") is not False:
                errors.append("release gate must not claim a weekly-slot selector approval")
            if decision.get("decision") != "READY-FOR-OWNER-SUBMISSION":
                errors.append("decision.json is not the owner-submission decision")
            if decision.get("okay_to_submit") is not True:
                errors.append("decision.json does not allow the owner to download and submit")
            if decision.get("okay_to_upload_by_this_project") is not False:
                errors.append("decision.json must record that this project uploaded nothing")
            if (decision.get("candidate") or {}).get("sha256") != sha_hex:
                errors.append("decision.json candidate is not the published candidate")
            if decision.get("run_card_sha256") != sha(lane_path):
                errors.append("decision.json is not hash-bound to the lane run card")
            if not decision.get("open_items"):
                errors.append("decision.json does not publish its open items")
        else:
            if gate.get("decision") != "DO-NOT-SUBMIT" or gate.get("okay_to_submit") is not False:
                errors.append("release gate is not a negative decision")
            if gate.get("candidate") is not None:
                errors.append("release gate unexpectedly names a candidate")
            if gate.get("authority", {}).get("selector_approval") is not False:
                errors.append("release gate does not explicitly reject selector authorization")
            if len(gate.get("blocking_reasons", [])) < 4:
                errors.append("release gate lacks documented blockers")
            if not any("witness" in r.lower() for r in gate.get("blocking_reasons", [])):
                errors.append("release gate does not record the literal witness stop")
            if decision.get("decision") != "DO-NOT-SUBMIT" or decision.get("okay_to_submit") is not False:
                errors.append("secondary decision.json is not negative")
            if decision.get("candidate") is not None:
                errors.append("secondary decision.json unexpectedly names a candidate")
            if decision.get("run_card_sha256") != sha(current_card_path):
                errors.append("secondary decision.json is not hash-bound to the current run card")
            if card.get("verdict") != "negative" or card.get("okay_to_submit") is not False:
                errors.append("current run card is not negative")
            if card.get("raster", {}).get("generated") is not False or card.get("raster", {}).get("sha256") is not None:
                errors.append("current run card must describe no generated raster and no SHA-256")
            if card.get("holdout_dti", {}).get("label") != "NOT-RUN" or card.get("holdout_dti", {}).get("value") is not None:
                errors.append("current run card must not claim a holdout score")
            if card.get("holdout_dti", {}).get("ci95") is not None or card.get("holdout_dti", {}).get("withheld_positive_count") is not None:
                errors.append("current run card must not invent a CI or withheld-positive count")
            if card.get("experiments", {}).get("geological_experiments_completed") != 0:
                errors.append("geological experiment budget count is not zero")
            if card.get("selector", {}).get("weekly_slots_used") != 0 or card.get("selector", {}).get("action") != "NONE":
                errors.append("current run card must not claim a selector/slot action")
            note = card.get("submission", {}).get("note", "")
            if len(note) > 140 or card.get("submission", {}).get("note_characters") != len(note):
                errors.append("negative run-card note is missing, miscounted, or exceeds 140 characters")
            if card.get("submission", {}).get("name") is not None:
                errors.append("a submission name must not be assigned without a candidate")

        hypotheses = prereg.get("hypotheses", [])
        if len(hypotheses) < 3 or len(hypotheses) > 5:
            errors.append("preregistration must include 3-5 hypotheses")
        ids = [h.get("id") for h in hypotheses]
        if len(ids) != len(set(ids)) or any(not x for x in ids):
            errors.append("preregistered hypothesis IDs are missing or duplicated")
        for h in hypotheses:
            for field in ("mechanism", "named_non_fault_mimic", "physical_signature", "difference_from_repository"):
                if not isinstance(h.get(field), str) or not h[field].strip():
                    errors.append(f"{h.get('id', '?')}: missing preregistration field {field}")
            if h.get("expected_dti") is not None:
                errors.append(f"{h.get('id', '?')}: prospective hypothesis contains an unverified DTI projection")

        proof = witness.get("witness", {})
        if proof.get("universal_blocker") is not True:
            errors.append("saved witness recheck no longer records the universal blocker")
        if proof.get("witness_positive_inside") != proof.get("footprint_cells") or proof.get("footprint_cells") != 5167373:
            errors.append("saved witness cell counts do not match the fail-closed preregistration")
        if proof.get("sha256") != prereg.get("global_stop", {}).get("witness_sha256"):
            errors.append("saved witness SHA-256 differs from preregistration")

        if sources.get("checked_date_utc") != "2026-10-28":
            errors.append("official-source audit date mismatch")
        if snapshot.get("observed_date_utc") != "2026-10-28":
            errors.append("public leaderboard snapshot date mismatch")
        if snapshot.get("visible_public_scores", {}).get("rank_1") != "0.4544":
            errors.append("public leaderboard snapshot leader value changed")
        if snapshot.get("visible_public_scores", {}).get("rank_25") != "0.3217" or snapshot.get("visible_public_scores", {}).get("rank_26") != "0.3195":
            errors.append("public leaderboard ranks 25/26 do not match the dated capture")

        copied_card = json.loads((DOCS / "data/session_7393d521_run_card.json").read_text())
        if copied_card != card:
            errors.append("published current run card differs from the source evidence")
        if lane is not None:
            copied_lane = json.loads((DOCS / "data/h66_sprp_run_card.json").read_text())
            if copied_lane != lane:
                errors.append("published lane run card differs from the source evidence")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed current evidence: {type(exc).__name__}: {exc}")

    expected_meta = "CLEARED" if lane is not None else "DO-NOT-SUBMIT"
    for rel in CORE_PAGES:
        path = DOCS / rel
        if not path.is_file():
            errors.append(f"missing required page: {rel}")
            continue
        parser = PageParser()
        body = path.read_text(encoding="utf-8")
        parser.feed(body)
        folded = " ".join(" ".join(parser.text).lower().split())
        if parser.meta.get("gemsdoe-decision") != expected_meta:
            errors.append(f"{rel}: project-decision meta tag is not '{expected_meta}'")
        for phrase in FORBIDDEN_POSITIVE:
            if phrase in folded:
                errors.append(f"{rel}: forbidden clearance claim: {phrase}")
        if lane is None:
            if "do not submit" not in folded and "no file is cleared" not in folded and "global stop is active" not in folded:
                errors.append(f"{rel}: no clear negative status in visible text")
        else:
            if "download the submission tif" not in folded and rel not in ("research.html", "method.html", "evidence.html", "session-review.html", "submission.html"):
                errors.append(f"{rel}: no obvious download-to-submit call to action")
            if "holDOUt" in folded and "holdout-dti" not in folded:
                errors.append(f"{rel}: holdout label is not spelled HOLDOUT-DTI")

    downloads = DOCS / "downloads/index.html"
    if downloads.is_file():
        parser = PageParser()
        parser.feed(downloads.read_text(encoding="utf-8"))
        if parser.meta.get("gemsdoe-decision") != expected_meta:
            errors.append("downloads index has the wrong decision meta tag")
        tif_links = [Path(urlparse(link).path).name for link in parser.targets
                     if Path(urlparse(link).path).suffix.lower() == ".tif"]
        if lane is None:
            if tif_links:
                errors.append("downloads index provides a direct TIFF link despite no clearance")
        else:
            if tif_links != [lane["candidate"]["download_file"]]:
                errors.append(f"downloads index must offer exactly the candidate TIF, found {tif_links}")
    else:
        errors.append("missing downloads/index.html")

    notice_path = DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt"
    try:
        notice = notice_path.read_text(encoding="utf-8")
        listed = {line.strip() for line in notice.splitlines()
                  if line.startswith("  ") and line.strip().lower().endswith(".tif")}
        present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
        if lane is None:
            if "DO NOT SUBMIT" not in notice or "No TIFF in this directory is cleared" not in notice:
                errors.append("legacy download notice does not state the global negative")
            if listed != present:
                errors.append(f"legacy download notice inventory mismatch: {sorted(listed ^ present)}")
            if "CLEARED FOR SUBMISSION" in notice.upper():
                errors.append("legacy download notice contains positive clearance text")
        else:
            name = lane["candidate"]["download_file"]
            if name not in listed:
                errors.append("the download notice does not list the published candidate")
            if "DO NOT SUBMIT" not in notice:
                errors.append("the download notice does not mark the archive as DO NOT SUBMIT")
            if listed != present:
                errors.append(f"download notice inventory mismatch: {sorted(listed ^ present)}")
    except OSError as exc:
        errors.append(f"missing legacy download notice: {exc}")

    # All local links must resolve.
    for page in sorted(DOCS.rglob("*.html")):
        parser = PageParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"cannot read {page.relative_to(DOCS)}: {exc}")
            continue
        rel = str(page.relative_to(DOCS))
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: missing/unsafe local link {link}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    state = "one published candidate, hash-bound and evidence-complete" if lane else \
        "fail-closed negative decision, hash-bound evidence, no candidate links"
    print(f"Site check PASS: {state}, and local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
