#!/usr/bin/env python3
"""Re-run the format and uniqueness gates on an emitted candidate, without refitting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import shared, validate  # noqa: E402

EVID = ROOT / "evidence" / "release"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("--collar", type=float, default=3.0)
    args = ap.parse_args()
    card_path = EVID / "candidate_run_card.json"
    card = json.loads(card_path.read_text())
    path = Path(args.file) if args.file else ROOT / card["submission"]["path"]
    footprint, catalogue = shared.load_masks()
    comparators = json.loads((EVID / "comparators.json").read_text())["comparators"]
    fmt = validate.validate_format(path, footprint, catalogue, collar_px=args.collar)
    uniq = validate.uniqueness_audit(path, footprint, catalogue, comparators)
    card["submission"]["file"] = path.name
    card["submission"]["path"] = str(path.relative_to(ROOT))
    card["submission"]["sha256"] = fmt["detail"]["sha256"]
    card["format_validator"] = fmt
    card["uniqueness_audit"] = uniq
    card["verdict"] = "promote" if (fmt["passed"] and uniq["passed"]) else "negative"
    card_path.write_text(json.dumps(card, indent=2) + "\n")

    # Rewrite the downloadable receipt from the freshly measured card. The receipt
    # and the card must never disagree: the receipt is what a visitor reads after
    # clicking "Download its receipt (JSON)", so a stale copy is a published claim.
    receipt = path.parent / (path.stem + ".json")
    receipt.write_text(json.dumps({
        "file": path.name, "sha256": fmt["detail"]["sha256"], "dots": fmt["detail"]["dots"],
        "note": card["note"], "format_passed": fmt["passed"],
        "uniqueness_passed": uniq["passed"],
        "format_checks": fmt["checks"], "uniqueness_checks": uniq["checks"],
        "rules": shared.SOURCES,
    }, indent=2) + "\n")
    print(json.dumps({"receipt": str(receipt.relative_to(ROOT)),
                      "format": fmt["passed"], "uniqueness": uniq["passed"],
                      "failed": [k for k, v in fmt["checks"].items() if not v]
                      + [k for k, v in uniq["checks"].items() if not v],
                      "worst_overlap": round(uniq["worst_overlap_within_3px"], 4),
                      "worst_abs_rho": round(uniq["worst_abs_spearman"], 4)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
