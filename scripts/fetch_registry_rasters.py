#!/usr/bin/env python3
"""Re-fetch the sibling registry rasters that the uniqueness gate compares against.

Source of truth for *which* bytes count: ``registry/registry_index.json`` (sha256 per file).
Source of *bytes*: the owner repositories on GitHub via the API (``gh api``), at the repository's
default branch (``HEAD``) for GEMSDOE sites and at the pinned ``ref`` for ledger rows that carry
one in ``registry/upstream_live_ledger_rasters.json``.

Rules (fail closed, but report rather than abort):
* A downloaded file is kept only if its sha256 equals a sha256 in the index.
* Entries that cannot be matched are written to ``evidence/registry_fetch_2026-10-28.json`` as
  ``unverified`` so the uniqueness claim is scoped to what was really compared.
* Nothing is written into ``docs/``; bytes go to the git-ignored ``.cache/registry/``.

Owner bytes establish byte identity only, not organizer provenance.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "registry" / "registry_index.json"
LEDGER = ROOT / "registry" / "upstream_live_ledger_rasters.json"
CACHE = ROOT / ".cache" / "registry"
OUT = ROOT / "evidence" / "registry_fetch_2026-10-28.json"
OWNER = "buffedlizard55-lab"


def gh_raw(repo: str, path: str, ref: str) -> bytes | None:
    proc = subprocess.run(
        ["gh", "api", f"repos/{OWNER}/{repo}/contents/{path}?ref={ref}",
         "-H", "Accept: application/vnd.github.raw"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    return proc.stdout if proc.returncode == 0 else None


def main() -> int:
    index = json.loads(INDEX.read_text())["files"]
    wanted: dict[str, dict] = {}
    for e in index:
        if e.get("status") == "ok" and e.get("sha256"):
            wanted.setdefault(e["sha256"], e)

    ledger_rows = json.loads(LEDGER.read_text())["rows"]
    jobs: list[tuple[str, str, str, str]] = []  # (sha, repo, path, ref)
    for r in ledger_rows:
        if r.get("status") == "ok" and r.get("path") and r.get("ref") and r.get("repo"):
            for sha_key in ("sha256",):
                if r.get(sha_key):
                    jobs.append((r[sha_key], r["repo"], r["path"], r["ref"]))
    done = {j[0] for j in jobs}
    for sha, e in wanted.items():
        if sha in done:
            continue
        site = e.get("site", "")
        path = e.get("path", "")
        if site.startswith("GEMSDOE") and ".cache/sites/" in path:
            rel = path.split(f".cache/sites/{site}/", 1)[1]
            jobs.append((sha, site, rel, "HEAD"))

    CACHE.mkdir(parents=True, exist_ok=True)
    matched, unverified = {}, []
    for sha, repo, path, ref in jobs:
        data = gh_raw(repo, path, ref)
        if data is None:
            unverified.append({"sha256": sha, "repo": repo, "path": path, "ref": ref,
                               "reason": "gh api failed"})
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != sha:
            unverified.append({"sha256": sha, "repo": repo, "path": path, "ref": ref,
                               "reason": "sha256 mismatch", "got": digest})
            continue
        dest = CACHE / f"{sha[:16]}_{Path(path).name}"
        dest.write_bytes(data)
        matched[sha] = str(dest.relative_to(ROOT))

    indexed_unique = len(wanted)
    missing = [sha for sha in wanted if sha not in matched]
    summary = {
        "schema": "gems-registry-fetch-v1",
        "index_entries_ok": sum(1 for e in index if e.get("status") == "ok"),
        "unique_dot_masks_in_index": indexed_unique,
        "attempted": len(jobs),
        "sha_verified": len(matched),
        "unverified_attempts": unverified,
        "unique_sha_not_fetched": [
            {"sha256": s, "site": wanted[s].get("site"), "path": wanted[s].get("path")} for s in missing],
        "matched_files": matched,
    }
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in (
        "unique_dot_masks_in_index", "attempted", "sha_verified")}, indent=2))
    print(f"unverified attempts: {len(unverified)}; unique index sha not fetched: {len(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
