#!/usr/bin/env python3
"""Audit preserved parallel artifacts and update the single negative run card."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems_project.concurrent_audit import audit_concurrent  # noqa: E402
from gems_project.run_card import make_card  # noqa: E402


def main():
    try:
        result = audit_concurrent()
        path = ROOT / 'evidence/concurrent_audit.json'
        path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        card = make_card(ROOT / 'evidence/focus_audit.json')
        (ROOT / 'evidence/run_card.json').write_text(json.dumps(card, indent=2, allow_nan=False) + '\n')
    except Exception as exc:
        print(f'PARALLEL AUDIT INCOMPLETE / DO NOT SUBMIT: {exc}', file=sys.stderr)
        return 2
    print(result['conclusion'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
