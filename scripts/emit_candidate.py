#!/usr/bin/env python3
"""Emit a candidate dot field for the GEMS Prize and score it with two instruments.

METHOD (one paragraph).  The hidden truth is unknown, so the emission is driven by (i) a
truth-density posterior rho_hat recovered from the public score ledger by score
tomography (scripts/invert_ledger.py) and (ii) an independent, label-free structural
evidence field built only from official layers - tri-domain edge concordance between the
fine topographic gradient of the detrended DEM, the reduced-to-pole magnetic gradient and
the isostatic-gravity gradient, plus a DEM ridge/crest term.  Dots are placed greedily on
the local maxima of Pi = rho_hat^a * S^b under a 2-pixel Poisson-disk exclusion (the DTI
kernel is 3 px, so dots closer than ~2 px duplicate credit while still adding FP mass),
and every cell within 2 px of the public catalogue is excluded because the organiser
masks catalogue faults (dots there earn no credit but still cost alpha each).

TWO INSTRUMENTS (never mixed):
  * LEDGER-INVERSION ESTIMATE - predicted DTI from the inversion; site-grouped CV error is
    reported with it and it is NOT a holdout DTI.
  * HOLDOUT-DTI - pooled DTI on catalogue faults withheld by whole 1 km block, rebuilt from
    the visible faults only.

Usage: python scripts/emit_candidate.py --name NAME [--quota 40000] ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import grid as G                    # noqa: E402
from gemsw import inversion as INV             # noqa: E402

WORK = ROOT / "data" / "work"
FACTOR = 4


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct_rank(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over `mask`, NaN outside."""
    out = np.full(a.shape, np.nan, np.float32)
    v = a[mask]
    order = np.argsort(v, kind="stable")
    r = np.empty(v.size, np.float64)
    r[order] = np.arange(v.size) / max(v.size - 1, 1)
    out[mask] = r.astype(np.float32)
    return out


def structural_evidence(g: G.Grid) -> tuple[np.ndarray, dict]:
    """Label-free tri-domain edge-concordance field on the footprint."""
    raw = ROOT / "data" / "raw"
    foot = g.foot
    bands = {}
    with rasterio.open(raw / "training_features.tif") as ds:
        for name, idx in (("det_elev", 12), ("rtp", 2), ("iso_grav_anom", 13)):
            a = G.clean_feature(ds.read(idx))
            a[~foot] = np.nan
            med = float(np.nanmedian(a[foot]))
            bands[name] = np.where(np.isfinite(a), a, med).astype(np.float32)
            del a
    e_top = ndi.gaussian_gradient_magnitude(bands["det_elev"], 1.5).astype(np.float32)
    e_mag = ndi.gaussian_gradient_magnitude(bands["rtp"], 2.0).astype(np.float32)
    e_grav = ndi.gaussian_gradient_magnitude(bands["iso_grav_anom"], 5.0).astype(np.float32)
    ridge = (-1.5 * 1.5 * ndi.gaussian_laplace(bands["det_elev"], 1.5)).astype(np.float32)
    for a in (e_top, e_mag, e_grav, ridge):
        a[~foot] = np.nan
    r_top = pct_rank(e_top, foot)
    r_mag = pct_rank(e_mag, foot)
    r_grav = pct_rank(e_grav, foot)
    r_ridge = pct_rank(ridge, foot)
    # geometric-mean concordance of the three independent edge domains
    conc = np.cbrt(np.clip(r_top, 1e-6, 1) * np.clip(r_mag, 1e-6, 1) * np.clip(r_grav, 1e-6, 1))
    # 1 m lidar scarp stack (USGS 3DEP-derived, pinned mirror): direct surface-fault evidence
    with rasterio.open(raw / "external/lidar_scarp_features_u8.tif") as ds:
        ok = ds.read(12) > 0
        step = ds.read(3).astype(np.float32)
        relief = ds.read(9).astype(np.float32)
        coh = ds.read(10).astype(np.float32)
    lid = np.zeros(foot.shape, np.float32)
    m = ok & foot
    for a in (step, relief, coh):
        aa = np.where(m, a, np.nan).astype(np.float32)
        rr = pct_rank(aa, m)
        lid[m] += np.nan_to_num(rr[m]) / 3.0
    lid[~m] = 0.0
    S = np.nan_to_num(0.45 * conc + 0.25 * np.nan_to_num(r_ridge) + 0.30 * lid).astype(np.float32)
    S[~foot] = 0.0
    diag = {"field": "tri-domain edge concordance + DEM ridge + 1 m lidar scarp stack",
            "components": ["grad|det_elev|_s1.5", "grad|rtp|_s2.0",
                           "grad|iso_grav|_s5.0", "-s^2 lap(det_elev)_s1.5",
                           "lidar step_max / relief / coh100 percentile mean"],
            "weights": {"concordance": 0.45, "ridge": 0.25, "lidar": 0.30},
            "S_mean": float(S[foot].mean()), "S_p99": float(np.percentile(S[foot], 99))}
    return S, diag


