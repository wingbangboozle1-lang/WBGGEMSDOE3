"""Fail-closed entry point; the former finalizer emitted an unsafe UNIQUE_PASS.

The prior finalizer treated a saved binary TIFF as its own continuous surface,
compared an incomplete local raster subset, and could overwrite the evidence
card with an unverified projection. The current candidate fails the registered-
lattice overlap lower bound. This entry point writes no files and cannot approve
or finalize an upload. See evidence/run_card.json for the current review card.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "evidence" / "run_card.json"


def main() -> int:
    card = json.loads(CARD.read_text())
    print(json.dumps({
        "status": "BLOCKED_NOT_FINALIZED",
        "card": str(CARD.relative_to(ROOT)),
        "verdict": card["verdict"],
        "raster_sha256": card["raster_sha256"],
        "ok_to_submit": card["submission"]["submit_allowed"],
        "reason": "Missing lane, holdout inputs and complete registry; literal lattice-overlap bound fails. No evidence or TIFF was rewritten.",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
