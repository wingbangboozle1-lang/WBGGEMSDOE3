"""CSPES lane: Cross-Scale Potential-field Edge Stability (preregistered 2026-10-27).

Label-independent fault-probability surface built only from the hash-pinned 19-band
public mirror. No catalogue-derived feature is used anywhere in this module, so the
construction cannot leak hidden fault segments; the shared hide-and-recover evaluator
still masks visible faults pixel-exactly.

Frozen specification (knowledge/preregistration-2026-10-27.md):
  bands   : iso_grav_anom (13), rtp (2), det_elev (12)
  scales  : gradient magnitude at sigma=2,5 px (elevation also 1.5,3,6)
  ranks   : empirical-CDF rank within the finite footprint -> uniform [0,1] marginals
  persist : P_x = min(rank G_x(2), rank G_x(5)) for x in gravity and RTP magnetics
  align   : A = (1 + cos(theta_g - theta_m)) / 2, polarity-invariant collinearity
  topo    : T = rank G_elev(2); conditioning factor (1 - 0.5 T)
  surface : S = P_g * P_m * (0.5 + 0.5 A) * (1 - 0.5 T)
  place   : greedy top-K, min Euclidean distance 2 px NMS, catalogue pixels excluded
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

from .grid import EXPECTED_SHAPE

# Band indices are 1-based rasterio band numbers, verified against the GeoTIFF's own
# descriptions this session (training_features.tif, 19 float32 bands, EPSG:32611).
BAND_RTP = 2
BAND_DET_ELEV = 12
BAND_ISO_GRAV = 13
SCALES_POTFIELD = (2.0, 5.0)
SCALES_ELEV = (1.5, 3.0, 6.0)
TOPO_PENALTY = 0.5          # frozen in the preregistration
NMS_RADIUS_PX = 2.0
DEFAULT_BUDGET = 37_654     # matches the B2 / D2.8 incumbent family for paired comparison


def _fill(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """NaN -> in-footprint median so Gaussian filters never see the sentinel."""
    out = a.copy()
    med = float(np.nanmedian(a[foot]))
    out[~np.isfinite(out)] = med
    return out


def _footprint_rank(values: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Empirical-CDF rank of finite footprint values mapped to uniform (0,1]."""
    out = np.zeros(values.shape, dtype=np.float32)
    v = values[foot]
    finite = np.isfinite(v)
    if finite.sum() < 100:
        return out
    r = rankdata(v[finite], method="average") / float(finite.sum())
    tmp = np.zeros(int(foot.sum()), dtype=np.float32)
    tmp[finite] = r.astype(np.float32)
    out[foot] = tmp
    return out


