#!/usr/bin/env python3
"""Restore the SHA-pinned external layers that live in the GEMSDOE24 owner mirror.

Why this exists: `src/gemsdoe/pipeline.py`, `scripts/gd_layer_rank.py` and the
LBCAL lane read `.cache/upstream/x24/data/external/*`, but the shared template's
`prepare_data.py` only restores the core competition rasters.  This script
fetches exactly the `external/*` rows of `registry/data_manifest.json` (plus the
un-pinned LiDAR band dictionary JSON, whose SHA-256 is printed so it can be
pinned) through the GitHub contents API (`gh api`, an allowed host) and refuses
any file whose SHA-256 differs from its pin.

Provenance: owner mirror, integrity-pinned, NOT organizer-authenticated.
Usage: .venv/bin/python scripts/restore_x24_external.py [--ids ext_lidar_scarp_features_u8 ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".cache" / "upstream" / "x24"
OWNER_JSON_REF = "07345ea0604953d7efb858d9cfbc21e20c7aca0b"
DEFAULT_IDS = (
    "ext_lidar_scarp_features_u8",
    "ext_geodawn_rad_u8",
    "ext_derived_sgmc_faults_100m_u8",
    "ext_tiger_road_distance_m",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gh_raw(repo: str, path: str, ref: str, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with tmp.open("wb") as fh:
        r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                            "-H", "Accept: application/vnd.github.raw"], stdout=fh)
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=list(DEFAULT_IDS))
    a = ap.parse_args()
    rows = {r["id"]: r for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    bad = []
    for rid in a.ids:
        row = rows[rid]
        out = DEST / "data" / row["dest"]
        if not (out.is_file() and sha256(out) == row["sha256"]):
            ok = gh_raw(row["repo"], row["path"], row["ref"], out)
            if not ok:
                bad.append((rid, "download_failed"))
                continue
        got = sha256(out)
        if got != row["sha256"]:
            out.unlink(missing_ok=True)
            bad.append((rid, f"sha_mismatch {got}"))
            continue
        print(f"[x24] OK {rid} -> {out.relative_to(ROOT)} sha256={got[:16]}…", flush=True)
    # Band dictionary for the LiDAR product (not pinned upstream; record its digest).
    meta = DEST / "data" / "external" / "lidar_scarp_features.json"
    if gh_raw("buffedlizard55-lab/GEMSDOE24", "data/external/lidar_scarp_features.json", OWNER_JSON_REF, meta):
        print(f"[x24] fetched lidar_scarp_features.json sha256={sha256(meta)} (record, not pinned upstream)")
    else:
        bad.append(("lidar_scarp_features.json", "download_failed"))
    if bad:
        print("[x24] FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
