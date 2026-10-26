#!/usr/bin/env python3
"""Download every scored raster pinned in registry/upstream_live_ledger_rasters.json and verify sha256.

Source of the pins: GEMSDOE32 evidence/live_ledger_rasters.json (owner repos on github.com).
Scores are OWNER-REPORTED (no organizer receipts).  A file whose sha256 differs from its pin is
rejected (never silently used).  Output: data/ledger/<site>__<name>.tif + data/ledger/index.json
Usage: python scripts/fetch_ledger_rasters.py [--jobs 4]
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"


def fetch(row: dict, out_dir: Path) -> dict:
    name = f"{row['site']}__{Path(row['path']).name}"
    out = out_dir / name
    if not (out.exists() and hashlib.sha256(out.read_bytes()).hexdigest() == row["sha256"]):
        with out.open("wb") as fh:
            r = subprocess.run(["gh", "api", f"repos/{OWNER}/{row['repo']}/contents/{row['path']}?ref={row['ref']}",
                                "-H", "Accept: application/vnd.github.raw"], stdout=fh)
        if r.returncode != 0:
            out.unlink(missing_ok=True)
            return dict(row, status="download_failed", local=None)
    got = hashlib.sha256(out.read_bytes()).hexdigest()
    ok = got == row["sha256"]
    if not ok:
        out.unlink(missing_ok=True)
    return dict(site=row["site"], submission=row["submission"], score=row["score"], repo=row["repo"], path=row["path"],
                sha256=row["sha256"], local=str(out.relative_to(ROOT)) if ok else None,
                status="verified" if ok else "sha_mismatch")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    pins = json.loads((ROOT / "registry/upstream_live_ledger_rasters.json").read_text())["rows"]
    pins = [r for r in pins if r.get("status") == "ok"]
    out_dir = ROOT / "data/ledger"
    out_dir.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda r: fetch(r, out_dir), pins))
    (out_dir / "index.json").write_text(json.dumps(res, indent=1))
    bad = [r for r in res if r["status"] != "verified"]
    print(f"verified {len(res)-len(bad)}/{len(res)}; bad={[b['submission'] for b in bad]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
