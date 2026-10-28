#!/usr/bin/env python3
"""Fail-closed checks for the published site, decisions and local links.

Two decisions coexist in this repository and both are checked here:
  - The SGCE-era *auto-submit gate* (docs/data/release_gate.json) must stay
    exactly as strict as it always was: no human selector has approved
    anything, so it must keep reading DO-NOT-SUBMIT / okay_to_submit=False.
  - The SMSR lane's *project recommendation* (docs/data/smsr_run_card.json)
    is a separate, weaker claim ("promote-to-selector", not "submit"); the
    six top-level pages plus the SMSR lane page must say so consistently
    and must not overclaim beyond what the evidence actually supports.
Historical lane pages (amdc, fchd, hce, cspes, lst1, lbcal, rfl,
session-1f0b051d, thcs) remain individually negative and must keep saying so
for their own files.
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
PROMOTED_PAGES = PAGES + ("smsr/index.html",)
LANE_DIRS = ("amdc", "fchd", "hce", "cspes", "lst1", "lbcal", "rfl", "session-1f0b051d", "thcs")
FORBIDDEN = (
    "organizer confirmed this score", "organizer-confirmed score of", "automatically submitted",
    "auto-submitted", "guaranteed accepted", "no caveats apply",
    "100% safe", "selector has approved", "selector approved this", "is fully deconfounded",
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


def check_auto_submit_gate(errors: list[str]) -> None:
    """The SGCE-era strict gate: unchanged, still closed, still true."""
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
            errors.append("auto-submit gate or selector state is not fail-closed")
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
            errors.append("secondary decision.json contradicts the auto-submit gate")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed auto-submit-gate evidence: {type(exc).__name__}: {exc}")


def check_smsr_promotion(errors: list[str]) -> None:
    """The SMSR lane's own, separate, weaker 'promote-to-selector' claim."""
    try:
        published = json.loads((DOCS / "data/smsr_run_card.json").read_text())
        source = json.loads((ROOT / "evidence/smsr_run_card.json").read_text())
        if published != source:
            errors.append("published SMSR run card does not match evidence/smsr_run_card.json")
        if source.get("verdict") != "promote-to-selector":
            errors.append("SMSR run card verdict is not promote-to-selector")
        if source.get("slots_used_by_this_session") != 0:
            errors.append("SMSR run card claims a spent slot without selector action")
        fname = source["file"].split("/")[-1]
        raster_sha = source["raster_sha256"]
        for rel in (source["file"], f"docs/smsr/downloads/{fname}"):
            path = ROOT / rel
            if not path.is_file() or sha(path) != raster_sha:
                errors.append(f"SMSR raster bytes missing or mismatched: {rel}")
        validator = source.get("validator_output", {})
        if not validator or any(v is not True for v in validator.values()):
            errors.append("SMSR validator output is incomplete or reports a failure")
        wit = source.get("uniqueness", {}).get("vs_dense_witness_17GEMSDOE_E_proba_multiscale", {})
        if wit.get("dot_overlap_3px", 0) < 0.70 or wit.get("spearman_full_footprint", 1) > 0.90:
            errors.append("SMSR dense-witness caveat no longer has the expected shape")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed SMSR promotion evidence: {type(exc).__name__}: {exc}")


def main() -> int:
    errors: list[str] = []
    check_auto_submit_gate(errors)
    check_smsr_promotion(errors)

    missing = [name for name in PROMOTED_PAGES if not (DOCS / name).is_file()]
    if missing:
        errors.append("missing required pages: " + ", ".join(missing))
    for page in sorted(DOCS.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        text = " ".join(parser.text)
        folded = " ".join(text.lower().split())
        rel = str(page.relative_to(DOCS))
        is_promoted = rel in PROMOTED_PAGES
        is_lane = rel.split("/")[0] in LANE_DIRS and rel not in PROMOTED_PAGES
        if is_promoted:
            if "promote to selector" not in folded:
                errors.append(f"{rel}: missing PROMOTE TO SELECTOR status")
            if parser.meta.get("gemsdoe-decision") != "PROMOTE-TO-SELECTOR":
                errors.append(f"{rel}: missing or inconsistent decision meta")
        elif is_lane and parser.meta.get("gemsdoe-lane-decision") == "DO-NOT-SUBMIT":
            if "do not submit" not in folded:
                errors.append(f"{rel}: lane claims DO-NOT-SUBMIT meta but body text does not say so")
        for phrase in FORBIDDEN:
            if phrase in folded:
                errors.append(f"{rel}: forbidden overclaim: {phrase}")
        if page.parent == DOCS and page.name in PAGES and "assets/status.js" not in text:
            pass  # status.js is referenced via <script src>, not body text; checked via targets below
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: missing/unsafe local link {link}")
        if page.parent == DOCS and page.name in PAGES:
            if "assets/status.js" not in page.read_text(encoding="utf-8"):
                errors.append(f"{rel}: missing assets/status.js")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Site check PASS: auto-submit gate, SMSR promotion evidence, statuses and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
