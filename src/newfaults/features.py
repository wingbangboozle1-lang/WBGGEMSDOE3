"""Static evidence stack built from the 19 official bands + official auxiliary layers.

The stack is written feature-major to a float16 memmap
(``data/work/features_f16.dat``, shape ``(F, H, W)``) so that
row-block reads stay contiguous on a 3 GB machine.

Design rationale (why these features):
  * single-band pixel values are weak fault indicators here (observed max |AUC-0.5| ~ 0.07);
    faults are one-pixel *lines*, so the informative statistics are local, oriented and
    multi-scale;
  * a fault that appears in several independent evidence types (magnetic, gravity,
    topographic, geodetic) is far more likely to be a real mapped structure than a
    single-data artefact, hence the cross-band congruence channel;
  * geothermal proximity (hot springs, volcanic vents) encodes where expert reviewers
    are motivated to map new structures for a geothermal prize.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, sobel

from . import data

#: bands that carry the strongest lineament signal in this dataset (see knowledge note)
CORE_BANDS = {
    "detrend_elev": 12,
    "detrend_slope": 19,
    "mag_tilt": 6,
    "mag_hgrad": 3,
    "grav_iso": 13,
    "grav_vgrad": 11,
    "geod_second_inv": 4,
    "eq_density": 16,
    "depth_basement": 15,
}

#: bands used for the multi-evidence lineament congruence channel
CONGRUENCE_BANDS = ("mag_tilt", "mag_hgrad", "grav_iso", "grav_vgrad", "detrend_slope")

EPS = 1e-9


def _fill(a: np.ndarray) -> np.ndarray:
    """Replace NaN by the finite median (all official bands are >99.8 % finite)."""
    nan = ~np.isfinite(a)
    if not nan.any():
        return a
    out = a.copy()
    out[nan] = float(np.nanmedian(a))
    return out


def zscore(a: np.ndarray, ref: np.ndarray | None = None) -> np.ndarray:
    r = a.ravel() if ref is None else ref.ravel()
    r = r[np.isfinite(r)]
    med = float(np.median(r))
    mad = float(np.median(np.abs(r - med))) or 1.0
    return np.clip((a - med) / (1.4826 * mad), -8.0, 8.0).astype(np.float32)


def gradient(a: np.ndarray) -> np.ndarray:
    gx = sobel(a, axis=1, mode="nearest")
    gy = sobel(a, axis=0, mode="nearest")
    return np.hypot(gx, gy).astype(np.float32)


def structure(a: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Structure-tensor channels at scale ``r``.

    Returns ``(coherence, ridge, orientation)`` where
    coherence = (l1 - l2) / (l1 + l2)    (how anisotropic the local edge field is)
    ridge     = l1 + l2 normalised       (edge energy at this scale)
    orientation = 0.5 * atan2(2 Jxy, Jxx - Jyy)
    """
    gx = sobel(a, axis=1, mode="nearest")
    gy = sobel(a, axis=0, mode="nearest")
    jxx = gaussian_filter(gx * gx, r, mode="nearest")
    jyy = gaussian_filter(gy * gy, r, mode="nearest")
    jxy = gaussian_filter(gx * gy, r, mode="nearest")
    tr = jxx + jyy
    diff = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy**2)
    l1 = 0.5 * (tr + diff)
    l2 = 0.5 * (tr - diff)
    coherence = ((l1 - l2) / (l1 + l2 + EPS)).astype(np.float32)
    energy = (l1 + l2).astype(np.float32)
    orient = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy + EPS)).astype(np.float32)
    return coherence, energy, orient


def point_distance(shape: tuple[int, int], rows, cols) -> np.ndarray:
    """Euclidean distance (px) to the nearest of the given points."""
    seed = np.ones(shape, bool)
    rr = np.asarray(rows, int)
    cc = np.asarray(cols, int)
    ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    seed[rr[ok], cc[ok]] = False
    return distance_transform_edt(seed).astype(np.float32)


def mask_distance(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~np.asarray(mask, bool)).astype(np.float32)


def _geo_points() -> dict[str, np.ndarray]:
    """Row/col arrays for the geothermal evidence tables (official GDR 1391 mirrors)."""
    ws = data.wellspring_table()
    thermal = [r for r in ws if np.isfinite(r["temp_c"]) and r["temp_c"] >= 30.0]
    hot = [r for r in ws if np.isfinite(r["temp_c"]) and r["temp_c"] >= 60.0]
    vents = data.vent_table()
    return {
        "spring_all": np.array([[r["row"], r["col"]] for r in ws]).T,
        "spring_thermal30": np.array([[r["row"], r["col"]] for r in thermal]).T
        if thermal else np.zeros((2, 0), int),
        "spring_hot60": np.array([[r["row"], r["col"]] for r in hot]).T if hot else np.zeros((2, 0), int),
        "vent": np.array([[r["row"], r["col"]] for r in vents]).T if vents else np.zeros((2, 0), int),
    }


