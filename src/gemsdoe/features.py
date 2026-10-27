"""Physically motivated, catalogue-free feature engineering on the 100 m grid.

Design rules (non-negotiable, because the scored ground truth is fault pixels that
are NOT in the public catalogue -- see the official problem description):

1. No feature may depend on the fault catalogue. Distance-to-catalogue-fault
   features have a large AUC against the training labels and near-zero transfer
   to unseen faults (the classic leakage trap for this competition).
2. Every derived feature must have a stated physical mechanism. Three named
   hypotheses are implemented here:

   H-A  *Fabric refraction* (magnetic / gravity): the dominant orientation of the
        potential-field fabric changes abruptly across a fault. This keys on the
        *orientation* discontinuity, not on gradient magnitude, so a buried fault
        that leaves no strong edge can still be detected.

   H-B  *Basement isopach hinge*: a steep depth-to-basement gradient marks a
        range-front / basin-margin hinge. Where cover is thick the surface scarp is
        absent, which is exactly where published mapping is incomplete.

   H-C  *Paired scarp / relay step-over*: en-echelon normal-fault arrays leave
        paired, sub-parallel scarps with a topographic bench between them.

   Named non-fault mimics (recorded, never assumed away):
   H-A: lithologic contacts, survey flight-line and leveling artefacts.
   H-B: isostatic-gravity interpolation artefacts; thickness changes unrelated to faulting.
   H-C: shorelines/terraces, roads and railroad grades, fan edges, cut-and-fill.

Memory discipline: features are written straight into a float32 memmap; at most a
few 49 MB arrays are resident at once (the sandbox has 3 GB RAM).
"""

from __future__ import annotations

import json

import numpy as np
from scipy import ndimage as ndi

from . import config as C
from . import io as gio

DE_SCALES = (1, 2, 3, 5, 8)
CURV_SCALES = (2, 5)
MAG_SCALES = (1, 2, 4)
GRAV_SCALES = (2, 4, 8)


def derived_names() -> list[str]:
    """Deterministic names of every derived feature, in write order."""
    n: list[str] = []
    for s in DE_SCALES:
        n += [f"de_log_s{s}", f"de_slope_s{s}"]
    for s in CURV_SCALES:
        n += [f"de_cprof_s{s}", f"de_cplan_s{s}", f"de_coh_s{s}",
              f"de_ori_cos_s{s}", f"de_ori_sin_s{s}"]
    n += ["de_relief_s8", "de_paired_scarp"]
    for layer, scales in (("rtp", MAG_SCALES), ("iso_grav_anom", GRAV_SCALES)):
        for s in scales:
            n += [f"{layer}_hg_s{s}", f"{layer}_log_s{s}"]
        n += [f"{layer}_fabric_kink", f"{layer}_coh_s2"]
    for s in (2, 4):
        n += [f"depth_hg_s{s}"]
    n += ["depth_hinge"]
    n += ["cond_log_s1", "cond_log_s2", "cond_hg_s2"]
    n += ["tmi_hg_s2", "tmi_log_s2", "tmi_vg_hg_s2", "tc_log_s1", "tc_log_s2",
          "mag_anom_log_s2", "tmi_hg_log_s2"]
    n += ["ieq_g_s2", "ieq_g_s4", "deq_g_s2", "ieq_hg_s2"]
    n += ["des_g_s2", "des_log_s2"]
    return n


def all_names() -> list[str]:
    return list(C.BAND_NAMES) + derived_names()


def _fill_nearest(a: np.ndarray) -> np.ndarray:
    bad = ~np.isfinite(a)
    if not bad.any():
        return a
    if bad.all():
        return np.zeros_like(a)
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return a[tuple(idx)]


def _g(a, s):
    return ndi.gaussian_filter(a, s, mode="nearest", truncate=4.0)


def _grad(a):
    gy, gx = np.gradient(a)
    return gx, gy


def _slope(a):
    gx, gy = _grad(a)
    return np.hypot(gx, gy)


def _log(a, s):
    """Negative Laplacian of Gaussian: positive on ridges (scarps / contacts)."""
    return -ndi.gaussian_laplace(a, s, mode="nearest", truncate=4.0)


def _structure(a, s):
    gx, gy = _grad(a)
    Jxx = _g(gx * gx, s)
    Jxy = _g(gx * gy, s)
    Jyy = _g(gy * gy, s)
    tr = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    coh = disc / (tr + 1e-9)
    theta = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy)
    return coh.astype(np.float32), theta.astype(np.float32)


class _Writer:
    def __init__(self, path, names, shape):
        self.path = path
        self.names = names
        self.idx = 0
        self.stack = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                               shape=(len(names),) + shape)

    def add(self, name: str, arr) -> None:
        expect = self.names[self.idx]
        if name != expect:
            raise RuntimeError(f"feature name drift: got {name!r} expected {expect!r}")
        a = np.asarray(arr, dtype=np.float32)
        if a.shape != (C.HEIGHT, C.WIDTH):
            raise ValueError(f"{name}: shape {a.shape}")
        self.stack[self.idx] = np.clip(np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0),
                                       -1e6, 1e6)
        self.idx += 1
        ndi.gaussian_filter  # noqa: B018  (keep import used)

    def close(self):
        self.stack.flush()
        del self.stack


