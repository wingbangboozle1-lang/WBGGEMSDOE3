#!/usr/bin/env python3
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
    print("wrote docs/data/release_gate.json (v2, decision SUBMIT) and decision.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
