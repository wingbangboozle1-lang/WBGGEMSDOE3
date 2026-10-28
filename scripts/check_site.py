#!/usr/bin/env python3
"""Fail-closed checks for the published site, release evidence and local links.

Policy revision 2026-10-28 (user brief): the site must make it obvious whether a
generated TIF is OK to download and submit.  The checked contract is now the KHD
release: every primary page states SUBMISSION-READY, the candidate bytes are
hash-bound into docs/data/khd_release.json, the run card exists and binds the same
sha256, and every local link resolves.  Stale approval phrases remain forbidden on
non-primary (archive) pages.  This is a publication consistency check, not a model,
registry or organizer validator.
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
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html",
         "evidence.html", "submission.html")
REQUIRED_PHRASE = "ok to download and submit"
STALE_FORBIDDEN = (
    "one new file cleared", "one file cleared for upload",
    "the repository's cleared upload", "submit it only as",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
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
    rel_path = DOCS / "data/khd_release.json"
    try:
        rel = json.loads(rel_path.read_text())
        if rel.get("decision") != "SUBMISSION-READY" or rel.get("okay_to_submit") is not True:
            errors.append("khd_release.json: decision is not SUBMISSION-READY")
        cand = rel["candidate"]
        tif = ROOT / cand["file"]
        if not tif.is_file():
            errors.append(f"candidate file missing: {cand['file']}")
        elif sha(tif) != cand["sha256"]:
            errors.append("candidate file bytes differ from khd_release.json sha256")
        card_path = ROOT / rel["run_card"]
        if not card_path.is_file():
            errors.append("run card missing")
        else:
            card = json.loads(card_path.read_text())
            if card.get("raster_sha256") != cand["sha256"]:
                errors.append("run card raster_sha256 differs from release candidate sha256")
            if len(card.get("submission_note", "")) > 140 or len(card.get("submission_name", "")) > 140:
                errors.append("submission note/name exceeds 140 chars")
            if card.get("verdict") not in {"promote", "negative"}:
                errors.append("run card verdict must be promote or negative")
            if not isinstance(card.get("holdout_dti", {}).get("khd", {}).get("pooled_dti"), float):
                errors.append("run card is missing HOLDOUT-DTI for the candidate")
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
        if page.parent == DOCS and page.name in PAGES:
            if parser.meta.get("gemsdoe-decision") != "SUBMISSION-READY":
                errors.append(f"{page.name}: missing or inconsistent decision meta")
            if REQUIRED_PHRASE not in folded:
                errors.append(f"{page.name}: missing the required OK-TO-DOWNLOAD-AND-SUBMIT status")
        else:
            for phrase in STALE_FORBIDDEN:
                if phrase in folded:
                    errors.append(f"{page.relative_to(DOCS)}: forbidden stale approval: {phrase}")
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
    print("Site check PASS: SUBMISSION-READY release, hash-bound candidate + run card, "
          "statuses and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
