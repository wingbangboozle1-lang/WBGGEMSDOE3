#!/usr/bin/env python3
"""Retired KHD positive site publisher.

The historical KHD builder declared SUBMISSION-READY despite a negative lane
card and a failed literal registry gate. Its earlier content-aware waiver is
not authorized. Preserve its evidence as historical data, but never render it
as a positive approval. Use scripts/build_site.py and scripts/check_site.py.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("BLOCKED: retired KHD positive publisher; use scripts/build_site.py and scripts/check_site.py.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
