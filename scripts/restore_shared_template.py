#!/usr/bin/env python3
"""Restore the unchanged, pinned shared evaluator/writer into an ignored cache.

No private fork is created. Upstream source has no license identified by the
GitHub API; check permission before redistribution or further use.
"""
from __future__ import annotations

import json
from pathlib import Path
from github_bytes import fetch_pinned

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "config/shared-template.json").read_text())
    target = ROOT / "data/cache/shared-template"
    for item in manifest["files"]:
        upstream = item["upstream_path"]
        if upstream.startswith("src/gems57/"):
            relative = Path("gems57") / Path(upstream).name
        elif upstream == "scripts/prepare_data.py":
            relative = Path("scripts/prepare_data.py")
        else:
            raise ValueError(f"unexpected template path: {upstream}")
        fetch_pinned(manifest["repository"], manifest["ref"], upstream,
                     target / relative, item["sha256"], item["bytes"])
    print(f"Verified {len(manifest['files'])} unmodified upstream files in {target}")
    print("No cached feature-stack arrays are included in this source checkout.")
    print("No upstream license was identified; do not redistribute without permission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
