#!/usr/bin/env python3
"""Re-run the pinned, read-only nine-site and universal-witness audit."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.audit import audit  # noqa: E402
from gems_project.run_card import make_card  # noqa: E402


def main():
    try:
        result = audit()
    except Exception as error:
        # A failed check is never an implicit uniqueness pass.
        print(f"AUDIT INCOMPLETE / DO NOT SUBMIT: {error}", file=sys.stderr)
        return 2
    dest = ROOT / "evidence/focus_audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    card = make_card(dest)
    (ROOT / "evidence/run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"{result['status']}: {result['witness']['witness_positive_inside']} / {result['witness']['footprint_cells']} footprint cells positive in registered witness")
    print(f"Evidence: {dest.relative_to(ROOT)}. This audit created no candidate, ran no experiment, and used no competition slot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
