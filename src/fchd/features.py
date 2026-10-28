"""Strictly zero-catalogue 62-feature physical stack for the FCHD-NCM lane.

Memory-safe implementation (< 500 MB peak RAM on 3.8 GiB hosts): builds one physical
layer at a time on the (3730, 3292) grid, extracts the 5,167,373 footprint pixels,
encodes monotonic 0..250 quantile bins into a disk-backed uint8 memmap
(HistGradientBoostingClassifier natively bins continuous features into <=255 bins),
and also persists 3 float32 physical composite indices for structural-physical
interaction terms in E2/E3.

Never accesses labels.tif, existing_faults.tif, or derived_sgmc_faults_100m_u8.tif.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from src.thcs.features import _extract_gdr1391_rasters

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
EXT_DIR = RAW_DIR / "external"
WORK_DIR = ROOT / "data" / "work"

GRID_SHAPE = (3730, 3292)

FEATURE_NAMES: tuple[str, ...] = (
    # Group 1: 10 m 3DEP Fluvial Chi & Absolute Elevation / Lahontan Deconfounder (12)
    "chi_channel_valid",
    "chi_step_pos_300m",
    "chi_step_pos_800m",
    "chi_step_asym_300m",
    "chi_ksn_300m",
    "chi_ksn_jump_800m",
    "chi_area_weighted_step",
    "chi_cross_branch_dk",
    "zmean_m_abs",
    "zmean_relief_1km",
    "lahontan_sehoo_band",
    "lahontan_contour_mimic",
    # Group 2: 10 m 3DEP Sub-Grid Planar Facet & Piedmont Geomorphology (10)
    "topo10_slope_p90",
    "topo10_slope_std",
    "topo10_relief_local",
    "topo10_curv_prof",
    "topo10_aspect_coh",
    "topo10_hs_lineament",
    "topo10_planar_facet_idx",
    "topo10_piedmont_inflection",
    "topo10_lineament_contrast",
    "topo10_steep_frac",
    # Group 3: Anthropogenic BLM Mining & TIGER Road Deconfounders (4)
    "blm_claim_dist_log",
    "blm_mine_scarp_mimic",
    "tiger_road_dist_log",
    "road_cut_mimic",
    # Group 4: 1 m 3DEP LiDAR Tectonic Scarp Geometry (8)
    "lidar_valid",
    "lidar_ex_max",
    "lidar_step_max",
    "lidar_cross_max",
    "lidar_coh100",
    "lidar_scarp_sharpness",
    "lidar_face_asym",
    "lidar_strike_smooth",
    # Group 5: Potential-Field 0->150 m Worms, Basement & Float32 Radiometrics (18)
    "grav_iso_anom",
    "grav_hgrad_100m",
    "grav_tilt_angle",
    "grav_worm_zero_cross",
    "mag_tmi",
    "mag_hgrad_0m",
    "mag_hgrad_up150m",
    "mag_worm_persistence",
    "mag_worm_updip_shift",
    "basement_depth",
    "basement_depth_grad",
    "concealed_basin_worm",
    "rad_tc_f32",
    "rad_tc_hgrad",
    "rad_thk_ratio",
    "rad_uth_ratio",
    "geod_max_shear",
    "geod_2nd_inv",
    # Group 6: Official 100 m Geophysical/Seismic Context & GDR #1391 Blind Hydrothermal Plumes (10)
    "tf_det_elev",
    "tf_cond_surf",
    "tf_eq_density",
    "tf_det_elev_slope",
    "gdr_probe2m_dab_2p5km",
    "gdr_probe2m_grad",
    "gdr_sinter_tufa_3km",
    "gdr_sinter_aniso_ridge",
    "gdr_well_sio2_3km",
    "gdr_volcanic_vent_dist",
)

assert len(FEATURE_NAMES) == 62


def _memory_sweep() -> None:
    """Return large transient buffers to the OS.

    The 62-feature build holds ~20 full-grid float32 intermediates (~49.5 MB each)
    plus per-call EDT scratch from `_fill_outside` (~300 MB).  Without an explicit
    `del` + arena trim, glibc retains those freed pages as RSS and the build was
    OOM-killed at the 3.8 GiB cgroup limit on 2026-10-28 (IR-29).  Values
    and write order are unchanged; only memory release timing differs.
    """
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL(None).malloc_trim(0)
    except Exception:  # pragma: no cover - allocator hint only
        pass


def _quantize_u8(vec: np.ndarray) -> np.ndarray:
    """Monotonic 251-level (0..250) rank-quantile encoding on finite footprint values."""
    v = np.asarray(vec, dtype=np.float32)
    bad = ~np.isfinite(v)
    if bad.any():
        med = float(np.nanmedian(v)) if (~bad).any() else 0.0
        v = v.copy()
        v[bad] = med
    vmin = float(v.min())
    vmax = float(v.max())
    if vmax <= vmin + 1e-12:
        return np.zeros(v.shape, dtype=np.uint8)
    # Subsample 250k points for exact quantile edges in O(1) memory
    rng = np.random.default_rng(20261027)
    sub = v[rng.choice(v.size, size=min(250_000, v.size), replace=False)]
    edges = np.unique(np.quantile(sub, np.linspace(0.0, 1.0, 251)[1:-1]))
    if edges.size == 0:
        return ((v > vmin).astype(np.uint8) * 128)
    return np.searchsorted(edges, v, side="right").astype(np.uint8)


def _hgrad(arr: np.ndarray, sigma: float = 1.4) -> np.ndarray:
    s = ndi.gaussian_filter(arr.astype(np.float32), sigma=sigma, mode="nearest")
    gy = ndi.sobel(s, axis=0, mode="nearest") * np.float32(0.125)
    gx = ndi.sobel(s, axis=1, mode="nearest") * np.float32(0.125)
    return np.hypot(gy, gx).astype(np.float32)


def _tilt_angle(arr: np.ndarray, sigma: float = 1.8) -> np.ndarray:
    s = ndi.gaussian_filter(arr.astype(np.float32), sigma=sigma, mode="nearest")
    gy = ndi.sobel(s, axis=0, mode="nearest") * np.float32(0.125)
    gx = ndi.sobel(s, axis=1, mode="nearest") * np.float32(0.125)
    hg = np.hypot(gy, gx) + np.float32(1e-5)
    lap = ndi.laplace(s, mode="nearest")
    return np.arctan2(-lap, hg).astype(np.float32)


def _fill_outside(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    bad = (~valid) | (~np.isfinite(out)) | (np.abs(out) > 1e10)
    if bad.any() and (~bad).any():
        _, idx = ndi.distance_transform_edt(bad, return_indices=True)
        out[bad] = out[idx[0][bad], idx[1][bad]]
    elif bad.any():
        out.fill(0.0)
    return out


def _build_gdr1391_rasters(transform, crs, foot: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Reuse tested zero-catalogue GDR #1391 rasterizer from `src.thcs.features`."""
    (
        dab_1km,
        dab_3km,
        _probe_prox,
        sinter_dens,
        sinter_prox,
        _well_temp_2km,
        well_geot_3km,
        _well_hot_prox,
        vent_prox,
    ) = _extract_gdr1391_rasters(RAW_DIR, GRID_SHAPE, transform, crs, foot)
    probe_grad = _hgrad(dab_3km, sigma=2.5)
    return dab_3km, probe_grad, sinter_prox, sinter_dens, well_geot_3km, vent_prox


