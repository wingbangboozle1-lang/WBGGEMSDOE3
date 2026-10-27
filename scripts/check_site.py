#!/usr/bin/env python3
"""Check the generated dossier: required pages, resolvable local links, and — most
importantly — that the download the front page advertises is the exact file whose
SHA-256 is recorded in the evidence and in docs/data/decision.json.
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
REQUIRED = {"index.html", "executive-summary.html", "how-to-submit.html",
            "research.html", "evidence.html"}
EVIDENCE_BANNER = "LEDGER-INVERSION ESTIMATE"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors: list[str] = []
    present = {p.name for p in DOCS.glob("*.html")}
    if not REQUIRED <= present:
        errors.append(f"missing required pages: {sorted(REQUIRED - present)}")

    for page in sorted(DOCS.glob("*.html")):
        if page.name == "lst1" or page.name.startswith("review"):
            continue
        parser = Links()
        parser.feed(page.read_text())
        blob = " ".join(parser.text)
        if page.name in REQUIRED and EVIDENCE_BANNER not in blob:
            errors.append(f"{page.name}: missing evidence-class statement")
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f"{page.name}: missing/unsafe local link {link}")

    decision = json.loads((DOCS / "data/decision.json").read_text())
    card = json.loads((ROOT / "evidence/candidate_run_card.json").read_text())
    cited = DOCS / "downloads" / decision["submission"]
    if not cited.is_file():
        errors.append(f"advertised download is absent: {cited}")
    else:
        if sha256(cited) != decision["sha256"]:
            errors.append("advertised download SHA-256 does not match decision.json")
        if decision["sha256"] != card["file"]["sha256"]:
            errors.append("decision.json and the run card disagree on the file hash")
        if sha256(ROOT / "submission" / decision["submission"]) != decision["sha256"]:
            errors.append("docs/downloads and submission/ copies differ")
    front = (DOCS / "index.html").read_text()
    if f"downloads/{decision['submission']}" not in front:
        errors.append("front page does not link the cleared download")
    if "0.2778" not in front:
        errors.append("front page omits the comparison with the site champion")
    note = card["submission_note"]
    if len(note) > 140:
        errors.append(f"submission note is {len(note)} characters (limit 140)")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Site check: pages, links, download hash and note length PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
