"""Independent feature-field library -> rank-bin maps over the ACTIVE domain (footprint minus catalogue).

Every field is derived ONLY from competition-provided layers or the hash-pinned public external layers
(registry/data_manifest).  No field is derived from any registry/submission raster (H19-5 etc.); the
H19-5 network enters the model ONLY as a nuisance control (see ledger.py), never as a feature.

Bin code 0 = missing/no data.  Codes 1..9 = quantile bins of the field inside the active domain:
  <2%, 2-5, 5-10, 10-25, 25-75, 75-90, 90-95, 95-98, >98   (two-sided: polarity is learned, not assumed)
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi
from .grid import RAW, Grid, clean_feature
import rasterio

QEDGES = np.array([0.02, 0.05, 0.10, 0.25, 0.75, 0.90, 0.95, 0.98])
NBINS = 10
BAND_NAMES = ["mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc", "geod_shearrate",
              "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
              "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg", "det_elev_slope"]
LIDAR = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max", "upface_max", "cross_max",
         "relief", "coh100", "strike"]
RAD = ["K", "Th", "U", "TC"]
EXT = ["ThK", "UK", "UTh", "TMI_up150"]


def _fill(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """NaN -> in-footprint median so that filters do not see the sentinel; outside footprint also median."""
    out = a.copy()
    med = np.nanmedian(a[foot])
    out[~np.isfinite(out)] = med
    return out


def to_bins(field: np.ndarray, active: np.ndarray, domain: np.ndarray | None = None) -> np.ndarray:
    """field (full grid, NaN=missing) -> uint8 rank-bin codes (0 = missing, 1..NBINS-1 = quantile bins).

    Quantile edges are computed over `active` pixels only; codes are returned for `domain` (default: active)
    in row-major order, so the same edges can be applied to catalogue pixels (needed by the fold-local hold-out).
    """
    v = field[active]
    ok = np.isfinite(v)
    dom = active if domain is None else domain
    out = field[dom]
    codes = np.zeros(out.shape, np.uint8)
    if ok.sum() < 100:
        return codes
    edges = np.quantile(v[ok], QEDGES)
    oko = np.isfinite(out)
    codes[oko] = np.minimum(1 + np.searchsorted(edges, out[oko], side="right"), NBINS - 1).astype(np.uint8)
    return codes


def iter_fields(g: Grid, raw=RAW):
    """Yield (name, family, full-grid float32 field with NaN for missing)."""
    foot = g.foot
    tf = rasterio.open(raw / "training_features.tif")
    base = {}
    for i, n in enumerate(BAND_NAMES, start=1):
        base[n] = clean_feature(tf.read(i))
        base[n][~foot] = np.nan
        yield n, "band", base[n]
    with rasterio.open(raw / "external/lidar_scarp_features_u8.tif") as ds:
        valid = ds.read(12) > 0
        for j, n in enumerate(LIDAR, start=1):
            a = ds.read(j).astype(np.float32)
            a[~valid | ~foot] = np.nan
            yield "lidar_" + n, "lidar", a
        lidar_valid = valid
    with rasterio.open(raw / "external/geodawn_rad_u8.tif") as ds:
        for j, n in enumerate(RAD, start=1):
            a = ds.read(j).astype(np.float32); a[~foot] = np.nan
            yield "rad_" + n, "radiometric", a
    with rasterio.open(raw / "external/geodawn_extensions_u8.tif") as ds:
        for j, n in enumerate(EXT, start=1):
            a = ds.read(j).astype(np.float32); a[~foot] = np.nan
            yield "ext_" + n, "radiometric", a
    # ---- derived multi-scale edge / ridge fields (all from competition bands) ----
    for n in ["det_elev", "tmi", "rtp", "mag_anom", "iso_grav_anom", "cond_surf", "depth_to_base_surf", "tc"]:
        f = _fill(base[n], foot)
        scales = (1.5, 3.0, 6.0) if n == "det_elev" else (2.0, 5.0)
        for s in scales:
            gm = ndi.gaussian_gradient_magnitude(f, s).astype(np.float32); gm[~foot] = np.nan
            yield f"gradmag_{n}_s{s:g}", "derived-edge", gm
    f = _fill(base["det_elev"], foot)
    for s in (1.5, 3.0):
        lg = (-s * s * ndi.gaussian_laplace(f, s)).astype(np.float32); lg[~foot] = np.nan   # +ve = ridge/crest
        yield f"log_det_elev_s{s:g}", "derived-ridge", lg
    # local relief and roughness of detrended elevation
    mx = ndi.maximum_filter(f, size=7); mn = ndi.minimum_filter(f, size=7)
    rl = (mx - mn).astype(np.float32); rl[~foot] = np.nan
    yield "relief7_det_elev", "derived-ridge", rl
    # geodetic strain gradient and seismicity-density smooth
    for n in ["geod_2ndinv", "geod_shearrate", "geod_dilaterate"]:
        gm = ndi.gaussian_gradient_magnitude(_fill(base[n], foot), 4.0).astype(np.float32); gm[~foot] = np.nan
        yield f"gradmag_{n}_s4", "derived-edge", gm
    # pseudo-gravity-like contrast: mag vs gravity gradient product (rank-product -> cross-gradient proxy)
    gg = ndi.gaussian_gradient_magnitude(_fill(base["iso_grav_anom"], foot), 3.0)
    gm_ = ndi.gaussian_gradient_magnitude(_fill(base["rtp"], foot), 3.0)
    from scipy.stats import rankdata
    cg = np.sqrt(rankdata(gg[foot]) * rankdata(gm_[foot])).astype(np.float32)
    cgf = np.full(foot.shape, np.nan, np.float32); cgf[foot] = cg
    yield "crossgrad_rank_grav_mag_s3", "derived-edge", cgf
    # external point/line proximity layers
    import csv
    for fn, nm in [("gdr_wellspring_in_footprint.csv", "dist_wellspring"), ("gdr_volcanic_vents_in_footprint.csv", "dist_vent")]:
        pts = np.zeros(foot.shape, bool)
        with open(raw / "external" / fn) as fh:
            for r in csv.DictReader(fh):
                try:
                    rr, cc = int(float(r["row"])), int(float(r["col"]))
                except Exception:
                    continue
                if 0 <= rr < foot.shape[0] and 0 <= cc < foot.shape[1]:
                    pts[rr, cc] = True
        d = ndi.distance_transform_edt(~pts).astype(np.float32); d[~foot] = np.nan
        yield nm, "external-point", d
    with rasterio.open(raw / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sg = ds.read(1) > 0
    d = ndi.distance_transform_edt(~sg).astype(np.float32); d[~foot] = np.nan
    yield "dist_sgmc_fault", "external-geologic-map", d
    with rasterio.open(raw / "external/tiger_road_distance_m.tif") as ds:
        a = ds.read(1).astype(np.float32); a[~foot | ~np.isfinite(a)] = np.nan
    yield "dist_tiger_road_m", "anthropogenic-nuisance", a
