#!/usr/bin/env python3
"""Check the generated site decision, local links, and published research bytes.

The governing card and ``release_gate.json`` must agree.  A negative gate may
publish reproducibility artifacts but must never advertise them as uploadable
competition submissions.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ("index.html", "executive-summary.html", "research.html", "evidence.html")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta" and values.get("name") == "gemsdoe-decision":
            self.meta["decision"] = values.get("content", "")
        self.targets.extend(value for key, value in attrs if key in {"href", "src"} and value)

    def handle_data(self, data):
        self.text.append(data)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_links(page: Path, errors: list[str]) -> None:
    parser = Links()
    parser.feed(page.read_text())
    for link in parser.targets:
        parsed = urlparse(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (page.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(DOCS.resolve()) or not target.exists():
            errors.append(f"{page.name}: missing/unsafe local link {link}")


def main() -> int:
    errors: list[str] = []
    governing = json.loads((DOCS / "data" / "run_card.json").read_text())
    gate = json.loads((DOCS / "data" / "release_gate.json").read_text())
    expected = gate.get("decision")
    if expected not in {"SUBMIT", "DO-NOT-SUBMIT"}:
        errors.append(f"invalid release decision: {expected!r}")
    if governing.get("verdict") != "negative" or expected != "DO-NOT-SUBMIT":
        errors.append("site is not using the committed negative governing decision")
    if gate.get("okay_to_submit") is not False:
        errors.append("negative release gate incorrectly allows submission")

    for name in PAGES:
        page = DOCS / name
        if not page.exists():
            errors.append(f"missing page {name}")
            continue
        parser = Links()
        parser.feed(page.read_text())
        if parser.meta.get("decision") != expected:
            errors.append(f"{name}: decision meta {parser.meta.get('decision')!r} != {expected!r}")
        text = " ".join(parser.text)
        if "DO NOT SUBMIT" not in text:
            errors.append(f"{name}: negative decision is not visible")
        if "OK TO DOWNLOAD AND SUBMIT" in text:
            errors.append(f"{name}: unsafe positive upload call-to-action")
        check_links(page, errors)

    candidate = gate.get("candidate", {})
    if gate.get("okay_to_download_for_research"):
        tif = Path(candidate.get("submission", "")).name
        published = DOCS / "downloads" / tif
        if not tif or not published.exists():
            errors.append("research candidate is not published")
        elif sha256(published) != candidate.get("sha256"):
            errors.append("published research candidate SHA-256 does not match release gate")

    downloads = (DOCS / "downloads" / "index.html")
    if not downloads.exists() or "DO NOT SUBMIT" not in downloads.read_text():
        errors.append("downloads index does not mark artifacts as research-only")

    # CSPES is an independent lane and must retain its negative presentation.
    lane = DOCS / "cspes"
    if lane.is_dir():
        lane_pages = sorted(lane.glob("*.html"))
        if not lane_pages:
            errors.append("CSPES lane directory has no pages")
        for page in lane_pages:
            text = page.read_text()
            if "Not cleared for upload" not in text and "NOT OK TO SUBMIT" not in text:
                errors.append(f"{page.name}: CSPES lane lost its negative banner")
            check_links(page, errors)
        cspes_card = lane / "data" / "cspes_run_card.json"
        if not cspes_card.exists() or json.loads(cspes_card.read_text()).get("verdict") != "negative":
            errors.append("CSPES lane card must remain negative")

    # HCE must report the global stop even though its lane records a separate
    # content-aware diagnostic.
    hce = DOCS / "hce"
    if hce.is_dir():
        for page in sorted(hce.glob("*.html")):
            text = page.read_text()
            if "Global release gate: DO NOT SUBMIT" not in text:
                errors.append(f"{page.name}: HCE page omits global release stop")
            check_links(page, errors)

    if errors:
        print("\n".join(errors))
        return 1
    print(f"Site check PASS: {len(PAGES)} pages, decision {expected}, links resolve, research bytes verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
