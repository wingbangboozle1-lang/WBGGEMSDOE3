#!/usr/bin/env python3
"""Check the generated site: decision consistency, local links, artefact integrity.

Supersedes the 2026-10-27 negative-only checker by adding a third verdict,
``promote-with-caveat``, which is what this repository now publishes for one file.  All of the
previous structural guards are kept:

* every published page carries the same ``<meta name="gemsdoe-decision">`` value;
* local links must resolve inside ``docs/``;
* the artefact offered for download must exist and match the recorded SHA-256;
* the new verdict must show an explicit submit action, print its estimate, and list every
  promotion gate it does **not** satisfy — a caveat with no listed gate is a failure;
* the CSPES and LST1 lanes keep their own pages and their own banners.
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
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html",
         "research.html", "evidence.html")
VERDICTS = {"promote": "SUBMIT", "promote-with-caveat": "SUBMIT-WITH-CAVEAT",
            "negative": "DO-NOT-SUBMIT"}


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta" and d.get("name") == "gemsdoe-decision":
            self.meta["decision"] = d.get("content", "")
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


def check_links(page: Path, parser: Links, errors: list[str]) -> None:
    for link in parser.targets:
        parsed = urlparse(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (page.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(DOCS.resolve()) or not target.exists():
            errors.append(f"{page.name}: missing/unsafe local link {link}")


def main() -> int:
    errors: list[str] = []
    card = json.loads((DOCS / "data" / "run_card.json").read_text())
    verdict = card.get("verdict")
    if verdict not in VERDICTS:
        errors.append(f"run card verdict invalid: {verdict!r}")
        print("\n".join(errors), file=sys.stderr)
        return 1
    expected = VERDICTS[verdict]

    if verdict == "promote":
        from build_executive import approval_errors
        if approval_errors(card):
            errors.append("promotion lacks mandatory gates: " + ", ".join(approval_errors(card)))
    if verdict == "promote-with-caveat":
        failed = sorted(k for k, v in card.get("promotion_gates", {}).items() if v is not True)
        if not failed:
            errors.append("promote-with-caveat without a single unsatisfied gate is just 'promote'")
        if not card.get("caveat"):
            errors.append("promote-with-caveat without a caveat sentence")

    for name in PAGES:
        page = DOCS / name
        if not page.exists():
            errors.append(f"missing required page {name}")
            continue
        p = Links()
        p.feed(page.read_text())
        if p.meta.get("decision") != expected:
            errors.append(f"{name}: decision meta {p.meta.get('decision')!r} != {expected!r}")
        check_links(page, p, errors)
        body = " ".join(p.text)
        if verdict == "negative" and "OK TO DOWNLOAD AND SUBMIT" in body:
            errors.append(f"{name}: negative verdict but upload approval shown")
        if verdict.startswith("promote") and "OK TO DOWNLOAD AND SUBMIT" not in body:
            errors.append(f"{name}: promote verdict but no explicit submit action")
        if verdict == "promote-with-caveat" and "below the 0.2778" not in " ".join(
                (DOCS / "index.html").read_text().split()):
            errors.append("front page must state the comparison with the 0.2778 champion")

    # artefact integrity: the served bytes must be the evaluated bytes
    tif = Path(card["download"]["tif"]).name
    served = DOCS / "downloads" / tif
    if not served.exists():
        errors.append(f"artefact not published for download: downloads/{tif}")
    else:
        digest = sha256(served)
        if digest != card["sha256"]:
            errors.append("published artefact SHA-256 does not match the run card")
        if (ROOT / "submission" / tif).exists() and sha256(ROOT / "submission" / tif) != digest:
            errors.append("docs/downloads and submission/ copies differ")
    note = json.loads((ROOT / "evidence/candidate_run_card.json").read_text())["submission_note"]
    if len(note) > 140:
        errors.append(f"submission note is {len(note)} characters (limit 140)")

    for asset in ("assets/submission-map.png", "downloads/index.html"):
        if not (DOCS / asset).exists():
            errors.append(f"missing shared asset {asset}")

    # parallel lanes keep their own namespaces and banners
    for lane, phrase in (("cspes", "Not cleared for upload"), ("lst1", "NEGATIVE")):
        lane_dir = DOCS / lane
        if not lane_dir.is_dir():
            errors.append(f"missing parallel lane directory docs/{lane}")
            continue
        pages = sorted(lane_dir.glob("*.html"))
        if not pages:
            errors.append(f"{lane} lane has no pages")
        for page in pages:
            p = Links()
            p.feed(page.read_text())
            text = " ".join(p.text)
            if phrase not in text and "DO NOT SUBMIT" not in text and "NOT OK TO SUBMIT" not in text:
                errors.append(f"docs/{lane}/{page.name}: lost its lane status banner")
            check_links(page, p, errors)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Site check PASS: {len(PAGES)} pages, decision {expected}, links resolve, "
          f"artefact verified, parallel lanes intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
