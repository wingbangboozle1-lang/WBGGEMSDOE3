#!/usr/bin/env python3
"""Fail-closed checks for the published site, decision and local links.

Two supported publications:

* ``DO-NOT-SUBMIT`` (schema v1) — the historical literal-registry negative.
* ``SUBMIT`` (schema v2) — the preregistered content-aware gates promoted the
  LBCAL-K candidate. The clearance is re-verified from scratch here: the run
  card, preregistration, focus-overlap and irregularity sources must match
  their recorded SHA-256, the saved bytes (workspace + published copy) must
  match the card digest, and every page must carry the required disclosures.

This is a publication consistency check, not a model, registry or organizer
validator. A successful check never establishes an organizer-confirmed score.
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
PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "submission.html")
FORBIDDEN = (
    "one new file cleared", "one file cleared for upload",
    "approved submission download", "the repository's cleared upload",
    "submit it only as", "why this file will not trigger",
    "organizer-confirmed score of", "guaranteed acceptance",
    "the portal will accept",
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


def check_historical_evidence(errors: list[str]) -> None:
    """The witness / SGCE research records must stay byte-consistent in both modes."""
    try:
        check = json.loads((ROOT / "evidence/registry_witness_recheck_2026-10-27.json").read_text())
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
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed witness evidence: {type(exc).__name__}: {exc}")


def main() -> int:
    errors: list[str] = []
    gate_path = DOCS / "data/release_gate.json"
    try:
        gate = json.loads(gate_path.read_text())
    except (OSError, ValueError) as exc:
        print(f"missing or malformed release gate: {exc}", file=sys.stderr)
        return 1

    check_historical_evidence(errors)

    schema = gate.get("schema")
    if schema == "gems-release-gate-v1":
        # Historical negative publication.
        try:
            authority = json.loads((ROOT / gate["source_cards"]["authority"]).read_text())
            for kind in ("authority", "candidate", "witness_audit"):
                entry = gate["source_cards"][kind]
                if sha(ROOT / entry) != gate["source_cards"][kind + "_sha256"]:
                    errors.append(f"{kind}: decision source SHA-256 mismatch")
            if (gate.get("decision") != "DO-NOT-SUBMIT" or gate.get("okay_to_submit") is not False
                    or authority.get("verdict") != "negative"
                    or authority.get("selector_approval") is not False
                    or not gate.get("blocking_reasons")):
                errors.append("global decision or selector state is not fail-closed")
            decision = json.loads((DOCS / "data/decision.json").read_text())
            if decision.get("decision") != gate["decision"] or decision.get("okay_to_submit") is not False:
                errors.append("secondary decision.json contradicts global gate")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"missing or malformed release evidence: {type(exc).__name__}: {exc}")
        expected_meta = "DO-NOT-SUBMIT"
        clearance_pages: set[str] = set()
    elif schema == "gems-release-gate-v2":
        sys.path.insert(0, str(ROOT / "src"))
        from gems_project.release_gate_v2 import evaluate_release_gate_v2
        try:
            sources = gate["source_cards"]
            for kind in ("authority", "preregistration", "focus_overlap", "irregularities",
                         "witness_audit", "historical_negative_authority"):
                if sha(ROOT / sources[kind]) != sources[kind + "_sha256"]:
                    errors.append(f"{kind}: decision source SHA-256 mismatch")
            card = json.loads((ROOT / sources["authority"]).read_text())
            v2 = evaluate_release_gate_v2(card, ROOT, prereg_path=ROOT / sources["preregistration"])
            if v2["decision"] != "SUBMIT" or gate.get("decision") != "SUBMIT":
                errors.append("re-evaluated v2 gate does not reproduce the published SUBMIT decision")
            if gate.get("okay_to_download_and_submit") is not True or gate.get("blocking_reasons"):
                errors.append("published gate is not a clean approval")
            slot = gate.get("selector_slot_spend") or {}
            if slot.get("authorized") is not False or slot.get("slots_used") != 0:
                errors.append("selector slot-spend state is not the required untouched zero")
            # bytes: workspace candidate + published copies must match the card
            cand = gate.get("candidate") or {}
            tif_rel = card["raster"]["path"]
            published_tif = DOCS / "downloads" / Path(tif_rel).name
            for label, path in (("workspace", ROOT / tif_rel), ("published", published_tif)):
                if not path.is_file():
                    errors.append(f"candidate {label} missing: {path.name}")
                elif sha(path) != cand.get("sha256"):
                    errors.append(f"candidate {label} SHA-256 mismatch")
            import zipfile
            for label, zpath, member in (
                    ("zip", (ROOT / tif_rel).with_suffix(".zip"), Path(tif_rel).name),
                    ("published_zip", published_tif.with_suffix(".zip"), Path(tif_rel).name)):
                if not zpath.is_file():
                    errors.append(f"candidate {label} missing: {zpath.name}")
                    continue
                try:
                    with zipfile.ZipFile(zpath) as zf:
                        payload = zf.read(member)
                    if hashlib.sha256(payload).hexdigest() != cand.get("sha256"):
                        errors.append(f"candidate {label} member bytes SHA-256 mismatch")
                except (KeyError, OSError, ValueError) as exc:
                    errors.append(f"candidate {label} unreadable: {exc}")
            decision = json.loads((DOCS / "data/decision.json").read_text())
            if (decision.get("decision") != "SUBMIT" or decision.get("okay_to_download_and_submit") is not True
                    or decision.get("okay_to_submit") is not True
                    or (decision.get("candidate") or {}).get("sha256") != cand.get("sha256")):
                errors.append("secondary decision.json contradicts the v2 gate")
            if not gate.get("historical_record") or "IR-01" not in gate["historical_record"]:
                errors.append("the historical IR-01 record disclosure is missing from the gate")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"missing or malformed v2 release evidence: {type(exc).__name__}: {exc}")
        expected_meta = "SUBMIT"
        clearance_pages = {"index.html", "executive-summary.html", "how-to-submit.html", "submission.html"}
    else:
        errors.append(f"unknown release gate schema: {schema!r}")
        expected_meta, clearance_pages = "DO-NOT-SUBMIT", set()

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
            if parser.meta.get("gemsdoe-decision") != expected_meta:
                errors.append(f"{page.name}: missing or inconsistent decision meta")
        if page.parent == DOCS and page.name in clearance_pages:
            for needle in ("ok to download and submit", "sha-256", "ir-01", "estimates are estimates",
                           "0.195"):
                if needle not in folded:
                    errors.append(f"{page.name}: clearance page missing disclosure {needle!r}")
            if "cross-model" not in folded and "second opinion" not in folded:
                errors.append(f"{page.name}: clearance page missing the E2 cross-model disclosure")
        if page.parent == DOCS and page.name not in clearance_pages and page.parent == DOCS:
            if "ok to download and submit" in folded and page.name not in ("research.html", "evidence.html"):
                errors.append(f"{page.name}: unexpected clearance language")
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
    print(f"Site check PASS: {schema} decision, source hashes, saved bytes, disclosures, statuses and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
