#!/usr/bin/env python
"""Build and validate the 2026-10-31 unique submission (corridor-geometry lane).

Strategy (tuned on the segment-hide holdout, confirmed on two further folds):

    prior  = Gaussian corridor density of the published catalogue, sigma = 24 px (2.4 km)
    domain = inside the official AOI, outside the known-fault mask, and
             3 px <= distance-to-published-catalogue < 12 px
    emit   = binary dots, greedy-thinned to a 4 px minimum separation,
             highest prior first, value 1.0; 0.0 everywhere else in the AOI

Rationale is measured, not asserted: on the holdout, 60 % of withheld fault pixels lie
3-12 px from the visible catalogue and none lie within 2 px (see
knowledge/hypotheses-newfaults-2026-10-31.md).

Output values are strictly inside [0, 1] with **no NaN anywhere**, so the portal's
"Predicted values must be in range [0, 1]" rejection cannot be triggered by NaN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.newfaults import data, features, model     # noqa: E402

NAME = "wbg-corridor-band3to12-s24-sep4-20261031T{stamp}Z"
VERSION = "corridor-geometry-v1"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def build(sigma: float = 24.0, t_min: float = 3.0, t_max: float = 12.0, min_sep: float = 4.0) -> tuple:
    lab = data.load_labels()
    foot = lab >= 0
    cat = lab == 1
    d_vis = features.mask_distance(cat)
    prior = features.corridor_prior(cat, sigma)
    legal = foot & (d_vis >= t_min) & (d_vis < t_max)
    v = np.where(legal, prior, -np.inf).ravel()
    order = np.argsort(-v, kind="stable")
    n = int(np.isfinite(v[order]).sum())
    ys, xs = np.unravel_index(order[:n], prior.shape)
    dots = model._greedy_thin(ys, xs, prior[ys, xs], prior.shape, min_sep)
    arr = np.zeros(lab.shape, np.float32)
    arr[dots] = 1.0
    meta = {
        "version": VERSION, "sigma_px": sigma, "t_min_px": t_min, "t_max_px": t_max,
        "min_sep_px": min_sep, "n_dots": int(dots.sum()),
        "footprint_px": int(foot.sum()),
        "dots_outside_footprint": int((dots & ~foot).sum()),
        "dots_on_known_faults": int((dots & cat).sum()),
        "min_dist_to_catalogue_px": float(d_vis[dots].min()) if dots.any() else None,
    }
    return arr, dots, meta, lab, foot, cat


def write(arr: np.ndarray, out: Path) -> None:
    with rasterio.open(data.OFFICIAL / "sample_submission.tif") as ds:
        prof = ds.profile.copy()
    prof.update(dtype="float32", count=1, nodata=None, compress="lzw")
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr.astype(np.float32), 1)


def validate(path: Path) -> dict:
    """Every submission-format rule, re-checked from the saved bytes."""
    with rasterio.open(data.OFFICIAL / "sample_submission.tif") as ref:
        r_shape, r_crs, r_tr = ref.shape, ref.crs, ref.transform
        r_bounds = ref.bounds
    with rasterio.open(path) as ds:
        a = ds.read(1)
        cnt, dt, shp, crs, tr, nod = ds.count, ds.dtypes[0], ds.shape, ds.crs, ds.transform, ds.nodata
        bounds = ds.bounds
    finite = np.isfinite(a)
    checks = {
        "single_band": cnt == 1,
        "dtype_float32": dt == "float32",
        "shape_matches_sample": shp == r_shape,
        "crs_matches_sample": crs == r_crs,
        "transform_matches_sample": tuple(tr)[:6] == tuple(r_tr)[:6],
        "bounds_match_sample": bounds == r_bounds,
        "no_nan": bool(finite.all()),
        "min_ge_0": bool(a.min() >= 0.0),
        "max_le_1": bool(a.max() <= 1.0),
        "has_positive_predictions": bool((a > 0).sum() > 0),
        "no_positive_outside_footprint": True,   # filled below
    }
    lab = data.load_labels()
    foot = lab >= 0
    checks["no_positive_outside_footprint"] = bool(((a > 0) & ~foot).sum() == 0)
    checks["no_positive_on_known_faults"] = bool(((a > 0) & (lab == 1)).sum() == 0)
    checks["crs_is_epsg32611"] = str(crs) == "EPSG:32611"
    return {
        "passed": bool(all(checks.values())),
        "checks": checks,
        "n_positive": int((a > 0).sum()),
        "min": float(a.min()), "max": float(a.max()), "dtype": dt, "count": cnt,
        "crs": str(crs), "shape": list(shp), "nodata": None if nod is None else float(nod),
        "transform": [float(x) for x in tuple(tr)[:6]],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=ROOT / "submission" / "newfaults-2026-10-31")
    ap.add_argument("--stamp", default="025500")
    a = ap.parse_args()
    arr, dots, meta, lab, foot, cat = build()
    name = NAME.format(stamp=a.stamp)
    tif = a.out_dir / f"{name}-zeros.tif"
    write(arr, tif)
    val = validate(tif)
    zpath = a.out_dir / f"{name}-zeros.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)
    manifest = {
        "submission_name": name,
        "file_tif": str(tif.relative_to(ROOT)),
        "file_zip": str(zpath.relative_to(ROOT)),
        "sha256_tif": sha256_file(tif),
        "sha256_zip": sha256_file(zpath),
        "bytes_tif": tif.stat().st_size,
        "build": meta,
        "validation": val,
        "note": "corridor band 3-12 px, sep 4 px, sigma 24 px; unique lane",
    }
    (a.out_dir / f"{name}-manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))
    if not val["passed"]:
        raise SystemExit("VALIDATION FAILED")


if __name__ == "__main__":
    main()
