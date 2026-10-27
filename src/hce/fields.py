"""Build the HCE-1 static feature stack from the hash-pinned competition mirror.

All fields are functions of the 19 competition bands or the owner-mirrored external
layers ONLY.  No label, submission raster, or hidden fold enters a static field.
Each field is stored as a 10-bin quantile code (0 = missing) over the 5,167,373
finite footprint cells, in a memory-mappable uint8 array of shape
(n_fields, n_footprint).  Quantile binning makes tree fitting cheap and robust to
the unknown physical units of the uint8 external layers.

The ONE derived statistic that is new in this lane is `phase_congruence`:
for six independent physical channels we compute the structure-tensor gradient
orientation, then measure |sum_j w_j exp(2i theta_j)| / sum_j w_j, i.e. the
degree to which strong edges in radiometric ratios, magnetics, gravity, strain
and topography are COLLINEAR.  A single-channel edge (a scarp, a lithologic
contact, a survey stripe) is not enough; the statistic requires agreement.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"

BANDS = ["mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
         "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
         "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi",
         "depth_to_base_surf", "ieq_n100a15", "cond_surf", "iso_grav_anom_hg",
         "det_elev_slope"]
LIDAR = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
         "downface_max", "upface_max", "cross_max", "relief", "coh100", "strike"]
RAD = ["K", "Th", "U", "TC"]
EXT = ["ThK", "UK", "UTh", "TMI_up150"]
QEDGES = np.array([0.02, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.98])


def _clean(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32, copy=True)
    a[~np.isfinite(a) | (a < -1e30)] = np.nan
    return a


def _fill(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = a[foot]
    med = float(np.nanmedian(v)) if np.isfinite(v).any() else 0.0
    out = np.where(np.isfinite(a), a, med).astype(np.float32)
    out[~foot] = med
    return out


def _bin(field: np.ndarray, foot: np.ndarray, fidx: np.ndarray) -> np.ndarray:
    v = field.ravel()[fidx]
    ok = np.isfinite(v)
    out = np.zeros(v.shape, np.uint8)
    if ok.sum() < 1000:
        return out
    edges = np.quantile(v[ok], QEDGES)
    out[ok] = (1 + np.searchsorted(edges, v[ok], side="right")).astype(np.uint8)
    return out


def _structure_tensor(f: np.ndarray, foot: np.ndarray, sigma=2.0, rho=4.0):
    """Return (edge strength, coherence, unit double-angle phasor real/imag)."""
    s = ndi.gaussian_filter(_fill(f, foot), sigma)
    gy, gx = np.gradient(s)
    j11 = ndi.gaussian_filter(gy * gy, rho)
    j22 = ndi.gaussian_filter(gx * gx, rho)
    j12 = ndi.gaussian_filter(gy * gx, rho)
    tr = j11 + j22
    disc = np.sqrt(np.maximum((j11 - j22) ** 2 + 4.0 * j12 ** 2, 0.0))
    lam1 = (tr + disc) / 2.0
    lam2 = (tr - disc) / 2.0
    coh = disc / (tr + 1e-9)
    strength = np.sqrt(np.maximum(lam1, 0.0))
    # double-angle representation: z = (j11-j22) + 2i j12, normalised
    norm = np.sqrt((j11 - j22) ** 2 + 4.0 * j12 ** 2) + 1e-9
    zr = (j11 - j22) / norm
    zi = 2.0 * j12 / norm
    strength[~foot] = np.nan
    return strength, coh, zr, zi


def build(out_dir: Path | None = None) -> dict:
    out_dir = Path(out_dir or WORK)
    out_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(RAW / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    fidx = np.flatnonzero(foot.ravel()).astype(np.uint32)
    n = fidx.size
    names: list[str] = []
    arrays: list[np.ndarray] = []

    def add(name: str, field: np.ndarray):
        assert field.shape == foot.shape, (name, field.shape)
        names.append(name)
        arrays.append(_bin(field, foot, fidx))

    tf = rasterio.open(RAW / "training_features.tif")
    base: dict[str, np.ndarray] = {}
    for i, nm in enumerate(BANDS, start=1):
        a = _clean(tf.read(i))
        base[nm] = a
        add("band_" + nm, a)
    tf.close()

    with rasterio.open(RAW / "external/lidar_scarp_features_u8.tif") as ds:
        valid = ds.read(12) > 0
        for j, nm in enumerate(LIDAR, start=1):
            a = ds.read(j).astype(np.float32)
            a[~valid] = np.nan
            if nm in ("upface_max", "downface_max", "ex_max", "lapneg_max", "relief", "coh100", "step_max"):
                add("lidar_" + nm, a)
    with rasterio.open(RAW / "external/geodawn_rad_u8.tif") as ds:
        rad = {nm: ds.read(j).astype(np.float32) for j, nm in enumerate(RAD, start=1)}
        for nm, a in rad.items():
            add("rad_" + nm, a)
    with rasterio.open(RAW / "external/geodawn_extensions_u8.tif") as ds:
        ext = {nm: ds.read(j).astype(np.float32) for j, nm in enumerate(EXT, start=1)}
        for nm, a in ext.items():
            add("ext_" + nm, a)

    # ---- radiometric log-ratio channels (hydrothermal K/Th, U/Th alteration) ----
    kth = np.log((rad["K"] + 1.0) / (rad["Th"] + 1.0))
    uth = np.log((rad["U"] + 1.0) / (rad["Th"] + 1.0))
    add("logratio_K_Th", kth)
    add("logratio_U_Th", uth)

    # ---- multi-scale single-channel edge fields ----
    for nm, sigmas in (("det_elev", (1.5, 3.0, 6.0)), ("rtp", (2.0, 5.0)),
                       ("iso_grav_anom", (2.0, 5.0)), ("geod_2ndinv", (4.0,)),
                       ("tc", (2.0,)), ("mag_anom", (2.0,))):
        f = _fill(base[nm], foot)
        for s in sigmas:
            add(f"gradmag_{nm}_s{s:g}", ndi.gaussian_gradient_magnitude(f, s))
    f = _fill(base["det_elev"], foot)
    for s in (1.5, 3.0):
        add(f"log_det_elev_s{s:g}", -s * s * ndi.gaussian_laplace(f, s))
    mx = ndi.maximum_filter(f, size=7)
    mn = ndi.minimum_filter(f, size=7)
    add("relief7_det_elev", mx - mn)

    # ---- NOVEL: cross-channel collinear edge (phase) congruence ----
    channels = {
        "logratio_K_Th": kth,
        "logratio_U_Th": uth,
        "rtp": base["rtp"],
        "iso_grav_anom": base["iso_grav_anom"],
        "geod_2ndinv": base["geod_2ndinv"],
        "det_elev": base["det_elev"],
    }
    sre = np.zeros(foot.shape, np.float64)
    sim = np.zeros(foot.shape, np.float64)
    wsum = np.zeros(foot.shape, np.float64)
    count = np.zeros(foot.shape, np.float32)
    for nm, ch in channels.items():
        st, coh, zr, zi = _structure_tensor(ch, foot)
        s90 = float(np.nanpercentile(st[foot], 90)) or 1.0
        w = np.clip(st / s90, 0.0, 1.0) * coh
        sre += w * zr
        sim += w * zi
        wsum += w
        count += (w > 0.5).astype(np.float32)
    congr = np.sqrt(sre ** 2 + sim ** 2) / (wsum + 1e-9)
    congr[~foot] = np.nan
    add("phase_congruence", congr)
    add("congruent_channel_count", count.astype(np.float32))
    add("joint_edge_strength", wsum.astype(np.float32))

    # ---- external structural / nuisance proximity ----
    with rasterio.open(RAW / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sg = ds.read(1) > 0
    add("dist_sgmc_fault", ndi.distance_transform_edt(~sg).astype(np.float32))
    with rasterio.open(RAW / "external/tiger_road_distance_m.tif") as ds:
        rd = _clean(ds.read(1))
    add("dist_tiger_road_m", rd)
    for fn, nm in (("gdr_wellspring_in_footprint.csv", "dist_wellspring"),
                   ("gdr_volcanic_vents_in_footprint.csv", "dist_vent")):
        import csv
        pts = np.zeros(foot.shape, bool)
        with (RAW / "external" / fn).open() as fh:
            for r in csv.DictReader(fh):
                try:
                    rr, cc = int(float(r["row"])), int(float(r["col"]))
                except Exception:
                    continue
                if 0 <= rr < foot.shape[0] and 0 <= cc < foot.shape[1]:
                    pts[rr, cc] = True
        add(nm, ndi.distance_transform_edt(~pts).astype(np.float32))

    X = np.stack(arrays, axis=0)
    assert X.shape[0] == len(names) and X.shape[1] == n
    np.save(out_dir / "hce_X.npy", X)
    np.save(out_dir / "hce_fidx.npy", fidx)
    np.save(out_dir / "hce_foot.npy", np.packbits(foot.ravel()))
    meta = dict(names=names, shape=list(foot.shape), n_footprint=int(n),
                n_fields=len(names), qedges=QEDGES.tolist(),
                source="hash-pinned owner mirror (registry/data_manifest.json); NOT organizer-authenticated",
                novel_fields=["phase_congruence", "congruent_channel_count", "joint_edge_strength"],
                channels=list(channels))
    (out_dir / "hce_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"[hce/fields] {len(names)} fields x {n:,} footprint cells -> {out_dir/'hce_X.npy'} ({X.nbytes/1e6:.0f} MB)")
    return meta


def load():
    meta = json.loads((WORK / "hce_meta.json").read_text())
    X = np.load(WORK / "hce_X.npy", mmap_mode="r")
    fidx = np.load(WORK / "hce_fidx.npy")
    foot = np.unpackbits(np.load(WORK / "hce_foot.npy"))[:meta["shape"][0] * meta["shape"][1]].reshape(meta["shape"]).astype(bool)
    return meta, X, fidx, foot


def dynamic_geometry(visible: np.ndarray, foot: np.ndarray, fidx: np.ndarray) -> dict[str, np.ndarray]:
    """Fold-legal catalogue geometry: only the VISIBLE traces are used."""
    d_vis = ndi.distance_transform_edt(~visible).astype(np.float32)
    # endpoints = visible pixels with <=1 eight-neighbour
    nb = ndi.convolve(visible.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - visible
    tips = visible & (nb <= 1)
    d_tip = ndi.distance_transform_edt(~tips).astype(np.float32) if tips.any() else np.full(foot.shape, 999.0, np.float32)
    out = {}
    for nm, f in (("dyn_d_visible", d_vis), ("dyn_d_tips", d_tip)):
        v = f.ravel()[fidx]
        edges = np.quantile(v, QEDGES)
        out[nm] = (1 + np.searchsorted(edges, v, side="right")).astype(np.uint8)
    return out


if __name__ == "__main__":
    build()
