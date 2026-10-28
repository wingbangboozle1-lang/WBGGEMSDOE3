#!/usr/bin/env python3
"""Fail-closed consistency check for the repository-wide DO-NOT-SUBMIT site.

This is a publication consistency check, not an organizer validator. It re-evaluates the
committed authority and candidate cards with the shared release-gate function, binds the
published negative decision to source hashes, checks the mirrored-witness measurement and
archived bytes, verifies current pages/download labels, rejects positive site-wide metadata,
and resolves local HTML links.
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
sys.path.insert(0, str(ROOT / "src"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402

AUTHORITY = ROOT / "evidence/session_9b794637_run_card.json"
CANDIDATE = ROOT / "evidence/session2_run_card.json"
WITNESS_AUDIT = ROOT / "evidence/session_c1e656ce_witness_recheck.json"
CANDIDATE_TIF = "wbggems3-sgce-20261027-f52d35d8-zeros.tif"
CURRENT_PAGES = (
    "index.html", "executive-summary.html", "how-to-submit.html", "research.html",
    "method.html", "evidence.html", "session-review.html", "submission.html",
    "downloads/index.html",
)
FORBIDDEN_POSITIVE = (
    "ok to download and submit",
    "one file cleared for upload",
    "one submission raster is ready",
    "cleared unique submission artifact",
    "submit-with-caveat",
    "the only file cleared for upload",
    "this file is cleared for submission",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[attrs["name"]] = attrs.get("content", "")
        for key in ("href", "src"):
            if attrs.get(key):
                self.targets.append(attrs[key])

    def handle_data(self, data):
        self.text.append(data)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    try:
        gate = _load(DOCS / "data/release_gate.json")
        authority = _load(AUTHORITY)
        candidate = _load(CANDIDATE)
        expected = evaluate_release_gate(authority, candidate)
        if gate.get("schema") != "gems-release-gate-v1":
            errors.append("release gate schema is not the fail-closed v1 schema")
        if gate.get("decision") != "DO-NOT-SUBMIT" or gate.get("okay_to_submit") is not False:
            errors.append("published release gate is not DO-NOT-SUBMIT")
        if gate.get("candidate") != expected.get("candidate"):
            errors.append("published candidate summary differs from the shared evaluator")
        if gate.get("authority") != expected.get("authority"):
            errors.append("published authority summary differs from the shared evaluator")
        if not set(expected["blocking_reasons"]).issubset(set(gate.get("blocking_reasons", []))):
            errors.append("published release gate omits one or more shared blocking reasons")
        if not gate.get("source_cards"):
            errors.append("release gate has no source-card hash bindings")
        for key in ("authority", "candidate", "witness_audit"):
            rel = gate["source_cards"].get(key)
            expected_sha = gate["source_cards"].get(f"{key}_sha256")
            if not isinstance(rel, str) or not isinstance(expected_sha, str):
                errors.append(f"release gate source binding is incomplete: {key}")
                continue
            source = ROOT / rel
            if not source.is_file() or sha(source) != expected_sha:
                errors.append(f"release gate source SHA-256 mismatch: {key}")
        if gate.get("source_cards", {}).get("authority") != "evidence/session_9b794637_run_card.json":
            errors.append("release gate points at an unexpected authority card")
        if gate.get("source_cards", {}).get("candidate") != "evidence/session2_run_card.json":
            errors.append("release gate points at an unexpected historical candidate card")
        if gate.get("source_cards", {}).get("witness_audit") != "evidence/session_c1e656ce_witness_recheck.json":
            errors.append("release gate points at an unexpected witness audit")
        if gate.get("okay_to_download_for_research") is not True:
            errors.append("historical research-download status is missing")

        decision = _load(DOCS / "data/decision.json")
        if (decision.get("decision") != "DO-NOT-SUBMIT"
                or decision.get("okay_to_submit") is not False
                or decision.get("candidate") is not None
                or decision.get("source") != "release_gate.json"):
            errors.append("secondary decision.json is stale or contradicts the release gate")
        if (DOCS / "data/run_card.json").read_bytes() != AUTHORITY.read_bytes():
            errors.append("published run_card.json does not equal the current authority card")

        witness = _load(WITNESS_AUDIT)
        w = witness.get("witness", {})
        c = witness.get("candidate", {})
        if (witness.get("approved_for_submission") is not False
                or witness.get("verdict") != "negative"
                or w.get("registered") is not True
                or w.get("universal_blocker") is not True
                or not isinstance(w.get("footprint_cells"), int)
                or w.get("witness_positive_inside") != w.get("footprint_cells")
                or c.get("literal_duplicate") is not True
                or c.get("directed_overlap_within_3px_all_positive") != 1.0):
            errors.append("current saved-byte witness audit no longer supports the documented conditional stop")
        if w.get("definition") != "finite, GDAL-valid value > 0; directed Euclidean overlap <= 3 pixels":
            errors.append("witness support definition changed; review the duplicate interpretation")
        if sha(ROOT / "registry/registry_session2.json") != w.get("registry_sha256"):
            errors.append("pinned registry-index hash changed")
        candidate_file = DOCS / "downloads" / CANDIDATE_TIF
        submission_file = ROOT / "submission" / CANDIDATE_TIF
        if not candidate_file.is_file() or sha(candidate_file) != c.get("sha256"):
            errors.append("archived SGCE research TIFF does not match the witness audit")
        if not submission_file.is_file() or sha(submission_file) != c.get("sha256"):
            errors.append("source SGCE research TIFF does not match the witness audit")

        review = _load(ROOT / "evidence/session_c1e656ce_run_card.json")
        if (review.get("branch") != "arena/c1e656ce-wbggemsdoe3"
                or review.get("verdict") != "negative"
                or review.get("submission_name") is not None
                or review.get("raster_sha256") is not None
                or review.get("selector_approval") is not False
                or review.get("experiments_run") != 0
                or review.get("weekly_slots_used") != 0
                or review.get("holdout_dti", {}).get("status") != "NOT RUN"
                or review.get("registry_comparison", {}).get("new_candidate_tested") is not False
                or review.get("validator_output", {}).get("new_raster_generated") is not False
                or len(review.get("submission_note", "")) > 140):
            errors.append("current session run card is missing a fail-closed field or exceeds the note limit")
        if (DOCS / "data/session_c1e656ce_run_card.json").read_bytes() != (ROOT / "evidence/session_c1e656ce_run_card.json").read_bytes():
            errors.append("published current review run card differs from its source")
        if (DOCS / "data/pair_identification.json").read_bytes() != (ROOT / "evidence/pair_identification.json").read_bytes():
            errors.append("published pair-identification record differs from its source")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"missing or malformed fail-closed evidence: {type(exc).__name__}: {exc}")

    for rel in CURRENT_PAGES:
        if not (DOCS / rel).is_file():
            errors.append(f"missing current page: {rel}")

    downloads = DOCS / "downloads"
    tif_names = {p.name for p in downloads.glob("*.tif")}
    if (downloads / "LEGACY-DO-NOT-SUBMIT.txt").is_file():
        notice = (downloads / "LEGACY-DO-NOT-SUBMIT.txt").read_text(encoding="utf-8")
        for name in tif_names:
            if name not in notice:
                errors.append(f"plain-text archive notice omits TIFF: {name}")
        if "No TIFF in this directory is cleared" not in notice:
            errors.append("plain-text archive notice does not state that no TIFF is cleared")
    else:
        errors.append("missing plain-text DO-NOT-SUBMIT archive notice")

    current_page_set = set(CURRENT_PAGES)
    for page in sorted(DOCS.rglob("*.html")):
        rel = str(page.relative_to(DOCS))
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        text = " ".join(" ".join(parser.text).lower().split())
        if rel in current_page_set:
            if parser.meta.get("gemsdoe-decision") != "DO-NOT-SUBMIT":
                errors.append(f"{rel}: current page lacks the negative repository decision meta")
            if "do not submit" not in text and "no file is cleared" not in text:
                errors.append(f"{rel}: current page lacks visible negative status")
            for phrase in FORBIDDEN_POSITIVE:
                if phrase in text:
                    errors.append(f"{rel}: contains positive-release phrase {phrase!r}")
        if parser.meta.get("gemsdoe-decision") not in (None, "DO-NOT-SUBMIT"):
            errors.append(f"{rel}: positive repository-wide decision meta is forbidden")
        if parser.meta.get("gemsdoe-lane-decision") not in (None, "DO-NOT-SUBMIT"):
            errors.append(f"{rel}: positive lane decision meta is forbidden")
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: missing or unsafe local link {link}")

    if (DOCS / "downloads/index.html").is_file():
        page = PageParser()
        page.feed((DOCS / "downloads/index.html").read_text(encoding="utf-8"))
        linked_tifs = {Path(unquote(urlparse(link).path)).name for link in page.targets
                       if urlparse(link).path.lower().endswith(".tif")}
        if linked_tifs != tif_names:
            errors.append(f"downloads index TIFF inventory differs from archive: {linked_tifs ^ tif_names}")
        if "research only · do not submit" not in " ".join(page.text).lower():
            errors.append("downloads index does not label the TIFFs research-only")

    if (DOCS / "executive-summary.html").is_file():
        summary = (DOCS / "executive-summary.html").read_text(encoding="utf-8")
        for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                     "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
            if site not in summary:
                errors.append(f"nine-site executive summary omits {site}")
        lower = summary.lower()
        if "owner-reported" not in lower or "not estimable" not in lower or "0.2778" not in summary:
            errors.append("nine-site executive summary lacks evidence classes, estimate status, or GEMSDOE32 claim")
        if "0.3047" in summary or "0.2948" in summary:
            errors.append("nine-site executive summary republishes stale ledger-inversion estimates")

    for path in sorted(DOCS.rglob("*.json")):
        try:
            data = _load(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path.relative_to(DOCS)}: malformed published JSON: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        decision = str(data.get("decision", "")).upper()
        if data.get("okay_to_submit") is True or decision in {"SUBMIT", "SUBMISSION-READY", "SUBMIT-WITH-CAVEAT"}:
            errors.append(f"{path.relative_to(DOCS)}: stale positive machine-readable release claim")
        if (isinstance(data.get("verdict"), str)
                and data.get("verdict") in {"promote", "promote-with-caveat"}
                and not data.get("_archive_notice")):
            errors.append(f"{path.relative_to(DOCS)}: unmarked historical promote card")

    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    if "python scripts/build_site.py && python scripts/check_site.py" not in workflow:
        errors.append("Pages workflow does not build and check the fail-closed site")
    if "build_site_v3.py" in workflow or "build_evidence_page.py" in workflow:
        errors.append("Pages workflow invokes a retired positive publisher")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Site check PASS: negative v1 gate, bound evidence, research-only downloads, current pages and local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
