#!/usr/bin/env python3
"""Independent check of the published GEMS site against the release gate.

`build_site.py` and this script deliberately share one verifier (`gems_project.site_gate`) and
nothing else: the builder assembles pages, the checker re-reads them from disk.  A check that
passes means the published pages, the published bytes and the saved evidence agree with each
other.  It does not mean the organizer accepted the file.

Two decisions are supported, and both are checked:

* SUBMIT          -- the candidate re-verifies from saved bytes, the pages point at exactly that
                     file, and nobody claims a score we do not have (no leaderboard projection,
                     no ORGANIZER-CONFIRMED number).
* DO-NOT-SUBMIT   -- the gate names its blocking reasons, the pages say so, and no download
                     button offers a TIFF.
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

from gems_project.site_gate import HOLDOUT_LABEL, verify_candidate  # noqa: E402

CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html",
              "method.html", "evidence.html", "session-review.html", "submission.html")
# Pages a visitor reaches before deciding whether to upload.
CLEARANCE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "submission.html")
# Claims that would overstate what we know, in either direction.
FORBIDDEN_ALWAYS = (
    "organizer-confirmed 0.",
    "projected leaderboard score",
    "expected leaderboard score",
    "guaranteed score",
    "this will rank",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.meta: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") in {"gemsdoe-decision", "gemsdoe-lane-decision"}:
            self.meta[a["name"]] = a.get("content", "")
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def parse(path: Path) -> tuple[PageParser, str]:
    p = PageParser()
    body = path.read_text(encoding="utf-8")
    p.feed(body)
    return p, " ".join(" ".join(p.text).split())


def check_evidence_numbers(gate: dict, errors: list[str]) -> None:
    """The gate must quote the evidence, not paraphrase it."""
    ev = gate.get("evidence", {})
    try:
        hold = json.loads((ROOT / ev["holdout"]).read_text())
        uniq = json.loads((ROOT / ev["uniqueness"]).read_text())
        can = json.loads((ROOT / ev["canary"]).read_text())
        card = json.loads((ROOT / ev["run_card"]).read_text())
    except (OSError, KeyError, ValueError) as exc:
        errors.append(f"evidence file missing or unreadable: {type(exc).__name__}: {exc}")
        return

    for i, f in enumerate(gate["holdout"]["folds"]):
        src = next(x for x in hold["folds"] if x["fold"] == f["fold"])
        if abs(src["corridor"]["dti"] - f["dti"]) > 1e-9:
            errors.append(f"fold {i}: gate DTI differs from holdout_final.json")
        if [round(c, 9) for c in src["corridor"]["ci95"]] != [round(c, 9) for c in f["ci95"]]:
            errors.append(f"fold {i}: gate CI differs from holdout_final.json")
    if abs(hold["pooled"]["dti_mean"] - gate["holdout"]["mean_dti"]) > 1e-9:
        errors.append("gate mean HOLDOUT-DTI differs from holdout_final.json")
    if hold.get("label") != gate["holdout"].get("protocol"):
        errors.append("gate holdout protocol label differs from the evidence")
    if gate["holdout"]["label"] != HOLDOUT_LABEL:
        errors.append("gate does not label the local proxy HOLDOUT-DTI")

    v = uniq["verdict"]
    if abs(v["max_cand_within_3px"] - gate["uniqueness"]["max_cand_within_3px"]) > 1e-9:
        errors.append("gate overlap differs from the uniqueness audit")
    if abs(v["max_spearman"] - gate["uniqueness"]["max_abs_spearman"]) > 1e-9:
        errors.append("gate |Spearman| differs from the uniqueness audit")
    if v["n_references"] != gate["uniqueness"]["n_references"]:
        errors.append("gate reference count differs from the uniqueness audit")

    if can["n_features"] != gate["canary"]["n_features"]:
        errors.append("gate canary feature count differs from the canary file")
    if abs(can["max_auc"] - gate["canary"]["max_auc"]) > 1e-12:
        errors.append("gate canary AUC differs from the canary file")

    if card.get("raster", {}).get("sha256") != gate["candidate"]["sha256"]:
        errors.append("run card raster SHA-256 differs from the gate candidate")
    if card.get("verdict") != "promote" or card.get("okay_to_submit") is not True:
        errors.append("run card is not a positive, promoting record")


def main() -> int:
    errors: list[str] = []
    gate_path = DOCS / "data" / "release_gate.json"
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"release gate missing or malformed: {exc}", file=sys.stderr)
        return 1

    if gate.get("schema") != "gems-release-gate-v2":
        errors.append("release gate is not schema gems-release-gate-v2")
    decision = gate.get("decision")
    if decision not in {"SUBMIT", "DO-NOT-SUBMIT"}:
        errors.append("release gate decision is not SUBMIT or DO-NOT-SUBMIT")

    reasons, facts = verify_candidate(gate, ROOT)
    errors += [f"gate condition failed: {r}" for r in reasons]
    if decision == "SUBMIT" and reasons:
        errors.append("gate claims SUBMIT but its conditions do not re-verify")
    if decision == "DO-NOT-SUBMIT" and not gate.get("blocking_reasons"):
        errors.append("negative gate lists no blocking reasons")
    if gate.get("okay_to_submit") is not (decision == "SUBMIT"):
        errors.append("okay_to_submit disagrees with the decision")
    if facts.get("sha256") != gate.get("candidate", {}).get("sha256"):
        errors.append("published TIFF hash differs from the gate")
    if not reasons:
        check_evidence_numbers(gate, errors)
        if not gate.get("uniqueness", {}).get("scope_statement"):
            errors.append("gate has no uniqueness scope statement")
        if len(gate.get("residual_risks", [])) < 3:
            errors.append("gate lists fewer than three residual risks")

    # ---- pages ------------------------------------------------------------------
    parsed: dict[str, tuple[PageParser, str]] = {}
    for rel in CORE_PAGES:
        path = DOCS / rel
        if not path.is_file():
            errors.append(f"missing required page: {rel}")
            continue
        p, text = parse(path)
        parsed[rel] = (p, text)
        if p.meta.get("gemsdoe-decision") != decision:
            errors.append(f"{rel}: meta decision {p.meta.get('gemsdoe-decision')!r} != gate {decision!r}")
        low = text.lower()
        for phrase in FORBIDDEN_ALWAYS:
            if phrase in low:
                errors.append(f"{rel}: forbidden overclaim: {phrase!r}")

    if decision == "SUBMIT":
        name = gate["candidate"]["submission_name"]
        fname = Path(gate["candidate"]["tif"]).name
        scope_head = gate["uniqueness"]["scope_statement"][:60]
        for rel in CLEARANCE_PAGES:
            if rel not in parsed:
                continue
            text = parsed[rel][1]
            if fname not in text:
                errors.append(f"{rel}: does not name the cleared file {fname}")
            if "cleared" not in text.lower():
                errors.append(f"{rel}: does not state that the file is cleared")
        for rel in ("index.html", "executive-summary.html", "how-to-submit.html"):
            if rel in parsed and scope_head not in parsed[rel][1]:
                errors.append(f"{rel}: does not disclose the uniqueness scope limit")
        if "how-to-submit.html" in parsed:
            text = parsed["how-to-submit.html"][1]
            if gate["candidate"]["note"] not in text:
                errors.append("how-to-submit.html: does not print the exact submission note")
            if gate["candidate"]["sha256"] not in text:
                errors.append("how-to-submit.html: does not print the full SHA-256")
        if "executive-summary.html" in parsed:
            text = parsed["executive-summary.html"][1]
            if HOLDOUT_LABEL not in text:
                errors.append("executive-summary.html: local score is not labelled HOLDOUT-DTI")
            if "OWNER-REPORTED" not in text.upper():
                errors.append("executive-summary.html: focus-site scores are not labelled owner-reported")
            if f"HOLDOUT-DTI {gate['holdout']['mean_dti']:.3f}" not in text:
                errors.append("executive-summary.html: table score differs from the gate mean")
        if "index.html" in parsed:
            hrefs = parsed["index.html"][0].targets
            if not any(urlparse(h).path.endswith(fname) for h in hrefs):
                errors.append("index.html: no download link to the cleared TIFF")
    else:
        for rel in CLEARANCE_PAGES:
            if rel in parsed and "do not submit" not in parsed[rel][1].lower():
                errors.append(f"{rel}: negative gate is not stated in visible text")

    # ---- download inventory ------------------------------------------------------
    downloads = DOCS / "downloads"
    dpath = downloads / "index.html"
    if not dpath.is_file():
        errors.append("missing downloads/index.html")
    else:
        dp, dtext = parse(dpath)
        if dp.meta.get("gemsdoe-decision") != decision:
            errors.append("downloads/index.html: meta decision disagrees with the gate")
        tif_links = {Path(urlparse(u).path).name for u in dp.targets
                     if Path(urlparse(u).path).suffix.lower() == ".tif"}
        if decision == "SUBMIT":
            cleared = Path(gate["candidate"]["tif"]).name
            if cleared not in tif_links:
                errors.append("downloads/index.html: cleared TIFF is not linked")
            stray = tif_links - {cleared}
            if stray:
                errors.append(f"downloads/index.html links non-cleared TIFFs: {sorted(stray)}")
        elif tif_links:
            errors.append("negative gate but downloads/index.html still links a TIFF")

    notice = downloads / "LEGACY-DO-NOT-SUBMIT.txt"
    try:
        lines = notice.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"missing legacy notice: {exc}")
        lines = []
    if lines:
        present = {p.name for p in downloads.glob("*.tif")}
        cleared = Path(gate["candidate"]["tif"]).name if decision == "SUBMIT" else None
        if cleared:
            if cleared not in present:
                errors.append("cleared TIFF is not published under docs/downloads")
            i = lines.index("CLEARED (see ../data/release_gate.json):") if any(
                "CLEARED (see" in ln for ln in lines) else None
            if i is None:
                errors.append("legacy notice has no CLEARED section")
            else:
                cleared_lines = []
                for ln in lines[i + 1:]:
                    if ln.startswith("  "):
                        cleared_lines.append(ln.strip())
                    else:
                        break
                cleared_listed = {x for x in cleared_lines if x.lower().endswith(".tif")}
                if cleared_listed != {cleared}:
                    errors.append(f"legacy notice cleared section is {sorted(cleared_listed)}, expected [{cleared}]")
        legacy_listed = {ln.strip() for ln in lines if ln.startswith("  ") and ln.strip().lower().endswith(".tif")}
        expected_legacy = present - ({cleared} if cleared else set())
        missing = expected_legacy - legacy_listed
        if missing:
            errors.append(f"legacy notice omits research-only TIFFs: {sorted(missing)}")
        if not any("DO NOT SUBMIT" in ln for ln in lines):
            errors.append("legacy notice does not state DO NOT SUBMIT for the archive")

    # ---- links -------------------------------------------------------------------
    for page in sorted(DOCS.rglob("*.html")):
        p, _ = parse(page)
        rel = str(page.relative_to(DOCS))
        for link in p.targets:
            parsed_link = urlparse(link)
            if parsed_link.scheme or parsed_link.netloc or not parsed_link.path:
                continue
            target = (page.parent / unquote(parsed_link.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.is_file():
                errors.append(f"{rel}: missing/unsafe local link {link}")

    # ---- published copies of the evidence ---------------------------------------
    pub = DOCS / "data"
    for rel in gate.get("evidence", {}).values():
        p = ROOT / rel
        if not p.is_file():
            continue
        copy = pub / p.name
        if copy.is_file() and sha(copy) != sha(p):
            errors.append(f"published copy of {p.name} differs from its source evidence")
    for name in ("release_gate.json", "run_card.json"):
        if not (pub / name).is_file():
            errors.append(f"docs/data/{name} is missing")

    if errors:
        print("\n".join(dict.fromkeys(errors)), file=sys.stderr)
        return 1
    print(f"Site check PASS: gate {decision}, {len(gate.get('blocking_reasons', []))} blocking reason(s), "
          f"evidence re-verified, download inventory consistent, local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