def build_feature_stack(force: bool = False, verbose: bool = True):
    """Compute (or load) the feature stack. Returns (float32 memmap (n,H,W), names)."""
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = C.CACHE_DIR / "feature_stack.npy"
    npath = C.CACHE_DIR / "feature_names.json"
    names = all_names()
    if path.exists() and npath.exists() and not force:
        got = json.loads(npath.read_text())
        arr = np.load(path, mmap_mode="r")
        if got == names and arr.shape == (len(names), C.HEIGHT, C.WIDTH):
            if verbose:
                print(f"[features] cached {arr.shape} ({len(names)} features)")
            return arr, names

    w = _Writer(path, names, (C.HEIGHT, C.WIDTH))
    bidx = {n: i for i, n in enumerate(C.BAND_NAMES)}

    for i, nm in enumerate(C.BAND_NAMES):
        a = _fill_nearest(gio.read_band(C.FEATURES_TIF, i + 1))
        w.add(nm, a)
        if verbose:
            print(f"[features] band {i+1:2d} {nm:22s} {float(np.nanmin(a)):.3g}..{float(np.nanmax(a)):.3g}",
                  flush=True)

    def get(name):
        return np.asarray(w.stack[bidx[name]])

    de = get("det_elev")
    gsc = {s: _g(de, s) for s in DE_SCALES}
    for s in DE_SCALES:
        w.add(f"de_log_s{s}", _log(de, s))
        w.add(f"de_slope_s{s}", _slope(gsc[s]))
    for s in CURV_SCALES:
        gx, gy = _grad(gsc[s])
        gxx, gxy1 = _grad(gx)
        gyy, gxy2 = _grad(gy)
        gxy = 0.5 * (gxy1 + gxy2)
        den = gx * gx + gy * gy + 1e-9
        w.add(f"de_cprof_s{s}", (gxx * gx * gx + 2.0 * gxy * gx * gy + gyy * gy * gy) / den)
        w.add(f"de_cplan_s{s}", (gxx * gy * gy - 2.0 * gxy * gx * gy + gyy * gx * gx) / den)
        coh, th = _structure(gsc[s], s)
        w.add(f"de_coh_s{s}", coh)
        w.add(f"de_ori_cos_s{s}", np.cos(2 * th))
        w.add(f"de_ori_sin_s{s}", np.sin(2 * th))
    w.add("de_relief_s8", gsc[8] - gsc[1])

    # H-C paired scarp: correlate the ridge indicator at +-3 px perpendicular
    ridge = _log(de, 2).astype(np.float32)
    coh2, th2 = _structure(gsc[2], 2)
    H, W = C.HEIGHT, C.WIDTH
    rows = np.arange(H, dtype=np.float32)[:, None]
    cols = np.arange(W, dtype=np.float32)[None, :]
    sin2, cos2 = np.sin(th2), np.cos(th2)
    dy = np.rint(3.0 * sin2)
    dx = np.rint(3.0 * cos2)
    r1 = np.clip(rows + dy, 0, H - 1).astype(np.int32)
    c1 = np.clip(cols + dx, 0, W - 1).astype(np.int32)
    r2 = np.clip(rows - dy, 0, H - 1).astype(np.int32)
    c2 = np.clip(cols - dx, 0, W - 1).astype(np.int32)
    w.add("de_paired_scarp", np.minimum(ridge[r1, c1] * ridge[r2, c2], 1e6))

    for layer, scales in (("rtp", MAG_SCALES), ("iso_grav_anom", GRAV_SCALES)):
        a = get(layer)
        for s in scales:
            w.add(f"{layer}_hg_s{s}", _slope(_g(a, s)))
            w.add(f"{layer}_log_s{s}", _log(a, s))
        coh_a, th_a = _structure(_g(a, 2), 2)
        coh_b, th_b = _structure(_g(a, 6), 6)
        dth = 0.5 * np.abs(np.angle(np.exp(1j * 2 * (th_a - th_b))))
        w.add(f"{layer}_fabric_kink", dth * coh_a * coh_b)
        w.add(f"{layer}_coh_s2", coh_a)

    dep = get("depth_to_base_surf")
    for s in (2, 4):
        w.add(f"depth_hg_s{s}", _slope(_g(dep, s)))
    w.add("depth_hinge", _g(dep, 4) - _g(dep, 12))

    cond = get("cond_surf")
    w.add("cond_log_s1", _log(cond, 1))
    w.add("cond_log_s2", _log(cond, 2))
    w.add("cond_hg_s2", _slope(_g(cond, 2)))

    tmi = get("tmi")
    w.add("tmi_hg_s2", _slope(_g(tmi, 2)))
    w.add("tmi_log_s2", _log(tmi, 2))
    w.add("tmi_vg_hg_s2", _slope(_g(get("tmi_vg"), 2)))
    tc = get("tc")
    w.add("tc_log_s1", _log(tc, 1))
    w.add("tc_log_s2", _log(tc, 2))
    w.add("mag_anom_log_s2", _log(get("mag_anom"), 2))
    w.add("tmi_hg_log_s2", _log(get("tmi_hg"), 2))

    ieq = get("ieq_n100a15")
    w.add("ieq_g_s2", _g(ieq, 2))
    w.add("ieq_g_s4", _g(ieq, 4))
    w.add("deq_g_s2", _g(get("deq_n100a15"), 2))
    w.add("ieq_hg_s2", _slope(_g(ieq, 2)))

    des = get("det_elev_slope")
    w.add("des_g_s2", _g(des, 2))
    w.add("des_log_s2", _log(des, 2))

    written = w.idx
    w.close()
    if written != len(names):
        raise RuntimeError(f"wrote {written} features, expected {len(names)}")
    npath.write_text(json.dumps(names, indent=1))
    if verbose:
        print(f"[features] wrote {path} shape=({len(names)},{C.HEIGHT},{C.WIDTH}) float32")
    return np.load(path, mmap_mode="r"), names