def feature_plan() -> list[tuple[str, str]]:
    """(feature name, kind) in the exact order the builder writes them."""
    plan: list[tuple[str, str]] = []
    for name in CORE_BANDS:
        plan += [(f"{name}__z", "z"),
                 (f"{name}__grad", "grad"),
                 (f"{name}__std4", "std4"),
                 (f"{name}__coh4", "coh4"),
                 (f"{name}__coh9", "coh9")]
    for name in CONGRUENCE_BANDS:
        plan += [(f"{name}__lines", "lines")]
    plan += [
        ("congruence__mean", "cong"),
        ("congruence__min", "cong_min"),
        ("congruence__max", "cong_max"),
        ("congruence__strike_cos", "strike_cos"),
        ("congruence__strike_sin", "strike_sin"),
        ("geod_second_inv__grad_r6", "grad6"),
        ("geod_shear__grad_r6", "grad6"),
        ("eq_density__z", "z16"),
        ("depth_basement__z", "z15"),
        ("conductivity__z", "z17"),
        ("grav_iso__mean8", "mean8"),
        ("detrend_elev__mean8", "mean8_12"),
        ("dist__spring_all", "dpts"),
        ("dist__spring_thermal30", "dpts"),
        ("dist__spring_hot60", "dpts"),
        ("dist__vent", "dpts"),
        ("dist__sgmc_fault", "dsgmc"),
        ("dist__acq_block_edge", "dblock"),
    ]
    return plan


def _compute(name: str, kind: str, cache: dict) -> np.ndarray:
    def band(nm: str) -> np.ndarray:
        if nm not in cache:
            cache[nm] = _fill(data.band(CORE_BANDS[nm])) if nm in CORE_BANDS else _fill(data.band(_by_name(nm)))
        return cache[nm]

    shape = (3730, 3292)
    if kind == "z":
        return zscore(band(name.split("__")[0]))
    if kind == "grad":
        return zscore(gradient(band(name.split("__")[0])))
    if kind == "std4":
        b = zscore(band(name.split("__")[0]))
        return zscore(gaussian_filter(b * b, 4, mode="nearest") - gaussian_filter(b, 4, mode="nearest") ** 2)
    if kind == "coh4":
        return structure(band(name.split("__")[0]), 4)[0]
    if kind == "coh9":
        return structure(band(name.split("__")[0]), 9)[0]
    if kind == "lines":
        b = band(name.split("__")[0])
        coh = structure(b, 4)[0]
        return zscore(gradient(b) * (0.25 + 0.75 * coh))
    if kind in ("cong", "cong_min", "cong_max"):
        stack = []
        for nm in CONGRUENCE_BANDS:
            b = band(nm)
            coh = structure(b, 4)[0]
            stack.append(zscore(gradient(b) * (0.25 + 0.75 * coh)))
        s = np.stack(stack)
        return {"cong": s.mean(0), "cong_min": s.min(0), "cong_max": s.max(0)}[kind].astype(np.float32)
    if kind in ("strike_cos", "strike_sin"):
        # dominant strike from the highest-coherence core band
        coh = structure(band("detrend_slope"), 6)[0]
        _, _, orient = structure(band("detrend_elev"), 6)
        th = orient
        out = (np.cos(th) if kind == "strike_cos" else np.sin(th)).astype(np.float32)
        return np.where(coh > 0.2, out, 0.0).astype(np.float32)
    if kind == "grad6":
        return zscore(gaussian_filter(gradient(band(name.split("__")[0])), 6, mode="nearest"))
    if kind == "z16":
        return zscore(band("eq_density"))
    if kind == "z15":
        return zscore(band("depth_basement"))
    if kind == "z17":
        return zscore(_fill(data.band(17)))
    if kind == "mean8":
        return zscore(gaussian_filter(band("grav_iso"), 8, mode="nearest"))
    if kind == "mean8_12":
        return zscore(gaussian_filter(band("detrend_elev"), 8, mode="nearest"))
    if kind == "dpts":
        pts = _geo_points()
        key = name.split("__")[1]
        if pts[key].size == 0:
            return np.zeros(shape, np.float32)
        return np.clip(point_distance(shape, pts[key][0], pts[key][1]), 0, 60).astype(np.float32)
    if kind == "dsgmc":
        sg = data.u8_layer("derived_sgmc_faults_100m_u8.tif")
        return np.clip(mask_distance(np.nan_to_num(sg) > 0), 0, 60).astype(np.float32)
    if kind == "dblock":
        blk = data.u8_layer("acquisition_block_id_100m.tif")
        edges = np.zeros(shape, bool)
        edges[:-1, :] |= blk[:-1, :] != blk[1:, :]
        edges[:, :-1] |= blk[:, :-1] != blk[:, 1:]
        return np.clip(mask_distance(edges), 0, 60).astype(np.float32)
    raise KeyError(kind)


_NAME_TO_BAND = {
    "mag_anom": 1, "mag_rtp": 2, "mag_hgrad": 3, "geod_second_inv": 4, "grav_iso_slope": 5,
    "mag_tilt": 6, "geod_shear": 7, "geod_dilat": 8, "mag_vgrad": 9, "dist_eq": 10,
    "grav_vgrad": 11, "detrend_elev": 12, "grav_iso": 13, "mag_tmi": 14,
    "depth_basement": 15, "eq_density": 16, "conductivity": 17, "grav_hgrad": 18,
    "detrend_slope": 19}


