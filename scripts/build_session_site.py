#!/usr/bin/env python3
"""Retired session-specific publisher.

The historical renderer included a click-to-submit flow for a negative lane and
could publish it without the current global gate. The canonical site is
scripts/build_site.py, which publishes the fail-closed repository-wide decision.
"""
import sys


def main() -> int:
    print(
        "BLOCKED: build_session_site.py is retired; it could publish upload steps "
        "for a negative lane. Use scripts/build_site.py instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
