#!/usr/bin/env python3
"""Retired positive evidence-page writer.

The historical implementation imported the v3 positive renderer and wrote an
unqualified SUBMIT meta tag. All current pages must be generated together by
the negative, hash-bound site builder.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("BLOCKED: retired evidence writer; use scripts/build_site.py and scripts/check_site.py.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
