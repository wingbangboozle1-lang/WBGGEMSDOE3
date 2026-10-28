#!/usr/bin/env python3
"""Retired positive dossier generator.

The previous implementation contained stale SUBMIT-WITH-CAVEAT content and a
content-aware uniqueness waiver. Do not use it to rewrite docs/. Run the
fail-closed scripts/build_site.py and scripts/check_site.py instead.
"""
from __future__ import annotations

import sys


def main() -> int:
    print("BLOCKED: retired positive dossier generator; use scripts/build_site.py and scripts/check_site.py.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
