#!/usr/bin/env python3
"""Independent Pass-3 verification of the session deliverable.
Shares no code with session_finalize's validator: rasterio+numpy+scipy only,
EDT-based overlaps (finalize used KDTree), recomputed from saved bytes."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/session_1f0b051d_run_card.json").read_text())
NAME = CARD["submission_name"]
OUT = ROOT / "evidence" / "session_1f0b051d_verify.json"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    checks = {}
    with rasterio.open(ROOT / ".cache/data/sample_submission.tif") as t:
        tshape, ttr, tcrs, t_arr = t.shape, t.transform, str(t.crs), t.read(1)
        foot = np.isfinite(t_arr)
    with rasterio.open(ROOT / ".cache/data/labels.tif") as t:
        lab = (t.read(1) == 1) & foot
    sub = ROOT / "submission" / NAME
    dl = ROOT / "docs/session-1f0b051d/downloads" / NAME
    zp = ROOT / "docs/session-1f0b051d/downloads" / (Path(NAME).stem + ".zip")
    b = sub.read_bytes()
    checks["sha256_matches_card"] = sha(b) == CARD["raster_sha256"]
    checks["docs_copy_byte_identical"] = dl.read_bytes() == b
    z = zipfile.ZipFile(zp)
    checks["zip_single_tif_inner_identical"] = (z.namelist() == [NAME] and z.read(NAME) == b)
    with rasterio.open(sub) as ds:
        a = ds.read(1)
        checks.update({
            "bands_1": ds.count == 1, "dtype_float32": ds.dtypes[0] == "float32",
            "shape_ok": ds.shape == tshape, "transform_ok": ds.transform == ttr,
            "crs_ok": str(ds.crs) == tcrs, "crs_epsg": ds.crs.to_epsg(),
            "nodata": ds.nodata,
        })
    checks["whole_array_finite"] = bool(np.isfinite(a).all())
    checks["whole_array_min_max"] = [float(a.min()), float(a.max())]
    checks["values_binary_0_1"] = sorted(float(x) for x in np.unique(a)) == [0.0, 1.0]
    dots = (a > 0) & foot
    checks["dots"] = int(dots.sum())
    checks["dots_match_card"] = int(dots.sum()) == CARD["dots"]
    checks["dots_on_catalogue"] = int((dots & lab).sum())
    checks["dots_outside_footprint"] = int(((a > 0) & ~foot).sum())
    d_cat = ndi.distance_transform_edt(~lab)
    checks["min_distance_to_catalogue_px"] = float(d_cat[dots].min())
    ys, xs = np.nonzero(dots)
    dself, _ = cKDTree(np.c_[ys, xs]).query(np.c_[ys, xs], k=2)
    checks["min_pairwise_spacing_px"] = float(dself[:, 1].min())

    def w3(other_mask):
        d = ndi.distance_transform_edt(~other_mask)
        return float((d[dots] <= 3).mean())

    def load(p):
        with rasterio.open(p) as ds:
            x = ds.read(1).astype(np.float32)
        return (np.where(np.isfinite(x), x, 0) > 0) & foot

    checks["within3_edt"] = {
        "champion_GEMSDOE32": w3(load(ROOT / ".cache/focus/GEMSDOE32.tif")),
        "skarpline_union": w3(load(ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif")),
        "h19_5_continuous": w3(load(ROOT / ".cache/upstream/x24/inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif")),
        "pindrop_v4_nodes": w3(load(ROOT / "data/ledger/GEMSDOE3__pindrop-v4-nodes-20260925T152420Z-f347b70daa.tif")),
        "ovtr_ml_cover": w3(load(ROOT / "data/ledger/GEMSDOE67__gemsdoe67-ovtr-ml-cover-tau3p0-20261012-nan.tif")),
        "lattice_s5_space_filling": w3(load(ROOT / "data/ledger/13GEMSDOE__13gems_20261001_r13-lattice-s5_v2_nan-outside.tif")),
    }
    checks["all_format_checks_pass"] = bool(
        checks["sha256_matches_card"] and checks["docs_copy_byte_identical"]
        and checks["zip_single_tif_inner_identical"] and checks["bands_1"]
        and checks["dtype_float32"] and checks["shape_ok"] and checks["transform_ok"]
        and checks["crs_ok"] and checks["whole_array_finite"] and checks["values_binary_0_1"]
        and checks["dots_on_catalogue"] == 0 and checks["dots_outside_footprint"] == 0
        and checks["min_distance_to_catalogue_px"] >= 2.236 - 1e-9)
    OUT.write_text(json.dumps({"file": NAME, "checks": checks}, indent=1, default=float))
    print(json.dumps(checks, indent=1, default=float))


if __name__ == "__main__":
    main()
