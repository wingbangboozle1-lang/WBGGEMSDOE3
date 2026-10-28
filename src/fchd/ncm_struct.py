"""Nested Component-Masked (NCM) fold-legal structural-mechanics features for FCHD-NCM.

Every function in this module takes an explicit `vis_mask` boolean raster and static
zero-catalogue physical composites. It NEVER reads `labels.tif` or withheld holdout faults.
To prevent `IR-11` proximity-halo collapse, raw monotonic `-d_vis` is excluded; instead we
model directional PCA fault-tip propagation cones, two-fault Crider-Pollard relay bridges,
and non-monotonic piedmont/graben step-out bands (vanishing near `d <= 4 px`), trained via
4-fold out-of-component masking inside `train_zone = foot & ~collar`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

STRUCT_FEATURE_NAMES: tuple[str, ...] = (
    "ncm_tip_cone_narrow",
    "ncm_tip_cone_splay",
    "ncm_relay_corridor",
    "ncm_piedmont_stepout_1p8km",
    "ncm_graben_stepout_4p2km",
    "ncm_belt_density_8km",
    "ncm_belt_strike_aniso",
    "ncm_tip_x_scarp",
    "ncm_tip_x_basin_worm",
    "ncm_stepout_x_piedmont",
)

assert len(STRUCT_FEATURE_NAMES) == 10

# Precompute local (101, 101) coordinate grids for R=50 px (5 km) tip stamps
_R_TIP = 50
_YY, _XX = np.mgrid[-_R_TIP : _R_TIP + 1, -_R_TIP : _R_TIP + 1].astype(np.float32)
_RR = np.hypot(_YY, _XX)
_VALID_RING = (_RR >= 3.5) & (_RR <= float(_R_TIP))
_INV_RR = np.where(_RR > 1e-4, 1.0 / np.maximum(_RR, 1e-4), 0.0).astype(np.float32)
_DECAY_22 = np.exp(-_RR / np.float32(22.0)).astype(np.float32) * _VALID_RING
_DECAY_28 = np.exp(-_RR / np.float32(28.0)).astype(np.float32) * _VALID_RING


def label_fault_components(vis_mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Bridge 1-px gaps so continuous fault traces form single mechanical components."""
    bridged = ndi.binary_dilation(vis_mask, structure=np.ones((3, 3), dtype=bool))
    comp_lbl, n_comp = ndi.label(bridged, structure=np.ones((3, 3), dtype=bool))
    comp_lbl = np.where(vis_mask, comp_lbl, 0).astype(np.int32)
    return comp_lbl, int(n_comp)


