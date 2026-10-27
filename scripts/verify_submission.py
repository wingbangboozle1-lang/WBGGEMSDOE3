#!/usr/bin/env python3
"""Retired historical verifier; its lattice-null test cannot clear an artifact."""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "DISABLED / NOT AUTHORITATIVE: the historical independent verifier exempts "
        "lattice-like rasters and checks only a subset of the current registry. "
        "It cannot establish literal-rule uniqueness or submission approval. See "
        "evidence/lst1_run_card.json and scripts/check_candidate.py.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