def build_or_load_static_features(force: bool = False) -> dict:
    """Build or load the 62-feature uint8 footprint memmap + 3 physical composites + mimic/relief strata."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    mmap_path = WORK_DIR / "fchd_static_62_u8.dat"
    meta_path = WORK_DIR / "fchd_static_62_meta.json"
    comp_path = WORK_DIR / "fchd_composites_f32.npz"

    with rasterio.open(RAW_DIR / "sample_submission.tif") as ss_ds:
        foot = np.isfinite(ss_ds.read(1))
        transform = ss_ds.transform
        crs = ss_ds.crs
    n_foot = int(foot.sum())

    if not force and mmap_path.is_file() and meta_path.is_file() and comp_path.is_file():
        meta = json.loads(meta_path.read_text())
        if meta.get("feature_names") == list(FEATURE_NAMES) and meta.get("n_foot") == n_foot:
            X_u8 = np.memmap(mmap_path, dtype=np.uint8, mode="r", shape=(n_foot, len(FEATURE_NAMES)))
            comp = np.load(comp_path)
            return {
                "foot": foot,
                "X_u8": X_u8,
                "feature_names": FEATURE_NAMES,
                "scarp_comp": comp["scarp_comp"],
                "basin_comp": comp["basin_comp"],
                "piedmont_comp": comp["piedmont_comp"],
                "relief_bin": comp["relief_bin"],
                "mimic_score": comp["mimic_score"],
            }

    X_u8 = np.memmap(mmap_path, dtype=np.uint8, mode="w+", shape=(n_foot, len(FEATURE_NAMES)))

    def _put(col_idx: int, name: str, arr2d: np.ndarray) -> np.ndarray:
        assert FEATURE_NAMES[col_idx] == name
        q = _quantize_u8(arr2d[foot])
        X_u8[:, col_idx] = q
        return q

    # --- Load true isostatic gravity (band 13) & gravity horizontal gradient (band 18) ---
    with rasterio.open(RAW_DIR / "training_features.tif") as tf_ds:
        grav = _fill_outside(tf_ds.read(13), foot)     # b13: iso_grav_anom
        grav_hg = _fill_outside(tf_ds.read(18), foot)  # b18: iso_grav_anom_hg
    grav_hg_p90 = float(np.percentile(grav_hg[foot], 90)) + 1e-5

    # --- Group 1: 10 m Fluvial Chi + zmean_m ---
    with rasterio.open(EXT_DIR / "dem10_chi_100m_i16.tif") as chi_ds:
        b_step_max = chi_ds.read(1).astype(np.float32)
        b_step_min = chi_ds.read(2).astype(np.float32)
        b_ksn = chi_ds.read(3).astype(np.float32)
        b_area = chi_ds.read(4).astype(np.float32)
        zmean = _fill_outside(chi_ds.read(5).astype(np.float32), chi_ds.read(5) > -32000)

    ch_valid = (b_step_max > -32000) & foot
    step_pos = np.where(ch_valid, np.maximum(b_step_max, 0.0) * 0.001, 0.0).astype(np.float32)
    step_asym = np.where(ch_valid, (b_step_max - np.abs(b_step_min)) * 0.001, 0.0).astype(np.float32)
    ksn_raw = np.where(ch_valid, np.maximum(b_ksn, 0.0), 0.0).astype(np.float32)
    area_wt = np.where(ch_valid, np.maximum(b_area * 0.001 - 5.0, 0.0), 0.0).astype(np.float32)

    chi_step_300 = ndi.gaussian_filter(ndi.maximum_filter(step_pos, size=5), sigma=1.2).astype(np.float32)
    chi_step_800 = ndi.gaussian_filter(ndi.maximum_filter(step_pos, size=9), sigma=3.5).astype(np.float32)
    chi_asym_300 = ndi.gaussian_filter(ndi.maximum_filter(step_asym, size=5), sigma=1.5).astype(np.float32)
    chi_ksn_300 = ndi.gaussian_filter(ndi.maximum_filter(ksn_raw, size=5), sigma=1.2).astype(np.float32)
    ksn_interp = _fill_outside(ksn_raw, ch_valid)
    chi_ksn_jump = (chi_ksn_300 - ndi.gaussian_filter(ksn_interp, sigma=8.0)).astype(np.float32)
    chi_area_step = ndi.gaussian_filter(ndi.maximum_filter(step_pos * area_wt, size=5), sigma=1.5).astype(np.float32)

    with rasterio.open(EXT_DIR / "dem10_chi_100m_sig_i32.tif") as sig_ds:
        sig = sig_ds.read(1)
    sig_fill = _fill_outside(sig.astype(np.float32), (sig > 0) & foot)
    branch_boundary = (ndi.maximum_filter(sig_fill, size=3) != ndi.minimum_filter(sig_fill, size=3)).astype(np.float32)
    ksn_diff_3 = (ndi.maximum_filter(ksn_interp, size=5) - ndi.minimum_filter(ksn_interp, size=5)) * branch_boundary
    chi_cross_dk = ndi.gaussian_filter(ksn_diff_3, sigma=2.5).astype(np.float32)

    zmean_rel_1km = (zmean - ndi.gaussian_filter(zmean, sigma=10.0, mode="nearest")).astype(np.float32)
    lahontan_band = np.exp(-0.5 * ((zmean - np.float32(1338.0)) / np.float32(16.0)) ** 2).astype(np.float32)

    with rasterio.open(EXT_DIR / "topo_10m_derived_100m_u8.tif") as t10_ds:
        t10_slope_p90 = t10_ds.read(1).astype(np.float32)
        t10_steep = t10_ds.read(3).astype(np.float32)
        t10_slope_std = t10_ds.read(4).astype(np.float32)
        t10_relief = t10_ds.read(5).astype(np.float32)
        t10_curv = t10_ds.read(6).astype(np.float32)
        t10_acoh = t10_ds.read(7).astype(np.float32)
        t10_lin = t10_ds.read(8).astype(np.float32)

    lahontan_mimic = (lahontan_band * t10_curv / (np.float32(1.0) + grav_hg / grav_hg_p90)).astype(np.float32)

    _put(0, "chi_channel_valid", ch_valid.astype(np.float32))
    q_chi300 = _put(1, "chi_step_pos_300m", chi_step_300)
    _put(2, "chi_step_pos_800m", chi_step_800)
    _put(3, "chi_step_asym_300m", chi_asym_300)
    _put(4, "chi_ksn_300m", chi_ksn_300)
    _put(5, "chi_ksn_jump_800m", chi_ksn_jump)
    _put(6, "chi_area_weighted_step", chi_area_step)
    _put(7, "chi_cross_branch_dk", chi_cross_dk)
    _put(8, "zmean_m_abs", zmean)
    _put(9, "zmean_relief_1km", zmean_rel_1km)
    _put(10, "lahontan_sehoo_band", lahontan_band)
    q_lah_mimic = _put(11, "lahontan_contour_mimic", lahontan_mimic)

    del b_step_max, b_step_min, b_ksn, b_area, sig, sig_fill, branch_boundary, ksn_diff_3
    del step_pos, step_asym, ksn_raw, area_wt, ch_valid, ksn_interp
    del chi_step_300, chi_step_800, chi_asym_300, chi_ksn_300, chi_area_step, chi_cross_dk, chi_ksn_jump
    del zmean, zmean_rel_1km, lahontan_band, lahontan_mimic
    _memory_sweep()

    # --- Group 2: 10 m Sub-Grid Facet & Piedmont Geomorphology ---
    planar_facet = (t10_acoh * t10_slope_p90 / (t10_slope_std + np.float32(20.0))).astype(np.float32)
    piedmont_infl = (t10_curv * np.exp(-0.5 * ((t10_slope_p90 - np.float32(45.0)) / np.float32(38.0)) ** 2)).astype(np.float32)
    lin_contrast = (t10_lin - ndi.gaussian_filter(t10_lin, sigma=6.0, mode="nearest")).astype(np.float32)

    q_slp90 = _put(12, "topo10_slope_p90", t10_slope_p90)
    _put(13, "topo10_slope_std", t10_slope_std)
    q_rel10 = _put(14, "topo10_relief_local", t10_relief)
    q_curv10 = _put(15, "topo10_curv_prof", t10_curv)
    _put(16, "topo10_aspect_coh", t10_acoh)
    q_lin10 = _put(17, "topo10_hs_lineament", t10_lin)
    _put(18, "topo10_planar_facet_idx", planar_facet)
    q_pied = _put(19, "topo10_piedmont_inflection", piedmont_infl)
    _put(20, "topo10_lineament_contrast", lin_contrast)
    _put(21, "topo10_steep_frac", t10_steep)

    # --- Group 3 & 4: BLM/Road Deconfounders + 1 m LiDAR ---
    with rasterio.open(EXT_DIR / "blm_closed_claim_distance_m.tif") as blm_ds:
        blm_d = _fill_outside(blm_ds.read(1), foot)
    with rasterio.open(EXT_DIR / "tiger_road_distance_m.tif") as rd_ds:
        rd_d = _fill_outside(rd_ds.read(1), foot)

    with rasterio.open(EXT_DIR / "lidar_scarp_features_u8.tif") as lid_ds:
        lid_ex = lid_ds.read(1).astype(np.float32)
        lid_step = lid_ds.read(3).astype(np.float32)
        lid_ln = lid_ds.read(4).astype(np.float32)
        lid_lp = lid_ds.read(5).astype(np.float32)
        lid_dn = lid_ds.read(6).astype(np.float32)
        lid_up = lid_ds.read(7).astype(np.float32)
        lid_cr = lid_ds.read(8).astype(np.float32)
        lid_coh = lid_ds.read(10).astype(np.float32)
        lid_strk = lid_ds.read(11).astype(np.float32)
        lid_val = (lid_ds.read(12) > 0).astype(np.float32)

    blm_mimic = (np.exp(-np.maximum(blm_d, 0.0) / np.float32(300.0)) * t10_curv).astype(np.float32)
    road_mimic = (np.exp(-np.maximum(rd_d, 0.0) / np.float32(220.0)) * np.maximum(lid_step, t10_curv * 0.5)).astype(np.float32)

    _put(22, "blm_claim_dist_log", np.log1p(np.maximum(blm_d, 0.0)))
    q_blm_mim = _put(23, "blm_mine_scarp_mimic", blm_mimic)
    _put(24, "tiger_road_dist_log", np.log1p(np.maximum(rd_d, 0.0)))
    q_rd_mim = _put(25, "road_cut_mimic", road_mimic)

    lid_sharp = ((lid_ln + lid_lp) * lid_coh * np.float32(1.0 / 255.0)).astype(np.float32)
    lid_asym = (np.abs(lid_dn - lid_up) / (lid_dn + lid_up + np.float32(10.0))).astype(np.float32)
    lid_strk_sm = ndi.gaussian_filter(lid_strk * lid_val, sigma=2.0).astype(np.float32)

    _put(26, "lidar_valid", lid_val)
    _put(27, "lidar_ex_max", lid_ex)
    q_lid_step = _put(28, "lidar_step_max", lid_step)
    _put(29, "lidar_cross_max", lid_cr)
    _put(30, "lidar_coh100", lid_coh)
    _put(31, "lidar_scarp_sharpness", lid_sharp)
    _put(32, "lidar_face_asym", lid_asym)
    _put(33, "lidar_strike_smooth", lid_strk_sm)

    del blm_d, rd_d, lid_ex, lid_ln, lid_lp, lid_dn, lid_up, lid_cr, lid_coh, lid_strk, t10_slope_std, t10_acoh, t10_steep
    del t10_slope_p90, t10_relief, t10_curv, t10_lin, planar_facet, piedmont_infl, lin_contrast
    del blm_mimic, road_mimic, lid_sharp, lid_asym, lid_strk_sm, lid_step, lid_val
    _memory_sweep()

    # --- Group 5: Potential-Field 0->150 m Worms, True Basement Depth (b15) & Float32 Radiometrics (b6) ---
    with rasterio.open(RAW_DIR / "training_features.tif") as tf_ds:
        rtp = _fill_outside(tf_ds.read(2), foot)       # b2:  rtp (Reduced-to-Pole magnetic anomaly)
        mag_hg0 = _fill_outside(tf_ds.read(3), foot)   # b3:  tmi_hg (surface magnetic horizontal gradient)
        geod_i2 = _fill_outside(tf_ds.read(4), foot)   # b4:  geod_2ndinv
        rad_tc = _fill_outside(tf_ds.read(6), foot)    # b6:  tc (IR-20: GeoDAWN float32 Radiometric Total Count)
        geod_sh = _fill_outside(tf_ds.read(7), foot)   # b7:  geod_shearrate
        grav_vg = _fill_outside(tf_ds.read(11), foot)  # b11: iso_grav_anom_vg
        det_elev = _fill_outside(tf_ds.read(12), foot) # b12: det_elev
        mag = _fill_outside(tf_ds.read(14), foot)      # b14: tmi
        base_d = _fill_outside(tf_ds.read(15), foot)   # b15: depth_to_base_surf (true sedimentary cover thickness!)
        eq_dens = _fill_outside(tf_ds.read(16), foot)  # b16: ieq_n100a15 (earthquake density)
        cond_s = _fill_outside(tf_ds.read(17), foot)   # b17: cond_surf (subsurface electrical conductivity)
        det_slp = _fill_outside(tf_ds.read(19), foot)  # b19: det_elev_slope

    with rasterio.open(EXT_DIR / "geodawn_extensions_u8.tif") as gext_ds:
        thk = gext_ds.read(1).astype(np.float32)
        uth = gext_ds.read(3).astype(np.float32)
        tmi_up150 = gext_ds.read(4).astype(np.float32)

    grav_tilt = np.arctan2(grav_vg, np.maximum(grav_hg, 0.0) + np.float32(1e-5)).astype(np.float32)
    grav_worm = (np.exp(-np.abs(grav_tilt) / np.float32(0.28)) * grav_hg).astype(np.float32)
    rtp_hg = _hgrad(rtp, sigma=1.5)
    mag_hg0_comb = (0.5 * (mag_hg0 / (float(np.percentile(mag_hg0[foot], 90)) + 1e-5)) + 0.5 * (rtp_hg / (float(np.percentile(rtp_hg[foot], 90)) + 1e-5))).astype(np.float32)
    mag_hg150 = _hgrad(tmi_up150, sigma=1.8)
    m0_n = mag_hg0_comb
    m150_n = mag_hg150 / (float(np.percentile(mag_hg150[foot], 90)) + 1e-5)
    mag_persist = np.sqrt(np.maximum(m0_n * m150_n, 0.0)).astype(np.float32)
    mag_shift = (m150_n - m0_n).astype(np.float32)
    base_hg = _hgrad(base_d, sigma=1.8)
    basin_ind = (base_d > float(np.percentile(base_d[foot], 45))).astype(np.float32)
    concealed_worm = (basin_ind * (grav_hg / grav_hg_p90 + m150_n + base_hg / (float(np.percentile(base_hg[foot], 90)) + 1e-5))).astype(np.float32)
    rad_tc_hg = _hgrad(rad_tc, sigma=1.6)

    _put(34, "grav_iso_anom", grav)
    q_ghg = _put(35, "grav_hgrad_100m", grav_hg)
    _put(36, "grav_tilt_angle", grav_tilt)
    _put(37, "grav_worm_zero_cross", grav_worm)
    _put(38, "mag_tmi", mag)
    _put(39, "mag_hgrad_0m", mag_hg0_comb)
    _put(40, "mag_hgrad_up150m", mag_hg150)
    q_mpers = _put(41, "mag_worm_persistence", mag_persist)
    _put(42, "mag_worm_updip_shift", mag_shift)
    _put(43, "basement_depth", base_d)
    _put(44, "basement_depth_grad", base_hg)
    q_cworm = _put(45, "concealed_basin_worm", concealed_worm)
    _put(46, "rad_tc_f32", rad_tc)
    _put(47, "rad_tc_hgrad", rad_tc_hg)
    _put(48, "rad_thk_ratio", thk)
    _put(49, "rad_uth_ratio", uth)
    _put(50, "geod_max_shear", geod_sh)
    _put(51, "geod_2nd_inv", geod_i2)
    del rtp, mag_hg0, geod_i2, rad_tc, geod_sh, grav_vg, grav, grav_hg
    del grav_tilt, grav_worm, rtp_hg, mag_hg0_comb, mag_hg150, m0_n, m150_n
    del mag_persist, mag_shift, mag, base_d, base_hg, basin_ind, concealed_worm
    del rad_tc_hg, thk, uth, tmi_up150
    _memory_sweep()

    # --- Group 6: 100 m Context & GDR #1391 Blind Hydrothermal Plumes ---
    probe_sm, probe_grad, sinter_3km, sinter_aniso, well_sio2, vent_dist = _build_gdr1391_rasters(transform, crs, foot)

    _put(52, "tf_det_elev", det_elev)
    _put(53, "tf_cond_surf", cond_s)
    _put(54, "tf_eq_density", eq_dens)
    _put(55, "tf_det_elev_slope", det_slp)
    q_prb = _put(56, "gdr_probe2m_dab_2p5km", probe_sm)
    _put(57, "gdr_probe2m_grad", probe_grad)
    q_snt = _put(58, "gdr_sinter_tufa_3km", sinter_3km)
    _put(59, "gdr_sinter_aniso_ridge", sinter_aniso)
    q_wll = _put(60, "gdr_well_sio2_3km", well_sio2)
    _put(61, "gdr_volcanic_vent_dist", vent_dist)
    del det_elev, eq_dens, cond_s, det_slp
    del probe_sm, probe_grad, sinter_3km, sinter_aniso, well_sio2, vent_dist
    _memory_sweep()

    X_u8.flush()

    # Build 3 normalized [0, 1] physical composite maps on the 2D grid for E2/E3 interactions
    scarp_comp = np.zeros(GRID_SHAPE, dtype=np.float32)
    scarp_comp[foot] = (
        0.30 * (q_curv10.astype(np.float32) / 250.0)
        + 0.25 * (q_lin10.astype(np.float32) / 250.0)
        + 0.25 * (q_lid_step.astype(np.float32) / 250.0)
        + 0.20 * (q_chi300.astype(np.float32) / 250.0)
    )
    basin_comp = np.zeros(GRID_SHAPE, dtype=np.float32)
    basin_comp[foot] = (
        0.35 * (q_cworm.astype(np.float32) / 250.0)
        + 0.20 * (q_mpers.astype(np.float32) / 250.0)
        + 0.15 * (q_ghg.astype(np.float32) / 250.0)
        + 0.12 * (q_prb.astype(np.float32) / 250.0)
        + 0.10 * (q_snt.astype(np.float32) / 250.0)
        + 0.08 * (q_wll.astype(np.float32) / 250.0)
    )
    piedmont_comp = np.zeros(GRID_SHAPE, dtype=np.float32)
    piedmont_comp[foot] = (
        0.40 * (q_pied.astype(np.float32) / 250.0)
        + 0.35 * (q_chi300.astype(np.float32) / 250.0)
        + 0.25 * (q_ghg.astype(np.float32) / 250.0)
    )

    # Relief stratum (0..15) for Relief-Matched Hard-Negative Contrastive Sampling
    relief_bin = np.clip(((q_slp90.astype(np.int32) + q_rel10.astype(np.int32)) * 16) // 501, 0, 15).astype(np.uint8)
    # Non-fault mimic intensity (Lahontan shoreline + BLM claim bench + road cut) for hard-negative sampling
    mimic_score = np.maximum.reduce([
        q_lah_mimic.astype(np.float32),
        q_blm_mim.astype(np.float32),
        q_rd_mim.astype(np.float32),
    ]) / np.float32(250.0)

    np.savez(
        comp_path,
        scarp_comp=scarp_comp,
        basin_comp=basin_comp,
        piedmont_comp=piedmont_comp,
        relief_bin=relief_bin,
        mimic_score=mimic_score,
    )
    meta_path.write_text(json.dumps({
        "schema": "fchd-static-62-v1",
        "n_foot": n_foot,
        "feature_names": list(FEATURE_NAMES),
    }, indent=2) + "\n")

    X_ro = np.memmap(mmap_path, dtype=np.uint8, mode="r", shape=(n_foot, len(FEATURE_NAMES)))
    return {
        "foot": foot,
        "X_u8": X_ro,
        "feature_names": FEATURE_NAMES,
        "scarp_comp": scarp_comp,
        "basin_comp": basin_comp,
        "piedmont_comp": piedmont_comp,
        "relief_bin": relief_bin,
        "mimic_score": mimic_score,
    }
