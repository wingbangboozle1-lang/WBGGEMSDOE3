#!/usr/bin/env python3
"""Generate the fail-closed repository-wide release decision.

This script does not generate a raster or select a competition slot.  It only
reconciles the governing run card with a lane candidate card so that the site
cannot advertise a lane-local proxy result as upload clearance.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    authority_path = ROOT / "evidence" / "run_card.json"
    candidate_path = ROOT / "evidence" / "gemsdoe_run_card.json"
    authority = json.loads(authority_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    gate = evaluate_release_gate(authority, candidate)
    gate["source_cards"] = {
        "authority": str(authority_path.relative_to(ROOT)),
        "authority_sha256": digest(authority_path),
        "candidate": str(candidate_path.relative_to(ROOT)),
        "candidate_sha256": digest(candidate_path),
    }
    out = ROOT / "evidence" / "release_gate.json"
    out.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    print(f"{gate['decision']}: wrote {out.relative_to(ROOT)}")
    return 0 if gate["okay_to_submit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
