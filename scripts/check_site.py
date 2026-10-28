#!/usr/bin/env python3
"""Fail-closed publication check for docs/ (schema gems-release-gate-v2).

What it enforces, in order:

1. ``docs/data/release_gate.json`` exists, is hash-bound to its four evidence cards, and its
   decision agrees with ``evidence/run_card_v3.json``.
2. The *published* GeoTIFF's SHA-256 equals the run card's, and the machine validation recorded in
   ``evidence/design_estimate.json`` passed (values inside [0, 1], no non-finite cell, CRS / shape /
   transform identical to the sample submission, zeros outside the footprint).
3. ``evidence/uniqueness_gate.json`` passed the user's duplicate rule
   (directed 3-px overlap <= 0.70 and |Spearman| <= 0.90).
4. Every current page carries the decision in a ``gemsdoe-decision`` meta tag and in its text, and
   restates the estimate *as an estimate*.
5. Pages must not contain stale numeric claims from the earlier brief (0.4413 / 0.3195 as
   "current") nor forbidden clearance phrasing.
6. Legacy lane pages that document negative results keep their "DO NOT SUBMIT" status.
7. Every local link resolves inside docs/.

A passing check means the site is consistent with the recorded decision. It is not an organizer
validation and it does not certify a competition score.
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
LEGACY_NEGATIVE = ("downloads/index.html", "rfl/index.html", "thcs/index.html",
                   "session-1f0b051d/index.html")
FORBIDDEN = (
    "organizer-confirmed score is",
    "confirmed leaderboard score",
    "guaranteed score",
    "this will beat the leaderboard",
    "0.4413 is the current high score",
    "0.3195 is the current high score",
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
    decision = "SUBMIT"
    published = None
    try:
        gate = json.loads((DOCS / "data" / "release_gate.json").read_text())
        card = json.loads((ROOT / gate["source_cards"]["run_card"]).read_text())
        est = json.loads((ROOT / gate["source_cards"]["design"]).read_text())
        uniq = json.loads((ROOT / gate["source_cards"]["uniqueness"]).read_text())
        pair = json.loads((ROOT / gate["source_cards"]["pair"]).read_text())
        for key in ("run_card", "design", "uniqueness", "pair"):
            if sha(ROOT / gate["source_cards"][key]) != gate["source_cards"][key + "_sha256"]:
                errors.append(f"{key}: decision source SHA-256 mismatch")
        if gate.get("schema") != "gems-release-gate-v2":
            errors.append("unexpected release-gate schema")
        if gate.get("decision") != decision or gate.get("okay_to_submit") is not True:
            errors.append("release gate does not authorise the published file")
        if card.get("verdict", "").split()[0] != "promote":
            errors.append("run card verdict is not promote")
        published = ROOT / est["validation"]["path"]
        if sha(published) != card["raster"]["sha256"]:
            errors.append("published GeoTIFF bytes differ from the run card")
        if not est["validation"]["all_pass"]:
            errors.append("format validation did not pass")
        if est["validation"]["n_nonfinite"] != 0 or not est["validation"]["in_0_1"]:
            errors.append("values outside [0, 1] or non-finite cells present")
        if not (est["validation"]["crs_match"] and est["validation"]["shape_match"]
                and est["validation"]["transform_match"]):
            errors.append("grid mismatch against sample_submission.tif")
        if not uniq.get("unique"):
            errors.append("uniqueness gate failed")
        if uniq["max_directed_overlap"] > 0.70 or uniq["max_abs_spearman"] > 0.90:
            errors.append("uniqueness thresholds breached")
        if not pair["pair"]["champion_is_subset_of_base"]:
            errors.append("pair identification is not reproducible from the bytes")
        decision_json = json.loads((DOCS / "data" / "decision.json").read_text())
        if decision_json.get("decision") != decision or decision_json.get("okay_to_submit") is not True:
            errors.append("secondary decision.json contradicts the release gate")
        if decision_json.get("sha256") != card["raster"]["sha256"]:
            errors.append("decision.json points at different bytes")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed release evidence: {type(exc).__name__}: {exc}")

    for name in PAGES:
        if not (DOCS / name).is_file():
            errors.append(f"missing required page: {name}")
    for rel in LEGACY_NEGATIVE:
        p = DOCS / rel
        if p.is_file() and "do not submit" not in p.read_text(encoding="utf-8").lower():
            errors.append(f"{rel}: legacy negative page lost its DO NOT SUBMIT status")

    for page in sorted(DOCS.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        folded = " ".join(" ".join(parser.text).lower().split())
        rel = str(page.relative_to(DOCS))
        is_current = page.parent == DOCS and page.name in PAGES
        for phrase in FORBIDDEN:
            if is_current and phrase in folded:
                errors.append(f"{rel}: forbidden stale or unqualified claim: {phrase}")
        if is_current:
            if parser.meta.get("gemsdoe-decision") != decision:
                errors.append(f"{page.name}: missing or inconsistent decision meta")
            if "estimate" not in folded:
                errors.append(f"{page.name}: decision page does not label its number an estimate")
            if published is not None and published.name not in page.read_text(encoding="utf-8") \
                    and page.name != "evidence.html":
                errors.append(f"{page.name}: published file name not referenced")
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
    print("Site check PASS: hash-bound SUBMIT gate, published bytes, format, uniqueness and links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
