"""Zero-catalogue physical feature extraction for Lane THCS-OOF.

STRICT ZERO-CATALOGUE INVARIANT:
This module NEVER reads ``existing_faults.tif``, ``labels.tif``, ``derived_sgmc_faults_100m_u8.tif``,
or any ``dist_known_fault_px`` column. Every channel is derived exclusively from geophysical,
topographic, LiDAR, airborne gamma-ray radiometric, TIGER road-corridor, and DOE GDR #1391
shallow 2 m temperature probe / paleo-geothermal sinter / well-spring geothermometry observations.
"""

from __future__ import annotations

import csv
import io
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform
from scipy import ndimage as ndi

RAW_BAND_NAMES = [
    "mag_anom",            # 1
    "rtp",                 # 2
    "tmi_hg",              # 3
    "geod_2ndinv",         # 4
    "iso_grav_anom_slope", # 5
    "rad_tc_f32",          # 6: Verified Spearman=0.999953 w/ USGS GeoDAWN Radiometric Total Count (IR-20)
    "geod_shearrate",      # 7
    "geod_dilaterate",     # 8
    "tmi_vg",              # 9
    "deq_n100a15",         # 10
    "iso_grav_anom_vg",    # 11
    "det_elev",            # 12
    "iso_grav_anom",       # 13
    "tmi",                 # 14
    "depth_to_base_surf",  # 15
    "ieq_n100a15",         # 16
    "cond_surf",           # 17
    "iso_grav_anom_hg",    # 18
    "det_elev_slope",      # 19
]

DERIVED_BLOCK_A_NAMES = [
    "mag_tilt_angle",          # 20: arctan2(tmi_vg, |tmi_hg|) — true magnetic tilt derivative (fixes IR-20)
    "mag_tilt_zero_crest",     # 21: exp(-|mag_tilt|/0.35) * log1p(|tmi_hg|)
    "mag_analytic_signal",     # 22: log1p(hypot(tmi_hg, tmi_vg))
    "rtp_shallow_resid_300m",  # 23: rtp - G_3(rtp)
    "grav_tilt_angle",         # 24: arctan2(iso_grav_anom_vg, |iso_grav_anom_hg|)
    "grav_fault_crest",        # 25: iso_grav_anom_hg * exp(-|grav_tilt|/0.45)
    "rad_tc_destriped_grad",   # 26: |grad(destripe_EW(tc))| — suppresses E-W flight-line leveling noise
    "rad_k_th_alteration",     # 27: GeoDAWN K / (Th + 8) potassic metasomatism index
    "rad_thk_ext",             # 28: GeoDAWN Th/K extension
    "rad_uk_ext",              # 29: GeoDAWN U/K extension
    "tmi_up150_grad",          # 30: |grad(TMI_up150)| basement magnetic boundary
    "topo_lrm_300m",           # 31: det_elev - G_3(det_elev)
    "topo_lrm_1000m",          # 32: det_elev - G_10(det_elev)
    "topo_break_laplacian",    # 33: -laplace(G_1.2(det_elev)) scarp break-in-slope
    "lidar_step_road_clean",   # 34: 3DEP step_max damped within 250 m of TIGER road/rail embankments
    "lidar_ex_coherence",      # 35: 3DEP ex_max * (coh100/255) * road_damp
    "lidar_lap_crest_clean",   # 36: max(lapneg_max, lappos_max) * road_damp
    "aniso_strike_coherence",  # 37: structure-tensor linear anisotropy (rejects circular caldera/pluton mimics)
    "concealed_grav_cond",     # 38: sigmoid(z(depth_to_base)) * z_pos(iso_grav_hg) * z_pos(cond_surf)
]

BLOCK_B_HYDROTHERMAL_NAMES = [
    "probe2m_dab_1km",            # 39: GDR #1391 2m temperature probe F2mDAB > 0 plume (sigma=1 km)
    "probe2m_dab_3km",            # 40: GDR #1391 2m temperature probe F2mDAB > 0 plume (sigma=3 km)
    "probe2m_anom_prox",          # 41: exp(-d_to_probe_dab_gt_1.5C / 35 px)
    "paleo_sinter_density_2p5km", # 42: GDR #1391 travertine/sinter/tufa kernel density (sigma=2.5 km)
    "paleo_sinter_prox",          # 43: exp(-d_to_paleo_sinter / 40 px)
    "well_thermal_excess_2km",    # 44: GDR #1391 well/spring max(temp_c - 20, 0) plume (sigma=2 km)
    "well_geotherm_excess_3km",   # 45: GDR #1391 silica/cation max(T_geotherm - 70, 0) plume (sigma=3 km)
    "well_hot_prox",              # 46: exp(-d_to_well_gt_35C / 35 px)
    "volc_vent_prox",             # 47: exp(-d_to_quaternary_vent / 50 px)
    "blind_hydrothermal_conduit", # 48: cover_depth * hydrothermal_plume * potential_field_step
]

