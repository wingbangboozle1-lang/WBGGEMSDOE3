#!/usr/bin/env python3
"""Restore the pinned shared template and its hash-verified public data bridge.

The bridge is a peer-maintained mirror, not an authenticated DrivenData download.
The default also materializes the template's 19 ignored band caches.  No model,
holdout, candidate raster, or competition submission is created here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.template import ensure_template  # noqa: E402


def prepare_command(python_executable: str, template_root: Path) -> list[str]:
    """Return the upstream template's data-restore command; do not fork it."""
    script = Path(template_root) / "scripts" / "prepare_data.py"
    if not script.is_file():
        raise FileNotFoundError(f"pinned template data tool is missing: {script}")
    return [python_executable, str(script), "--fetch", "--cache-bands"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--template-only", action="store_true",
                      help="verify/restore only the pinned template archive; do not fetch data")
    mode.add_argument("--dry-run", action="store_true",
                      help="verify/restore the template and print, but do not run, the data command")
    args = parser.parse_args(argv)

    template = ensure_template()
    print(f"Pinned shared template verified: {template}")
    if args.template_only:
        print("Template-only mode: no data or band caches fetched.")
        return 0

    command = prepare_command(sys.executable, template)
    if args.dry_run:
        print("Would run in the pinned template directory:")
        print(" ".join(command))
        return 0

    # The upstream script performs SHA-256 checks and atomically assembles the
    # public mirror. Its `gh api` calls use the existing GitHub CLI connection;
    # no DrivenData credentials are requested or stored.
    subprocess.run(command, cwd=template, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
