#!/usr/bin/env python3
"""Deprecated entry point kept for the CI workflows and import compatibility.

The four top-level pages and ``docs/data/run_card.json`` are now rendered by
``scripts/build_dossier.py`` from ``evidence/*.json`` only.  This module delegates to it and
re-exports the historical dashboard helpers from ``build_site_legacy`` so that older tests, the
CSPES lane and the freshness feed keep working.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hce_banner import HCE_BANNER  # noqa: E402,F401
from build_site_legacy import (  # noqa: E402,F401
    decision, esc, guide, historical_h6_section, human_age, layout, overview,
)

__all__ = ["build", "main", "human_age", "overview", "guide", "historical_h6_section", "HCE_BANNER"]


def build() -> int:
    """Rebuild the dossier pages (pure function of the evidence files)."""
    from build_dossier import main as dossier_main
    return dossier_main()


def main() -> int:
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
