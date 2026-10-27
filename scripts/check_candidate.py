"""Read-only, fail-closed format diagnostic; it cannot authorize a submission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems_project.format_preflight import raster_report  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--template', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = raster_report(args.candidate, args.template)
    except Exception as exc:
        print(json.dumps({'format_ok': False, 'approved_for_submission': False,
                          'error': f'{type(exc).__name__}: {exc}'}, indent=2))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['format_ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
