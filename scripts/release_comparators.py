#!/usr/bin/env python3
"""Write the comparator manifest used by the automated uniqueness gate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CACHE = ROOT / ".cache" / "comparators" / "focus9"
OUT = ROOT / "evidence" / "release" / "comparators.json"


def main() -> int:
    import rasterio

    focus = json.loads((ROOT / "evidence" / "release" / "focus_sites.json").read_text())
    rows = []
    for rec in focus["sites"]:
        path = CACHE / f"{rec['site']}__{rec['file']}"
        if not path.is_file():
            continue
        with rasterio.open(path) as src:
            shape = [src.height, src.width]
        rows.append({
            "site": rec["site"], "name": rec["file"], "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size, "shape": shape,
            "owner_reported_score": rec["owner_reported_score"],
            "dots": rec.get("dots"),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_by": "scripts/release_comparators.py",
        "provenance": "bytes fetched with the GitHub contents API at the commit "
                      "pinned by evidence/release/focus_sites.json; the repositories "
                      "are public mirrors and these files are not organizer receipts",
        "comparators": rows,
    }, indent=2) + "\n")
    print(f"{len(rows)} comparators -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
