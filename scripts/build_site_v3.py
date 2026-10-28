#!/usr/bin/env python3
"""Retired unsafe renderer.

The former version rendered an INVDESIGN TIFF as cleared despite having no
compliant HOLDOUT-DTI and omitting a registered dense raster from its literal
uniqueness decision. The current builder is scripts/build_site.py, which
publishes the negative gate. Do not restore this renderer without a separately
reviewed protocol change and complete evidence.
"""
import sys


def main() -> int:
    print(
        "BLOCKED: build_site_v3.py is retired; it can publish unsupported upload approval. "
        "Run scripts/build_site.py and scripts/check_site.py instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
