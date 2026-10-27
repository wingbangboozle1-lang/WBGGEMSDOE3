#!/usr/bin/env python3
"""Retired LST1 candidate builder; it cannot satisfy the current literal registry rule.

The historical TIFF and evidence remain available under the LST1 research namespace.
This entrypoint intentionally creates or overwrites no raster. Do not restore its old
lattice-null exemption or use it to select a competition slot.
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "DISABLED / DO NOT SUBMIT: the historical LST1 builder uses a lattice-null "
        "uniqueness exception, while the current protocol applies the 70% rule to "
        "every registered raster. The pinned full-footprint witness blocks every "
        "nonempty candidate. See evidence/run_card.json and README.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