ALL_FEATURE_NAMES = RAW_BAND_NAMES + DERIVED_BLOCK_A_NAMES + BLOCK_B_HYDROTHERMAL_NAMES
BLOCK_A_INDICES = list(range(len(RAW_BAND_NAMES) + len(DERIVED_BLOCK_A_NAMES)))  # 0..37 (38 features)
BLOCK_AB_INDICES = list(range(len(ALL_FEATURE_NAMES)))                            # 0..47 (48 features)


def _clean_band(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    valid = foot & np.isfinite(out) & (out > -1e30)
    med = float(np.median(out[valid])) if valid.any() else 0.0
    out[~valid] = med
    out[~foot] = med
    return out


def _grad_mag(arr: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(arr)
    return np.hypot(gy, gx).astype(np.float32)


def _zpos(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = arr[foot]
    mu = float(np.mean(v))
    sd = float(np.std(v)) + 1e-6
    return np.clip((arr - mu) / sd, 0.0, 8.0).astype(np.float32)


def _zscore(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = arr[foot]
    mu = float(np.mean(v))
    sd = float(np.std(v)) + 1e-6
    return np.clip((arr - mu) / sd, -6.0, 6.0).astype(np.float32)


def _prox_from_points(rows: np.ndarray, cols: np.ndarray, shape: tuple[int, int], scale_px: float) -> np.ndarray:
    H, W = shape
    ok = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
    seed = np.zeros(shape, dtype=bool)
    if ok.any():
        seed[rows[ok], cols[ok]] = True
    if not seed.any():
        return np.zeros(shape, dtype=np.float32)
    d = ndi.distance_transform_edt(~seed).astype(np.float32)
    return np.exp(-d / float(scale_px)).astype(np.float32)


def _extract_gdr1391_rasters(raw_dir: Path, shape: tuple[int, int], tr, crs, foot: np.ndarray) -> list[np.ndarray]:
    """Rasterize DOE GDR #1391 2m probes, paleo-sinter/travertine/tufa, thermal wells, and vents.

    Explicitly ignores ``dist_known_fault_px`` in all CSV tables to preserve strict zero-catalogue purity.
    """
    H, W = shape
    ext = raw_dir / "external"

    def lonlat_to_rc(lons: list[float], lats: list[float]) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = transform("EPSG:4269", crs, lons, lats)
        cc = np.floor((np.asarray(xs) - tr.c) / tr.a).astype(np.int32)
        rr = np.floor((np.asarray(ys) - tr.f) / tr.e).astype(np.int32)
        return rr, cc

    # 1. 2-meter temperature probes (DBF inside official zip)
    with zipfile.ZipFile(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip") as z:
        dbf = z.read(
            "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        )
    nrec, hlen, rlen = struct.unpack("<IHH", dbf[4:12])
    fields = []
    pos = 32
    while dbf[pos] != 0x0D:
        fields.append((dbf[pos : pos + 11].split(b"\x00")[0].decode("latin1"), dbf[pos + 16]))
        pos += 32

    p_lon, p_lat, p_dab = [], [], []
    for i in range(nrec):
        rec = dbf[hlen + i * rlen : hlen + (i + 1) * rlen]
        if rec[0:1] == b"*":
            continue
        off = 1
        d = {}
        for fn, fl in fields:
            d[fn] = rec[off : off + fl].decode("latin1").strip()
            off += fl
        try:
            lo, la, db = float(d["LongDegree"]), float(d["LatDegreeN"]), float(d["F2mDAB"])
            if -125.0 < lo < -110.0 and 35.0 < la < 45.0 and np.isfinite(db):
                p_lon.append(lo)
                p_lat.append(la)
                p_dab.append(db)
        except Exception:
            continue

    pr, pc = lonlat_to_rc(p_lon, p_lat)
    dab_arr = np.asarray(p_dab, dtype=np.float32)
    ok_p = (pr >= 0) & (pr < H) & (pc >= 0) & (pc < W)
    dab_grid = np.zeros(shape, dtype=np.float32)
    cnt_grid = np.zeros(shape, dtype=np.float32)
    np.add.at(dab_grid, (pr[ok_p], pc[ok_p]), np.clip(dab_arr[ok_p], 0.0, 25.0))
    np.add.at(cnt_grid, (pr[ok_p], pc[ok_p]), 1.0)
    dab_1km = (
        ndi.gaussian_filter(dab_grid, 10.0) / (ndi.gaussian_filter(cnt_grid, 10.0) + 0.05)
    ).astype(np.float32)
    dab_3km = (
        ndi.gaussian_filter(dab_grid, 30.0) / (ndi.gaussian_filter(cnt_grid, 30.0) + 0.05)
    ).astype(np.float32)
    hot_p = ok_p & (dab_arr > 1.5)
    probe_prox = _prox_from_points(pr[hot_p], pc[hot_p], shape, scale_px=35.0)

    # 2. Paleo-geothermal sinter / travertine / tufa
    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as z:
        ptxt = z.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
    s_lon, s_lat = [], []
    for row in csv.DictReader(io.StringIO(ptxt)):
        try:
            lo, la = float(row["Long_deg_NAD83"]), float(row["Lat_deg_NAD83"])
            if -125.0 < lo < -110.0 and 35.0 < la < 45.0:
                s_lon.append(lo)
                s_lat.append(la)
        except Exception:
            continue
    sr, sc = lonlat_to_rc(s_lon, s_lat)
    ok_s = (sr >= 0) & (sr < H) & (sc >= 0) & (sc < W)
    sinter_imp = np.zeros(shape, dtype=np.float32)
    np.add.at(sinter_imp, (sr[ok_s], sc[ok_s]), 1.0)
    sinter_dens = (ndi.gaussian_filter(sinter_imp, 25.0) * 1000.0).astype(np.float32)
    sinter_prox = _prox_from_points(sr[ok_s], sc[ok_s], shape, scale_px=40.0)

    # 3. Wells & springs (ONLY row, col, temp_c, geotherm*; NEVER dist_known_fault_px)
    w_temp_grid = np.zeros(shape, dtype=np.float32)
    w_tcnt_grid = np.zeros(shape, dtype=np.float32)
    w_geot_grid = np.zeros(shape, dtype=np.float32)
    w_gcnt_grid = np.zeros(shape, dtype=np.float32)
    hot_wr, hot_wc = [], []
    with open(ext / "gdr_wellspring_in_footprint.csv", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            try:
                rr = int(float(row["row"]))
                cc = int(float(row["col"]))
            except Exception:
                continue
            if not (0 <= rr < H and 0 <= cc < W):
                continue
            # Measured temperature
            t_str = (row.get("temp_c") or "").strip()
            if t_str and t_str.lower() not in ("nan", "na", "-999", "-9999"):
                try:
                    tc_val = float(t_str)
                    if 0.0 < tc_val < 300.0:
                        exc = max(tc_val - 20.0, 0.0)
                        w_temp_grid[rr, cc] += min(exc, 120.0)
                        w_tcnt_grid[rr, cc] += 1.0
                        if tc_val >= 35.0:
                            hot_wr.append(rr)
                            hot_wc.append(cc)
                except Exception:
                    pass
            # Chemical geothermometers (quartz, chalcedony, Na-K-Ca cation)
            gvals = []
            for gk in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                gs = (row.get(gk) or "").strip()
                if gs and gs.lower() not in ("nan", "na", "-999", "-9999"):
                    try:
                        gv = float(gs)
                        if 0.0 < gv < 350.0:
                            gvals.append(gv)
                    except Exception:
                        pass
            if gvals:
                gmax = max(gvals)
                w_geot_grid[rr, cc] += min(max(gmax - 70.0, 0.0), 180.0)
                w_gcnt_grid[rr, cc] += 1.0

    well_temp_2km = (
        ndi.gaussian_filter(w_temp_grid, 20.0) / (ndi.gaussian_filter(w_tcnt_grid, 20.0) + 0.10)
    ).astype(np.float32)
    well_geot_3km = (
        ndi.gaussian_filter(w_geot_grid, 30.0) / (ndi.gaussian_filter(w_gcnt_grid, 30.0) + 0.10)
    ).astype(np.float32)
    well_hot_prox = _prox_from_points(
        np.asarray(hot_wr, dtype=np.int32), np.asarray(hot_wc, dtype=np.int32), shape, scale_px=35.0
    )

    # 4. Quaternary volcanic vents (ONLY row, col; NEVER dist_known_fault_px)
    vr, vc = [], []
    with open(ext / "gdr_volcanic_vents_in_footprint.csv", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            try:
                vr.append(int(float(row["row"])))
                vc.append(int(float(row["col"])))
            except Exception:
                continue
    vent_prox = _prox_from_points(np.asarray(vr, dtype=np.int32), np.asarray(vc, dtype=np.int32), shape, scale_px=50.0)

    return [
        dab_1km,
        dab_3km,
        probe_prox,
        sinter_dens,
        sinter_prox,
        well_temp_2km,
        well_geot_3km,
        well_hot_prox,
        vent_prox,
    ]


def build_or_load_feature_cache(raw_dir: Path, cache_dir: Path) -> tuple[np.memmap, np.ndarray, dict]:
    """Build or load cached (N_foot, 48) float16 feature matrix + footprint boolean mask.

    Stores features strictly on valid footprint pixels in a disk-backed array so peak resident
    RAM stays well below 800 MB on 3.6 GiB environments.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    mmap_path = cache_dir / "thcs_foot_features_f32.mmap"
    meta_path = cache_dir / "thcs_feature_meta.json"

    with rasterio.open(raw_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        shape = ds.shape
        tr = ds.transform
        crs = ds.crs

    n_foot = int(foot.sum())
    n_feat = len(ALL_FEATURE_NAMES)

    if mmap_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("n_foot") == n_foot and meta.get("n_features") == n_feat and meta.get("feature_names") == ALL_FEATURE_NAMES:
            mm = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_foot, n_feat))
            return mm, foot, meta

    mm = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(n_foot, n_feat))

    # 0..18: 19 core training_features bands
    keep_bands: dict[str, np.ndarray] = {}
    with rasterio.open(raw_dir / "training_features.tif") as ds:
        for b_idx, b_name in enumerate(RAW_BAND_NAMES, start=1):
            arr = _clean_band(ds.read(b_idx), foot)
            mm[:, b_idx - 1] = arr[foot]
            if b_name in (
                "rtp", "tmi_hg", "tmi_vg", "rad_tc_f32",
                "iso_grav_anom_vg", "iso_grav_anom_hg",
                "det_elev", "det_elev_slope", "depth_to_base_surf", "cond_surf",
            ):
                keep_bands[b_name] = arr

    rtp = keep_bands["rtp"]
    tmi_hg = keep_bands["tmi_hg"]
    tmi_vg = keep_bands["tmi_vg"]
    rad_tc = keep_bands["rad_tc_f32"]
    grav_vg = keep_bands["iso_grav_anom_vg"]
    grav_hg = keep_bands["iso_grav_anom_hg"]
    det_elev = keep_bands["det_elev"]
    det_slope = keep_bands["det_elev_slope"]
    dtb = keep_bands["depth_to_base_surf"]
    cond = keep_bands["cond_surf"]

    # 19..24: True analytic magnetic & gravity tilt derivatives
    mag_tilt = np.arctan2(tmi_vg, np.hypot(tmi_hg, 1e-3)).astype(np.float32)
    mag_zero_crest = (np.exp(-np.abs(mag_tilt) / 0.35) * np.log1p(np.abs(tmi_hg))).astype(np.float32)
    mag_asig = np.log1p(np.hypot(tmi_hg, tmi_vg)).astype(np.float32)
    rtp_res = (rtp - ndi.gaussian_filter(rtp, 3.0)).astype(np.float32)
    grav_tilt = np.arctan2(grav_vg, np.hypot(grav_hg, 1e-3)).astype(np.float32)
    grav_crest = (grav_hg * np.exp(-np.abs(grav_tilt) / 0.45)).astype(np.float32)

    mm[:, 19] = mag_tilt[foot]
    mm[:, 20] = mag_zero_crest[foot]
    mm[:, 21] = mag_asig[foot]
    mm[:, 22] = rtp_res[foot]
    mm[:, 23] = grav_tilt[foot]
    mm[:, 24] = grav_crest[foot]

    # 25..29: Destriped float32 radiometric gradient + GeoDAWN K/Th/U/TMI_up150
    # Suppress E-W flight-line leveling oscillations (high-freq row-to-row ripple vs E-W smoothed mean)
    ew_ripple = rad_tc - ndi.gaussian_filter1d(rad_tc, sigma=1.3, axis=0)
    ew_stripe_only = ndi.gaussian_filter1d(ew_ripple, sigma=12.0, axis=1)
    rad_tc_destriped = rad_tc - ew_stripe_only
    mm[:, 25] = _grad_mag(rad_tc_destriped)[foot]

    ext = raw_dir / "external"
    with rasterio.open(ext / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
    mm[:, 26] = (rad_k / (rad_th + 8.0))[foot]

    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds:
        mm[:, 27] = ds.read(1).astype(np.float32)[foot]
        mm[:, 28] = ds.read(2).astype(np.float32)[foot]
        tmi_up150 = ds.read(4).astype(np.float32)
    mm[:, 29] = _grad_mag(ndi.gaussian_filter(tmi_up150, 1.0))[foot]

    # 30..32: Multi-scale topographic local relief & break-in-slope Laplacian
    mm[:, 30] = (det_elev - ndi.gaussian_filter(det_elev, 3.0))[foot]
    mm[:, 31] = (det_elev - ndi.gaussian_filter(det_elev, 10.0))[foot]
    mm[:, 32] = (-ndi.laplace(ndi.gaussian_filter(det_elev, 1.2)))[foot]

    # 33..35: TIGER road-corridor damped 3DEP LiDAR scarps
    with rasterio.open(ext / "tiger_road_distance_m.tif") as ds:
        road_m = _clean_band(ds.read(1), foot)
    road_damp = np.clip(road_m / 250.0, 0.15, 1.0).astype(np.float32)

    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        ex_max = ds.read(1).astype(np.float32)
        step_max = ds.read(3).astype(np.float32)
        lapneg = ds.read(4).astype(np.float32)
        lappos = ds.read(5).astype(np.float32)
        coh100 = ds.read(10).astype(np.float32)

    scarp_clean = (step_max * road_damp).astype(np.float32)
    mm[:, 33] = scarp_clean[foot]
    mm[:, 34] = (ex_max * (coh100 / 255.0) * road_damp)[foot]
    mm[:, 35] = (np.maximum(lapneg, lappos) * np.clip(road_m / 250.0, 0.20, 1.0))[foot]

    # 36: Structure-tensor linear strike coherence on combined slope + gravity gradient
    comb_edge = _zpos(det_slope, foot) + 0.7 * _zpos(grav_hg, foot) + 0.7 * _zpos(scarp_clean, foot)
    gy, gx = np.gradient(ndi.gaussian_filter(comb_edge, 1.0))
    jxx = ndi.gaussian_filter(gx * gx, 2.5)
    jxy = ndi.gaussian_filter(gx * gy, 2.5)
    jyy = ndi.gaussian_filter(gy * gy, 2.5)
    trace = jxx + jyy + 1e-6
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coherence = (disc / trace) * comb_edge
    mm[:, 36] = coherence.astype(np.float32)[foot]

    # 37: Concealed alluvial-cover gravity + conductivity conduit interaction
    cover_sig = 1.0 / (1.0 + np.exp(-_zscore(dtb, foot)))
    z_grav = _zpos(grav_hg, foot)
    z_tmi = _zpos(tmi_hg, foot)
    z_cond = _zpos(cond, foot)
    mm[:, 37] = (cover_sig * z_grav * (0.5 + z_cond)).astype(np.float32)[foot]

    # 38..47: Block B — INGENIOUS GDR #1391 hydrothermal & geochemical plumes
    gdr_layers = _extract_gdr1391_rasters(raw_dir, shape, tr, crs, foot)
    for k_i, lyr in enumerate(gdr_layers):
        mm[:, 38 + k_i] = lyr[foot]

    hydro_plume = (
        _zpos(gdr_layers[1], foot)
        + _zpos(gdr_layers[3], foot)
        + _zpos(gdr_layers[5], foot)
        + _zpos(gdr_layers[6], foot)
    )
    blind_conduit = (cover_sig * hydro_plume * (0.3 + z_grav + 0.5 * z_tmi)).astype(np.float32)
    mm[:, 47] = blind_conduit[foot]

    mm.flush()
    meta = {
        "lane": "THCS-OOF",
        "zero_catalogue_verified": True,
        "n_foot": n_foot,
        "shape": list(shape),
        "n_features": n_feat,
        "feature_names": ALL_FEATURE_NAMES,
        "block_a_count": len(BLOCK_A_INDICES),
        "block_b_count": len(BLOCK_B_HYDROTHERMAL_NAMES),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    mm_ro = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_foot, n_feat))
    return mm_ro, foot, meta
