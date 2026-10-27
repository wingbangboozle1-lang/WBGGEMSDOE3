"""SGCE lane — stress-gated continuation + DTI-optimal coverage (session 2026-10-27).

Preregistered in knowledge/preregistration-2026-10-27.md (hypothesis H1).  All catalogue-derived
inputs are computed from the `visible` mask passed in; a holdout cell passes cell.visible_full,
the real build passes the full public catalogue.  No previous submission raster enters rho.

Static fields come only from the hash-pinned competition feature stack and the mirrored official
external layers (scripts/session2_build_bins.py).  The dot placement reuses src/gemsw/alloc.py,
which implements the exact alpha=0.2, beta=0.8, R=3 px DTI marginal gain.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from . import alloc as A

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data" / "work"
FIELDS = [
    "geod_dilaterate", "geod_2ndinv", "geod_shearrate", "det_elev", "det_elev_slope", "tc",
    "tmi_hg", "iso_grav_anom_slope", "cond_surf", "depth_to_base_surf", "ieq_n100a15",
    "lidar_upface_max", "lidar_downface_max", "rad_K", "rad_Th", "rad_U", "dist_sgmc_fault",
    "gradmag_det_elev_s6", "log_det_elev_s3", "crossgrad_rank_grav_mag_s3",
]
NBINS = 10
MASS = 13_000.0          # modelling scale, NOT a claim about the hidden label count
SIGMA_DEFAULT = 15.0     # 1.5 km geometric decay from visible faults (E1)
CORRIDOR_PX = 25         # along-strike extrapolation length
CORRIDOR_W = 2           # corridor half-width (pixels)
RELAY_MAX_PX = 25        # endpoint pairing distance
B_PX = 2.01              # B2 annulus: remove dots within 2 px of visible faults (masked/near-masked zone)


def rank_bins(field: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Full-grid uint8 quantile codes 1..9; 0 means missing/outside footprint. Edges are label-free."""
    a = np.asarray(field, np.float32)
    v = a[foot]
    ok = np.isfinite(v)
    if ok.sum() < 1000:
        return np.zeros(a.shape, np.uint8)
    edges = np.quantile(v[ok], [0.02, 0.05, 0.10, 0.25, 0.75, 0.90, 0.95, 0.98])
    out = np.zeros(a.shape, np.uint8)
    good = np.isfinite(a)
    out[good] = (1 + np.searchsorted(edges, a[good], side="right")).astype(np.uint8)
    out[~foot] = 0
    return np.minimum(out, NBINS - 1)


def build_bins(g, path: Path | None = None) -> Path:
    """Compute the 20 preregistered static fields once and store them as one uint8 memmap."""
    from .features import iter_fields
    path = path or (WORK / "sgce_bins.dat")
    path.parent.mkdir(parents=True, exist_ok=True)
    wanted = set(FIELDS)
    store = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8,
                                     shape=(len(FIELDS), *g.foot.shape))
    got = set()
    for name, family, field in iter_fields(g):
        if name not in wanted:
            continue
        store[FIELDS.index(name)] = rank_bins(field, g.foot)
        got.add(name)
        print(f"[sgce] bin {name:32s} ({family})", flush=True)
        del field
    store.flush()
    missing = wanted - got
    if missing:
        raise RuntimeError(f"missing preregistered fields: {sorted(missing)}")
    print(f"[sgce] wrote {path} with {len(FIELDS)} fields", flush=True)
    return path


def load_bins(g, path: Path | None = None) -> np.ndarray:
    path = path or (WORK / "sgce_bins.dat")
    return np.load(path, mmap_mode="r")


def _components(vis: np.ndarray):
    lab, n = ndi.label(vis, structure=np.ones((3, 3), int))
    return lab, n


def _rasterise_segments(segments, shape) -> np.ndarray:
    """Vectorised: stamp every segment into ONE mask, then dilate once (no per-segment Python loop)."""
    H, W = shape
    ys, xs = [], []
    for (y0, x0, y1, x1) in segments:
        n = int(max(abs(y1 - y0), abs(x1 - x0))) + 1
        t = np.linspace(0.0, 1.0, n)
        ys.append(np.rint(y0 + (y1 - y0) * t).astype(np.int32))
        xs.append(np.rint(x0 + (x1 - x0) * t).astype(np.int32))
    if not ys:
        return np.zeros((H, W), bool)
    yy, xx = np.concatenate(ys), np.concatenate(xs)
    ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
    line = np.zeros((H, W), bool)
    line[yy[ok], xx[ok]] = True
    disk = (np.add.outer(np.arange(-CORRIDOR_W, CORRIDOR_W + 1) ** 2,
                         np.arange(-CORRIDOR_W, CORRIDOR_W + 1) ** 2) <= CORRIDOR_W ** 2 + 0.25)
    return ndi.binary_dilation(line, structure=disk)


