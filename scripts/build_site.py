#!/usr/bin/env python3
"""Active site entry point for the 2026-10-27 SGCE decision.

The four top-level pages, the download index and the JSON copies are rendered deterministically by
``session2_site.py`` from committed evidence.  Historical helper names (``HCE_BANNER``,
``historical_h6_section``, ``human_age`` …) are re-exported from ``build_site_legacy`` so the CSPES,
RFL, HCE and LST1 lanes and their tests keep working after the merge of parallel sessions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_site_legacy import (  # noqa: E402,F401
    decision, esc, guide, historical_h6_section, layout, overview, research, evidence,
)
from hce_banner import HCE_BANNER  # noqa: E402,F401
from session2_site import human_age, main  # noqa: E402,F401


def build() -> None:
    """Compatibility alias used by the reproducibility tests."""
    return main()


if __name__ == "__main__":
    raise SystemExit(main() or 0)
