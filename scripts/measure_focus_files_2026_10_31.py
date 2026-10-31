#!/usr/bin/env python3
"""Re-measure the nine focus GEMSDOE files from their pinned upstream commits.

Evidence class: RASTER-MEASUREMENT of owner-published files. Nothing here is a
HOLDOUT-DTI, an organizer score, or an upload approval.

Steps (all reproducible, all verifiable by hand):
1. Read the pinned commit and expected SHA-256 for each focus file from
   evidence/focus_audit.json (written 2026-10-27, unchanged here).
2. Download the pinned commit tarball from codeload.github.com (an allowed host),
   extract only the target file, and compare its SHA-256 to the pinned value.
3. Measure the strict portal-style rules: single band, EPSG:32611, shape/transform,
   finite and inside [0, 1] over the WHOLE array, NaN count, and positive-cell count.
4. Compare each file's positive support with every other focus file (3-px overlap).

Usage: .venv/bin/python scripts/measure_focus_files_2026_10_31.py
Writes: evidence/focus_measure_2026_10_31.json and a cache under ~/.cache/gems_focus.
"""
from __future__ import annotations

import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache" / "gems_focus"
AUDIT = ROOT / "evidence" / "focus_audit.json"
OUT = ROOT / "evidence" / "focus_measure_2026_10_31.json"
TEMPLATE = ROOT / "data" / "template_grid.tif"


def fetch_member(owner_repo: str, commit: str, member_suffix: str, dest: Path) -> Path:
    """Fetch a commit tarball from codeload and extract the one file we need."""
    CACHE.mkdir(parents=True, exist_ok=True)
    tgz = CACHE / f"{owner_repo.split('/')[1]}-{commit[:12]}.tgz"
    if not tgz.exists():
        url = f"https://codeload.github.com/{owner_repo}/tar.gz/{commit}"
        with urllib.request.urlopen(url, timeout=300) as r, open(tgz, "wb") as w:
            w.write(r.read())
    with tarfile.open(tgz, "r:gz") as t:
        for m in t.getmembers():
            if m.name.endswith(member_suffix):
                f = t.extractfile(m)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read())
                return dest
    raise FileNotFoundError(member_suffix)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    report = {
        "schema": "focus-measure-v1",
        "date_utc": "2026-10-31",
        "evidence_class": "RASTER-MEASUREMENT of owner-published files; NOT HOLDOUT-DTI, NOT organizer-confirmed, NOT an upload approval",
        "sources": "codeload.github.com tarballs at the commits pinned in evidence/focus_audit.json",
        "files": [],
    }
    arrays = {}
    for s in audit["focus_sites"]:
        owner_repo = s["source"].split("github.com/")[1].split("/blob/")[0]
        commit = s["source"].split("/blob/")[1].split("/")[0]
        fname = s["filename"]
        dest = CACHE / "files" / s["site"] / fname
        fetch_member(owner_repo, commit, fname, dest)
        h = sha256(dest)
        row = {
            "site": s["site"],
            "filename": fname,
            "commit": commit,
            "sha256": h,
            "sha256_matches_pinned_audit": h == s["sha256"],
            "owner_reported_score": s["claimed_by_owner_not_receipt"],
            "score_label": "OWNER-REPORTED / UNVERIFIED (not a receipt)",
        }
        with rasterio.open(dest) as ds:
            a = ds.read(1).astype(np.float64)
            row.update(
                count=ds.count,
                dtype=ds.dtypes[0],
                crs=str(ds.crs),
                shape=[ds.height, ds.width],
                transform=list(ds.transform)[:6],
                nodata=None if ds.nodata is None or np.isnan(ds.nodata) else float(ds.nodata),
                nodata_is_nan=bool(ds.nodata is not None and np.isnan(ds.nodata)),
            )
        nan_mask = ~np.isfinite(a)
        row["nan_cells_whole_array"] = int(nan_mask.sum())
        row["zero_cells"] = int((a == 0).sum())
        row["positive_cells"] = int((np.isfinite(a) & (a > 0)).sum())
        finite = a[np.isfinite(a)]
        row["min_finite"] = float(finite.min())
        row["max_finite"] = float(finite.max())
        row["strict_whole_array_0_1_no_nan"] = bool(
            (not nan_mask.any()) and finite.min() >= 0.0 and finite.max() <= 1.0
        )
        row["outside_encoding"] = "nan" if s["filename"].endswith("nan.tif") else (
            "zeros" if s["filename"].endswith("zeros.tif") else "unlabelled")
        arrays[s["site"]] = a > 0
        report["files"].append(row)

    # Pairwise 3-px overlap of positive support (directed: share of A's positives within 3 px of B's).
    names = list(arrays)
    pair = {}
    for a_name in names:
        for b_name in names:
            if a_name == b_name:
                continue
            A, B = arrays[a_name], arrays[b_name]
            near_b = ndi.distance_transform_edt(~B) <= 3.0
            pair[f"{a_name}->{b_name}"] = round(float((A & near_b).sum() / max(A.sum(), 1)), 6)
    report["directed_3px_overlap"] = pair
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for r in report["files"]:
        print(r["site"], r["sha256_matches_pinned_audit"], r["outside_encoding"],
              r["nan_cells_whole_array"], r["strict_whole_array_0_1_no_nan"], r["positive_cells"])


if __name__ == "__main__":
    main()
