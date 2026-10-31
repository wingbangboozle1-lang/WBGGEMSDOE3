#!/usr/bin/env python3
"""Blocked retired FCHD publisher.

The former publisher copied a historical research TIFF and ZIP into a public
page with direct download links. That conflicts with the current fail-closed
project decision. Use ``scripts/build_site.py`` to render the research-only,
no-direct-download archive summary.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "BLOCKED: legacy FCHD publisher exposed an unapproved research TIFF/ZIP. "
        "Run scripts/build_site.py for the current fail-closed site.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
