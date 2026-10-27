#!/usr/bin/env python3
"""Stage 1 of the ledger inversion: reduce all 118 scored probes to coarse-grid operators.

Outputs (all under the git-ignored ``data/work/``):

* ``probes.npz``  - per-probe kA block means, dots per block, published score, sha256
* ``feats.npz``   - block-mean of official (competition/GeoDAWN/GDR/USGS) feature fields

Nothing from a sibling raster's *values* enters the feature matrix: peer files are used
only as probe supports (measurement operators) paired with one published scalar each.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import grid as G                     # noqa: E402
from gemsw import inversion as INV              # noqa: E402
from gemsw import features as F                 # noqa: E402

WORK = ROOT / "data" / "work"
FACTOR = 4

# Feature fields used to parametrise the truth density.  Every name must come from
# gemsw.features.iter_fields (official competition bands, GeoDAWN, lidar, GDR, USGS SGMC).
DENSITY_FEATURES = [
    "dist_sgmc_fault",          # distance to the public state-geologic-map faults
    "gradmag_det_elev_s3",      # 300 m topographic gradient magnitude
    "log_det_elev_s3",          # ridge/crest curvature of detrended elevation
    "gradmag_rtp_s2",           # reduced-to-pole magnetic gradient
    "gradmag_iso_grav_anom_s5",  # isostatic-gravity gradient (long wavelength)
    "crossgrad_rank_grav_mag_s3",  # gravity-magnetic concordance
    "lidar_step_max",           # 1 m lidar scarp step
    "lidar_relief",             # 1 m lidar relief
    "rad_ThK",                  # radiometric Th/K contrast
    "dist_wellspring",          # distance to GDR 1391 wells/springs
    "dist_vent",                # distance to GDR 1391 volcanic vents
    "det_elev",                 # detrended elevation
    "cond_surf",                # conductance of the surface (competition band)
    "depth_to_base_surf",       # depth to basement (competition band)
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_probes(g: G.Grid) -> dict:
    """Load every verified ledger raster and reduce it to dots + published score."""
    rows = json.loads((ROOT / "data/ledger/index.json").read_text())
    rows = [r for r in rows if r.get("status") == "verified"]
    dots, scores, names, shas = [], [], [], []
    import rasterio

    for r in rows:
        path = ROOT / r["local"]
        if sha256(path) != r["sha256"]:
            raise ValueError(f"ledger raster no longer matches its pin: {path}")
        with rasterio.open(path) as ds:
            a = ds.read(1)
        finite = np.isfinite(a)
        if ds.nodata is not None and np.isfinite(ds.nodata):
            finite &= a != ds.nodata
        d = finite & g.foot & (a > 0.5)
        dots.append(d)
        scores.append(float(r["score"]))
        names.append(f"{r['site']}::{r['submission']}")
        shas.append(r["sha256"])
    return dict(dots=dots, scores=np.array(scores), names=names, sha256=shas)


def build_features(g: G.Grid) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Memory-lean block-mean feature builder (reads one band at a time, float32 only).

    Names and derivations mirror gemsw.features.iter_fields, restricted to the 14 fields
    that parametrise the density, so nothing here is a private fork of the science.
    """
    import rasterio
    from scipy import ndimage as ndi

    foot = g.foot
    cols: list[np.ndarray] = []
    names: list[str] = []

    def add(name: str, full: np.ndarray, log: bool = False) -> None:
        v = np.asarray(full, np.float64)
        med = np.nanmedian(v[foot])
        v = np.where(np.isfinite(v), v, med)
        if log:
            v = np.log1p(np.maximum(v, 0.0))
        cols.append(INV.block_mean(v, FACTOR).ravel())
        names.append(name)
        del v

    raw = ROOT / "data" / "raw"
    # --- competition numerical bands (one at a time) ---
    want_bands = {"det_elev": 12, "cond_surf": 17, "depth_to_base_surf": 15,
                  "iso_grav_anom": 13, "rtp": 2}
    bands: dict[str, np.ndarray] = {}
    with rasterio.open(raw / "training_features.tif") as ds:
        for name, idx in want_bands.items():
            a = G.clean_feature(ds.read(idx))
            a[~foot] = np.nan
            bands[name] = a
    def filled(a: np.ndarray) -> np.ndarray:
        med = np.nanmedian(a[foot])
        return np.where(np.isfinite(a), a, med).astype(np.float32)

    add("det_elev", bands["det_elev"])
    add("cond_surf", bands["cond_surf"])
    add("depth_to_base_surf", bands["depth_to_base_surf"])
    for name, sigma in (("det_elev", 3.0), ("rtp", 2.0), ("iso_grav_anom", 5.0)):
        gm = ndi.gaussian_gradient_magnitude(filled(bands[name]), sigma)
        gm[~foot] = np.nan
        add(f"gradmag_{name}_s{sigma:g}", gm)
    lg = -3.0 * 3.0 * ndi.gaussian_laplace(filled(bands["det_elev"]), 3.0)
    lg[~foot] = np.nan
    add("log_det_elev_s3", lg)
    gg = ndi.gaussian_gradient_magnitude(filled(bands["iso_grav_anom"]), 3.0)
    gm_ = ndi.gaussian_gradient_magnitude(filled(bands["rtp"]), 3.0)
    from scipy.stats import rankdata
    cg = np.full(foot.shape, np.nan, np.float32)
    cg[foot] = np.sqrt(rankdata(gg[foot]) * rankdata(gm_[foot])).astype(np.float32)
    add("crossgrad_rank_grav_mag_s3", cg)
    del gg, gm_, cg, bands

    # --- lidar scarp stack (uint8, band 12 is validity) ---
    with rasterio.open(raw / "external/lidar_scarp_features_u8.tif") as ds:
        ok = ds.read(12) > 0
        for j, nm in ((3, "lidar_step_max"), (9, "lidar_relief")):
            a = ds.read(j).astype(np.float32)
            a[~ok | ~foot] = np.nan
            add(nm, a)
    # --- radiometrics: Th/K ---
    with rasterio.open(raw / "external/geodawn_rad_u8.tif") as ds:
        th = ds.read(2).astype(np.float32)
        kk = ds.read(1).astype(np.float32)
    thk = np.where((kk > 0) & (th > 0), th / np.maximum(kk, 1), np.nan).astype(np.float32)
    thk[~foot] = np.nan
    add("rad_ThK", thk)
    del th, kk, thk

    # --- point / line proximity layers from the pinned official-derived mirrors ---
    import csv
    for fn, nm in (("gdr_wellspring_in_footprint.csv", "dist_wellspring"),
                   ("gdr_volcanic_vents_in_footprint.csv", "dist_vent")):
        pts = np.zeros(foot.shape, bool)
        with open(raw / "external" / fn) as fh:
            for r in csv.DictReader(fh):
                try:
                    rr, cc = int(float(r["row"])), int(float(r["col"]))
                except Exception:
                    continue
                if 0 <= rr < foot.shape[0] and 0 <= cc < foot.shape[1]:
                    pts[rr, cc] = True
        dist = ndi.distance_transform_edt(~pts).astype(np.float32)
        dist[~foot] = np.nan
        add(nm, dist, log=True)
    with rasterio.open(raw / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sg = ds.read(1) > 0
    dist = ndi.distance_transform_edt(~sg).astype(np.float32)
    dist[~foot] = np.nan
    add("dist_sgmc_fault", dist, log=True)

    X = np.column_stack(cols)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return ((X - mu) / sd).astype(np.float64), names, np.column_stack([mu, sd])


def main() -> int:
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    g = G.load_grid()
    print(f"[grid] footprint={g.foot.sum():,} catalogue={g.labels.sum():,}", flush=True)

    cache = WORK / f"probes_f{FACTOR}.npz"
    if not cache.exists():
        p = load_probes(g)
        print(f"[probes] {len(p['dots'])} verified scored rasters in {time.time()-t0:.0f}s", flush=True)
        ps = INV.build_probe_set(p["dots"], p["scores"], p["names"], g.foot, g.labels, factor=FACTOR)
        np.savez_compressed(
            cache, kA=ps.kA.astype(np.float16), nblocks=ps.nblocks.astype(np.uint16),
            names=np.array(ps.names), scores=ps.scores, n_dots=ps.n_dots,
            active_blocks=ps.active_blocks.ravel(), block_shape=np.array(ps.block_shape),
            factor=FACTOR, sha256=np.array(p["sha256"]))
        print(f"[probes] cached {cache.name} in {time.time()-t0:.0f}s", flush=True)

    fcache = WORK / f"feats_f{FACTOR}.npz"
    if not fcache.exists():
        Z, names, stat = build_features(g)
        np.savez_compressed(fcache, Z=Z, names=np.array(names), stat=stat)
        print(f"[feats] {len(names)} fields cached {Z.shape} in {time.time()-t0:.0f}s", flush=True)

    d = np.load(cache, allow_pickle=False)
    f = np.load(fcache, allow_pickle=False)
    print(json.dumps({
        "probes": int(len(d["scores"])), "blocks": int(d["kA"].shape[1]),
        "block_shape": d["block_shape"].tolist(), "features": f["names"].tolist(),
        "score_min": float(d["scores"].min()), "score_max": float(d["scores"].max()),
        "elapsed_s": round(time.time() - t0, 1)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