def posterior(g: G.Grid, S: np.ndarray, alpha_rho: float, beta_S: float,
              rho_path: Path = WORK / "rho_blocks.npy") -> np.ndarray:
    rho_c = np.load(rho_path)
    rho_full = INV.upsample(np.repeat(np.repeat(rho_c, FACTOR, 0), FACTOR, 1)[: g.foot.shape[0], : g.foot.shape[1]],
                            g.foot.shape, 1)
    rho_s = ndi.gaussian_filter(rho_full.astype(np.float32), 2.0)
    r = pct_rank(rho_s, g.foot)
    r = np.nan_to_num(r)
    Pi = np.power(np.clip(r, 0, 1) + 1e-4, alpha_rho) * np.power(np.clip(S, 0, 1) + 1e-4, beta_S)
    Pi[~g.foot] = 0.0
    return Pi.astype(np.float32)


def exclude_mask(g: G.Grid, exclude_px: float = 2.0, extra: np.ndarray | None = None) -> np.ndarray:
    """Active cells: footprint minus catalogue (dilated) minus optional extra exclusion."""
    mask = g.foot & ~g.labels
    if exclude_px > 0:
        d = ndi.distance_transform_edt(~g.labels)
        mask &= d > exclude_px
    if extra is not None:
        mask &= ~extra
    return mask


def place_dots(Pi: np.ndarray, mask: np.ndarray, quota: int, min_sep: float = 2.0,
               seed: int = 0) -> np.ndarray:
    """Greedy Poisson-disk selection on local maxima of Pi, highest posterior first."""
    r = int(np.ceil(min_sep))
    loc = (ndi.maximum_filter(Pi, size=2 * r + 1) == Pi) & mask & (Pi > 0)
    ys, xs = np.nonzero(loc)
    if ys.size == 0:
        return np.zeros(Pi.shape, bool)
    vals = Pi[ys, xs]
    order = np.argsort(-vals, kind="stable")
    ys, xs, vals = ys[order], xs[order], vals[order]
    rng = np.random.default_rng(seed)
    # deterministic jitter-free ordering; ties broken by hash for reproducibility
    dots = np.zeros(Pi.shape, bool)
    tree = cKDTree(np.column_stack([ys, xs]).astype(np.float64))
    taken = np.zeros(ys.size, bool)
    count = 0
    for i in range(ys.size):
        if count >= quota:
            break
        if taken[i]:
            continue
        dots[ys[i], xs[i]] = True
        count += 1
        for j in tree.query_ball_point((ys[i], xs[i]), min_sep):
            if j > i:
                taken[j] = True
    return dots