def geometry(vis: np.ndarray, foot: np.ndarray, sigma: float = SIGMA_DEFAULT) -> dict:
    """Fold-local visible-catalogue geometry: annulus + along-strike continuation + relays."""
    H, W = vis.shape
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    lab, n = _components(vis)
    slices = ndi.find_objects(lab)
    endpoints: list[tuple[float, float, float]] = []  # (row, col, strike angle)
    corridor_segments: list[tuple[float, float, float, float]] = []
    for cid in range(1, n + 1):
        sl = slices[cid - 1]
        if sl is None:
            continue
        sy, sx = np.nonzero(lab[sl] == cid)
        if sy.size < 8:
            continue
        ys, xs = sy + sl[0].start, sx + sl[1].start
        pts = np.column_stack([ys, xs]).astype(np.float64)
        c = pts.mean(axis=0)
        cov = np.cov((pts - c).T)
        vals, vecs = np.linalg.eigh(cov)
        axis = vecs[:, -1]
        proj = (pts - c) @ axis
        lo, hi = pts[np.argmin(proj)], pts[np.argmax(proj)]
        ang = float(np.arctan2(axis[1], axis[0]))
        endpoints.append((float(lo[0]), float(lo[1]), ang))
        endpoints.append((float(hi[0]), float(hi[1]), ang))
        corridor_segments.append((lo[0] - CORRIDOR_PX * axis[0], lo[1] - CORRIDOR_PX * axis[1],
                                  lo[0], lo[1]))
        corridor_segments.append((hi[0], hi[1], hi[0] + CORRIDOR_PX * axis[0],
                                  hi[1] + CORRIDOR_PX * axis[1]))
    relay_segments: list[tuple[float, float, float, float]] = []
    if len(endpoints) > 1:
        coords = np.array([[e[0], e[1]] for e in endpoints])
        angles = np.array([e[2] for e in endpoints])
        pairs = cKDTree(coords).query_pairs(RELAY_MAX_PX, output_type="ndarray")
        if pairs.size:
            da = np.abs(np.abs(angles[pairs[:, 0]] - angles[pairs[:, 1]]) % np.pi)
            da = np.minimum(da, np.pi - da)
            keep = (da < np.deg2rad(35)) & (pairs[:, 0] // 2 != pairs[:, 1] // 2)
            for i, j in pairs[keep][:5000]:
                relay_segments.append((coords[i, 0], coords[i, 1], coords[j, 0], coords[j, 1]))
    corridor = _rasterise_segments(corridor_segments, (H, W))
    relay = _rasterise_segments(relay_segments, (H, W))
    geom = np.exp(-d_vis / float(sigma)).astype(np.float32)
    geom *= (1.0 + 1.5 * corridor + 0.8 * relay)
    geom[~foot | vis] = 0.0
    return dict(d_vis=d_vis, geom=geom, corridor=corridor, relay=relay,
                n_components=int(n), n_endpoints=len(endpoints),
                corridor_px=int(corridor.sum()), relay_px=int(relay.sum()))


def density(bins: np.ndarray, vis: np.ndarray, foot: np.ndarray, geo: dict,
            shrink: float = 0.5, clip: float = 1.5) -> tuple[np.ndarray, dict]:
    """rho = NB susceptibility (visible-only) x geometric continuation x strain gate, normalised to MASS."""
    active = foot & ~vis
    logodds = np.zeros(int(foot.sum()), np.float32)
    per_field = {}
    for k, name in enumerate(FIELDS):
        code = np.asarray(bins[k]).reshape(-1)
        pc = np.bincount(code[np.flatnonzero(vis.ravel())], minlength=NBINS)[:NBINS].astype(float) + 1.0
        nc = np.bincount(code[np.flatnonzero(active.ravel())], minlength=NBINS)[:NBINS].astype(float) + 1.0
        l = np.log((pc / pc.sum()) / (nc / nc.sum()))
        l[0] = 0.0
        per_field[name] = [round(float(x), 4) for x in l]
        logodds += l[code[foot.ravel()]].astype(np.float32)
    m = np.exp(np.clip(shrink * logodds, -clip, clip))
    strain_bin = np.asarray(bins[FIELDS.index("geod_2ndinv")]).astype(np.float32)
    gate = 0.4 + 0.6 * (strain_bin / (NBINS - 1))
    rho = np.zeros(foot.shape, np.float32)
    rho[foot] = m * geo["geom"][foot] * gate[foot]
    rho[vis | ~foot] = 0.0
    total = float(rho.sum())
    if total <= 0:
        raise RuntimeError("zero density")
    rho *= np.float32(MASS / total)
    return rho, dict(mass_before=total, mass_after=MASS, min=float(rho[foot].min()),
                     max=float(rho.max()), mean_active=float(rho[active].mean()),
                     nb_logodds=per_field)


def place(rho: np.ndarray, vis: np.ndarray, foot: np.ndarray, geo: dict,
          n_cap: int = 45_000, mu: float = 0.28, max_rounds: int = 12, iters: int = 3,
          avoid: np.ndarray | None = None, region: tuple[slice, slice] | None = None) -> dict:
    """Binary dots by the shared Dinkelbach/NMS allocator on the exact DTI kernel.

    Dinkelbach fixed point: mu <- model DTI of the selected set; a lower achieved DTI lowers the
    marginal inclusion bar, which is what allows a competitive dot count instead of an arbitrary
    hand-tuned threshold.  No hidden label is used: rho is the modelled density.
    """
    sl = region or (slice(None), slice(None))
    cand = (foot & ~vis & (geo["d_vis"] > B_PX))[sl]
    if avoid is not None:
        cand &= ~avoid[sl]
    best = None
    trace = []
    for it in range(iters):
        r = A.allocate(rho[sl], cand, mu=mu, n_max=n_cap, min_gain=0.0, max_rounds=max_rounds)
        dots = np.zeros(foot.shape, bool)
        dots[sl] = r["dots"]
        exp = A.expected_dti(rho, dots)
        best = dict(dots=dots, n=int(dots.sum()), expected=exp, mu=mu, n_cap=n_cap,
                    rounds=max_rounds, trace=trace)
        trace.append(dict(iter=it, mu=mu, n=int(dots.sum()), model_dti=exp["dti"]))
        if abs(exp["dti"] - mu) < 5e-4:
            break
        mu = float(exp["dti"])
    return best
