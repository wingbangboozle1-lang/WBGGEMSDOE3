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
              "repo-review.html", "submission.html")
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
        "run_card": "evidence/session_7393d521_run_card.json",
        "witness_recheck": "evidence/registry_witness_recheck_2026-10-27.json",
        "preregistration": "evidence/preregistration_2026-10-28.json",
        "official_sources": "evidence/official_source_check_2026-10-28.json",
        "leaderboard_snapshot": "evidence/leaderboard_observation_2026-10-28.json",
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
        witness = json.loads((ROOT / expected_sources["witness_recheck"]).read_text(encoding="utf-8"))
        upstream = json.loads((ROOT / "evidence/latest-upstream-check.json").read_text(encoding="utf-8"))
        published_upstream = json.loads((DOCS / "data/latest-upstream-check.json").read_text(encoding="utf-8"))

        if upstream.get("approved_for_submission") is not False:
            errors.append("upstream identity monitor must explicitly deny submission authorization")
        upstream_rows = upstream.get("repositories", [])
        if (len(upstream_rows) != 9 or
                {row.get("site") for row in upstream_rows} !=
                {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}):
            errors.append("upstream identity monitor must cover each of the nine focus sites exactly once")
        if published_upstream != upstream:
            errors.append("published upstream identity check is stale or differs from its source evidence")
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
            errors.append("public leaderboard ranks 25/26 do not match the dated 2026-10-28 capture")
        latest_snapshot = json.loads((ROOT / "evidence/leaderboard_observation_2026-10-29.json").read_text(encoding="utf-8"))
        latest_sources = json.loads((ROOT / "evidence/official_source_check_2026-10-29.json").read_text(encoding="utf-8"))
        if (latest_snapshot.get("observed_date_utc") != "2026-10-29"
                or latest_snapshot.get("visible_public_scores", {}).get("rank_25") != "0.3330"
                or latest_snapshot.get("visible_public_scores", {}).get("rank_26") != "0.3328"):
            errors.append("latest dated public leaderboard capture is missing or inconsistent")
        if latest_sources.get("checked_date_utc") != "2026-10-29":
            errors.append("latest dated official-source audit is missing or inconsistent")
        current_review = (DOCS / "repo-review.html").read_text(encoding="utf-8")
        if "not a causal finding" not in current_review.lower() or "0.2778" not in current_review:
            errors.append("repository review page lacks GEMSDOE32 score caveat")
        if "0.3330" not in current_review or "0.3328" not in current_review:
            errors.append("repository review page lacks latest dated public leaderboard rows")

        copied_card = json.loads((DOCS / "data/session_7393d521_run_card.json").read_text())
        if copied_card != card:
            errors.append("published current run card differs from the source evidence")
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