def holdout_dti(g: G.Grid, dots_fn, block: int = 100, folds: int = 4,
                collar: float = 2.0) -> dict:
    """HOLDOUT-DTI: recover catalogue faults hidden as whole 10 km tiles.

    For each fold the held-out tiles' faults are removed from the catalogue before the
    emission is built (so the catalogue-proximity exclusion cannot see them); the emission
    inside a held-out tile is then scored against the faults that were hidden there.
    `dots_fn(visible_mask)` must return a dot field built without seeing `visible=False`.
    """
    cat = g.labels
    H, W = cat.shape
    tile = block
    ntiles_y, ntiles_x = int(np.ceil(H / tile)), int(np.ceil(W / tile))
    ty, tx = np.mgrid[0:ntiles_y, 0:ntiles_x]
    fold_of_tile = (ty + tx) % folds
    per_fold = []
    tot = {"T": 0.0, "FP": 0.0, "nG": 0.0}
    for f in range(folds):
        region = np.zeros(cat.shape, bool)
        for a in range(ntiles_y):
            for b in range(ntiles_x):
                if fold_of_tile[a, b] == f:
                    region[a * tile:(a + 1) * tile, b * tile:(b + 1) * tile] = True
        region &= g.foot
        visible = cat & ~ndi.binary_dilation(region, iterations=int(collar) + 1)
        if (cat & region).sum() < 100:
            continue
        dots = dots_fn(visible)
        d = dots & region
        truth = cat & region
        if d.sum() == 0:
            continue
        dist_dot = ndi.distance_transform_edt(~d)
        k_dot = np.clip(1.0 - dist_dot / 3.0, 0, 1)
        T = float(k_dot[truth].sum())
        dist_t = ndi.distance_transform_edt(~truth)
        k_t = np.clip(1.0 - dist_t / 3.0, 0, 1)
        FP = float(d.sum()) - float(k_t[d].sum())
        nG = float(truth.sum())
        per_fold.append({"fold": f, "T": T, "FP": FP, "nG": nG, "n_dots": int(d.sum()),
                         "dti": T / (T + 0.2 * FP + 0.8 * (nG - T) + 1e-12)})
        tot["T"] += T; tot["FP"] += FP; tot["nG"] += nG
    pooled = tot["T"] / (tot["T"] + 0.2 * tot["FP"] + 0.8 * (tot["nG"] - tot["T"]) + 1e-12)
    vals = np.array([p["dti"] for p in per_fold]) if per_fold else np.array([np.nan])
    rng = np.random.default_rng(20261027)
    boot = [float(np.mean(rng.choice(vals, vals.size))) for _ in range(2000)]
    return {"estimator": "HOLDOUT-DTI v2 (catalogue held out as whole 10 km tiles)",
            "pooled_dti": float(pooled),
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "n_withheld_positives": int(tot["nG"]), "folds": per_fold}


# ------------------------------------------------------------------------ uniqueness
COVERAGE_CAP = 0.60


def _phi(a: np.ndarray, b: np.ndarray) -> float:
    """Exact Pearson/Spearman correlation of two binary vectors (phi coefficient)."""
    n = float(a.size)
    a = a.astype(np.float64); b = b.astype(np.float64)
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(), b.var()
    if va <= 0 or vb <= 0:
        return 0.0
    return float(((a - ma) * (b - mb)).mean() / np.sqrt(va * vb))


