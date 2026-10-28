#!/usr/bin/env python3
"""Retired schema-v2 positive release-gate publisher.

The historical generator could declare SUBMIT while its evidence lacked a
literal registry pass and a comparable candidate holdout. It is intentionally
inert so stale positive pages cannot be recreated by an easy command.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("BLOCKED: schema-v2 positive release publisher is retired; use scripts/build_site.py.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
