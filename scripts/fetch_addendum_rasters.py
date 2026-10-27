#!/usr/bin/env python3
"""Fetch the 2026-10-27 ledger addendum: scored/unscored rasters NOT in
registry/upstream_live_ledger_rasters.json (generated 2026-10-26).

Every row is pinned to an exact commit (resolved from the owner repo's default
branch on 2026-10-27) and a SHA-256 computed from the downloaded bytes.  The
first run records the digest in registry/ledger_addendum_2026-10-27.json; later
runs refuse any byte change.  Scores are OWNER-REPORTED values copied from the
user's 2026-10-27 brief (no organizer receipts); `null` means the brief listed
the submission without a score.

Usage: .venv/bin/python scripts/fetch_addendum_rasters.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "ledger_addendum"
REG = ROOT / "registry" / "ledger_addendum_2026-10-27.json"

# (site as listed by the user, submission name as listed, owner-reported score or None,
#  repo, commit, path).  Commits were resolved with `gh api repos/<repo>/commits/<default branch>`.
ROWS = [
    ("GEMSDOE27", "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite", 0.2250,
     "buffedlizard55-lab/GEMSDOE27", "59246f662cd6", "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif"),
    ("GEMSDOE28", "gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite", 0.0206,
     "buffedlizard55-lab/GEMSDOE28", "191a5608af3f", "docs/downloads/gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif"),
    ("GEMSDOE33", "gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros", 0.0963,
     "buffedlizard55-lab/GEMSDOE33", "844f51481904", "docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif"),
    ("GEMSDOE36", "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros", 0.1647,
     "buffedlizard55-lab/GEMSDOE36", "6306b61ba113", "docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif"),
    ("GEMSDOE64", "h64-lidar-scarp-cv-20261011T220000Z", 0.0383,
     "buffedlizard55-lab/GEMSDOE64", "4791ebcc7ce3", "docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif"),
    ("GEMSDOE79", "gems79-tilt-ring-100000dots-20261022T212135Z-50a5d7498c71-zeros", 0.0005,
     "buffedlizard55-lab/GEMSDOE79", "0352e5ef356c", "docs/downloads/gems79-tilt-ring-100000dots-20261022T212135Z-50a5d7498c71-zeros.tif"),
    # Unscored (listed with an empty score) -- registry members for uniqueness only.
    ("KANLERGEMSDOE3", "kanlergemsdoe3-h-k3-1-cadg-submod-exp-k3-3-oof8f-37654-20261026-f0565e6d10f9-zeros", None,
     "kanlerxz87-cyber/KANLERGEMSDOE3", "ee683eeff93a", "docs/cadg-submod/downloads/kanlergemsdoe3-h-k3-1-cadg-submod-exp-k3-3-oof8f-37654-20261026-f0565e6d10f9-zeros.tif"),
    ("KANLERGEMSDOE2", "kanlergems2-htcads-exp-2-37654dots-20261026T235227Z-11a2f251-zeros", None,
     "kanlerxz87-cyber/KANLERGEMSDOE2", "bd31c5582720", "docs/downloads/kanlergems2-htcads-exp-2-37654dots-20261026T235227Z-11a2f251-zeros.tif"),
    ("WBGGEMSDOE3 (file found in WBGGEMSDOE2 repo)", "wbg3-h3pack-34k-20261027T174337Z-zeros", None,
     "wingbangboozle1-lang/WBGGEMSDOE2", "92ba5fb6ac1b", "docs/downloads/h3-pack/wbg3-h3pack-34k-20261027T174337Z-zeros.tif"),
    ("WBGGEMSDOE2 (file found in WBGGEMSDOE1 repo)", "wbg2-offcatalogue-density-36k-20261027", None,
     "wingbangboozle1-lang/WBGGEMSDOE1", "4ebb9124ca81", "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif"),
    ("GEMSDOE88", "gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT", None,
     "buffedlizard55-lab/GEMSDOE88", "a9f928241cf6", "docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif"),
    ("GEMSDOE91", "gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405", None,
     "buffedlizard55-lab/GEMSDOE91", "0e10f15a1043", "docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405.tif"),
    ("WBGGEMSDOE1", "wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros", None,
     "wingbangboozle1-lang/WBGGEMSDOE1", "4ebb9124ca81", "docs/downloads/wbggemsdoe1-h1-mvgz-20261026T215656Z-ac61afda-zeros.tif"),
    ("WBGGEMSDOE1", "gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros", None,
     "wingbangboozle1-lang/WBGGEMSDOE1", "4ebb9124ca81", "docs/downloads/gemsdoe1-tip1-directional-tip-gradient-20261026-9a4b9b4bc8cd-zeros.tif"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_commit(repo: str, short: str) -> str:
    r = subprocess.run(["gh", "api", f"repos/{repo}/commits/{short}", "--jq", ".sha"],
                       capture_output=True, text=True)
    if r.returncode != 0 or len(r.stdout.strip()) != 40:
        raise RuntimeError(f"cannot resolve {repo}@{short}: {r.stderr.strip()}")
    return r.stdout.strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prior = {}
    if REG.is_file():
        prior = {r["local"]: r for r in json.loads(REG.read_text())["rows"]}
    rows, bad = [], []
    for site, name, score, repo, short, path in ROWS:
        local = OUT_DIR / f"{repo.split('/')[1]}__{Path(path).name}"
        rel = str(local.relative_to(ROOT))
        commit = prior.get(rel, {}).get("commit") or resolve_commit(repo, short)
        if not local.is_file():
            with local.open("wb") as fh:
                r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={commit}",
                                    "-H", "Accept: application/vnd.github.raw"], stdout=fh)
            if r.returncode != 0:
                local.unlink(missing_ok=True)
                bad.append((name, "download_failed"))
                continue
        digest = sha256(local)
        if rel in prior and prior[rel]["sha256"] != digest:
            bad.append((name, "sha_changed"))
            continue
        rows.append(dict(site=site, submission=name, score=score,
                         score_class="OWNER-REPORT (user brief 2026-10-27)" if score is not None else "UNSCORED (listed without score)",
                         repo=repo, commit=commit, path=path,
                         url=f"https://github.com/{repo}/blob/{commit}/{path}",
                         local=rel, sha256=digest, bytes=local.stat().st_size))
        print(f"[addendum] {digest[:12]} {score} {name}")
    REG.write_text(json.dumps(dict(
        schema_version=1,
        generated_utc="2026-10-27",
        note=("Rasters listed in the 2026-10-27 user brief but absent from registry/upstream_live_ledger_rasters.json. "
              "Scores are owner-reported, not organizer receipts. SHA-256 computed from downloaded bytes."),
        rows=rows), indent=1) + "\n")
    if bad:
        print("[addendum] FAILED", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
