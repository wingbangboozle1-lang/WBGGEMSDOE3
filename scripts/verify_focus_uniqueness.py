#!/usr/bin/env python3
"""Independent uniqueness check of a candidate GeoTIFF against the nine focus-site files.

Shares no code with src/gemsw. For every focus file pinned in ``evidence/nine_site_table.json``:
  1. fetch the exact file from the GitHub API (host api.github.com, raw accept header) at its pinned ref,
  2. verify its SHA-256 against the pin (refuse on mismatch),
  3. measure dot overlap: share of candidate dots within 3 px (300 m, the DTI kernel radius) of a focus dot,
     and the reverse share.
Dots are cells with value > 0 inside the candidate's finite footprint (the repo's own dot definition).
Writes ``evidence/focus_uniqueness_independent_2026-10-27.json``.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

# The reference sample is independently hash-checked even when cached.
from verify_format_independent import sample_path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "focus_check"
RADIUS_PX = 3.0


def fetch(repo: str, path: str, ref: str) -> bytes:
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.raw"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def dots_of(a: np.ndarray) -> np.ndarray:
    return np.isfinite(a) & (a > 0)


def within(src: np.ndarray, ref: np.ndarray) -> float:
    """Share of True cells in src that lie within RADIUS_PX of a True cell in ref."""
    if not src.any() or not ref.any():
        return 0.0
    dist = ndi.distance_transform_edt(~ref)
    return float((dist[src] <= RADIUS_PX).mean())


def main(candidate: Path, out_json: Path) -> int:
    table = json.loads((ROOT / "evidence/nine_site_table.json").read_text())
    ledger = json.loads((ROOT / "registry/upstream_live_ledger_rasters.json").read_text())
    by_sha = {r["sha256"]: r for r in ledger["rows"] if r.get("sha256") and r.get("status") == "ok"}
    CACHE.mkdir(parents=True, exist_ok=True)
    with rasterio.open(sample_path()) as s:
        footprint = np.isfinite(s.read(1))
        ref_grid = (s.shape, s.transform, s.crs)
    with rasterio.open(candidate) as c:
        cand = c.read(1)
        cshape, ctr, ccrs = c.shape, c.transform, c.crs
        if c.count != 1 or (cshape, ctr, ccrs) != ref_grid:
            raise ValueError("candidate must be single-band and match the pinned sample grid")
    cdots = dots_of(cand) & footprint
    results, errors = [], []
    for row in table["rows"]:
        sha = row["sha256"]
        meta = by_sha.get(sha)
        if meta is None:
            errors.append(f"{row['site']}: pinned sha {sha[:12]} not in ledger registry")
            continue
        raw_path = CACHE / f"{sha}.tif"
        if not raw_path.exists():
            repo = meta["repo"] if "/" in meta["repo"] else f"buffedlizard55-lab/{meta['repo']}"
            raw_path.write_bytes(fetch(repo, meta["path"], meta["ref"]))
        raw = raw_path.read_bytes()
        got = hashlib.sha256(raw).hexdigest()
        if got != sha:
            errors.append(f"{row['site']}: SHA mismatch {got} != {sha}")
            raw_path.unlink()
            continue
        with rasterio.open(raw_path) as f:
            a = f.read(1)
            same_grid = f.count == 1 and f.shape == cshape and f.transform == ctr and f.crs == ccrs
        if not same_grid:
            errors.append(f"{row['site']}: single-band grid mismatch")
            continue
        fdots = dots_of(a) & footprint
        results.append({
            "site": row["site"],
            "file": meta["path"].split("/")[-1],
            "repo": meta["repo"] if "/" in meta["repo"] else f"buffedlizard55-lab/{meta['repo']}",
            "ref": meta["ref"],
            "sha256": sha,
            "same_grid_as_candidate": bool(same_grid),
            "focus_dots": int(fdots.sum()),
            "candidate_dots": int(cdots.sum()),
            "candidate_dots_within_3px_of_focus": round(within(cdots, fdots), 4),
            "focus_dots_within_3px_of_candidate": round(within(fdots, cdots), 4),
        })
    # Pairwise focus-vs-focus matrix (same measure, candidate side = row file's dots).
    masks = {}
    for r in results:
        with rasterio.open(CACHE / f"{r['sha256']}.tif") as f:
            masks[r["site"]] = dots_of(f.read(1)) & footprint
    pairwise = {}
    for a_site, am in masks.items():
        for b_site, bm in masks.items():
            if a_site != b_site:
                pairwise[f"{a_site}->{b_site}"] = round(within(am, bm), 4)
    worst_pair = max(pairwise.items(), key=lambda kv: kv[1]) if pairwise else None
    worst = max((r["candidate_dots_within_3px_of_focus"] for r in results), default=None)
    out = {
        "schema": "focus-uniqueness-independent-v1",
        "candidate": candidate.name,
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "radius_px": RADIUS_PX,
        "dot_definition": "finite and > 0 inside the hash-pinned sample footprint (repo definition)",
        "n_focus_files_checked": len(results),
        "max_candidate_overlap_with_focus": worst,
        "per_file": results,
        "focus_vs_focus_max_pair": worst_pair,
        "focus_vs_focus_pairwise": pairwise,
        "errors": errors,
        "label": "LOCAL-UNIQUENESS-CHECK (independent recomputation; not an organizer result)",
    }
    out_json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("candidate", "n_focus_files_checked", "max_candidate_overlap_with_focus")}, indent=1))
    for r in results:
        print(f"{r['site']:10s} {r['candidate_dots_within_3px_of_focus']:.4f}  rev {r['focus_dots_within_3px_of_candidate']:.4f}  grid_ok={r['same_grid_as_candidate']}  {r['file']}")
    for e in errors:
        print("ERROR", e, file=sys.stderr)
    return 1 if errors or len(results) != len(table["rows"]) else 0


if __name__ == "__main__":
    cand = ROOT / "docs/downloads/wbggems3-sgce-20261027-f52d35d8-nan.tif"
    out = ROOT / "evidence/focus_uniqueness_independent_2026-10-27.json"
    if len(sys.argv) > 1:
        cand = Path(sys.argv[1])
    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
    raise SystemExit(main(cand, out))
