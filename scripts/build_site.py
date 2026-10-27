#!/usr/bin/env python3
"""Compatibility entry point for the 2026-10-27 SGCE decision site.

The full deterministic generator lives in session2_site.py.  Keeping this module (and the
``human_age`` / ``build`` names) preserves the historical tests and the CI commands while the
published decision now reflects the new positive evidence card.
"""
from __future__ import annotations

from session2_site import esc, human_age, layout, main  # noqa: F401


def build() -> None:
    """Compatibility alias used by the reproducibility tests."""
    main()


if __name__ == "__main__":
    raise SystemExit(main())
