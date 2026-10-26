"""Read-only format preflight. This command cannot authorize submission."""
import argparse
import json
from pathlib import Path
from audit import inspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--template', type=Path, required=True)
    args = parser.parse_args()
    _, _, result = inspect(args.candidate, args.template)
    result['format_preflight_passed'] = (result['inside_values_in_0_1']
        and result['all_finite_values_in_0_1'] and result['no_inf_anywhere'])
    result['ok_to_submit'] = False
    result['reason'] = 'Format is necessary, not sufficient. Full scientific/novelty gates and separate selector required.'
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['format_preflight_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
