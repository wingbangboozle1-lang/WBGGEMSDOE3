#!/usr/bin/env python3
"""Retired legacy evidence renderer.

The historical implementation imported a renderer that emitted positive
submission instructions and could leave a mixed-status site. The current
evidence page is built as part of scripts/build_site.py from reviewed evidence.
"""
import sys


def main() -> int:
    print("BLOCKED: use scripts/build_site.py to render the consistent negative site.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