def _by_name(nm: str) -> int:
    return _NAME_TO_BAND[nm]


def build_static_stack(out: Path, overwrite: bool = False) -> dict:
    """Compute the plan and write it float16 feature-major; returns a manifest dict."""
    g = data.grid()
    plan = feature_plan()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not overwrite:
        arr = np.lib.format.open_memmap(out, mode="r")
        if arr.shape == (len(plan), *g.shape):
            return {"path": str(out), "shape": list(arr.shape), "names": [p[0] for p in plan], "cached": True}
    arr = np.lib.format.open_memmap(out, mode="w+", dtype=np.float16, shape=(len(plan), *g.shape))
    cache: dict = {}
    for i, (name, kind) in enumerate(plan):
        layer = _compute(name, kind, cache)
        if layer.shape != g.shape:
            raise ValueError(f"{name}: {layer.shape} != {g.shape}")
        arr[i] = layer.astype(np.float16)
        arr.flush()
        print(f"  [{i+1:02d}/{len(plan)}] {name}")
    del arr
    return {"path": str(out), "shape": [len(plan), *g.shape], "names": [p[0] for p in plan], "cached": False}


# ----------------------------------------------------------------------------------------------
# structural priors derived from the *visible* catalogue only
# ----------------------------------------------------------------------------------------------

def strike_field(visible: np.ndarray, smooth: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Local line direction of the catalogue.

    For a one-pixel line the image gradient is perpendicular to the line, so the line
    direction is ``atan2(gy, gx) + pi/2``.  Returns ``(cos_theta, sin_theta)``.
    """
    b = gaussian_filter(visible.astype(np.float32), smooth, mode="nearest")
    gx = sobel(b, axis=1, mode="nearest")
    gy = sobel(b, axis=0, mode="nearest")
    theta = np.arctan2(gy, gx) + np.pi / 2.0
    return np.cos(theta).astype(np.float32), np.sin(theta).astype(np.float32)


def along_strike_prior(visible: np.ndarray, distances=(2, 3, 4, 6, 8, 11, 14),
                       n_orient: int = 8, decay: float = 0.6) -> np.ndarray:
    """Along-strike continuation prior (ASCP).

    Accumulates the visible catalogue shifted along each of ``n_orient`` directions at
    several distances, weighting a direction by ``cos^2`` of its angular mismatch with
    the local strike and by ``1/d**decay``.  Faults propagate along strike through relay
    ramps, tip damage zones and en-echelon step-overs, so this prior concentrates mass on
    the *continuation* of mapped structures rather than smearing isotropically.
    """
    ct, st = strike_field(visible)
    H, W = visible.shape
    acc = np.zeros((H, W), np.float32)
    v = visible.astype(np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    for k in range(n_orient):
        ang = np.pi * k / n_orient
        ca, sa = float(np.cos(ang)), float(np.sin(ang))
        align = (ct * ca + st * sa) ** 2
        for d in distances:
            dy = int(round(-d * sa))
            dx = int(round(-d * ca))
            if dy == 0 and dx == 0:
                continue
            sh = np.roll(np.roll(v, dy, axis=0), dx, axis=1)
            acc += (sh * align * (1.0 / (d ** decay))).astype(np.float32)
    return acc


def corridor_prior(visible: np.ndarray, sigma: float = 24.0) -> np.ndarray:
    return gaussian_filter(visible.astype(np.float32), sigma, mode="nearest")


def parallel_offset_prior(visible: np.ndarray, distances=(3, 4, 5, 6, 8, 10, 12, 15),
                          decay: float = 0.35, n_orient: int = 8) -> np.ndarray:
    """Parallel-strand prior.

    Faults in an extensional terrane occur as en-echelon arrays of sub-parallel strands a
    few hundred metres apart, so a newly recognised fault is often a *parallel* strand
    offset from a mapped one.  The visible catalogue is shifted away from its local strike
    (i.e. along the fault normal) at several distances and accumulated, weighted by
    ``cos^2`` of the angular match with the normal and by ``1/d**decay``.
    """
    ct, st = strike_field(visible)
    H, W = visible.shape
    acc = np.zeros((H, W), np.float32)
    v = visible.astype(np.float32)
    for k in range(n_orient):
        ang = np.pi * k / n_orient
        ca, sa = float(np.cos(ang)), float(np.sin(ang))
        # alignment of the shift direction (ca, sa) with the local fault normal (-st, ct)
        align = np.clip(-ca * st + sa * ct, 0.0, None) ** 2
        align = align.astype(np.float32)
        for d in distances:
            dy = int(round(d * sa))
            dx = int(round(d * ca))
            if dy == 0 and dx == 0:
                continue
            sh = np.roll(np.roll(v, dy, axis=0), dx, axis=1)
            acc += sh * align * np.float32(1.0 / (d ** decay))
    return acc
