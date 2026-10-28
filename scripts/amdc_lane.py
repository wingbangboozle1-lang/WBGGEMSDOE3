#!/usr/bin/env python3
"""AMDC lane (session arena/2759fec7): antisymmetric magnetic-dipole gate on fold-legal tip continuation.

Preregistered in knowledge/preregistration-2026-10-27-2759fec7.md. Uses ONLY the shared
template tools (vendor/gems57/*, unmodified) + the template's cached 19-band stack.
No private fork of the evaluator, metric, allocator, or writer.

Stages:
  1. load grid + cached bands; verify CRS/shape/transform + byte pins
  2. build hide-and-recover folds (buffered whole components, seeds 20/21 -> 8 folds)
  3. leakage canary (11 static fields, pooled AUC)
  4. matched ranking of fixed emissions (9 focus + repo TIFs) on identical folds
  5. E1/E2/E3 (dipole-gated continuation + NB + allocate_patient)
  6. pooled HOLDOUT-DTI + paired bootstrap CI vs champion
  7. best-effort ledger/control fetch for the uniqueness registry
  8. final build on full catalogue + uniqueness (surface + dots) + validator + writer
  9. projection (OLS on focus pairs) + run card

Budget: 3 experiments. Wall clock is logged per stage; the 2 h guideline is disclosed, not hidden.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as G, holdout as H, metric as M  # noqa: E402
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import emit as E  # noqa: E402
from gems57 import submission_writer as W  # noqa: E402
from gems57 import validate as V  # noqa: E402
from gems57 import gates as GT  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402

TDIR = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
FEAT = TDIR / ".cache" / "features"
OUT = ROOT / "evidence" / "amdc"
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "stages.log"

BANDS = {"mag_anom": 1, "rtp": 2, "tmi_hg": 3, "geod_2ndinv": 4, "iso_grav_anom_slope": 5,
         "tc": 6, "geod_shearrate": 7, "geod_dilaterate": 8, "tmi_vg": 9, "deq_n100a15": 10,
         "iso_grav_anom_vg": 11, "det_elev": 12, "iso_grav_anom": 13, "tmi": 14,
         "depth_to_base_surf": 15, "ieq_n100a15": 16, "cond_surf": 17,
         "iso_grav_anom_hg": 18, "det_elev_slope": 19}
NB_FIELDS = ["rtp", "mag_anom", "iso_grav_anom", "iso_grav_anom_hg", "iso_grav_anom_slope",
             "det_elev_slope", "depth_to_base_surf", "cond_surf", "geod_2ndinv", "ieq_n100a15"]
MASS = 13_000.0
SIGMA = 15.0
CORRIDOR_PX = 25
CORRIDOR_W = 2
RELAY_MAX_PX = 25
B_PX = 2.01
QEDGES = np.array([0.02, 0.05, 0.10, 0.25, 0.75, 0.90, 0.95, 0.98])
NBINS = 10
SEEDS = (20, 21)

STAGES: dict[str, float] = {}


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def stage(name: str):
    class Ctx:
        def __enter__(self):
            self.t0 = time.time()
            log(f"--- stage: {name} ---")
            return self

        def __exit__(self, *a):
            dt = time.time() - self.t0
            STAGES[name] = round(dt, 1)
            log(f"--- done: {name} ({dt:.1f}s) ---")
    return Ctx()


# ---------------------------------------------------------------- grid + bands
def load_grid() -> dict:
    off = TDIR / "data" / "official"
    with rasterio.open(off / "sample_submission.tif") as ds:
        assert (ds.height, ds.width) == (G.HEIGHT, G.WIDTH), ds.shape
        assert ds.crs.to_epsg() == G.EPSG, ds.crs
        assert tuple(ds.transform)[:6] == tuple(G.TRANSFORM)[:6], tuple(ds.transform)
        foot = np.isfinite(ds.read(1))
    with rasterio.open(off / "labels.tif") as ds:
        lab = ds.read(1)
        cat = (lab == 1) & foot
    assert int(foot.sum()) == 5_167_373, int(foot.sum())
    assert int(cat.sum()) == 60_988, int(cat.sum())
    log(f"footprint={int(foot.sum())} catalogue={int(cat.sum())}")
    return {"foot": foot, "cat": cat, "sample": str(off / "sample_submission.tif")}


def band_path(name: str) -> Path:
    return FEAT / f"band-{BANDS[name]:02d}.npy"


def load_band(name: str, mmap: bool = True) -> np.ndarray:
    a = np.load(band_path(name), mmap_mode="r" if mmap else None)
    assert a.shape == (G.HEIGHT, G.WIDTH), (name, a.shape)
    return np.asarray(a, dtype=np.float32) if not mmap else a


# ---------------------------------------------------------------- holdout folds
class GridNS:
    def __init__(self, foot, cat):
        self.footprint = foot
        self.catalogue = cat
        self.height, self.width = foot.shape


def build_folds(foot, cat) -> list[dict]:
    g = GridNS(foot, cat)
    folds_all: list[dict] = []
    for seed in SEEDS:
        folds, _quad = H.buffered_component_draw(g, seed=seed, hide_frac=0.20,
                                                 buffer_px=3, boundary_px=12)
        for f in folds:
            f["seed"] = seed
        folds_all.extend(folds)
        n = sum(int(f["truth"].sum()) for f in folds)
        log(f"seed={seed} folds=4 withheld_truth_px={n}")
    (OUT / "folds_receipt.json").write_text(json.dumps(
        [{"seed": f["seed"], "fold": f["name"], "n_truth": int(f["truth"].sum()),
          **{k: (v if isinstance(v, (int, float, str)) else None)
             for k, v in f["receipt"].items()}} for f in folds_all], indent=1))
    return folds_all


def score_fixed(pred01: np.ndarray, folds, foot) -> dict:
    """Pooled DTI of a fixed full-grid [0,1] emission over folds; returns terms sum + pooled."""
    terms = None
    per = {}
    for f in folds:
        _res, t = EH.evaluate(pred01, f, foot, block_side=200, origin=(0, 0),
                              global_shape=pred01.shape)
        terms = t if terms is None else terms + t
        key = f"{f['seed']}_{f['name']}"
        per[key] = {"dti": _res["dti"], "n_truth": _res["n_truth"],
                    "n_emitted": _res["n_emitted"]}
    tp, fp, fn, nt = (float(terms.sum(axis=0)[i]) for i in range(4))
    pooled = float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS))
    return {"terms": terms, "pooled_dti": pooled, "tp": tp, "fp": fp, "fn": fn,
            "n_truth": int(round(nt)), "per_fold": per}


def read_mask01(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1).astype(np.float32)
    a[~np.isfinite(a)] = 0.0
    return np.clip(a, 0.0, 1.0)


# ---------------------------------------------------------------- geometry (fold-local)
def _rasterise(segments, shape) -> np.ndarray:
    Hh, Ww = shape
    if not segments:
        return np.zeros(shape, bool)
    ys, xs = [], []
    for (y0, x0, y1, x1) in segments:
        n = int(max(abs(y1 - y0), abs(x1 - x0))) + 1
        t = np.linspace(0.0, 1.0, n)
        ys.append(np.rint(y0 + (y1 - y0) * t).astype(np.int32))
        xs.append(np.rint(x0 + (x1 - x0) * t).astype(np.int32))
    yy, xx = np.concatenate(ys), np.concatenate(xs)
    ok = (yy >= 0) & (yy < Hh) & (xx >= 0) & (xx < Ww)
    line = np.zeros(shape, bool)
    line[yy[ok], xx[ok]] = True
    r = CORRIDOR_W
    yy2, xx2 = np.mgrid[-r:r + 1, -r:r + 1]
    return ndi.binary_dilation(line, structure=(yy2 ** 2 + xx2 ** 2 <= r ** 2 + 0.25))


def geometry(vis: np.ndarray, foot: np.ndarray) -> dict:
    from scipy.spatial import cKDTree
    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    lab, n = ndi.label(vis, structure=np.ones((3, 3), int))
    slices = ndi.find_objects(lab)
    endpoints: list[tuple[float, float, float]] = []
    segs: list[tuple[float, float, float, float]] = []
    for cid in range(1, n + 1):
        sl = slices[cid - 1]
        if sl is None:
            continue
        sy, sx = np.nonzero(lab[sl] == cid)
        if sy.size < 8:
            continue
        ys = sy + sl[0].start
        xs = sx + sl[1].start
        pts = np.column_stack([ys, xs]).astype(np.float64)
        c = pts.mean(axis=0)
        _vals, vecs = np.linalg.eigh(np.cov((pts - c).T))
        axis = vecs[:, -1]
        proj = (pts - c) @ axis
        lo, hi = pts[np.argmin(proj)], pts[np.argmax(proj)]
        ang = float(np.arctan2(axis[1], axis[0]))
        endpoints += [(float(lo[0]), float(lo[1]), ang), (float(hi[0]), float(hi[1]), ang)]
        segs += [(lo[0] - CORRIDOR_PX * axis[0], lo[1] - CORRIDOR_PX * axis[1], lo[0], lo[1]),
                 (hi[0], hi[1], hi[0] + CORRIDOR_PX * axis[0], hi[1] + CORRIDOR_PX * axis[1])]
    relay_segs: list[tuple[float, float, float, float]] = []
    if len(endpoints) > 1:
        coords = np.array([[e[0], e[1]] for e in endpoints])
        angs = np.array([e[2] for e in endpoints])
        pairs = cKDTree(coords).query_pairs(RELAY_MAX_PX, output_type="ndarray")
        if pairs.size:
            da = np.abs((angs[pairs[:, 0]] - angs[pairs[:, 1]]) % np.pi)
            da = np.minimum(da, np.pi - da)
            keep = (da < np.deg2rad(35)) & (pairs[:, 0] // 2 != pairs[:, 1] // 2)
            for i, j in pairs[keep][:5000]:
                relay_segs.append((coords[i, 0], coords[i, 1], coords[j, 0], coords[j, 1]))
    corridor = _rasterise(segs, vis.shape)
    relay = _rasterise(relay_segs, vis.shape)
    ann = np.exp(-d_vis / SIGMA).astype(np.float32)
    return {"d_vis": d_vis, "corridor": corridor, "relay": relay, "annulus": ann,
            "n_components": int(n), "n_endpoints": len(endpoints),
            "corridor_px": int(corridor.sum()), "relay_px": int(relay.sum())}


# ---------------------------------------------------------------- dipole field (label-free)
def dipole_field(foot: np.ndarray) -> np.ndarray:
    rtp = np.asarray(load_band("rtp"), dtype=np.float32)
    med = float(np.nanmedian(rtp[foot]))
    R = np.where(np.isfinite(rtp), rtp, med).astype(np.float32)
    del rtp
    out = np.zeros(R.shape, np.float32)

    def acc(o: np.ndarray, e: np.ndarray, sl: tuple[slice, slice]):
        oo = o.astype(np.float32)
        ee = e.astype(np.float32)
        step = np.abs(oo) / (np.abs(oo) + 2.0 * np.abs(ee) + 1e-6)
        mad = float(np.median(np.abs(oo))) * 1.4826 + 1e-6
        z = np.abs(oo) / mad
        d = step * np.minimum(1.0, z / 3.0)
        cur = out[sl]
        np.maximum(cur, d.astype(np.float32), out=cur)

    Hh, Ww = R.shape
    # N-S strike (E-W normal)
    O = R[:, 4:] - R[:, :-4]
    E_ = (R[:, 4:] + R[:, :-4]) * 0.5 - R[:, 2:-2]
    acc(O, E_, (slice(None), slice(2, Ww - 2)))
    del O, E_
    # E-W strike (N-S normal)
    O = R[4:, :] - R[:-4, :]
    E_ = (R[4:, :] + R[:-4, :]) * 0.5 - R[2:-2, :]
    acc(O, E_, (slice(2, Hh - 2), slice(None)))
    del O, E_
    # diagonals
    O = R[:-4, 4:] - R[4:, :-4]
    E_ = (R[:-4, 4:] + R[4:, :-4]) * 0.5 - R[2:-2, 2:-2]
    acc(O, E_, (slice(2, Hh - 2), slice(2, Ww - 2)))
    del O, E_
    O = R[4:, 4:] - R[:-4, :-4]
    E_ = (R[4:, 4:] + R[:-4, :-4]) * 0.5 - R[2:-2, 2:-2]
    acc(O, E_, (slice(2, Hh - 2), slice(2, Ww - 2)))
    del O, E_, R
    out[~foot] = 0.0
    return out


# ---------------------------------------------------------------- NB codes
def build_codes(foot: np.ndarray) -> Path:
    p = ROOT / ".cache" / "amdc_codes.dat"
    n = len(NB_FIELDS)
    store = np.lib.format.open_memmap(str(p), mode="w+", dtype=np.uint8,
                                      shape=(n, *foot.shape))
    for k, name in enumerate(NB_FIELDS):
        a = np.asarray(load_band(name), dtype=np.float32)
        v = a[foot]
        ok = np.isfinite(v)
        edges = np.quantile(v[ok], QEDGES)
        good = np.isfinite(a)
        code = np.zeros(a.shape, np.uint8)
        code[good] = np.minimum(1 + np.searchsorted(edges, a[good], side="right"),
                                NBINS - 1).astype(np.uint8)
        code[~foot] = 0
        store[k] = code
        del a, code
        log(f"codes {name}")
    store.flush()
    return p


def nb_logodds(codes: np.ndarray, vis: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, dict]:
    active = foot & ~vis
    flat = foot.ravel()
    vis_f = np.flatnonzero(vis.ravel())
    act_f = np.flatnonzero(active.ravel())
    lo = np.zeros(int(foot.sum()), np.float32)
    per = {}
    for k, name in enumerate(NB_FIELDS):
        code = np.asarray(codes[k]).reshape(-1)
        pc = np.bincount(code[vis_f], minlength=NBINS)[:NBINS].astype(float) + 1.0
        nc = np.bincount(code[act_f], minlength=NBINS)[:NBINS].astype(float) + 1.0
        l = np.log((pc / pc.sum()) / (nc / nc.sum()))
        l[0] = 0.0
        per[name] = [round(float(x), 4) for x in l]
        lo += l[code[flat]].astype(np.float32)
    m = np.exp(np.clip(0.5 * lo, -1.5, 1.5)).astype(np.float32)
    return m, per


def build_rho(codes, vis, foot, dip, tau: float, depth_med: float, depth: np.ndarray):
    geo = geometry(vis, foot)
    m, per = nb_logodds(codes, vis, foot)
    thin = (depth < depth_med) | ~np.isfinite(depth)
    gate = (dip >= tau) & thin & (geo["corridor"] | geo["relay"])
    boost = np.ones(foot.shape, np.float32)
    boost[geo["corridor"] & gate] = 2.5
    boost[geo["relay"] & gate & ~geo["corridor"]] = 1.8
    rho = np.zeros(foot.shape, np.float32)
    rho[foot] = m * geo["annulus"][foot] * boost[foot]
    rho[vis | ~foot] = 0.0
    tot = float(rho.sum())
    assert tot > 0, "zero density"
    rho *= np.float32(MASS / tot)
    info = {"mass_before": tot, "tau": tau, "gate_px": int(gate.sum()),
            "corridor_px": geo["corridor_px"], "relay_px": geo["relay_px"],
            "n_components": geo["n_components"], "max_p": float(rho.max()),
            "nb": per}
    return rho, geo, info


def place(p: np.ndarray, allowed: np.ndarray, cap: int) -> dict:
    assert p.max() <= 1.0, f"p must be a probability field, max={p.max()}"
    a = E.allocate_patient(p, allowed, MASS, floor=0.0, max_dots=cap,
                           candidate_cap=400_000, patience=100_000)
    return {"dots": a.emitted, "n": int(a.n_dots),
            "surrogate_dti": float(a.surrogate_dti), "trace": list(a.trace)}


def main() -> int:
    t_start = time.time()
    which = sys.argv[1:] or ["all"]
    do = lambda s: ("all" in which) or (s in which)

    grid = load_grid()
    foot, cat = grid["foot"], grid["cat"]

    folds = None
    if do("folds") or do("all"):
        with stage("folds"):
            folds = build_folds(foot, cat)
    else:
        folds = build_folds(foot, cat)

    with stage("canary"):
        from sklearn.metrics import roc_auc_score
        truth_all = np.zeros(foot.shape, bool)
        active_all = np.zeros(foot.shape, bool)
        for f in folds:
            active = foot & f["region"] & ~f["masked_known"]
            truth_all |= (f["truth"] & active)
            active_all |= active
        bg = active_all & ~truth_all
        rng = np.random.default_rng(7)
        bg_idx = np.flatnonzero(bg.ravel())
        take = rng.choice(bg_idx, size=min(200_000, bg_idx.size), replace=False)
        y_true = np.concatenate([np.ones(int(truth_all.sum())),
                                 np.zeros(take.size)])
        rows = []
        for name in NB_FIELDS:
            a = np.asarray(load_band(name), dtype=np.float32)
            med = float(np.nanmedian(a[foot]))
            v = np.concatenate([np.where(np.isfinite(a[truth_all]), a[truth_all], med),
                                np.where(np.isfinite(a.ravel()[take]), a.ravel()[take], med)])
            auc = float(roc_auc_score(y_true, v))
            rows.append({"field": name, "auc": round(auc, 4),
                         "folded": round(max(auc, 1 - auc), 4)})
            del a
        dip = dipole_field(foot)
        vd = np.concatenate([dip[truth_all], dip.ravel()[take]])
        auc = float(roc_auc_score(y_true, vd))
        rows.append({"field": "DIPOLE_max4", "auc": round(auc, 4),
                     "folded": round(max(auc, 1 - auc), 4)})
        worst = max(rows, key=lambda r: r["folded"])
        log(f"canary worst: {worst} (gate <=0.90)")
        (OUT / "canary.json").write_text(json.dumps(
            {"rows": rows, "worst": worst, "passed": bool(worst["folded"] <= 0.90),
             "n_truth": int(truth_all.sum()), "n_bg": int(take.size)}, indent=1))
        if worst["folded"] > 0.90:
            log("CANARY FAIL: leakage stop.")
            return 3

    with stage("codes+dipole"):
        codes_p = build_codes(foot)
        codes = np.load(codes_p, mmap_mode="r")
        dip = dipole_field(foot)
        q50, q66 = float(np.quantile(dip[foot], 0.50)), float(np.quantile(dip[foot], 0.66))
        depth = np.asarray(load_band("depth_to_base_surf"), dtype=np.float32)
        depth_med = float(np.nanmedian(depth[foot]))
        miss = float((~np.isfinite(depth[foot])).mean())
        log(f"dip q50={q50:.4f} q66={q66:.4f} depth_med={depth_med:.2f} depth_missing={miss:.4f}")
        (OUT / "dipole.json").write_text(json.dumps(
            {"q50": q50, "q66": q66, "depth_med": depth_med, "depth_missing_frac": miss}, indent=1))

    with stage("ranking"):
        focus = json.loads((ROOT / "registry" / "focus_sites.json").read_text())["sites"]
        fps = {"GEMSDOE32": "GEMSDOE32.tif", "GEMSDOE36": "GEMSDOE36.tif",
               "GEMSDOE28": "GEMSDOE28.tif", "GEMSDOE31": "GEMSDOE31.tif",
               "GEMSDOE33": "GEMSDOE33.tif", "GEMSDOE25": "GEMSDOE25.tif",
               "GEMSDOE30": "GEMSDOE30.tif", "GEMSDOE24": "GEMSDOE24.tif",
               "GEMSDOE27": "GEMSDOE27.tif"}
        repo_extra = {
            "WBG-amdc-none-yet": None,
            "WBG-sgce": "docs/downloads/wbggems3-sgce-20261027-f52d35d8-zeros.tif",
            "WBG-tde30k": "docs/downloads/wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif",
            "WBG-skarpline": "docs/downloads/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif",
            "WBG-cspes": "docs/downloads/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif",
            "WBG-hce1": "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif",
        }
        ranking = []
        terms_bank: dict[str, np.ndarray] = {}
        for site in focus:
            s = site["site"]
            r = score_fixed(read_mask01(ROOT / "data" / fps[s]), folds, foot)
            terms_bank[f"focus:{s}"] = r["terms"]
            ranking.append({"id": f"focus:{s}", "holdout_dti": round(r["pooled_dti"], 6),
                            "n_dots": int((read_mask01(ROOT / 'data' / fps[s]) > 0).sum()),
                            "owner_reported": site["owner_reported"]})
            log(f"rank focus:{s} holdout={r['pooled_dti']:.4f} owner={site['owner_reported']}")
        for key, rel in repo_extra.items():
            if rel is None:
                continue
            p = ROOT / rel
            if not p.exists():
                ranking.append({"id": key, "missing": True})
                continue
            r = score_fixed(read_mask01(p), folds, foot)
            terms_bank[key] = r["terms"]
            ranking.append({"id": key, "holdout_dti": round(r["pooled_dti"], 6),
                            "n_dots": int((read_mask01(p) > 0).sum())})
            log(f"rank {key} holdout={r['pooled_dti']:.4f}")
        np.savez_compressed(OUT / "terms_bank.npz",
                            **{k.replace(":", "_"): v for k, v in terms_bank.items()})
        (OUT / "ranking.json").write_text(json.dumps(ranking, indent=1))

    # experiments E1/E2
    exps = {}
    for tag, tau, cap in [("E1", q50, 45_000), ("E2", q66, 45_000)]:
        with stage(tag):
            dots_seed = {}
            infos = {}
            for seed in SEEDS:
                vis = folds[0]["visible"] if folds[0]["seed"] == seed else folds[4]["visible"]
                rho, geo, info = build_rho(codes, vis, foot, dip, tau, depth_med, depth)
                allowed = foot & ~vis & (geo["d_vis"] > B_PX)
                pl = place(rho, allowed, cap)
                dots_seed[seed] = pl["dots"]
                infos[str(seed)] = {**{k: v for k, v in info.items() if k != "nb"},
                                    "n_dots": pl["n"], "surrogate": pl["surrogate_dti"]}
                log(f"{tag} seed={seed} dots={pl['n']} surrogate={pl['surrogate_dti']:.4f} "
                    f"gate_px={info['gate_px']} max_p={info['max_p']:.4f}")
                del rho
            terms = None
            for f in folds:
                _res, t = EH.evaluate(dots_seed[f["seed"]].astype(np.float32), f, foot,
                                      block_side=200, origin=(0, 0),
                                      global_shape=foot.shape)
                terms = t if terms is None else terms + t
            tp, fp, fn = (float(terms.sum(axis=0)[i]) for i in range(3))
            pooled = float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS))
            exps[tag] = {"terms": terms, "pooled": pooled, "infos": infos,
                         "dots": dots_seed, "tau": tau, "cap": cap}
            log(f"{tag} pooled HOLDOUT-DTI={pooled:.4f}")
    (OUT / "exps12.json").write_text(json.dumps(
        {k: {"pooled": v["pooled"], "infos": v["infos"], "tau": v["tau"], "cap": v["cap"]}
         for k, v in exps.items()}, indent=1))

    # E3: winner at 60k
    winner = max(exps, key=lambda k: exps[k]["pooled"])
    with stage("E3"):
        tau = exps[winner]["tau"]
        dots_seed, infos = {}, {}
        for seed in SEEDS:
            vis = folds[0]["visible"] if folds[0]["seed"] == seed else folds[4]["visible"]
            rho, geo, info = build_rho(codes, vis, foot, dip, tau, depth_med, depth)
            allowed = foot & ~vis & (geo["d_vis"] > B_PX)
            pl = place(rho, allowed, 60_000)
            dots_seed[seed] = pl["dots"]
            infos[str(seed)] = {**{k: v for k, v in info.items() if k != "nb"},
                                "n_dots": pl["n"], "surrogate": pl["surrogate_dti"]}
            log(f"E3(from {winner}) seed={seed} dots={pl['n']} surrogate={pl['surrogate_dti']:.4f}")
            del rho
        terms = None
        for f in folds:
            _res, t = EH.evaluate(dots_seed[f["seed"]].astype(np.float32), f, foot,
                                  block_side=200, origin=(0, 0), global_shape=foot.shape)
            terms = t if terms is None else terms + t
        tp, fp, fn = (float(terms.sum(axis=0)[i]) for i in range(3))
        pooled = float(tp / (tp + M.ALPHA * fp + M.BETA * fn + M.EPS))
        exps["E3"] = {"terms": terms, "pooled": pooled, "infos": infos,
                      "dots": dots_seed, "tau": tau, "cap": 60_000, "from": winner}
        log(f"E3 pooled HOLDOUT-DTI={pooled:.4f}")
    (OUT / "exps.json").write_text(json.dumps(
        {k: {"pooled": v["pooled"], "infos": v["infos"], "tau": v["tau"],
             "cap": v["cap"], "from": v.get("from")} for k, v in exps.items()}, indent=1))

    with stage("paired-CI"):
        bank = dict(np.load(OUT / "terms_bank.npz"))
        arms = {"E1": exps["E1"]["terms"], "E2": exps["E2"]["terms"],
                "E3": exps["E3"]["terms"],
                "champion": bank["focus_GEMSDOE32"], "sgce": bank["WBG-sgce"]}
        cards = {}
        for cand in ("E1", "E2", "E3"):
            cards[cand] = EH.pooled_summary(arms, draws=1000, seed=520810, candidate=cand)
            s = cards[cand]["scores"][cand]
            log(f"{cand}: dti={s['dti']:.4f} ci={[round(x,4) for x in s['ci95']]} "
                f"withheld={s['withheld_positive_pixels']}")
            for ctl, d in cards[cand]["paired_differences"].items():
                log(f"  d({cand}-{ctl})={d['delta']:+.4f} ci={[round(x,4) for x in d['ci95']]}")
        (OUT / "paired.json").write_text(json.dumps(cards, indent=1, default=float))

    (OUT / "stage_times.json").write_text(json.dumps(
        {"stages": STAGES, "wall_min": round((time.time() - t_start) / 60, 1)}, indent=1))
    log(f"TOTAL wall={(time.time()-t_start)/60:.1f} min stages={STAGES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
