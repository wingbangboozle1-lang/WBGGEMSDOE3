#!/usr/bin/env python3
"""Best-effort fetch of the owner-ledger registry + dense controls for AMDC uniqueness.

All files come from github.com via `gh api` (allowed host). Every byte is SHA-256
verified against its pin; mismatches are deleted and disclosed, never used.
Output: .cache/amdc_registry/** + evidence/amdc/registry_fetch.json
"""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "amdc_registry"
EVID = ROOT / "evidence" / "amdc"
EVID.mkdir(parents=True, exist_ok=True)
OWNER = "buffedlizard55-lab"
WITNESS = {"repo": "17GEMSDOE",
           "ref": "6fc71d19d49dca4960d5434bd81b6dd06fcc030a",
           "path": "docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif",
           "sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def fetch_one(repo: str, ref: str, path: str, dest: Path, want: str) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha(dest) == want:
        return {"dest": str(dest.relative_to(ROOT)), "status": "cached"}
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with tmp.open("wb") as fh:
            r = subprocess.run(
                ["gh", "api", f"repos/{OWNER}/{repo}/contents/{path}?ref={ref}",
                 "-H", "Accept: application/vnd.github.raw"],
                stdout=fh, timeout=180)
        if r.returncode != 0:
            tmp.unlink(missing_ok=True)
            return {"dest": str(dest.relative_to(ROOT)), "status": "download_failed"}
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return {"dest": str(dest.relative_to(ROOT)), "status": "timeout"}
    if sha(tmp) != want:
        tmp.unlink(missing_ok=True)
        return {"dest": str(dest.relative_to(ROOT)), "status": "sha_mismatch"}
    tmp.replace(dest)
    return {"dest": str(dest.relative_to(ROOT)), "status": "verified",
            "bytes": dest.stat().st_size}


def main() -> int:
    rows = json.loads((ROOT / "registry" / "upstream_live_ledger_rasters.json").read_text())["rows"]
    jobs = []
    for r in rows:
        if r.get("status") != "ok" or not r.get("sha256"):
            continue
        name = f"{r['site']}__{Path(r['path']).name}"
        jobs.append((r["repo"], r["ref"], r["path"], OUT / "ledger" / name, r["sha256"],
                     r["site"], r["submission"], r.get("score")))
    jobs.append((WITNESS["repo"], WITNESS["ref"], WITNESS["path"],
                 OUT / "controls" / "17GEMSDOE_E-proba.tif", WITNESS["sha256"],
                 "17GEMSDOE", "E-proba-control", None))
    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_one, repo, ref, path, dest, want): (site, sub, score, dest)
                for repo, ref, path, dest, want, site, sub, score in jobs}
        for f in cf.as_completed(futs):
            site, sub, score, dest = futs[f]
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001 - disclose, never crash the lane
                r = {"dest": str(dest.relative_to(ROOT)), "status": f"error:{e}"}
            r.update(site=site, submission=sub, owner_score=score)
            results.append(r)
            print(f"{r['status']}: {site}/{sub}", flush=True)
    ok = [r for r in results if r["status"] in ("verified", "cached")]
    bad = [r for r in results if r["status"] not in ("verified", "cached")]
    (EVID / "registry_fetch.json").write_text(json.dumps(
        {"fetched": len(ok), "failed": len(bad),
         "failures": [{"site": r["site"], "submission": r["submission"], "status": r["status"]}
                      for r in bad],
         "rows": sorted(results, key=lambda r: r["dest"])}, indent=1))
    print(f"fetched {len(ok)}/{len(results)}; failed={len(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
