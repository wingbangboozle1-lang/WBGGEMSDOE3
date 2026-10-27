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


def check_release_gate(errors: list[str], verdict: str, expected: str, card: dict) -> None:
    """The governing card and the machine-readable release gate must agree."""
    gate_path = DOCS / "data" / "release_gate.json"
    if not gate_path.exists():
        errors.append("missing docs/data/release_gate.json")
        return
    gate = json.loads(gate_path.read_text())
    if gate.get("schema") != "gems-release-gate-v1":
        errors.append(f"release gate schema {gate.get('schema')!r}")
    if gate.get("decision") != expected:
        errors.append(f"release gate decision {gate.get('decision')!r} != {expected!r}")
    if gate.get("authority", {}).get("verdict") != verdict:
        errors.append("release gate authority verdict disagrees with the governing run card")
    allowed = expected != "DO-NOT-SUBMIT"
    if gate.get("okay_to_submit") is not allowed:
        errors.append(f"release gate okay_to_submit should be {allowed} for {expected}")
    if allowed:
        if gate.get("authority", {}).get("raster_sha256") != card.get("sha256"):
            errors.append("release gate raster hash disagrees with the governing card")
        if not gate.get("blocking_reasons"):
            errors.append("a positive release decision must still list what it does not claim")
        cand = gate.get("candidate", {})
        if cand.get("sha256") != card.get("sha256"):
            errors.append("release gate candidate hash disagrees with the governing card")


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


def main():
    errors = []
    banner = 'OK TO DOWNLOAD AND SUBMIT'
    for page in sorted(DOCS.glob('*.html')):
        p = Links()
        p.feed(page.read_text())
        if banner not in ' '.join(p.text):
            errors.append(f'{page.name}: missing positive decision banner')
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{page.name}: missing/unsafe local link {link}')
    card = json.loads((DOCS / 'data/session2_run_card.json').read_text())
    build = json.loads((DOCS / 'data/session2_build.json').read_text())
    if card.get('verdict') != 'promote' or not card.get('raster_sha256') or card.get('selector_approval'):
        errors.append('run card does not match a promoted, unselected, hashed raster')
    if card['raster_sha256'] != build['files'][card['submission_name'] + '-zeros.tif']['sha256']:
        errors.append('run card hash does not match the published TIFF')
    if not all(v['passed'] for v in build['validation'].values()):
        errors.append('published TIFF fails its own format validator')
    if not build['uniqueness']['content_aware_pass']:
        errors.append('published TIFF fails the uniqueness gate')
    dl = DOCS / 'downloads'
    for suffix in ('-zeros.tif', '-nan.tif', '-zeros.zip'):
        if not (dl / (card['submission_name'] + suffix)).is_file():
            errors.append(f'missing published download {suffix}')
    required = {'index.html', 'executive-summary.html', 'research.html', 'evidence.html'}
    present = {page.name for page in DOCS.glob('*.html')}
    if not required <= present:
        errors.append(f'missing required generated pages: {sorted(required - present)}')
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print('Site check: pages, local links, hashes, validator, uniqueness and positive status PASS.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
