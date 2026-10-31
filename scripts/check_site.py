#!/usr/bin/env python3
"""Check the current negative GEMS site against its evidence and fail-closed contract.

A passing check validates publication consistency and links only. It is not a
scientific result, organizer validator, or submission authorization.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CORE_PAGES = (
    "index.html", "executive-summary.html", "how-to-submit.html", "research.html",
    "method.html", "evidence.html", "session-review.html", "submission.html",
)
CURRENT_CARD = "evidence/session_2026-10-31_run_card.json"
EXPECTED_SITES = {
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
}
FORBIDDEN_POSITIVE = (
    "download latest unique tif",
    "new unique tif submission",
    "download geotiff",
    "download zip",
    "one file cleared for upload",
    "one new file cleared",
    "submit a unique file below",
    "decision: submit",
    "safe to download and submit",
)
PUBLISHED_DATA_ALLOWLIST = {
    "session_2026-10-31_run_card.json", "session_7393d521_run_card.json", "run_card.json",
    "decision.json", "release_gate.json", "registry_witness_recheck_2026-10-27.json",
    "preregistration_2026-10-31.json", "preregistration-2026-10-31.md",
    "official_source_check_2026-10-31.json", "leaderboard_observation_2026-10-31.json",
    "leaderboard.json", "latest-upstream-check.json", "focus_audit.json", "focus_estimates.json",
    "why-0.2778.md", "h6_1_proximity_pruning_holdout.json", "master_audit_2026-10-27.json",
    "review-2026-10-31.md",
    "hce_run_card.json", "cspes_run_card.json", "fchd_run_card.json", "lst1_run_card.json",
    "lbcal_run_card.json", "rfl_run_card.json", "session_1f0b051d_run_card.json", "thcs_run_card.json",
    "amdc_run_card.json", "sgce_bytes_audit.json", "amdc_ranking.json", "amdc_paired.json",
    "amdc_projection.json", "amdc_exps.json", "amdc_canary.json", "amdc_uniqueness_remeasured.json",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def main() -> int:
    errors: list[str] = []
    expected_sources = {
        "run_card": CURRENT_CARD,
        "witness_recheck": "evidence/registry_witness_recheck_2026-10-27.json",
        "preregistration": "evidence/preregistration_2026-10-31.json",
        "official_sources": "evidence/official_source_check_2026-10-31.json",
        "leaderboard_snapshot": "evidence/leaderboard_observation_2026-10-31.json",
    }
    try:
        gate = read_json(DOCS / "data/release_gate.json")
        card = read_json(ROOT / CURRENT_CARD)
        decision = read_json(DOCS / "data/decision.json")
        prereg = read_json(ROOT / expected_sources["preregistration"])
        source_check = read_json(ROOT / expected_sources["official_sources"])
        snapshot = read_json(ROOT / expected_sources["leaderboard_snapshot"])
        witness = read_json(ROOT / expected_sources["witness_recheck"])
        feed = read_json(ROOT / "registry/leaderboard.json")
        focus = read_json(ROOT / "evidence/focus_audit.json")
        upstream = read_json(ROOT / "evidence/latest-upstream-check.json")
        published_upstream = read_json(DOCS / "data/latest-upstream-check.json")

        if gate.get("schema") != "gems-release-gate-v1":
            errors.append("release gate is not the fail-closed v1 schema")
        if gate.get("decision") != "DO-NOT-SUBMIT" or gate.get("okay_to_submit") is not False:
            errors.append("release gate is not a negative decision")
        if gate.get("candidate") is not None:
            errors.append("release gate unexpectedly names a candidate")
        if gate.get("authority", {}).get("selector_approval") is not False:
            errors.append("release gate does not explicitly reject selector authorization")
        if len(gate.get("blocking_reasons", [])) < 4:
            errors.append("release gate lacks documented blockers")
        if not any("witness" in reason.lower() for reason in gate.get("blocking_reasons", [])):
            errors.append("release gate does not record the literal witness stop")

        for key, rel in expected_sources.items():
            row = gate.get("source_cards", {}).get(key, {})
            source_path = ROOT / rel
            if row.get("path") != rel:
                errors.append(f"release-gate source path mismatch: {key}")
            elif not source_path.is_file() or sha(source_path) != row.get("sha256"):
                errors.append(f"release-gate source hash mismatch: {key}")

        if decision.get("decision") != "DO-NOT-SUBMIT" or decision.get("okay_to_submit") is not False:
            errors.append("secondary decision.json is not negative")
        if decision.get("candidate") is not None:
            errors.append("secondary decision.json unexpectedly names a candidate")
        if decision.get("run_card") != Path(CURRENT_CARD).name:
            errors.append("secondary decision.json does not name the current run card")
        if decision.get("run_card_sha256") != sha(ROOT / CURRENT_CARD):
            errors.append("secondary decision.json is not hash-bound to the current run card")

        if card.get("session_branch") != "arena/c71d77d7-wbggemsdoe3":
            errors.append("current run card is not bound to the active Arena branch")
        if card.get("review_date_utc") != "2026-10-31":
            errors.append("current run card has the wrong review date")
        if card.get("verdict") != "negative" or card.get("okay_to_submit") is not False:
            errors.append("current run card is not negative")
        if card.get("okay_to_download_for_submission") is not False:
            errors.append("current run card does not explicitly deny submission download")
        if card.get("lane_assignment", {}).get("assigned") is not False:
            errors.append("current run card must record the missing lane assignment")
        if card.get("raster", {}).get("generated") is not False or card.get("raster", {}).get("sha256") is not None:
            errors.append("current run card must describe no generated raster and no SHA-256")
        if card.get("holdout_dti", {}).get("label") != "NOT-RUN" or card.get("holdout_dti", {}).get("value") is not None:
            errors.append("current run card must not claim a holdout score")
        if card.get("holdout_dti", {}).get("ci95") is not None or card.get("holdout_dti", {}).get("withheld_positive_count") is not None:
            errors.append("current run card must not invent a CI or withheld-positive count")
        if card.get("registry", {}).get("surface_rank_correlation", {}).get("status") != "NOT_RUN_NO_SURFACE":
            errors.append("current run card must state that surface correlation was not run")
        if card.get("registry", {}).get("final_dot_overlap", {}).get("status") != "NOT_RUN_NO_CANDIDATE":
            errors.append("current run card must state that final-dot overlap was not run")
        if card.get("registry", {}).get("literal_dense_witness", {}).get("threshold_exceeded") is not True:
            errors.append("current run card must retain the active literal-witness stop")
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
        ids = [row.get("id") for row in hypotheses]
        if len(ids) != len(set(ids)) or any(not value for value in ids):
            errors.append("preregistered hypothesis IDs are missing or duplicated")
        for row in hypotheses:
            for field in (
                "mechanism", "named_non_fault_mimic", "physical_signature",
                "difference_from_repository", "expected_gain_vs_cost", "data_access_status",
            ):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    errors.append(f"{row.get('id', '?')}: missing preregistration field {field}")
            if row.get("expected_dti") is not None:
                errors.append(f"{row.get('id', '?')}: prospective hypothesis contains a DTI projection")
            if row.get("validation_status", "").startswith("NOT RUN") is False:
                errors.append(f"{row.get('id', '?')}: candidate must be explicitly untested")
            if row.get("viable_now") is not False:
                errors.append(f"{row.get('id', '?')}: candidate must not be marked viable now")
        if prereg.get("lane_assignment", {}).get("assigned") is not False:
            errors.append("preregistration must record the absent method-lane assignment")
        if prereg.get("global_stop", {}).get("active") is not True:
            errors.append("preregistration must retain the global literal stop")

        proof = witness.get("witness", {})
        if proof.get("universal_blocker") is not True:
            errors.append("saved witness recheck no longer records the universal blocker")
        if proof.get("witness_positive_inside") != proof.get("footprint_cells") or proof.get("footprint_cells") != 5167373:
            errors.append("saved witness cell counts do not match the fail-closed preregistration")
        if proof.get("sha256") != prereg.get("global_stop", {}).get("witness_sha256"):
            errors.append("saved witness SHA-256 differs from preregistration")

        if source_check.get("checked_date_utc") != "2026-10-31":
            errors.append("official-source audit date mismatch")
        if snapshot.get("observed_date_utc") != "2026-10-31":
            errors.append("public leaderboard observation date mismatch")
        scores = snapshot.get("visible_public_scores", {})
        if scores.get("rank_1") != "0.4544" or scores.get("rank_2") != "0.3925" or scores.get("rank_50") != "0.3195":
            errors.append("leaderboard rank 1/2/50 do not match the dated 2026-10-31 capture")
        if "not an upload receipt" not in snapshot.get("evidence_class", "").lower():
            errors.append("public leaderboard capture is not labeled as non-receipt evidence")
        if feed.get("snapshot") != "evidence/leaderboard_observation_2026-10-31.json":
            errors.append("registry leaderboard feed does not point to the dated manual snapshot")
        if "not an upload receipt" not in feed.get("evidence_class", "").lower():
            errors.append("registry leaderboard feed is not labeled as public-only evidence")
        auto_status = feed.get("automated_refresh_status", "")
        if not isinstance(auto_status, str) or not auto_status.strip():
            errors.append("registry leaderboard feed lacks explicit automated-refresh status")
        captured = feed.get("captured_ranks", {})
        if captured:
            if not isinstance(captured, dict) or not captured.get("1"):
                errors.append("automated leaderboard feed has malformed captured ranks")
            elif feed.get("best_public_dti") != captured.get("1"):
                errors.append("automated leaderboard leader differs from its captured-rank record")
            if not feed.get("last_success_utc"):
                errors.append("automated leaderboard fragment lacks a success timestamp")

        if {row.get("site") for row in focus.get("focus_sites", [])} != EXPECTED_SITES:
            errors.append("focus audit does not cover the nine requested sites exactly once")
        if upstream.get("approved_for_submission") is not False:
            errors.append("upstream identity monitor must explicitly deny submission authorization")
        upstream_rows = upstream.get("repositories", [])
        if len(upstream_rows) != 9 or {row.get("site") for row in upstream_rows} != EXPECTED_SITES:
            errors.append("upstream identity monitor must cover each focus site exactly once")
        if published_upstream != upstream:
            errors.append("published upstream identity check is stale or differs from its source evidence")

        for rel, source_path in (
            ("data/session_2026-10-31_run_card.json", ROOT / CURRENT_CARD),
            ("data/run_card.json", ROOT / CURRENT_CARD),
            ("data/preregistration_2026-10-31.json", ROOT / expected_sources["preregistration"]),
            ("data/official_source_check_2026-10-31.json", ROOT / expected_sources["official_sources"]),
            ("data/leaderboard_observation_2026-10-31.json", ROOT / expected_sources["leaderboard_snapshot"]),
            ("data/h6_1_proximity_pruning_holdout.json", ROOT / "evidence/h6_1_proximity_pruning_holdout.json"),
            ("data/leaderboard.json", ROOT / "registry/leaderboard.json"),
            ("data/focus_audit.json", ROOT / "evidence/focus_audit.json"),
            ("data/focus_estimates.json", ROOT / "evidence/focus_estimates_retired_2026-10-31.json"),
            ("data/review-2026-10-31.md", ROOT / "knowledge/review-2026-10-31.md"),
            ("data/preregistration-2026-10-31.md", ROOT / "knowledge/preregistration-2026-10-31.md"),
        ):
            target = DOCS / rel
            if not target.is_file() or target.read_bytes() != source_path.read_bytes():
                errors.append(f"published evidence copy is missing or differs: {rel}")

        published_data = {path.name for path in (DOCS / "data").iterdir() if path.is_file()}
        if published_data != PUBLISHED_DATA_ALLOWLIST:
            errors.append(
                "published data inventory differs from the current allowlist; "
                f"unexpected={sorted(published_data - PUBLISHED_DATA_ALLOWLIST)}, "
                f"missing={sorted(PUBLISHED_DATA_ALLOWLIST - published_data)}"
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed current evidence: {type(exc).__name__}: {exc}")

    all_pages = sorted(DOCS.rglob("*.html"))
    for rel in CORE_PAGES:
        path = DOCS / rel
        if not path.is_file():
            errors.append(f"missing required page: {rel}")
            continue
        parser = PageParser()
        body = path.read_text(encoding="utf-8")
        parser.feed(body)
        folded = " ".join(" ".join(parser.text).lower().split())
        if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
            errors.append(f"{rel}: missing negative project-decision meta tag")
        if "do not submit" not in folded and "no file is cleared" not in folded and "no candidate is eligible" not in folded:
            errors.append(f"{rel}: no clear negative status in visible text")
        for phrase in FORBIDDEN_POSITIVE:
            if phrase in folded:
                errors.append(f"{rel}: forbidden positive clearance/download claim: {phrase}")

    downloads = DOCS / "downloads/index.html"
    if not downloads.is_file():
        errors.append("missing downloads/index.html")
    else:
        parser = PageParser()
        parser.feed(downloads.read_text(encoding="utf-8"))
        folded = " ".join(" ".join(parser.text).lower().split())
        if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
            errors.append("downloads index missing negative meta")
        if "no direct tiff or zip download link" not in folded:
            errors.append("downloads index does not state that no direct TIFF/ZIP link is provided")

    # No published HTML page may directly link to a TIFF, TIF, or ZIP artifact.
    for page in all_pages:
        parser = PageParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"cannot read {page.relative_to(DOCS)}: {exc}")
            continue
        rel = str(page.relative_to(DOCS))
        for link in parser.targets:
            suffix = Path(urlparse(link).path).suffix.lower()
            if suffix in {".tif", ".tiff", ".zip"}:
                errors.append(f"{rel}: forbidden direct raster/archive link {link}")

        # All remaining local links must resolve within docs.
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: missing/unsafe local link {link}")

    notice_path = DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt"
    try:
        notice = notice_path.read_text(encoding="utf-8")
        listed = {line.strip() for line in notice.splitlines()
                  if line.startswith("  ") and line.strip().lower().endswith((".tif", ".tiff"))}
        present = {p.name for p in (DOCS / "downloads").glob("*")
                   if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}}
        if "DO NOT SUBMIT" not in notice or "No TIFF or ZIP in this directory is cleared" not in notice:
            errors.append("legacy download notice does not state the global negative")
        if listed != present:
            errors.append(f"legacy download notice TIFF inventory mismatch: {sorted(listed ^ present)}")
        listed_zips = {line.strip() for line in notice.splitlines()
                       if line.startswith("  ") and line.strip().lower().endswith(".zip")}
        present_zips = {p.name for p in (DOCS / "downloads").glob("*")
                        if p.is_file() and p.suffix.lower() == ".zip"}
        if listed_zips != present_zips:
            errors.append(f"legacy download notice ZIP inventory mismatch: {sorted(listed_zips ^ present_zips)}")
        if "CLEARED FOR SUBMISSION" in notice.upper():
            errors.append("legacy download notice contains positive clearance text")
    except OSError as exc:
        errors.append(f"missing legacy download notice: {exc}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Site check PASS: evidence hashes match, decision is negative, no candidate links exist, inventory is exact, and local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
