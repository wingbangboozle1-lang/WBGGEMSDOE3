"""Catalogue-independent structural feature planes.

Every plane here is computed from the official 19-band GeoDAWN feature stack
(``training_features.tif``) and from nothing else. **No plane uses the fault
catalogue**, so the supervised model cannot learn "predict near a known fault"
and the holdout cannot be gamed by catalogue proximity.

Physics being targeted (short form; the full table is written to
``evidence/release/feature_registry.json``):

``topo_ridge`` / ``topo_valley``
    Range-front ridge and trough axes of the detrended DEM. Fault scarps produce
    a crest/trough pair; the oriented filter responds to *linear* continuity,
    which suppresses isolated hills and pits.
``topo_curv``
    |Laplacian| of the detrended DEM: sharp breaks in slope (scarp faces).
``topo_relief``
    Context: local relief (can a scarp exist here at all).
``mag_hg_line`` / ``mag_vg_line`` / ``mag_low_line``
    Aeromagnetic lineaments. Fault zones in the Great Basin are imaged as
    linear gradients (contacts) and, where hydrothermal fluids have destroyed
    magnetite, as linear *lows* (``mag_low_line`` = oriented filter on the
    negative band-pass of RTP magnetics).
``grav_hg_line`` / ``grav_bp_line``
    Isostatic-gravity gradients and basin-scale band-pass: basin-bounding fault
    geometry beneath cover, where no surface scarp exists.
``strain_line`` / ``seis_line``
    Geodetic strain-magnitude and earthquake-density lineaments: active
    structure, independent of topography.
``cond_line`` / ``depth_bp_line``
    Conductivity-surface gradient and depth-to-basement band-pass: fluid
    pathways and basin thickness.

``concord``
    The multi-physics concordance plane. For four *independent* data categories
    (topography, magnetics, gravity, strain+seismicity) it computes the oriented
    line response at four strikes and asks where the same strike is a lineament
    in **several independent physics simultaneously**. A single-physics mimic
    (a road or a stream in the DEM, a cultural artefact in magnetics, a
    geothermal pipe in gravity) cannot satisfy that agreement.

Filters are evaluated with circular shifts (``np.roll``); the outer
``BORDER``-pixel frame is therefore invalid and is set to NaN. That frame is a
tiny fraction of the scored footprint and is excluded from every result.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, laplace

BORDER = 34          # invalid frame (px) from circular shifts and Gaussian support
LINE_HALF = 4        # along-strike half-length: 9 px = 900 m
LINE_GAP = 3         # perpendicular sample offset: 300 m, the official kernel scale
ORIENTATIONS_6 = (0.0, 30.0, 60.0, 90.0, 120.0, 150.0)
ORIENTATIONS_4 = (0.0, 45.0, 90.0, 135.0)


def _unit(theta_deg: float) -> tuple[int, int] | None:
    """Integer (dy, dx) direction for a strike in degrees, or None if non-lattice.

    Strikes are measured clockwise from north (dy = -sin, dx = +cos). Only
    directions representable on the pixel lattice are used, so the filter has no
    interpolation bias.
    """
    import math

    t = math.radians(theta_deg)
    dy, dx = -math.sin(t), math.cos(t)
    # snap to the nearest lattice direction with |dy|,|dx| <= 3
    best = None
    for ay in (-3, -2, -1, 0, 1, 2, 3):
        for ax in (-3, -2, -1, 0, 1, 2, 3):
            if (ay, ax) == (0, 0):
                continue
            ny, nx = ay / math.hypot(ay, ax), ax / math.hypot(ay, ax)
            dot = ny * dy + nx * dx
            if best is None or dot > best[0]:
                best = (dot, (ay, ax))
    return best[1] if best and best[0] > 0.985 else None


def _perpendicular(direction: tuple[int, int]) -> tuple[int, int]:
    dy, dx = direction
    return (-dx, dy)


def line_response(base: np.ndarray, orientations=ORIENTATIONS_6,
                  half: int = LINE_HALF, gap: int = LINE_GAP) -> np.ndarray:
    """Oriented linear feature response: mean along strike minus mean across it.

    Positive on ridges/highs, negative on troughs/lows. All rotations are
    integer pixel shifts, so the operator is exactly equivariant on the lattice.
    """
    best = np.full(base.shape, -np.inf, np.float32)
    used = 0
    for theta in orientations:
        d = _unit(theta)
        if d is None:
            continue
        used += 1
        dy, dx = d
        along = np.zeros(base.shape, np.float32)
        for t in range(-half, half + 1):
            along += np.roll(base, (t * dy, t * dx), axis=(0, 1))
        along /= (2 * half + 1)
        py, px = _perpendicular(d)
        across = 0.5 * (np.roll(base, (gap * py, gap * px), axis=(0, 1))
                        + np.roll(base, (-gap * py, -gap * px), axis=(0, 1)))
        np.maximum(best, along - across, out=best)
    if used == 0:
        raise ValueError("no lattice-representable orientations")
    return best


def directional_responses(base: np.ndarray, orientations=ORIENTATIONS_4,
                          half: int = LINE_HALF, gap: int = LINE_GAP) -> dict:
    """Signed line response for each lattice direction (used by ``concordance``)."""
    out = {}
    for theta in orientations:
        d = _unit(theta)
        if d is None:
            continue
        dy, dx = d
        along = np.zeros(base.shape, np.float32)
        for t in range(-half, half + 1):
            along += np.roll(base, (t * dy, t * dx), axis=(0, 1))
        along /= (2 * half + 1)
        py, px = _perpendicular(d)
        across = 0.5 * (np.roll(base, (gap * py, gap * px), axis=(0, 1))
                        + np.roll(base, (-gap * py, -gap * px), axis=(0, 1)))
        out[(dy, dx)] = along - across
    return out


def bandpass(a: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return gaussian_filter(a, lo, mode="nearest") - gaussian_filter(a, hi, mode="nearest")


def sanitise(a: np.ndarray, invalid: np.ndarray) -> np.ndarray:
    a = np.array(a, dtype=np.float32, copy=True)
    a[invalid] = np.nan
    a[:BORDER, :] = np.nan
    a[-BORDER:, :] = np.nan
    a[:, :BORDER] = np.nan
    a[:, -BORDER:] = np.nan
    return a


# --------------------------------------------------------------------------- #
# Plane definitions. Each entry: name, source bands, category, the callable,
# and the non-fault process that could mimic it (required by the run-card
# protocol). The callable receives the band reader.
# --------------------------------------------------------------------------- #
def _topo_ridge(get):
    return line_response(get("det_elev"))


def _topo_valley(get):
    return line_response(-get("det_elev"))


def _topo_curv(get):
    return np.abs(laplace(gaussian_filter(get("det_elev"), 2.0, mode="nearest")))


def _topo_relief(get):
    return bandpass(get("det_elev"), 10.0, 40.0)


def _mag_hg_line(get):
    return line_response(get("tmi_hg"))


def _mag_vg_line(get):
    return line_response(np.abs(get("tmi_vg")))


def _mag_low_line(get):
    return line_response(-bandpass(get("rtp"), 2.0, 12.0))


def _grav_hg_line(get):
    return line_response(get("iso_grav_anom_hg"))


def _grav_bp_line(get):
    return line_response(bandpass(get("iso_grav_anom"), 2.0, 14.0))


def _strain_line(get):
    strain = np.log1p(np.abs(get("geod_dilaterate"))) + np.log1p(get("geod_2ndinv"))
    return line_response(gaussian_filter(strain, 1.5, mode="nearest"))


def _seis_line(get):
    return line_response(np.log1p(np.abs(get("ieq_n100a15"))))


def _cond_line(get):
    cond = gaussian_filter(get("cond_surf"), 1.5, mode="nearest")
    gy, gx = np.gradient(cond)
    return line_response(np.hypot(gy, gx))


def _depth_bp_line(get):
    return line_response(bandpass(get("depth_to_base_surf"), 2.0, 14.0))


PLANES = {
    "topo_ridge": dict(bands=["det_elev"], category="topographic", fn=_topo_ridge,
                       target="range-front crest axes",
                       mimic="stream terraces and eolian ridges produce the same crest axis"),
    "topo_valley": dict(bands=["det_elev"], category="topographic", fn=_topo_valley,
                        target="trough axes along hanging-wall margins",
                        mimic="drainages incised along non-tectonic gradients"),
    "topo_curv": dict(bands=["det_elev"], category="topographic", fn=_topo_curv,
                      target="scarp-face curvature",
                      mimic="landslide headscarps, wave-cut benches, playa margins"),
    "topo_relief": dict(bands=["det_elev"], category="topographic", fn=_topo_relief,
                        target="local relief context",
                        mimic="volcanic centres and buttresses"),
    "mag_hg_line": dict(bands=["tmi_hg"], category="magnetic", fn=_mag_hg_line,
                        target="contact/edge lineaments",
                        mimic="cultural noise, survey flight-line striping"),
    "mag_vg_line": dict(bands=["tmi_vg"], category="magnetic", fn=_mag_vg_line,
                        target="vertical-gradient lineaments",
                        mimic="terrain effect on draped surveys"),
    "mag_low_line": dict(bands=["rtp"], category="magnetic", fn=_mag_low_line,
                         target="linear magnetic lows (magnetite destruction by hydrothermal fluid)",
                         mimic="sedimentary basins and non-magnetic intrusive bodies"),
    "grav_hg_line": dict(bands=["iso_grav_anom_hg"], category="gravity", fn=_grav_hg_line,
                         target="basement fabric and basin-bounding steps",
                         mimic="density contrasts from lithology alone"),
    "grav_bp_line": dict(bands=["iso_grav_anom"], category="gravity", fn=_grav_bp_line,
                         target="basin-scale structural steps",
                         mimic="isostatic compensation of topography"),
    "strain_line": dict(bands=["geod_dilaterate", "geod_2ndinv"], category="strain",
                        fn=_strain_line, target="strain-magnitude lineaments",
                        mimic="interseismic loading unrelated to near-surface faults"),
    "seis_line": dict(bands=["ieq_n100a15"], category="seismic", fn=_seis_line,
                      target="seismicity lineaments",
                      mimic="quarry blasts and induced seismicity from fluid operations"),
    "cond_line": dict(bands=["cond_surf"], category="subsurface", fn=_cond_line,
                      target="conductivity-gradient corridors (fluid pathways)",
                      mimic="clay/saline playa conductivity unrelated to structure"),
    "depth_bp_line": dict(bands=["depth_to_base_surf"], category="subsurface",
                          fn=_depth_bp_line, target="basement-thickness band-pass",
                          mimic="depocentre geometry without fault control"),
}

#: Fusion plane built from four independent categories.
CONCORD_CATEGORIES = {
    "topographic": lambda get: get("det_elev"),
    "magnetic": lambda get: get("tmi_hg"),
    "gravity": lambda get: get("iso_grav_anom_hg"),
    "strain": lambda get: (np.log1p(np.abs(get("geod_dilaterate")))
                           + np.log1p(get("geod_2ndinv"))),
}


def concordance_plane(get, orientations=ORIENTATIONS_4) -> np.ndarray:
    """Where several independent physics agree on the *same* strike direction.

    For each category and strike we take the standardised signed line response,
    then keep, per strike, the mean over categories; the plane is the maximum
    over strikes. A structure that is a lineament at the same azimuth in
    topography, magnetics and gravity scores high; a single-physics mimic does
    not, because its evidence is diluted by the categories that see nothing.
    """
    accum: dict = {}
    for name, reader in CONCORD_CATEGORIES.items():
        base = reader(get).astype(np.float32)
        resp = directional_responses(base, orientations)
        for direction, values in resp.items():
            # A category that prefers a different strike contributes 0 here, so
            # disagreement necessarily lowers the plane: that is the mechanism.
            accum[direction] = accum.get(direction, 0.0) + robust_z(values)
    n = len(CONCORD_CATEGORIES)
    per_strike = [accum[d] / n for d in accum]
    return np.max(np.stack(per_strike, axis=0), axis=0).astype(np.float32)


def robust_z(a: np.ndarray, step: int = 5) -> np.ndarray:
    """Median/IQR scaling from a strided subsample; NaN stays NaN."""
    sub = a[::step, ::step]
    ok = np.isfinite(sub)
    if not ok.any():
        return np.zeros_like(a, dtype=np.float32)
    med = float(np.median(sub[ok]))
    q75, q25 = np.percentile(sub[ok], [75, 25])
    iqr = float(q75 - q25)
    scale = iqr / 1.349 if iqr > 0 else float(np.std(sub[ok])) or 1.0
    return ((a - med) / scale).astype(np.float32)


def build_band_reader():
    """Reader that memoises at most two bands at a time (3 GB RAM sandbox)."""
    from . import shared

    cache: dict = {}
    order: list = []

    def get(name: str) -> np.ndarray:
        if name not in cache:
            if len(order) >= 2:
                cache.pop(order.pop(0), None)
            cache[name] = shared.band_plane(shared.BAND_INDEX[name])
            order.append(name)
        return cache[name]

    return get
