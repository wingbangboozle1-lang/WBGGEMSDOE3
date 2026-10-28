#!/usr/bin/env python3
"""Fetch the nine owner-published focus TIFFs at their pinned commit SHAs (fail closed).

Source: GitHub API (``gh api repos/<owner>/<repo>/contents/<path>?ref=<sha>``), the same
mechanism as ``scripts/fetch_mirrors.sh``.  Every file must match the sha256 pinned in
``registry/focus_sites.json``; any mismatch aborts with a non-zero exit and the bad bytes are
removed.  Owner bytes establish byte identity only, not organizer provenance.

Writes to ``.cache/focus/`` (git-ignored).  Requires an authenticated ``gh`` or GH_TOKEN.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "registry" / "focus_sites.json"
DEST = ROOT / ".cache" / "focus"
OWNER = "buffedlizard55-lab"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    spec = json.loads(SPEC.read_text())
    bad = []
    for f in spec["sites"]:
        repo = f["site"]
        path = f["path"]
        name = Path(path).name
        out = DEST / name
        proc = subprocess.run(
            ["gh", "api", f"repos/{OWNER}/{repo}/contents/{path}?ref={f['ref']}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if proc.returncode != 0:
            bad.append((repo, "gh api failed", proc.stderr.decode(errors="replace")[:200]))
            continue
        out.write_bytes(proc.stdout)
        digest = hashlib.sha256(proc.stdout).hexdigest()
        if digest != f["sha256"]:
            out.unlink(missing_ok=True)
            bad.append((repo, "sha256 mismatch", digest))
            continue
        print(f"OK {repo} {name} {len(proc.stdout)} bytes sha256={digest[:16]}")
    if bad:
        for b in bad:
            print("FAIL", *b, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
