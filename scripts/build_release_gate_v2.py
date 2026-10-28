#!/usr/bin/env python3
"""Retired unsafe positive gate generator.

The former v2 script promoted a candidate based on a limited registry set and
without the required HOLDOUT-DTI. It is intentionally blocked. The current
repository-wide gate is regenerated from the reviewed negative evidence by
scripts/build_site.py.
"""
import sys


def main() -> int:
    print(
        "BLOCKED: positive release-gate-v2 generation is retired. "
        "No current candidate satisfies the literal registry and holdout rules.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