def _stamp_tip(
    H: int,
    W: int,
    ty: int,
    tx: int,
    dy_u: float,
    dx_u: float,
    weight: float,
    cid: int,
    narrow_max1: np.ndarray,
    narrow_id1: np.ndarray,
    narrow_max2: np.ndarray,
    splay_max: np.ndarray,
) -> None:
    y0 = max(0, ty - _R_TIP)
    y1 = min(H, ty + _R_TIP + 1)
    x0 = max(0, tx - _R_TIP)
    x1 = min(W, tx + _R_TIP + 1)
    sy0 = y0 - (ty - _R_TIP)
    sy1 = sy0 + (y1 - y0)
    sx0 = x0 - (tx - _R_TIP)
    sx1 = sx0 + (x1 - x0)

    yy = _YY[sy0:sy1, sx0:sx1]
    xx = _XX[sy0:sy1, sx0:sx1]
    inv_r = _INV_RR[sy0:sy1, sx0:sx1]
    cos_a = (yy * np.float32(dy_u) + xx * np.float32(dx_u)) * inv_r

    # Narrow along-strike propagation lobe (+-28 deg)
    nar_ang = np.clip((cos_a - np.float32(0.88)) / np.float32(0.12), 0.0, 1.0)
    nar_val = (np.float32(weight) * _DECAY_22[sy0:sy1, sx0:sx1] * nar_ang).astype(np.float32)

    # Coulomb off-fault splay/horsetail lobe (16..50 deg)
    spl_ang = np.exp(-0.5 * ((cos_a - np.float32(0.82)) / np.float32(0.11)) ** 2) * (cos_a > 0.60)
    spl_val = (np.float32(weight) * _DECAY_28[sy0:sy1, sx0:sx1] * spl_ang).astype(np.float32)

    sub_splay = splay_max[y0:y1, x0:x1]
    np.maximum(sub_splay, spl_val, out=sub_splay)

    # Two-component tracking for Crider-Pollard relay bridge
    comb = np.maximum(nar_val, np.float32(0.75) * spl_val)
    pos = comb > 1e-4
    if not pos.any():
        return
    m1 = narrow_max1[y0:y1, x0:x1]
    id1 = narrow_id1[y0:y1, x0:x1]
    m2 = narrow_max2[y0:y1, x0:x1]

    same = id1 == cid
    # Case 1: same component already holds top slot -> just update m1
    upd_same = pos & same & (comb > m1)
    m1[upd_same] = comb[upd_same]

    # Case 2: different component holds top slot and comb beats m1 -> demote old m1 to m2
    beat_diff = pos & (~same) & (comb > m1)
    m2[beat_diff] = np.maximum(m2[beat_diff], m1[beat_diff])
    m1[beat_diff] = comb[beat_diff]
    id1[beat_diff] = cid

    # Case 3: different component holds top slot and comb is between m2 and m1 -> update m2
    mid_diff = pos & (~same) & (~beat_diff) & (comb > m2)
    m2[mid_diff] = comb[mid_diff]


