#!/usr/bin/env python
"""Uniqueness audit of the new candidate against every reference raster we hold.

Reference sets
--------------
* ``data/compare/*.tif``  -- the nine focus-site files, byte-verified against
  ``registry/focus_sites.json`` SHA-256 (the highest owner-reported file per site).
* ``docs/downloads/*.tif``, ``submission/*.tif`` -- this project's own earlier outputs.

Metrics (all measured, none asserted)
-------------------------------------
* ``identical_bytes``     -- SHA-256 equality with the candidate file.
* ``identical_dots``      -- identical positive-support set (the strict duplicate test).
* ``jaccard``             -- |A and B| / |A or B| on the positive supports.
* ``cand_within_3px``     -- fraction of candidate dots within 3 px of a reference dot
  (the lane rule in the brief: > 0.70 on one reference means drift into its lane).
* ``ref_within_3px``      -- the same in the other direction.
* ``spearman_smooth``     -- Spearman correlation of 1.5-px Gaussian-smoothed rasters on
  a 600k-pixel sample (the lane rule: |rho| > 0.90 means drift).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.newfaults import data      # noqa: E402

DISC3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_pos(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1).astype(np.float32)
    return np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0) > 0


def compare(cand: np.ndarray, ref: np.ndarray, cand_name: str, ref_name: str, foot: np.ndarray,
            rng: np.random.Generator, sample: int = 600_000) -> dict:
    n_c, n_r = int(cand.sum()), int(ref.sum())
    near_c = ndi.binary_dilation(ref, structure=DISC3)
    near_r = ndi.binary_dilation(cand, structure=DISC3)
    both = int((cand & ref).sum())
    union = int((cand | ref).sum())
    fi = np.flatnonzero(foot.ravel())
    idx = rng.choice(fi, min(sample, fi.size), replace=False)
    sc = rankdata(ndi.gaussian_filter(cand.astype(np.float32), 1.5).ravel()[idx])
    sr = rankdata(ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[idx])
    rho = float(np.corrcoef(sc, sr)[0, 1]) if sc.std() > 0 and sr.std() > 0 else 0.0
    return {
        "reference": ref_name,
        "ref_dots": n_r,
        "cand_dots": n_c,
        "identical_dots": bool(n_c == n_r and both == n_c),
        "jaccard": float(both / union) if union else 0.0,
        "cand_within_3px": float((cand & near_c).sum() / max(n_c, 1)),
        "ref_within_3px": float((ref & near_r).sum() / max(n_r, 1)),
        "spearman_smooth": rho,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    lab = data.load_labels()
    foot = lab >= 0
    cand = read_pos(a.candidate)
    cand_sha = sha256(a.candidate)
    rng = np.random.default_rng(11)

    refs: list[Path] = sorted((ROOT / "data" / "compare").glob("*.tif"))
    refs += sorted((ROOT / "docs" / "downloads").glob("*.tif"))
    refs += sorted((ROOT / "submission").glob("*.tif"))
    rows = []
    seen = set()
    for p in refs:
        s = sha256(p)
        if s in seen:
            continue
        seen.add(s)
        r = read_pos(p)
        if r.sum() == 0:
            continue
        row = compare(cand, r, a.candidate.name, str(p.relative_to(ROOT)), foot, rng)
        row["ref_sha256"] = s
        row["identical_bytes"] = bool(s == cand_sha)
        rows.append(row)

    dup_overlap = [r for r in rows if r["cand_within_3px"] > 0.70]
    dup_rho = [r for r in rows if abs(r["spearman_smooth"]) > 0.90]
    dup_exact = [r for r in rows if r["identical_dots"] or r["identical_bytes"]]
    verdict = {
        "candidate": a.candidate.name,
        "sha256": cand_sha,
        "n_candidate_dots": int(cand.sum()),
        "n_references": len(rows),
        "max_cand_within_3px": max((r["cand_within_3px"] for r in rows), default=0.0),
        "max_spearman": max((abs(r["spearman_smooth"]) for r in rows), default=0.0),
        "duplicates_exact": [r["reference"] for r in dup_exact],
        "duplicates_overlap_gt_070": [r["reference"] for r in dup_overlap],
        "duplicates_rho_gt_090": [r["reference"] for r in dup_rho],
        "unique_under_stated_rules": not (dup_exact or dup_overlap or dup_rho),
        "rules": {"overlap_max": 0.70, "spearman_max": 0.90, "exact_duplicate": "forbidden"},
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"verdict": verdict, "rows": rows}, indent=1, default=float))
    print(json.dumps(verdict, indent=1))
    top = sorted(rows, key=lambda r: -r["cand_within_3px"])[:6]
    print("\ntop overlaps:")
    for r in top:
        print(f"  {r['reference'][:58]:58s} within3px {r['cand_within_3px']:.4f} "
              f"jaccard {r['jaccard']:.4f} rho {r['spearman_smooth']:+.3f}")


if __name__ == "__main__":
    main()