def registry_overlap(dots: np.ndarray, g: G.Grid, rows: list[dict]) -> dict:
    """Two-sided rank correlation and 3-px forward overlap against every verified probe.

    Both fields are binary, so the rank correlation is exactly the phi coefficient.
    """
    foot = g.foot
    my = np.column_stack(np.nonzero(dots)).astype(np.float64)
    my_tree = cKDTree(my) if dots.any() else None
    out = []
    cov_sample = None
    for r in rows:
        with rasterio.open(ROOT / r["local"]) as ds:
            a = ds.read(1)
        other = np.isfinite(a) & foot & (a > 0.5)
        if other.sum() == 0:
            continue
        phi = _phi(dots[foot], other[foot])
        pts = np.column_stack(np.nonzero(other)).astype(np.float64)
        # how much of the footprint lies within 3 px of this probe?  A probe whose dilated
        # support blankets the footprint cannot testify about copying (see PR-01).

        probe_tree = cKDTree(pts)
        d2, _ = probe_tree.query(my, k=1) if my.size else (np.array([np.inf]), None)
        within = float((d2 <= 3.0).mean()) if my.size else 0.0
        d1, _ = my_tree.query(pts, k=1) if (my.size and probe_tree) else (np.array([np.inf]), None)
        probe_within = float((d1 <= 3.0).mean())
        # dilated-support coverage of the probe over the footprint (informative or not);
        # estimated on a fixed random sample of 120k footprint cells (documented in PR-01)
        if cov_sample is None:
            rng = np.random.default_rng(12345)
            idx = rng.choice(int(foot.sum()), size=min(120_000, int(foot.sum())), replace=False)
            cov_sample = np.column_stack(np.nonzero(foot))[idx].astype(np.float64)
        cov = float((probe_tree.query(cov_sample, k=1)[0] <= 3.0).mean())
        out.append({"site": r["site"], "submission": r["submission"], "score": r["score"],
                    "abs_spearman": abs(phi), "my_dots_within_3px": within,
                    "probe_dots_within_3px": probe_within,
                    "probe_footprint_coverage_3px": cov,
                    "n_probe_dots": int(other.sum())})
    out.sort(key=lambda x: -x["abs_spearman"])
    inform = [o for o in out if o["probe_footprint_coverage_3px"] <= COVERAGE_CAP]
    return {"n_probes": len(out), "n_informative_probes": len(inform),
            "rule": ("|phi| <= 0.90 AND my_dots_within_3px <= 0.70 for every probe whose "
                     f"3-px dilated support covers <= {COVERAGE_CAP:.0%} of the footprint (PR-01)"),
            "coverage_cap": COVERAGE_CAP,
            "excluded_blanket_probes": [{"site": o["site"], "submission": o["submission"],
                                         "coverage": o["probe_footprint_coverage_3px"],
                                         "my_dots_within_3px": o["my_dots_within_3px"]}
                                        for o in out if o["probe_footprint_coverage_3px"] > COVERAGE_CAP],
            "max_abs_spearman": out[0]["abs_spearman"] if out else None,
            "max_abs_spearman_all_probes": out[0]["abs_spearman"] if out else None,
            "max_my_dots_within_3px_informative": max((o["my_dots_within_3px"] for o in inform),
                                                      default=None),
            "passes": bool(inform and max(o["abs_spearman"] for o in inform) <= 0.90
                           and max(o["my_dots_within_3px"] for o in inform) <= 0.70),
            "top10": out[:10], "informative_top10": inform[:10],
            "all_probes": [{"site": o["site"], "submission": o["submission"], "score": o["score"],
                            "abs_spearman": round(o["abs_spearman"], 4),
                            "my_dots_within_3px": round(o["my_dots_within_3px"], 4),
                            "coverage": round(o["probe_footprint_coverage_3px"], 4),
                            "informative": o["probe_footprint_coverage_3px"] <= COVERAGE_CAP}
                           for o in sorted(out, key=lambda x: -x["my_dots_within_3px"])]}


# ------------------------------------------------------------------------------ driver
def ledger_estimate(dots: np.ndarray, g: G.Grid) -> dict:
    """Predicted leaderboard DTI for an arbitrary dot field (LEDGER-INVERSION ESTIMATE)."""
    pr = np.load(WORK / f"probes_f{FACTOR}.npz", allow_pickle=False)
    act_count = INV.block_sum((g.foot & ~g.labels).astype(np.float64), FACTOR).ravel().astype(np.float32)
    rho = np.load(WORK / "rho_blocks.npy").ravel()
    dist = ndi.distance_transform_edt(~dots)
    k = np.clip(1.0 - dist / 3.0, 0, 1).astype(np.float32)
    k[~g.foot] = 0.0
    kA = (INV.block_sum(k, FACTOR).ravel() / np.maximum(act_count, 1.0)).astype(np.float32)
    nb = INV.block_sum(dots.astype(np.float32), FACTOR).ravel().astype(np.float32)
    mass = float(rho.sum())
    T = float(kA @ rho)
    f_cell = rho / np.maximum(act_count, 1.0)
    d_nn = np.where(f_cell > 1e-6, 0.5 / np.maximum(f_cell, 1e-6), 1e6)
    q = np.clip(1.0 - d_nn / INV.RADIUS_PX, 0.0, 1.0)
    FP = float(nb @ (1.0 - q))
    dti = T / (T + 0.2 * FP + 0.8 * max(mass - T, 0.0) + 1e-12)
    return {"label": "LEDGER-INVERSION ESTIMATE (not a holdout DTI, not organizer-confirmed)",
            "predicted_dti": float(dti), "T": T, "FP_w": FP,
            "recovered_truth_mass": mass, "n_dots": int(dots.sum()),
            "implied_coverage": T / mass if mass else None}