def grad_magnitude(field: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian gradient magnitude at scale sigma (pixels)."""
    gy = ndi.gaussian_filter(field, sigma=sigma, order=[1, 0], mode="nearest")
    gx = ndi.gaussian_filter(field, sigma=sigma, order=[0, 1], mode="nearest")
    return np.hypot(gy, gx).astype(np.float32)


def grad_orientation(field: np.ndarray, sigma: float) -> np.ndarray:
    """Gradient orientation theta = atan2(gy, gx), radians on [-pi, pi]."""
    gy = ndi.gaussian_filter(field, sigma=sigma, order=[1, 0], mode="nearest")
    gx = ndi.gaussian_filter(field, sigma=sigma, order=[0, 1], mode="nearest")
    return np.arctan2(gy, gx).astype(np.float32)


@dataclass
class CSPESFields:
    surface: np.ndarray          # full-grid float32, 0 outside the footprint
    components: dict[str, np.ndarray]


def build_surface(bands: dict[str, np.ndarray], foot: np.ndarray) -> CSPESFields:
    """Construct the frozen CSPES surface from cleaned raw bands {rtp, grav, elev}."""
    grav = _fill(bands["grav"], foot)
    mag = _fill(bands["rtp"], foot)
    elev = _fill(bands["elev"], foot)

    gg = {s: grad_magnitude(grav, s) for s in SCALES_POTFIELD}
    gm = {s: grad_magnitude(mag, s) for s in SCALES_POTFIELD}
    ge2 = grad_magnitude(elev, SCALES_ELEV[0])

    rg = {s: _footprint_rank(gg[s], foot) for s in SCALES_POTFIELD}
    rm = {s: _footprint_rank(gm[s], foot) for s in SCALES_POTFIELD}
    p_g = np.minimum(rg[2.0], rg[5.0])
    p_m = np.minimum(rm[2.0], rm[5.0])

    theta_g = grad_orientation(grav, SCALES_POTFIELD[0])
    theta_m = grad_orientation(mag, SCALES_POTFIELD[0])
    align = ((1.0 + np.cos(theta_g - theta_m)) / 2.0).astype(np.float32)

    topo = _footprint_rank(ge2, foot)
    surface = p_g * p_m * (0.5 + 0.5 * align) * (1.0 - TOPO_PENALTY * topo)
    surface[~foot] = 0.0

    # Ablation surfaces share the exact same components and placement rule; they are
    # diagnostics of the frozen specification, not re-fitted estimators.
    comp = {
        "P_grav_persist": p_g,
        "P_mag_persist": p_m,
        "align": align,
        "topo_rank": topo,
        "rank_Ggrav_s2": rg[2.0],
        "rank_Ggrav_s5": rg[5.0],
        "rank_Gmag_s2": rm[2.0],
        "rank_Gmag_s5": rm[5.0],
        "rank_Gelev_s1.5": topo,
    }
    ablations = {
        "cspes_full": surface,
        "abl_grav_only": p_g * (1.0 - TOPO_PENALTY * topo),
        "abl_mag_only": p_m * (1.0 - TOPO_PENALTY * topo),
        "abl_no_topo_conditioning": p_g * p_m * (0.5 + 0.5 * align),
    }
    for k, v in ablations.items():
        vv = v.copy()
        vv[~foot] = 0.0
        comp[k] = vv.astype(np.float32)
    return CSPESFields(surface=surface.astype(np.float32), components=comp)


def _disc_offsets(radius: float) -> list[tuple[int, int]]:
    return [(dy, dx) for dy in range(-radius, radius + 1)
            for dx in range(-radius, radius + 1) if dy * dy + dx * dx <= radius * radius]


def place_dots(surface: np.ndarray, foot: np.ndarray, catalogue: np.ndarray,
               budget: int = DEFAULT_BUDGET, radius: float = NMS_RADIUS_PX,
               candidate_pool: int = 400_000) -> np.ndarray:
    """Greedy top-K placement with min-distance NMS; catalogue pixels never selected.

    Only the top `candidate_pool` surface cells are considered. The pool is enlarged
    automatically if NMS exhausts it before K dots are placed.
    """
    eligible = foot & ~catalogue & np.isfinite(surface) & (surface > 0)
    while True:
        idx = np.argpartition(surface[eligible],
                              eligible.sum() - min(candidate_pool, eligible.sum()))
        cand_flat = np.flatnonzero(eligible)[idx[-min(candidate_pool, eligible.sum()):]]
        order = cand_flat[np.argsort(-surface.ravel()[cand_flat], kind="stable")]
        H, W = surface.shape
        blocked = np.zeros(surface.shape, dtype=bool)
        offsets = _disc_offsets(int(radius))
        dots = np.zeros(surface.shape, dtype=bool)
        n = 0
        for flat in order:
            r, c = divmod(int(flat), W)
            if blocked[r, c]:
                continue
            dots[r, c] = True
            n += 1
            for dy, dx in offsets:
                rr, cc = r + dy, c + dx
                if 0 <= rr < H and 0 <= cc < W:
                    blocked[rr, cc] = True
            if n >= budget:
                return dots
        if candidate_pool >= eligible.sum():
            return dots  # fewer eligible, mutually separated cells than requested
        candidate_pool = min(candidate_pool * 2, eligible.sum())


def read_cspes_bands(path: Path) -> dict[str, np.ndarray]:
    """Read the three CSPES bands and apply the shared sentinel/NaN cleaning."""
    import rasterio
    from .grid import clean_feature
    with rasterio.open(path) as ds:
        assert ds.shape == EXPECTED_SHAPE, ds.shape
        out = {
            "rtp": clean_feature(ds.read(BAND_RTP)),
            "elev": clean_feature(ds.read(BAND_DET_ELEV)),
            "grav": clean_feature(ds.read(BAND_ISO_GRAV)),
        }
    return out
