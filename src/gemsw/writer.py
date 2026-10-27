"""ARCHIVED LST1 writer and validator, disabled. Historical portal-error and upload-readiness claims are unproven."""
from __future__ import annotations
import hashlib, zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import Affine

FOOT_PX = 5_167_373


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def write_submission(p: np.ndarray, foot: np.ndarray, labels: np.ndarray, template: Path, out: Path, mode: str) -> Path:
    """p: full-grid values (any dtype). In-footprint cells are clipped to [0,1] and NaN->0; catalogue cells -> 0."""
    raise RuntimeError("BLOCKED: retired local writer/validator; see evidence/run_card.json")
    assert mode in ("zeros", "nan")
    with rasterio.open(template) as t:
        prof = t.profile.copy()
    arr = np.zeros(foot.shape, np.float32)
    v = np.nan_to_num(np.asarray(p, np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    arr[foot] = np.clip(v[foot], 0.0, 1.0)
    arr[labels] = 0.0
    if mode == "nan":
        arr[~foot] = np.nan
        prof.update(nodata=np.nan)
    else:
        prof.update(nodata=None)
    prof.update(dtype="float32", count=1, compress="lzw")
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr, 1)
    return out


def write_zip(tif: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tif, arcname=tif.name)
    return zip_path


def validate(path: Path, template: Path, foot: np.ndarray, labels: np.ndarray, mode: str | None = None) -> dict:
    """Re-open the saved bytes and check every submission-format rule.  Returns dict(checks=..., passed=bool)."""
    raise RuntimeError("BLOCKED: retired local writer/validator; see evidence/run_card.json")
    with rasterio.open(template) as t:
        tshape, tcrs, ttr = t.shape, t.crs, t.transform
    with rasterio.open(path) as ds:
        a = ds.read(1)
        cnt, dt, shp, crs, tr, nod = ds.count, ds.dtypes[0], ds.shape, ds.crs, ds.transform, ds.nodata
    fin = np.isfinite(a)
    ins, outs = a[foot], a[~foot]
    checks = {
        "single_band": cnt == 1,
        "dtype_float32": dt == "float32",
        "shape_matches_template": shp == tshape,
        "crs_epsg_32611": crs is not None and crs.to_epsg() == 32611,
        "transform_matches_template": tr.almost_equals(ttr, precision=1e-6),
        "footprint_cells_expected": int(foot.sum()) == FOOT_PX,
        "in_footprint_all_finite": bool(np.isfinite(ins).all()),
        "in_footprint_no_nan": int(np.isnan(ins).sum()) == 0,
        "in_footprint_no_inf": int(np.isinf(ins).sum()) == 0,
        "in_footprint_no_sentinel": int((ins < -1e30).sum()) == 0,
        "in_footprint_range_0_1": bool(((ins >= 0) & (ins <= 1)).all()),
        "all_non_nan_values_in_0_1": bool(((a[fin] >= 0) & (a[fin] <= 1)).all()),
        "zero_on_catalogue": int((a[labels] > 0).sum()) == 0,
    }
    if mode is None:
        mode = "nan" if np.isnan(outs).all() else "zeros"
    checks["outside_footprint_compliant"] = bool(np.isnan(outs).all()) if mode == "nan" else bool((outs == 0).all())
    checks["has_dots"] = int((ins > 0).sum()) > 0
    return dict(file=path.name, mode=mode, sha256=sha256_file(path), bytes=path.stat().st_size,
                emitted_pixels=int((ins > 0).sum()), in_footprint_min=float(ins.min()), in_footprint_max=float(ins.max()),
                full_grid_nan=int(np.isnan(a).sum()), nodata=None if nod is None or (isinstance(nod, float) and np.isnan(nod)) else float(nod),
                checks=checks, passed=all(checks.values()))