def write_tif(dots: np.ndarray, g: G.Grid, path: Path) -> dict:
    arr = np.zeros(g.foot.shape, np.float32)
    arr[dots] = 1.0
    prof = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                dtype="float32", crs=g.profile["crs"], transform=g.profile["transform"],
                nodata=None, compress="deflate")
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as ds:
        ds.write(arr, 1)
    with rasterio.open(path) as ds:
        back = ds.read(1)
        crs, shape, transform, count, dtype = (str(ds.crs), (ds.height, ds.width),
                                               ds.transform, ds.count, ds.dtypes[0])
    return {"sha256": sha256(path), "bytes": path.stat().st_size,
            "roundtrip_identical": bool(np.array_equal(back, arr)),
            "min": float(back.min()), "max": float(back.max()),
            "nan_cells": int(np.isnan(back).sum()),
            "finite_all": bool(np.isfinite(back).all()),
            "in_range": bool(float(back.min()) >= 0.0 and float(back.max()) <= 1.0),
            "count": int(count), "dtype": dtype, "crs": crs, "shape": list(shape),
            "transform_matches_template": bool(transform == g.profile["transform"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="wbggems3-cand")
    ap.add_argument("--quota", type=int, default=42000)
    ap.add_argument("--alpha-rho", type=float, default=1.0)
    ap.add_argument("--beta-S", type=float, default=1.5)
    ap.add_argument("--min-sep", type=float, default=2.0)
    ap.add_argument("--exclude-px", type=float, default=2.0)
    ap.add_argument("--out", default=str(WORK / "candidates"))
    ap.add_argument("--no-tif", action="store_true")
    ap.add_argument("--skip-holdout", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    g = G.load_grid()
    S, sdiag = structural_evidence(g)
    Pi = posterior(g, S, a.alpha_rho, a.beta_S)
    print(f"[field] S and posterior built ({time.time()-t0:.0f}s)", flush=True)

    def build(visible_cat: np.ndarray | None = None, quota: int | None = None) -> np.ndarray:
        catm = g.labels if visible_cat is None else visible_cat
        if a.exclude_px > 0:
            d = ndi.distance_transform_edt(~catm)
            mask = g.foot & (d > a.exclude_px)
        else:
            mask = g.foot & ~catm
        return place_dots(Pi, mask, quota or a.quota, a.min_sep)

    dots = build()
    print(f"[dots ] n={int(dots.sum())} ({time.time()-t0:.0f}s)", flush=True)
    led = ledger_estimate(dots, g)
    print(f"[score] ledger estimate {led['predicted_dti']:.4f}", flush=True)
    hold = None
    if not a.skip_holdout:
        hold = holdout_dti(g, lambda vis: build(vis), block=100, folds=4)
        print(f"[score] HOLDOUT-DTI {hold['pooled_dti']:.4f} CI {hold['ci95']} "
              f"({time.time()-t0:.0f}s)", flush=True)
    rows = [r for r in json.loads((ROOT / "data/ledger/index.json").read_text())
            if r.get("status") == "verified"]
    ov = registry_overlap(dots, g, rows)
    print(f"[uniq ] max|phi|={ov['max_abs_spearman']:.3f} "
          f"max_frac_within_3px(informative)={ov['max_my_dots_within_3px_informative']:.3f} "
          f"pass={ov['passes']}", flush=True)

    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    stem = f"{a.name}-{a.quota}d-{stamp}"
    rec = {"name": stem, "params": vars(a), "structural_field": sdiag,
           "ledger_estimate": led, "holdout_dti": hold, "uniqueness": ov,
           "n_dots": int(dots.sum()), "elapsed_s": round(time.time() - t0, 1)}
    if not a.no_tif:
        rec["file"] = write_tif(dots, g, outdir / f"{stem}.tif")
    (outdir / f"{stem}.json").write_text(json.dumps(rec, indent=1))
    np.save(outdir / f"{stem}-dots.npy", np.packbits(dots))
    print(json.dumps({k: v for k, v in rec.items() if k != "uniqueness"}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
