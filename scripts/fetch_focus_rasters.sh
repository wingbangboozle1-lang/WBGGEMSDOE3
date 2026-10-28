#!/usr/bin/env bash
# Fetch the pinned comparator rasters listed in registry/focus_rasters_manifest.json into
# data/external/focus/ (gitignored) and verify every byte against the manifest SHA-256.
# Uses the GitHub API through `gh` (github.com/api.github.com are the allowed hosts here;
# raw.githubusercontent.com is not). Fails closed on any hash mismatch.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DEST="${1:-$ROOT/data/external/focus}"
mkdir -p "$DEST"
python3 - "$DEST" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
dest = Path(sys.argv[1])
man = json.loads(Path("registry/focus_rasters_manifest.json").read_text())
bad = 0
for e in man["entries"]:
    out = dest / e["file"]
    if not (out.exists() and hashlib.sha256(out.read_bytes()).hexdigest() == e["sha256"]):
        data = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                               f"repos/{e['repo']}/contents/{e['path']}?ref={e['ref']}"],
                              check=True, capture_output=True).stdout
        out.write_bytes(data)
    got = hashlib.sha256(out.read_bytes()).hexdigest()
    status = "OK " if got == e["sha256"] else "BAD"
    bad += got != e["sha256"]
    print(f"{status} {e['file']} {len(out.read_bytes())} {got[:16]}")
if bad:
    raise SystemExit(f"{bad} comparator(s) failed SHA-256 verification")
print(f"verified {len(man['entries'])} comparator rasters in {dest}")
PY
