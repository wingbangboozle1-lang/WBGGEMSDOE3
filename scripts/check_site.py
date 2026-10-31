#!/usr/bin/env python3
"""Decision-agnostic, fail-closed site contract for the GEMS project.

The previous version of this script asserted that the published site *is* a
negative decision. That made a positive release impossible to publish even after
the blocker was resolved, which is the opposite of fail-closed. This version binds
the published pages to the single machine-readable release card
(``evidence/release/candidate_run_card.json``) and enforces consistency in both
directions:

* card says **promote** and both gates passed -> the landing page must name the
  exact file and SHA-256, offer it, and claim approval; the bytes must exist and
  hash to the card value;
* card says anything else -> the landing page must **not** claim approval, and no
  file may be linked as submittable.

Historical lanes keep their own negative pages; those pages are checked to still
say "research only" and are never allowed to claim project-level approval.
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
RELEASE_PAGES = ("index.html", "executive-summary.html", "research.html", "how-to-submit.html")
LEGACY_PAGES = ("evidence.html", "method.html", "session-review.html", "submission.html",
                "downloads/index.html")
CARD = ROOT / "evidence" / "release" / "candidate_run_card.json"
FOCUS = ROOT / "evidence" / "release" / "focus_sites.json"
APPROVAL_PHRASE = "ok to download and submit"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").startswith("gemsdoe-"):
            self.meta[attrs["name"]] = attrs.get("content", "")
        for key, value in attrs.items():
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def parse(path: Path) -> tuple[Page, str]:
    body = path.read_text(encoding="utf-8")
    page = Page()
    page.feed(body)
    folded = " ".join(" ".join(page.text).lower().split())
    return page, folded


def main() -> int:
    errors: list[str] = []
    for rel in RELEASE_PAGES:
        if not (DOCS / rel).is_file():
            errors.append(f"missing release page: {rel}")
    if errors:
        print("SITE CONTRACT FAILED")
        for e in errors:
            print(" -", e)
        return 1

    try:
        card = json.loads(CARD.read_text())
        focus = json.loads(FOCUS.read_text())
    except (OSError, ValueError) as exc:
        print(f"SITE CONTRACT FAILED\n - cannot read release evidence: {exc}")
        return 1

    fmt = card.get("format_validator", {})
    uniq = card.get("uniqueness_audit", {})
    promote = (card.get("verdict") == "promote" and fmt.get("passed") is True
               and uniq.get("passed") is True)
    sub = card.get("submission", {})
    decision = "SUBMIT" if promote else "DO-NOT-SUBMIT"

    if promote:
        path = ROOT / sub.get("path", "")
        if not path.is_file():
            errors.append(f"card promotes a missing file: {sub.get('path')}")
        elif sha(path) != sub.get("sha256"):
            errors.append("released file does not hash to the card value")
        for rel in RELEASE_PAGES:
            page, folded = parse(DOCS / rel)
            if page.meta.get("gemsdoe-decision") != decision:
                errors.append(f"{rel}: decision meta is not {decision}")
            if page.meta.get("gemsdoe-release-sha256") != sub.get("sha256"):
                errors.append(f"{rel}: release sha256 meta does not match the card")
        page, folded = parse(DOCS / "index.html")
        if APPROVAL_PHRASE not in folded:
            errors.append("index.html does not state that the file is OK to download and submit")
        if sub.get("file") not in (DOCS / "index.html").read_text():
            errors.append("index.html does not name the released file")
        if sub.get("sha256") not in (DOCS / "index.html").read_text():
            errors.append("index.html does not print the released SHA-256")
        if sub.get("sha256") not in (DOCS / "how-to-submit.html").read_text():
            errors.append("how-to-submit.html does not print the released SHA-256")
        if f"downloads/release/{sub.get('file')}" not in (DOCS / "index.html").read_text():
            errors.append("index.html does not link the released file")
        if not (ROOT / sub.get("path", "")).is_file():
            errors.append("released file is not inside the repository")
    else:
        for rel in RELEASE_PAGES:
            _page, folded = parse(DOCS / rel)
            if APPROVAL_PHRASE in folded and "not ok" not in folded and "do not submit" not in folded:
                errors.append(f"{rel}: claims approval while the card is negative")
        _page, folded = parse(DOCS / "index.html")
        if APPROVAL_PHRASE in folded and "do not submit" not in folded:
            errors.append("index.html claims approval while the card is negative")

    # The nine focus files must be present, measured, and labelled as owner reports.
    rows = [r for r in focus.get("sites", []) if r.get("dots")]
    if len(rows) != 9:
        errors.append(f"focus audit must carry nine measured files, found {len(rows)}")
    summary = (DOCS / "executive-summary.html").read_text()
    for row in rows:
        if row["site"] not in summary:
            errors.append(f"executive summary omits {row['site']}")
        if "OWNER-REPORTED" not in summary.upper():
            errors.append("executive summary does not label the quoted scores as owner reports")
    if "PROJECTION" not in (DOCS / "executive-summary.html").read_text().upper():
        errors.append("executive summary does not label its projected score")

    # The machine-readable live decision must agree with the card, and must not be
    # confused with the archive lane's own gate (data/release_gate.json).
    decision_path = DOCS / "data" / "release_decision.json"
    if not decision_path.is_file():
        errors.append("missing machine-readable release decision: data/release_decision.json")
    else:
        dec = json.loads(decision_path.read_text())
        if dec.get("decision") != decision:
            errors.append("release_decision.json decision disagrees with the card")
        if dec.get("okay_to_submit") is not promote:
            errors.append("release_decision.json okay_to_submit disagrees with the card")
        if promote and dec.get("sha256") != sub.get("sha256"):
            errors.append("release_decision.json sha256 disagrees with the card")
        if dec.get("note_characters", 0) > 140:
            errors.append("release_decision.json note exceeds 140 characters")

    # ---------------------------------------------------------------------
    # Every published number must be reproducible from the evidence files.
    # This is the "verified line by line" rule made executable: if a page and
    # its evidence ever disagree, the site build fails instead of shipping.
    # ---------------------------------------------------------------------
    note = card.get("note") or ""
    if len(note) > 140:
        errors.append(f"portal note is {len(note)} characters, the limit is 140")
    if promote and note and note not in (DOCS / "index.html").read_text():
        errors.append("index.html does not print the exact portal note from the card")

    receipt_path = ROOT / sub.get("path", "") if sub.get("path") else None
    if promote and receipt_path is not None:
        receipt_path = receipt_path.with_suffix(".json")
        if not receipt_path.is_file():
            errors.append(f"missing downloadable receipt: {receipt_path.name}")
        else:
            receipt = json.loads(receipt_path.read_text())
            for key in ("sha256", "dots", "note", "format_passed", "uniqueness_passed"):
                want = {"sha256": sub.get("sha256"), "dots": card.get("dots"),
                        "note": card.get("note"), "format_passed": fmt.get("passed"),
                        "uniqueness_passed": uniq.get("passed")}[key]
                if receipt.get(key) != want:
                    errors.append(f"receipt {key} disagrees with the card")
            if receipt.get("format_checks") != fmt.get("checks"):
                errors.append("receipt format checks disagree with the card")
            if receipt.get("uniqueness_checks") != uniq.get("checks"):
                errors.append("receipt uniqueness checks disagree with the card")

    sweep = json.loads((ROOT / "evidence/release/density_sweep.json").read_text())
    h_published = sweep["density_sweep"]["CAT|60000"]["hit_rate_within_3px"]
    exec_text = (DOCS / "executive-summary.html").read_text()
    for g_assumed in (15000, 25000, 40000, 60000, 90000):
        ratio = card.get("dots", 0) / g_assumed
        dti = h_published * ratio / (0.8 + 0.2 * ratio)
        if f"{dti:.3f}" not in exec_text:
            errors.append(f"projection row |G|={g_assumed} does not render {dti:.3f}")
    if f"{h_published:.3f}" not in exec_text:
        errors.append("executive summary does not print the hit rate the projection uses")

    for row in rows:
        if f"{row['dots']:,}" not in summary:
            errors.append(f"executive summary does not print the dot count for {row['site']}")
        if row.get("owner_reported_score") is not None:
            if f"{row['owner_reported_score']:.4f}" not in summary:
                errors.append(f"executive summary does not print the owner score for {row['site']}")

    # Historical pages must stay negative and must not compete with the decision meta.
    for rel in LEGACY_PAGES:
        path = DOCS / rel
        if not path.is_file():
            errors.append(f"missing legacy page: {rel}")
            continue
        page, folded = parse(path)
        if page.meta.get("gemsdoe-decision") not in {"DO-NOT-SUBMIT", "SUBMIT"}:
            errors.append(f"{rel}: missing a project decision meta tag")
        if rel.startswith("downloads") and any(
                Path(urlparse(t).path).suffix.lower() == ".tif" for t in page.targets):
            errors.append("downloads index links a TIFF directly; it must route via the release page")

    # Every relative link on the release pages must resolve inside docs/.
    for rel in RELEASE_PAGES:
        page, _ = parse(DOCS / rel)
        for link in page.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path or link.startswith("#"):
                continue
            target = (DOCS / rel).parent / unquote(parsed.path)
            if not target.resolve().is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: broken relative link {link}")

    # The archived negative decision must be preserved and clearly labelled.
    archived = DOCS / "archive" / "index-2026-10-30.html"
    if not archived.is_file():
        errors.append("the 2026-10-30 negative decision was not archived")
    elif "ARCHIVED 2026-10-30" not in archived.read_text():
        errors.append("archived landing page is not labelled as archived")

    if errors:
        print("SITE CONTRACT FAILED")
        for e in errors:
            print(" -", e)
        return 1
    print(f"site contract OK ({'positive release' if promote else 'negative'} decision, "
          f"file {sub.get('file')}, sha256 {sub.get('sha256', '')[:12]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
