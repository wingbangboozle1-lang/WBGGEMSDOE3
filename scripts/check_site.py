#!/usr/bin/env python3
"""Fail-closed site contract for the current negative GEMS decision.

A passing check means the publication matches the recorded no-candidate stop. It
does not validate scientific performance or organizer acceptance.
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
CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html",
              "research.html", "method.html", "evidence.html", "session-review.html",
              "submission.html")
FORBIDDEN_POSITIVE = (
    "ok to download and submit",
    "one file cleared for upload",
    "one new file cleared",
    "the repository's cleared upload",
    "submit a unique file below",
    "decision: submit",
    "meta name=\"gemsdoe-decision\" content=\"submit\"",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
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


def main() -> int:
    errors: list[str] = []
    expected_sources = {
        "run_card": "evidence/session_3b056688_run_card.json",
        "review": "knowledge/review-2026-10-29-session.md",
        "witness_recheck": "evidence/registry_witness_recheck_2026-10-27.json",
        "preregistration": "evidence/preregistration_2026-10-28.json",
        "official_sources": "evidence/official_source_check_2026-10-28.json",
        "leaderboard_snapshot": "evidence/leaderboard_observation_2026-10-29.json",
        "leaderboard_feed": "registry/leaderboard.json",
    }
    gate_path = DOCS / "data/release_gate.json"
    current_card_path = ROOT / expected_sources["run_card"]
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        card = json.loads(current_card_path.read_text(encoding="utf-8"))
        decision = json.loads((DOCS / "data/decision.json").read_text(encoding="utf-8"))
        prereg = json.loads((ROOT / expected_sources["preregistration"]).read_text(encoding="utf-8"))
        sources = json.loads((ROOT / expected_sources["official_sources"]).read_text(encoding="utf-8"))
        snapshot = json.loads((ROOT / expected_sources["leaderboard_snapshot"]).read_text(encoding="utf-8"))
        feed = json.loads((ROOT / expected_sources["leaderboard_feed"]).read_text(encoding="utf-8"))
        witness = json.loads((ROOT / expected_sources["witness_recheck"]).read_text(encoding="utf-8"))

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
        if not any("witness" in r.lower() for r in gate.get("blocking_reasons", [])):
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
        if decision.get("run_card_sha256") != sha(current_card_path):
            errors.append("secondary decision.json is not hash-bound to the current run card")
        if decision.get("run_card") != current_card_path.name:
            errors.append("secondary decision.json names a stale current run card")

        if card.get("session_branch") != "arena/3b056688-wbggemsdoe3" or card.get("review_date_utc") != "2026-10-29":
            errors.append("current run card branch/date does not match this review")
        if card.get("verdict") != "negative" or card.get("okay_to_submit") is not False:
            errors.append("current run card is not negative")
        if card.get("raster", {}).get("generated") is not False or card.get("raster", {}).get("sha256") is not None:
            errors.append("current run card must describe no generated raster and no SHA-256")
        if card.get("holdout_dti", {}).get("label") != "NOT-RUN" or card.get("holdout_dti", {}).get("value") is not None:
            errors.append("current run card must not claim a holdout score")
        if card.get("holdout_dti", {}).get("ci95") is not None or card.get("holdout_dti", {}).get("withheld_positive_count") is not None:
            errors.append("current run card must not invent a CI or withheld-positive count")
        if card.get("holdout_dti", {}).get("evaluator_version") is not None:
            errors.append("a not-run holdout must not claim an evaluator version")
        if card.get("estimated_score", {}).get("value") is not None or card.get("estimated_score", {}).get("status") != "NOT_ESTIMATED":
            errors.append("current run card must not publish an unsupported estimate")
        if card.get("raster", {}).get("path") is not None:
            errors.append("current run card must not name a candidate raster")
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
            errors.append("2026-10-28 official-source audit date mismatch")
        if snapshot.get("observed_date_utc") != "2026-10-29":
            errors.append("2026-10-29 public leaderboard snapshot date mismatch")
        visible = snapshot.get("visible_public_scores", {})
        expected_snapshot = {"rank_1": "0.4544", "rank_25": "0.3330", "rank_26": "0.3328", "rank_48": "0.3180"}
        if any(visible.get(rank) != value for rank, value in expected_snapshot.items()):
            errors.append("public leaderboard rows do not match the dated 2026-10-29 capture")
        if "not a submission receipt" not in snapshot.get("evidence_class", "").lower():
            errors.append("public leaderboard snapshot is missing its evidence caveat")

        ranks = feed.get("captured_ranks")
        if not isinstance(ranks, dict) or not all(str(rank) in ranks for rank in (1, 2, 25, 26, 48)):
            errors.append("current public feed is missing one or more tracked ranks")
        else:
            for rank in (1, 2, 25, 26, 48):
                try:
                    value = float(ranks[str(rank)])
                    if not 0.0 <= value <= 1.0:
                        raise ValueError("outside range")
                except (TypeError, ValueError):
                    errors.append(f"current public feed rank {rank} is not a valid DTI")
        if feed.get("last_success_utc") is None:
            errors.append("current public feed has no last-success observation to display")
        if "not an upload receipt" not in feed.get("evidence_class", "").lower():
            errors.append("current public feed is missing its evidence caveat")

        copied_card = json.loads((DOCS / "data" / current_card_path.name).read_text())
        if copied_card != card:
            errors.append("published current run card differs from the source evidence")
        copied_feed = json.loads((DOCS / "data/leaderboard.json").read_text())
        if copied_feed != feed:
            errors.append("published current public feed differs from the source registry")
        copied_snapshot = json.loads((DOCS / "data" / Path(expected_sources["leaderboard_snapshot"]).name).read_text())
        if copied_snapshot != snapshot:
            errors.append("published dated leaderboard snapshot differs from source evidence")
        copied_review = (DOCS / "data" / Path(expected_sources["review"]).name).read_text(encoding="utf-8")
        if copied_review != (ROOT / expected_sources["review"]).read_text(encoding="utf-8"):
            errors.append("published latest review differs from the source review")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed current evidence: {type(exc).__name__}: {exc}")

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
        if "do not submit" not in folded and "no file is cleared" not in folded and "global stop is active" not in folded:
            errors.append(f"{rel}: no clear negative status in visible text")
        for phrase in FORBIDDEN_POSITIVE:
            if phrase in folded:
                errors.append(f"{rel}: forbidden positive clearance claim: {phrase}")

    downloads = DOCS / "downloads/index.html"
    if downloads.is_file():
        parser = PageParser()
        parser.feed(downloads.read_text(encoding="utf-8"))
        if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
            errors.append("downloads index missing negative meta")
        if any(Path(urlparse(link).path).suffix.lower() == ".tif" for link in parser.targets):
            errors.append("downloads index provides a direct TIFF link despite no clearance")
    else:
        errors.append("missing downloads/index.html")

    notice_path = DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt"
    try:
        notice = notice_path.read_text(encoding="utf-8")
        listed = {line.strip() for line in notice.splitlines()
                  if line.startswith("  ") and line.strip().lower().endswith(".tif")}
        present = {p.name for p in (DOCS / "downloads").glob("*.tif")}
        if "DO NOT SUBMIT" not in notice or "No TIFF in this directory is cleared" not in notice:
            errors.append("legacy download notice does not state the global negative")
        if listed != present:
            errors.append(f"legacy download notice inventory mismatch: {sorted(listed ^ present)}")
        if "CLEARED FOR SUBMISSION" in notice.upper():
            errors.append("legacy download notice contains positive clearance text")
    except OSError as exc:
        errors.append(f"missing legacy download notice: {exc}")

    # All local links must resolve. Archived lane pages are allowed to link to
    # research-only files only when their visible page explicitly says not to submit.
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
    print("Site check PASS: fail-closed negative decision, hash-bound evidence, no candidate links, and local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
