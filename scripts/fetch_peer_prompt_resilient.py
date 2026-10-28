#!/usr/bin/env python3
"""Resilient fetch of the 17 Oct-27 prompt peer rasters (sha256-verified, fail-disclosing).

Same pins as scripts/fetch_peer_prompt_rasters.py, but when the pinned commit 404s
(upstream history rewritten), falls back to the repository default branch and accepts
the file ONLY if its bytes still match the registered sha256. A file that cannot be
sha-verified is skipped and reported, never silently used.

Output: data/peer_extra/*.tif + evidence/peer_fetch_resilient_2026-10-28.json
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "peer_extra"
EVID = ROOT / "evidence" / "peer_fetch_resilient_2026-10-28.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gh_raw(repo: str, ref: str, path: str) -> bytes | None:
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
         "-H", "Accept: application/vnd.github.raw"],
        capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout


def fetch_one(row: dict) -> dict:
    dest = OUT_DIR / Path(row["path"]).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    want = row["sha256"]
    if dest.exists() and sha256_bytes(dest.read_bytes()) == want:
        return dict(site=row["site"], submission=row["submission"], status="cached",
                    local=str(dest.relative_to(ROOT)), sha256=want, ref_used="cache")
    attempts = []
    for ref in (row["commit"], "HEAD"):
        data = gh_raw(row["repo"], ref, row["path"])
        if data is None:
            attempts.append(f"{ref}:http_error")
            continue
        got = sha256_bytes(data)
        if got == want:
            dest.write_bytes(data)
            return dict(site=row["site"], submission=row["submission"],
                        status="verified", local=str(dest.relative_to(ROOT)),
                        sha256=got, ref_used=ref,
                        ref_note=None if ref == row["commit"]
                        else "pinned commit 404; default-branch bytes match the registered sha256")
        attempts.append(f"{ref}:sha_mismatch({got[:12]})")
    return dict(site=row["site"], submission=row["submission"], status="SKIPPED",
                local=None, sha256=None, ref_used=None, attempts=attempts)


def main() -> int:
    reg = json.loads((ROOT / "registry" / "peer_prompt_2026-10-27.json").read_text())
    rows = reg["rasters"]
    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(fetch_one, rows):
            results.append(res)
            print(res["status"], res["site"], res["submission"], res.get("ref_used"), flush=True)
    ok = sum(1 for r in results if r["status"] in ("cached", "verified"))
    skipped = [r for r in results if r["status"] == "SKIPPED"]
    doc = {
        "schema": "peer-fetch-resilient-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "expected": len(rows),
        "verified_or_cached": ok,
        "skipped": skipped,
        "rows": results,
        "note": "Byte identity is decided by sha256 against registry/peer_prompt_2026-10-27.json; "
                "a default-branch fallback only relocates identical bytes and is disclosed per row.",
    }
    EVID.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({"verified": ok, "skipped": len(skipped)}, indent=1))
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
