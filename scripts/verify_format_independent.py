#!/usr/bin/env python3
"""Independent format validator for a candidate submission TIFF (shares no code with src/gemsw).

Checks, against the OFFICIAL text (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):
  * single band, dtype float32, EPSG:32611, 100 m grid, same shape and transform as the training data;
  * every finite value in [0, 1]; no +/-inf;
  * "data outside the bounds is null or nan": cells outside the sample footprint must be NaN.
The footprint is the finite-cell mask of the owner-mirrored official sample_submission.tif, fetched from
api.github.com (repo buffedlizard55-lab/GEMSDOE24 @ 07345ea0) and pinned by SHA-256 2176d08e...
Mirror provenance is byte identity only, not organizer authentication.

Usage: verify_format_independent.py <candidate.tif> [--out evidence/x.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPO, SAMPLE_REF, SAMPLE_PATH = "buffedlizard55-lab/GEMSDOE24", "07345ea0604953d7efb858d9cfbc21e20c7aca0b", "data/bridge/sample_submission.tif"
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
CACHE = ROOT / ".cache" / "format_check"


def sample_path() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{SAMPLE_SHA}.tif"
    if not p.exists():
        url = f"https://api.github.com/repos/{SAMPLE_REPO}/contents/{SAMPLE_PATH}?ref={SAMPLE_REF}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.raw"})
        data = urllib.request.urlopen(req, timeout=120).read()
        if hashlib.sha256(data).hexdigest() != SAMPLE_SHA:
            raise SystemExit("pinned sample SHA-256 mismatch; refusing to validate")
        p.write_bytes(data)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    raw = args.candidate.read_bytes()
    with rasterio.open(sample_path()) as s:
        s_arr = s.read(1)
        ref = dict(shape=s.shape, transform=s.transform, crs=s.crs.to_string())
    foot = np.isfinite(s_arr)
    with rasterio.open(args.candidate) as c:
        a = c.read(1)
        checks = {
            "single_band": c.count == 1,
            "dtype_float32": c.dtypes[0] == "float32",
            "crs_epsg_32611": c.crs is not None and c.crs.to_epsg() == 32611,
            "shape_matches_sample": c.shape == ref["shape"],
            "transform_matches_sample": c.transform == ref["transform"],
        }
    fin = np.isfinite(a)
    vals = a[fin]
    outside = a[~foot]
    checks.update({
        "no_inf": bool(not np.isinf(a).any()),
        "finite_values_in_0_1": bool(((vals >= 0) & (vals <= 1)).all()),
        "finite_mask_equals_sample_footprint": bool(np.array_equal(fin, foot)),
        "outside_footprint_is_nan (official text)": bool(np.isnan(outside).all()),
        "inside_footprint_all_finite": bool(np.isfinite(a[foot]).all()),
    })
    result = {
        "schema": "format-independent-v1",
        "file": args.candidate.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "sample_footprint_cells": int(foot.sum()),
        "finite_cells": int(fin.sum()),
        "nan_cells": int(np.isnan(a).sum()),
        "positive_cells": int((np.nan_to_num(a) > 0).sum()),
        "value_min_finite": float(vals.min()) if vals.size else None,
        "value_max_finite": float(vals.max()) if vals.size else None,
        "checks": checks,
        "passed": all(checks.values()),
        "reference": {"sample_sha256": SAMPLE_SHA, "sample_repo": SAMPLE_REPO, "sample_ref": SAMPLE_REF},
        "label": "LOCAL FORMAT CHECK against official text; not organizer acceptance",
    }
    text = json.dumps(result, indent=1) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
