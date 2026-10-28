#!/usr/bin/env python3
"""Fail-closed checks for the published site, decision and local links.

This is a publication consistency check, not a model, registry or organizer
validator. A successful check can and currently must mean DO NOT SUBMIT.
"""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "submission.html")
FORBIDDEN = (
    "ok to download and submit", "one new file cleared", "one file cleared for upload",
    "approved submission download", "the repository's cleared upload", "submit it only as",
    "why this file will not trigger", "all automated local gates pass",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta" and d.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[d["name"]] = d.get("content", "")
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def main() -> int:
    errors: list[str] = []
    gate_path = DOCS / "data/release_gate.json"
    try:
        gate = json.loads(gate_path.read_text())
        authority = json.loads((ROOT / gate["source_cards"]["authority"]).read_text())
        check = json.loads((ROOT / gate["source_cards"]["witness_audit"]).read_text())
        for kind in ("authority", "candidate", "witness_audit"):
            entry = gate["source_cards"][kind]
            if sha(ROOT / entry) != gate["source_cards"][kind + "_sha256"]:
                errors.append(f"{kind}: decision source SHA-256 mismatch")
        if (gate.get("schema") != "gems-release-gate-v1" or gate.get("decision") != "DO-NOT-SUBMIT"
                or gate.get("okay_to_submit") is not False or authority.get("verdict") != "negative"
                or authority.get("selector_approval") is not False or not gate.get("blocking_reasons")):
            errors.append("global decision or selector state is not fail-closed")
        if (check.get("approved_for_submission") is not False or check.get("verdict") != "negative"
                or check["witness"].get("universal_blocker") is not True
                or check["witness"]["witness_positive_inside"] != check["witness"]["footprint_cells"]
                or sha(ROOT / check["witness"]["registry"]) != check["witness"]["registry_sha256"]
                or check["candidate"].get("literal_duplicate") is not True
                or check["candidate"].get("directed_overlap_within_3px_all_positive") != 1.0):
            errors.append("the published witness evidence is incomplete or inconsistent")
        for key in ("file", "published_file"):
            if sha(ROOT / check["candidate"][key]) != check["candidate"]["sha256"]:
                errors.append(f"research artifact bytes differ from witness audit: {key}")
        decision = json.loads((DOCS / "data/decision.json").read_text())
        if decision.get("decision") != gate["decision"] or decision.get("okay_to_submit") is not False:
            errors.append("secondary decision.json contradicts global gate")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed release evidence: {type(exc).__name__}: {exc}")

    missing = [name for name in PAGES if not (DOCS / name).is_file()]
    if missing:
        errors.append("missing required pages: " + ", ".join(missing))
    for page in sorted(DOCS.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        text = " ".join(parser.text)
        folded = " ".join(text.lower().split())
        if "do not submit" not in folded:
            errors.append(f"{page.relative_to(DOCS)}: missing DO NOT SUBMIT status")
        for phrase in FORBIDDEN:
            if phrase in folded:
                errors.append(f"{page.relative_to(DOCS)}: forbidden stale approval: {phrase}")
        if page.parent == DOCS and page.name in PAGES:
            if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
                errors.append(f"{page.name}: missing or inconsistent decision meta")
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{page.relative_to(DOCS)}: missing/unsafe local link {link}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Site check PASS: negative gate, source hashes, witness, research bytes, statuses and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
