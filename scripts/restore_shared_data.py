#!/usr/bin/env python3
"""Restore the shared template's pinned data and cached feature bands, unchanged."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.template import ensure_template  # noqa: E402


def main() -> int:
    template = ensure_template()
    # The upstream tool owns its own paths, checks every SHA and uses no portal login.
    print(f"[shared template] {template}", flush=True)
    print("[provenance] public GitHub mirror; not an authenticated DrivenData receipt", flush=True)
    args = sys.argv[1:] or ["--fetch", "--cache-bands"]
    return subprocess.run([sys.executable, str(template / "scripts/prepare_data.py"), *args], cwd=template, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
