#!/usr/bin/env python3
"""Fail-closed consistency checks for the current *negative* publication.

A site check verifies that the documented stop and the linked artifacts agree;
it is never an authorization or a competition score.
"""
from __future__ import annotations

import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "method.html", "evidence.html")
FORBIDDEN_APPROVAL = (
    "✅ submit this file", "download and submit the generated",
    "the portal should accept", "organizer-confirmed for the zeros encoding",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[attrs["name"]] = attrs.get("content", "")
        for key in ("href", "src"):
            if attrs.get(key):
                self.targets.append(attrs[key])

    def handle_data(self, data):
        self.text.append(data)


def main() -> int:
    errors: list[str] = []
    gate_path = DOCS / "data" / "release_gate.json"
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("schema") != "gems-release-gate-v1":
            errors.append("expected current fail-closed gems-release-gate-v1")
        if gate.get("decision") != "DO-NOT-SUBMIT" or gate.get("okay_to_submit") is not False:
            errors.append("release gate must remain DO-NOT-SUBMIT")
        if gate.get("okay_to_download_for_research") is not True:
            errors.append("research-download status must be explicit")
        if gate.get("authority", {}).get("verdict") != "negative":
            errors.append("governing authority must be negative")
        if gate.get("authority", {}).get("selector_approval") is not False:
            errors.append("a lane card may not silently replace separate selector approval")
        candidate = gate.get("candidate", {})
        if candidate.get("literal_registry_pass") is True:
            errors.append("candidate must not claim a literal registry pass")
        if candidate.get("lane_verdict") not in {"negative", "promote"}:
            errors.append("candidate lane status is missing or malformed")
        for key in ("authority", "candidate"):
            rel = gate.get("source_cards", {}).get(key)
            expected = gate.get("source_cards", {}).get(key + "_sha256")
            if not rel or not expected or sha(ROOT / rel) != expected:
                errors.append(f"{key}: missing or mismatched evidence hash")
        decision = json.loads((DOCS / "data" / "decision.json").read_text(encoding="utf-8"))
        if decision.get("decision") != "DO-NOT-SUBMIT" or decision.get("okay_to_submit") is not False:
            errors.append("decision.json contradicts the negative release gate")
        if decision.get("candidate") is not None:
            errors.append("decision.json must not name an upload candidate")
        witness = json.loads((DOCS / "data" / "registry_witness_recheck_2026-10-27.json").read_text(encoding="utf-8"))
        w = witness.get("witness", {})
        if not w.get("universal_blocker") or w.get("witness_positive_inside") != w.get("footprint_cells"):
            errors.append("published registry witness evidence no longer supports the stop")
        if witness.get("approved_for_submission") is not False:
            errors.append("witness audit must not approve a submission")
        reg_rel = w.get("registry")
        reg_sha = w.get("registry_sha256")
        if not reg_rel or sha(ROOT / reg_rel) != reg_sha:
            errors.append("registered witness index hash mismatch")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed release evidence: {type(exc).__name__}: {exc}")

    for name in PAGES:
        if not (DOCS / name).is_file():
            errors.append(f"missing required page: {name}")
    notice = DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt"
    notice_text = notice.read_text(encoding="utf-8").upper() if notice.is_file() else ""
    if "DO NOT SUBMIT" not in notice_text or "CLEARED FOR SUBMISSION" in notice_text:
        errors.append("download directory must be explicitly labelled DO NOT SUBMIT with no cleared files")

    for page in sorted(DOCS.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        folded = " ".join(" ".join(parser.text).lower().split())
        rel = str(page.relative_to(DOCS))
        is_current = page.parent == DOCS and page.name in PAGES
        if is_current:
            if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
                errors.append(f"{rel}: missing negative decision metadata")
            if "do not submit" not in folded:
                errors.append(f"{rel}: explicit DO NOT SUBMIT text missing")
            for phrase in FORBIDDEN_APPROVAL:
                if phrase in folded:
                    errors.append(f"{rel}: unsafe approval wording: {phrase}")
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
    print("Site check PASS: negative release gate, selector stop, witness evidence, and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