def compute_ncm_structural_grid(
    vis_mask: np.ndarray,
    scarp_comp: np.ndarray,
    basin_comp: np.ndarray,
    piedmont_comp: np.ndarray,
) -> np.ndarray:
    """Compute (10, H, W) float32 structural-mechanics stack strictly from `vis_mask`."""
    H, W = vis_mask.shape
    comp_lbl, n_comp = label_fault_components(vis_mask)

    narrow_max1 = np.zeros((H, W), dtype=np.float32)
    narrow_id1 = np.zeros((H, W), dtype=np.int32)
    narrow_max2 = np.zeros((H, W), dtype=np.float32)
    splay_max = np.zeros((H, W), dtype=np.float32)

    slices = ndi.find_objects(comp_lbl)
    for idx0, sl in enumerate(slices):
        if sl is None:
            continue
        cid = idx0 + 1
        sub = comp_lbl[sl] == cid
        n_px = int(sub.sum())
        if n_px < 6:
            continue
        ly, lx = np.nonzero(sub)
        ys = ly.astype(np.float32) + np.float32(sl[0].start)
        xs = lx.astype(np.float32) + np.float32(sl[1].start)
        cy = float(ys.mean())
        cx = float(xs.mean())
        dy = ys - np.float32(cy)
        dx = xs - np.float32(cx)
        cyy = float(np.dot(dy, dy)) / n_px + 1e-3
        cxx = float(np.dot(dx, dx)) / n_px + 1e-3
        cyx = float(np.dot(dy, dx)) / n_px
        # Analytic 2x2 principal eigenvector
        tr = cyy + cxx
        det = cyy * cxx - cyx * cyx
        disc = max(tr * tr - 4.0 * det, 0.0) ** 0.5
        lam1 = 0.5 * (tr + disc)
        lam2 = max(0.5 * (tr - disc), 0.25)
        if abs(cyx) > 1e-6:
            uy, ux = lam1 - cxx, cyx
        elif cyy >= cxx:
            uy, ux = 1.0, 0.0
        else:
            uy, ux = 0.0, 1.0
        norm = (uy * uy + ux * ux) ** 0.5 + 1e-12
        uy /= norm
        ux /= norm

        proj = dy * np.float32(uy) + dx * np.float32(ux)
        i_min = int(np.argmin(proj))
        i_max = int(np.argmax(proj))
        span = float(proj[i_max] - proj[i_min])
        if span < 4.0:
            continue
        linearity = min((lam1 / lam2) ** 0.25, 2.2)
        w = min(span / 24.0, 2.4) * (0.5 * linearity)

        # Endpoint 1 points along (-uy, -ux); Endpoint 2 points along (+uy, +ux)
        _stamp_tip(
            H, W, int(round(float(ys[i_min]))), int(round(float(xs[i_min]))),
            -uy, -ux, w, cid, narrow_max1, narrow_id1, narrow_max2, splay_max,
        )
        _stamp_tip(
            H, W, int(round(float(ys[i_max]))), int(round(float(xs[i_max]))),
            uy, ux, w, cid, narrow_max1, narrow_id1, narrow_max2, splay_max,
        )

    relay = np.sqrt(np.maximum(narrow_max1 * narrow_max2, 0.0)).astype(np.float32)

    # Non-monotonic piedmont (1.8 km) and half-graben (4.2 km) parallel step-out bands (0 inside <=4 px)
    # Computed via exact 4-px disk exclusion + fast 2x-grid EDT (sigma=11 px & 18 px are smooth at 200 m)
    near4 = ndi.maximum_filter(vis_mask.astype(np.uint8), size=9) > 0
    vis_2x = vis_mask[::2, ::2]
    if vis_2x.any():
        d_vis_2x = (ndi.distance_transform_edt(~vis_2x) * 2.0).astype(np.float32)
        d_vis = ndi.zoom(d_vis_2x, (H / d_vis_2x.shape[0], W / d_vis_2x.shape[1]), order=1).astype(np.float32)[:H, :W]
    else:
        d_vis = np.full((H, W), 200.0, dtype=np.float32)
    far_enough = (~near4).astype(np.float32)
    pied_band = (np.exp(-0.5 * ((d_vis - np.float32(18.0)) / np.float32(11.0)) ** 2) * far_enough).astype(np.float32)
    grab_band = (np.exp(-0.5 * ((d_vis - np.float32(42.0)) / np.float32(18.0)) ** 2) * far_enough).astype(np.float32)

    # Coarse 8 km tectonic-belt density & directional anisotropy on 4x downsampled grid (fast & non-local)
    vis_ds = vis_mask[::4, ::4].astype(np.float32)
    belt_8km_ds = ndi.gaussian_filter(vis_ds, sigma=20.0, mode="constant") - np.float32(0.35) * ndi.gaussian_filter(
        vis_ds, sigma=3.0, mode="constant"
    )
    gy_ds = ndi.sobel(ndi.gaussian_filter(vis_ds, sigma=8.0, mode="constant"), axis=0)
    gx_ds = ndi.sobel(ndi.gaussian_filter(vis_ds, sigma=8.0, mode="constant"), axis=1)
    aniso_ds = np.hypot(gy_ds, gx_ds)

    belt_8km = ndi.zoom(belt_8km_ds, (H / belt_8km_ds.shape[0], W / belt_8km_ds.shape[1]), order=1).astype(np.float32)[:H, :W]
    belt_aniso = ndi.zoom(aniso_ds, (H / aniso_ds.shape[0], W / aniso_ds.shape[1]), order=1).astype(np.float32)[:H, :W]

    tip_comb = narrow_max1 + np.float32(1.5) * relay
    tip_x_scarp = (tip_comb * scarp_comp).astype(np.float32)
    tip_x_basin = ((tip_comb + np.float32(0.7) * splay_max) * basin_comp).astype(np.float32)
    step_x_pied = ((pied_band + np.float32(0.6) * grab_band) * piedmont_comp).astype(np.float32)

    out = np.stack([
        narrow_max1,
        splay_max,
        relay,
        pied_band,
        grab_band,
        belt_8km,
        belt_aniso,
        tip_x_scarp,
        tip_x_basin,
        step_x_pied,
    ], axis=0)
    return out
