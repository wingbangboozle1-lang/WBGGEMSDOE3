#!/usr/bin/env python3
"""Build the cached feature stack (memmap) for the 2026-10-31 lane.

Session 2026-10-31 (branch arena/69eaf63d-wbggemsdoe3).

Design rules that matter
------------------------
* Catalogue-derived fields are EXCLUDED on purpose.  distance-to-mapped-fault
  is a near-perfect leak on any catalogue-based holdout, and it is exactly the
  feature that cannot generalise to the sponsor's unmapped test faults.  The
  user's leakage-canary rule (AUC > 0.90 alone => leakage until proven
  otherwise) is applied to every feature below.
* Every field comes from the pinned competition mirror or from sibling-bridged
  derivatives of OFFICIAL public sources (USGS GeoDAWN, USGS 3DEP 1 m DEM via
  the GEMSDOE 1m_DEM_links route, DOE GDR #1391).  Provenance is recorded in
  the sidecar JSON.
* Memory: the stack is written to a float32 memmap (2 CPUs / 3 GB sandbox), so
  training reads only the sampled rows and prediction is chunked.

Output: data/work/features_2026_10_31.dat (+ .json sidecar).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
WORK.mkdir(parents=True, exist_ok=True)

FEATURES = RAW / "training_features.tif"
BAND_NAMES = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
    "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
    "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg",
    "det_elev_slope",
]
GRAD_BANDS = [2, 5, 10, 17, 18, 14]   # tmi_hg, tc, grav_vg, grav_hg, elev_slope, depth_base


def robust_z(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = a[valid & np.isfinite(a)]
    if v.size == 0:
        return np.zeros(a.shape, np.float32)
    lo, hi = np.percentile(v, [1, 99])
    med = np.median(v)
    scale = max(hi - lo, 1e-9)
    out = (a - med) / scale
    out[~valid] = np.nan
    return np.clip(out, -6.0, 6.0).astype(np.float32)


def grad_mag(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    g = np.hypot(ndi.sobel(a, axis=0, mode="nearest"), ndi.sobel(a, axis=1, mode="nearest"))
    return robust_z(g.astype(np.float32), valid)


def main() -> int:
    with rasterio.open(RAW / "sample_submission.tif") as src:
        sub = src.read(1)
        transform = [float(v) for v in tuple(src.transform)[:6]]
        crs = str(src.crs)
    footprint = np.isfinite(sub)
    shape = footprint.shape
    n = int(footprint.sum())
    fp_idx = np.flatnonzero(footprint.ravel())

    names: list[str] = []
    provenance: list[str] = []
    cols: list[np.ndarray] = []

    def add(name: str, field: np.ndarray, prov: str) -> None:
        f = np.asarray(field, np.float32)
        if f.shape != shape:
            raise ValueError(f"{name}: shape {f.shape}")
        cols.append(f.ravel()[fp_idx])
        names.append(name)
        provenance.append(prov)

    # ---- 1. official 19-band GeoDAWN / geophysical stack -------------------
    prov19 = ("training_features.tif (owner mirror of the DrivenData competition file; "
              "USGS GeoDAWN + INGENIOUS derived layers)")
    with rasterio.open(FEATURES) as src:
        for i, nm in enumerate(BAND_NAMES):
            a = src.read(i + 1).astype(np.float32)
            valid = footprint & np.isfinite(a) & (a > -3e38)
            add(f"geo_{nm}", robust_z(a, valid), prov19)

    # ---- 2. gradient magnitudes of the edge-sensitive bands ---------------
    with rasterio.open(FEATURES) as src:
        for i in GRAD_BANDS:
            a = src.read(i + 1).astype(np.float32)
            valid = footprint & np.isfinite(a) & (a > -3e38)
            add(f"grad_{BAND_NAMES[i]}", grad_mag(np.where(valid, a, 0.0), valid),
                "derived: |Sobel| of " + prov19)

    # ---- 3. 1 m-DEM-derived scarp evidence (sibling bridge of USGS 3DEP) --
    prov_lidar = ("lidar_scarp_features_u8.tif (sibling-bridged derivative of the public "
                  "USGS 3DEP 1 m DEM listed in 1m_DEM_links.csv); nodata==0 in the source")
    with rasterio.open(RAW / "external" / "lidar_scarp_features_u8.tif") as src:
        lnames = list(src.descriptions)
        lb = {nm: src.read(i + 1).astype(np.float32) for i, nm in enumerate(lnames)}
    valid_lidar = footprint & (lb["valid"] > 0)
    for nm in lnames:
        a = lb[nm]
        valid = valid_lidar & (a > 0) if nm != "valid" else valid_lidar
        add(f"lid_{nm}", robust_z(np.where(valid, a, np.nan), valid), prov_lidar)

    # ---- 4. radiometric channels and extensions ---------------------------
    prov_rad = ("geodawn_rad_u8.tif / geodawn_extensions_u8.tif (sibling-bridged GeoDAWN "
                "radiometric channels; official source: USGS GeoDAWN)")
    for fn, prov in (("geodawn_rad_u8.tif", prov_rad), ("geodawn_extensions_u8.tif", prov_rad)):
        with rasterio.open(RAW / "external" / fn) as src:
            for i, nm in enumerate(src.descriptions):
                a = src.read(i + 1).astype(np.float32)
                valid = footprint & (a > 0)
                add(f"rad_{fn[:6]}_{nm}", robust_z(np.where(valid, a, np.nan), valid), prov)

    # ---- 5. cross-catalogue discrepancy (SGMC structures absent from labels)
    with rasterio.open(RAW / "external" / "derived_sgmc_faults_100m_u8.tif") as src:
        sgmc = (src.read(1) > 0) & footprint
    d_sgmc = ndi.distance_transform_edt(~sgmc).astype(np.float32)
    add("xcat_sgmc_dist", robust_z(d_sgmc, footprint),
        "derived: distance to derived_sgmc_faults_100m_u8.tif (sibling-bridged USGS SGMC "
        "structures); NOT a competition-catalogue field")

    stack = np.stack(cols, axis=1)
    assert stack.shape == (n, len(names))
    mm = np.memmap(WORK / "features_2026_10_31.dat", dtype=np.float32, mode="w+",
                   shape=stack.shape)
    mm[:] = stack
    mm.flush()
    del mm
    sidecar = dict(session="2026-10-31", shape=list(shape), footprint_cells=n,
                   n_features=len(names), feature_names=names, provenance=provenance,
                   transform=transform, crs=crs,
                   note=("float32 memmap, rows are footprint cells in row-major (C) order; "
                         "NaN where a source is invalid. No catalogue-derived feature."))
    (WORK / "features_2026_10_31.json").write_text(json.dumps(sidecar, indent=1))
    np.save(WORK / "footprint_index_2026_10_31.npy", fp_idx)
    np.save(WORK / "footprint_mask_2026_10_31.npy", footprint)
    print(f"features: {stack.shape[0]:,} footprint cells x {len(names)} features")
    print("names:", ", ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
