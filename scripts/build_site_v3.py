#!/usr/bin/env python3
"""Retired positive site publisher.

This historical renderer advertised SUBMIT without satisfying the controlling
literal-registry rule and comparable holdout gate. It is intentionally inert.
Use scripts/build_site.py followed by scripts/check_site.py; do not restore the
historical approval path.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("BLOCKED: retired positive publisher; use scripts/build_site.py and scripts/check_site.py.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
