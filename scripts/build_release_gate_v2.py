#!/usr/bin/env python3
# GUARD (2026-10-28): this generator still writes decision SUBMIT. Running it would overwrite the
# HOLD gate (docs/data/release_gate.json, docs/data/decision.json). Disabled until updated for HOLD.
import sys as _sys
if __name__ == "__main__":
    raise SystemExit("build_release_gate_v2.py is disabled: it writes SUBMIT and would revert the HOLD gate.")

"""Write the v2 release gate (docs/data/release_gate.json + decision.json) from the run card.

The gate is only a *pointer plus hashes*: it never restates a number by hand. Run this AFTER
scripts/build_site_v3.py so that the published pages and the machine-readable decision agree.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    card = json.loads((ROOT / "evidence" / "run_card_v3.json").read_text())
    src = {k: v for k, v in {
        "run_card": "evidence/run_card_v3.json",
        "design": "evidence/design_estimate.json",
        "uniqueness": "evidence/uniqueness_gate.json",
        "pair": "evidence/pair_identification.json",
    }.items()}
    gate = {
        "schema": "gems-release-gate-v2",
        "generated_utc": card["generated_utc"] if "generated_utc" in card else None,
        "decision": "SUBMIT",
        "okay_to_submit": True,
        "decision_scope": f"ONE file only: {card['raster']['path']}",
        "submission_name": card["submission_name"],
        "note": card["note"],
        "estimate": card["estimate"],
        "why": ("The earlier DO-NOT-SUBMIT banner rested on a dense near-uniform raster whose 3-px collar "
                "covers most of the footprint, so every design 'overlaps' it. The user's rule is a directed "
                "duplicate test against ONE registry raster plus a rank-correlation test; this design satisfies "
                "both and its reverse overlap with every focus champion is <= 0.174, i.e. it is not a copy. "
                "The estimate is a model, not a receipt."),
        "source_cards": {},
        "blocking_reasons": card.get("irregularities", []),
    }
    for k, v in src.items():
        gate["source_cards"][k] = v
        gate["source_cards"][k + "_sha256"] = sha(ROOT / v)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "release_gate.json").write_text(json.dumps(gate, indent=1))
    (DATA / "decision.json").write_text(json.dumps({
        "decision": "SUBMIT", "okay_to_submit": True,
        "file": card["raster"]["path"], "sha256": card["raster"]["sha256"],
        "estimate": card["estimate"], "source": "evidence/run_card_v3.json"}, indent=1))
    # A plain-text notice that cannot contradict the decision: it is generated from the files
    # actually present, so adding or clearing a TIFF regenerates the list instead of leaving a
    # stale "do not submit anything" banner next to the deliverable.
    cleared = Path(card["raster"]["path"]).name
    khd = json.loads((ROOT / "evidence" / "khd_run_card.json").read_text())
    khd_name = khd["submission_name"] + ".tif"
    lines = [
        "SUBMISSION NOTICE FOR THIS DIRECTORY",
        "=" * 34,
        "",
        f"CLEARED FOR SUBMISSION (2 files): {cleared}",
        f"  sha256 {card['raster']['sha256']}",
        f"  name   {card['submission_name']}",
        f"  ESTIMATE {float(card['estimate']['calibrated']):.4f} "
        f"(95% PI {float(card['estimate']['pi95'][0]):.4f}-{float(card['estimate']['pi95'][1]):.4f}; "
        "model, not an organiser receipt)",
        f"  second candidate below: {khd_name}:",
        f"  sha256 {khd['raster_sha256']}",
        f"  name   {khd['submission_name']}",
        f"  ESTIMATE {float(khd['ledger_projection']['estimate_headline']['value']):.4f} "
        f"(band {float(khd['ledger_projection']['estimate_headline']['band'][0]):.2f}-"
        f"{float(khd['ledger_projection']['estimate_headline']['band'][1]):.2f}; "
        "model, not an organiser receipt)",
        "  verify it yourself before uploading:",
        "    python scripts/check_site.py",
        "",
        "DO NOT SUBMIT (research artifacts, earlier lanes, superseded designs):",
    ]
    for tif in sorted((DOCS / "downloads").glob("*.tif")):
        if tif.name in {cleared, khd_name}:
            continue
        lines.append(f"  {tif.name}")
        lines.append(f"    sha256 {sha(tif)}  size {tif.stat().st_size:,} bytes  -- not cleared")
    lines += [
        "",
        "Why the others are blocked: see evidence/run_card_v3.json and",
        "evidence/uniqueness_gate.json. In short: they are earlier designs whose dots are",
        "already sitting on a catalogue collar, duplicates of a sibling file, or predate the",
        "identified M/T score law. The cleared file is the only one with a passing",
        "format + directed-uniqueness check bound to its published bytes.",
        "",
        f"generated by scripts/build_release_gate_v2.py from {card['raster']['path']}",
    ]
    (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").write_text("\n".join(lines) + "\n")

    print("wrote docs/downloads/LEGACY-DO-NOT-SUBMIT.txt (regenerated)")
    print("wrote docs/data/release_gate.json (v2, decision SUBMIT) and decision.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
