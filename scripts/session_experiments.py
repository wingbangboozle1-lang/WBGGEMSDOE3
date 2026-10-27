#!/usr/bin/env python3
"""Session 2026-10-27 experiments E1-E3 (preregistered in
knowledge/preregistration-2026-10-27-session-1f0b051d.md).

Lane H1: LiDAR scarp-dipole polarity detector on the pinned USGS-3DEP-derived
2 m lidar aggregate channels + dotted emission + B2 (sqrt5 px) catalogue trim.

Phases: fields | canary | lst | e1 | e2 | e3 | finalize
All performance outputs are labelled HOLDOUT-DTI / PROXY-DTI / LEDGER-PROJECTION.
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
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe import config as C          # noqa: E402
from gemsdoe import io as gio            # noqa: E402
from gemsdoe import metric as M          # noqa: E402
from gemsdoe import pipeline as P        # noqa: E402
from gemsdoe import validation as V      # noqa: E402
from gemsw import holdout as HO          # noqa: E402
from gemsw import ledger as LD           # noqa: E402

SESS = ROOT / ".cache" / "session"
SESS.mkdir(parents=True, exist_ok=True)
RAW = ROOT / "data" / "raw"
SQRT5 = float(np.hypot(2, 1))

LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid"]


def log(*a):
    print(*a, flush=True)


def grid():
    foot = gio.read_footprint()
    labels = gio.read_labels() & foot
    return foot, labels


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over mask (NaN outside mask -> 0)."""
    out = np.zeros(a.shape, np.float32)
    v = a[mask]
    ok = np.isfinite(v)
    r = np.zeros(v.size, np.float32)
    r[ok] = (rankdata(v[ok]) - 0.5) / max(ok.sum(), 1)
    out[mask] = r
    return out


# ---------------------------------------------------------------- fields
def dequant_lidar():
    meta = json.loads((RAW / "external/lidar_scarp_features.json").read_text())
    q = meta["quantisation"]
    out = {}
    with rasterio.open(RAW / "external/lidar_scarp_features_u8.tif") as ds:
        for i, nm in enumerate(LIDAR_BANDS, start=1):
            raw = ds.read(i).astype(np.float32)
            xmax, tr = q[nm]
            z = np.clip((raw - 1.0) / 254.0, 0.0, 1.0)
            x = xmax * (z ** 2) if tr == "sqrt" else xmax * z
            x[raw == 0] = np.nan
            out[nm] = x
    return out


def build_fields():
    foot, labels = grid()
    lid = dequant_lidar()
    lvalid = np.isfinite(lid["valid"]) & (lid["valid"] > 0) & foot
    log(f"[fields] lidar-valid cells in footprint: {int(lvalid.sum()):,} / {int(foot.sum()):,}")

    with rasterio.open(RAW / "external/tiger_road_distance_m.tif") as ds:
        road = ds.read(1).astype(np.float32)
        log(f"[fields] tiger road distance: dtype={ds.dtypes[0]} nodata={ds.nodata} "
            f"footprint pct[0,50,99,100]={np.nanpercentile(road[foot], [0,50,99,100])}")

    de = gio.read_band(C.FEATURES_TIF, 12)  # det_elev
    bad = ~np.isfinite(de)
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    de_f = de[tuple(idx)]
    de_log2 = -ndi.gaussian_laplace(de_f, 2, mode="nearest")
    de_g = ndi.gaussian_filter(de_f, 2, mode="nearest")

    # along-strike elevation change: |z(x+3s) - z(x-3s)| with s = lidar strike unit vector.
    # strike channel is in degrees 0..180 (doubled-angle-safe: use as orientation, axis not direction).
    th = np.deg2rad(np.nan_to_num(lid["strike"]))
    dy = np.rint(3 * np.sin(th)).astype(np.int32)
    dx = np.rint(3 * np.cos(th)).astype(np.int32)
    H, W = de_g.shape
    r = np.arange(H)[:, None]; c = np.arange(W)[None, :]
    along_dz = np.abs(de_g[np.clip(r + dy, 0, H - 1), np.clip(c + dx, 0, W - 1)]
                      - de_g[np.clip(r - dy, 0, H - 1), np.clip(c - dx, 0, W - 1)]).astype(np.float32)
    along_dz[~lvalid] = np.nan

    d_cat = ndi.distance_transform_edt(~labels).astype(np.float32)
    h19 = load_float(ROOT / ".cache/upstream/x24/inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif")
    d_h19 = ndi.distance_transform_edt(~((h19 > 0) & foot)).astype(np.float32)
    with rasterio.open(RAW / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) > 0
    d_sgmc = ndi.distance_transform_edt(~sgmc).astype(np.float32)

    fields = {}
    for nm in ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100"]:
        fields[f"lidar_{nm}"] = lid[nm]
    fields["lidar_strike"] = lid["strike"]
    fields["along_dz"] = along_dz
    fields["de_log2"] = de_log2.astype(np.float32)
    fields["de_slope2"] = np.hypot(*np.gradient(de_g)).astype(np.float32)
    fields["road_dist_m"] = road
    fields["d_cat"] = d_cat
    fields["d_h19"] = d_h19
    fields["d_sgmc"] = d_sgmc

    names = list(fields)
    mm = np.lib.format.open_memmap(SESS / "fields.npy", mode="w+", dtype=np.float32,
                                   shape=(len(names), C.HEIGHT, C.WIDTH))
    for i, nm in enumerate(names):
        mm[i] = fields[nm]
    mm.flush(); del mm
    np.save(SESS / "lidar_valid.npy", lvalid)
    (SESS / "field_names.json").write_text(json.dumps(names))
    log(f"[fields] wrote {(len(names), C.HEIGHT, C.WIDTH)} -> {SESS/'fields.npy'}")
    return names


def load_fields():
    names = json.loads((SESS / "field_names.json").read_text())
    return np.load(SESS / "fields.npy", mmap_mode="r"), names


def load_float(p) -> np.ndarray:
    with rasterio.open(p) as src:
        a = src.read(1).astype(np.float32)
    return np.where(np.isfinite(a), a, 0.0).astype(np.float32)


# ---------------------------------------------------------------- canary
def auc(pos, neg):
    x = np.r_[pos, neg]
    ok = np.isfinite(x)
    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))][ok]
    x = x[ok]
    if y.sum() == 0 or y.sum() == len(y):
        return float("nan"), float("nan")
    r = rankdata(x)
    n1 = y.sum(); n0 = len(y) - n1
    a = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return float(a), float(max(a, 1 - a))


def canary():
    foot, labels = grid()
    stack, names = load_fields()
    ctx = HO.load_holdout_context(RAW)
    # pooled withheld positives across the 8 hide-recover cells (full-grid coords)
    pos_rc = []
    seen = np.zeros(foot.shape, bool)
    for cell in ctx.cells:
        sl = cell.bbox
        sub = np.zeros(foot.shape, bool)
        m = np.zeros((sl[0].stop - sl[0].start, sl[1].stop - sl[1].start), bool)
        m[cell.truth_coords] = True
        sub[sl] = m
        pos_rc.append(sub & ~seen)
        seen |= sub
    withheld = seen & labels
    rng = np.random.default_rng(20261027)
    active = foot & ~labels
    aidx = np.flatnonzero(active.ravel())
    neg_flat = rng.choice(aidx, 200_000, replace=False)
    pos_flat = np.flatnonzero(withheld.ravel())
    log(f"[canary] withheld positives={pos_flat.size:,} negatives={neg_flat.size:,}")
    rows = []
    for i, nm in enumerate(names):
        fl = np.asarray(stack[i]).ravel()
        a_raw, a2 = auc(fl[pos_flat], fl[neg_flat])
        rows.append({"field": nm, "auc_raw": a_raw, "auc_two_polarity": a2,
                     "catalogue_derived": nm in ("d_cat",),
                     "note": "nuisance/trim only, never a detector feature" if nm in ("d_cat", "d_h19", "d_sgmc") else ""})
        log(f"[canary] {nm:16s} AUC={a_raw:.3f} AUC2={a2:.3f}")
    worst = max((r for r in rows if not r["catalogue_derived"]), key=lambda r: r["auc_two_polarity"])
    out = {"label": "LEAKAGE CANARY (single-field AUC vs withheld catalogue segments, pooled v3.0 cells)",
           "threshold": 0.90, "n_withheld_positives": int(pos_flat.size),
           "worst_non_catalogue_field": worst, "all_pass": bool(worst["auc_two_polarity"] <= 0.90),
           "fields": rows}
    (SESS / "canary.json").write_text(json.dumps(out, indent=1))
    log(f"[canary] worst non-catalogue field: {worst['field']} AUC2={worst['auc_two_polarity']:.3f} pass={out['all_pass']}")
    return out


# ---------------------------------------------------------------- LST (nuisance strata only)
def strata_codes(d_cat, d_h19, domain):
    def dig(d, edges, codes):
        return np.asarray(codes, np.uint8)[np.digitize(d, edges, right=True)]
    cat_code = dig(d_cat[domain], [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01], [1, 2, 3, 4, 5, 6, 7, 0])
    h_code = dig(d_h19[domain], [0.01, 1.01, 2.01, 3.01, 5.01, 10.01], [0, 1, 2, 3, 4, 5, 6])
    return (cat_code * 8 + h_code).astype(np.uint8)


def lst_build():
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    active = foot & ~labels
    codes = strata_codes(np.asarray(stack[ix["d_cat"]]), np.asarray(stack[ix["d_h19"]]), foot)
    bins = {"NUIS_catxH": codes[active[foot]]}
    NB = 64
    S = LD.sizes(bins, NB)
    idx = json.load(open(ROOT / "data/ledger/index.json"))
    rows, meta, digests = [], [], {}
    t0 = time.time()
    for rec in idx:
        if rec["status"] != "verified":
            continue
        a = load_float(ROOT / rec["local"])
        a[~active] = 0.0
        a = np.clip(a, 0.0, 1.0)
        dig = hashlib.sha256(np.round(a[active], 5).tobytes()).hexdigest()[:16]
        if dig in digests:
            digests[dig]["aliases"].append({"submission": rec["submission"], "score": rec["score"]})
            continue
        row = LD.design_row(a, active, bins, NB)
        m = {"site": rec["site"], "submission": rec["submission"], "score": rec["score"],
             "digest": dig, "N": row["N"], "dots": row["dots"], "aliases": []}
        digests[dig] = m; rows.append(row); meta.append(m)
        log(f"[lst] {len(rows):3d} {rec['submission'][:52]:52s} s={rec['score']:.4f} N={row['N']:.0f} t={time.time()-t0:.0f}s")
    s = np.array([np.mean([m["score"]] + [al["score"] for al in m["aliases"]]) for m in meta])
    np.savez_compressed(SESS / "lst_design.npz", A=np.stack([r["A"] for r in rows]),
                        B=np.stack([r["B"] for r in rows]), N=np.array([r["N"] for r in rows]),
                        s=s, S=S, names=np.array(["NUIS_catxH"]))
    (SESS / "lst_meta.json").write_text(json.dumps(meta, indent=1))
    log(f"[lst] design built: {len(rows)} unique rasters in {time.time()-t0:.0f}s")

    A = np.stack([r["A"] for r in rows]); B = np.stack([r["B"] for r in rows])
    N = np.array([r["N"] for r in rows])
    cols = [(0, b) for b in range(NB) if S[0, b] > 0]
    site = np.array([m["site"] for m in meta])
    fam = np.unique(site, return_inverse=True)[1]
    best = None
    for ridge in (1e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0):
        p = LD.loo(A, B, N, S, s, cols, ridge)
        mae = float(np.mean(np.abs(p - s))); sp = float(spearmanr(p, s)[0])
        log(f"[lst] ridge={ridge:g} LOO MAE={mae:.4f} Spearman={sp:.3f}")
        if best is None or mae < best[0]:
            best = (mae, sp, ridge)
    ridge = best[2]
    p_loo = LD.loo(A, B, N, S, s, cols, ridge)
    p_fam = LD.loo(A, B, N, S, s, cols, ridge, groups=fam)
    lam = LD.fit(A, B, N, S, s, cols, ridge)
    top = np.argsort(-s)[:20]
    res = {"label": "LEDGER-PROJECTION model (LST nuisance strata, refit this session; scores OWNER-REPORTED)",
           "n_unique_rasters": int(len(s)), "n_sites": int(len(np.unique(site))), "ridge": ridge,
           "loo_mae": float(np.mean(np.abs(p_loo - s))), "loo_spearman": float(spearmanr(p_loo, s)[0]),
           "family_cv_mae": float(np.mean(np.abs(p_fam - s))), "family_cv_spearman": float(spearmanr(p_fam, s)[0]),
           "family_cv_mae_top20": float(np.mean(np.abs(p_fam[top] - s[top]))),
           "g_hat": float(sum(lam[i] * S[c] for i, c in enumerate(cols))),
           "abs_err_quantiles_loo": {str(q): float(np.quantile(np.abs(p_loo - s), q)) for q in (0.5, 0.8, 0.9, 0.95)},
           "per_raster": [{"submission": m["submission"], "site": m["site"], "owner_reported": float(s[i]),
                           "loo_projection": float(p_loo[i]), "family_cv_projection": float(p_fam[i])}
                          for i, m in enumerate(meta)]}
    np.savez(SESS / "lst_model.npz", lam=lam, cols=np.array(cols), ridge=ridge)
    (SESS / "lst_fit_session.json").write_text(json.dumps(res, indent=1))
    log(f"[lst] refit done: LOO MAE={res['loo_mae']:.4f} famCV MAE={res['family_cv_mae']:.4f} g_hat={res['g_hat']:.0f}")
    return res


def lst_project(mask01: np.ndarray) -> dict:
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    active = foot & ~labels
    codes = strata_codes(np.asarray(stack[ix["d_cat"]]), np.asarray(stack[ix["d_h19"]]), foot)
    bins = {"NUIS_catxH": codes[active[foot]]}
    S = LD.sizes(bins, 64)
    mdl = np.load(SESS / "lst_model.npz")
    lam, cols = mdl["lam"], [tuple(c) for c in mdl["cols"]]
    a = np.where(active, mask01, 0.0).astype(np.float32)
    row = LD.design_row(a, active, bins, 64)
    pr = LD.project(lam, cols, row["A"], row["B"], row["N"], S)
    fit = json.loads((SESS / "lst_fit_session.json").read_text())
    return {"label": "LEDGER-PROJECTION (not a score)", "projection": pr["dti"],
            "tp_hat": pr["tp"], "g_hat": pr["g"], "fp_hat": pr["fp"], "mass": row["N"],
            "model_loo_mae": fit["loo_mae"], "model_family_cv_mae": fit["family_cv_mae"],
            "model_family_cv_mae_top20": fit["family_cv_mae_top20"]}


# ---------------------------------------------------------------- placement + evaluation
def greedy_dots(score, allowed, K, spacing):
    """Local-max prefilter + score-ordered inhibition (min Euclidean spacing)."""
    s = np.where(allowed, score, 0.0).astype(np.float32)
    mx = ndi.maximum_filter(s, size=3, mode="constant")
    cand = allowed & (s > 0) & (s >= mx)
    ys, xs = np.nonzero(cand)
    vals = s[ys, xs]
    order = np.argsort(-vals, kind="stable")
    ys, xs, vals = ys[order], xs[order], vals[order]
    lim = min(ys.size, max(6 * K, K))
    ys, xs = ys[:lim], xs[:lim]
    cell = max(spacing, 1.0)
    gh = int(C.HEIGHT // cell) + 2; gw = int(C.WIDTH // cell) + 2
    g = [[[] for _ in range(gw)] for _ in range(gh)]
    keep_y, keep_x = [], []
    sp2 = spacing * spacing
    for y, x in zip(ys.tolist(), xs.tolist()):
        if len(keep_y) >= K:
            break
        cy, cx = int(y // cell), int(x // cell)
        ok = True
        for gy in (cy - 1, cy, cy + 1):
            if gy < 0 or gy >= gh:
                continue
            row = g[gy]
            for gx in (cx - 1, cx, cx + 1):
                if gx < 0 or gx >= gw:
                    continue
                for (jy, jx) in row[gx]:
                    if (y - jy) ** 2 + (x - jx) ** 2 < sp2:
                        ok = False; break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            g[cy][cx].append((y, x)); keep_y.append(y); keep_x.append(x)
    dots = np.zeros(score.shape, bool)
    dots[np.array(keep_y), np.array(keep_x)] = True
    return dots


def density_spearman(surf_a_binary, surf_b_binary, foot, block=20):
    H, W = foot.shape
    h2, w2 = (H // block) * block, (W // block) * block
    def dens(m):
        x = m[:h2, :w2].astype(np.float32).reshape(h2 // block, block, w2 // block, block).mean(axis=(1, 3))
        f = foot[:h2, :w2].astype(np.float32).reshape(h2 // block, block, w2 // block, block).mean(axis=(1, 3))
        return x[f > 0.5].ravel(), f[f > 0.5].ravel()
    a, _ = dens(surf_a_binary); b, _ = dens(surf_b_binary)
    n = min(a.size, b.size)
    return float(spearmanr(a[:n], b[:n])[0])


def uniqueness(mask, comparators):
    """comparators: list of (name, path). Returns rows with within-3px (KDTree) + Jaccard + density rho."""
    from scipy.spatial import cKDTree
    foot, _ = grid()
    ys, xs = np.nonzero(mask & foot)
    pts = np.c_[ys, xs].astype(np.float64)
    rows = []
    for name, p in comparators:
        a = load_float(p)
        sup = (a > 0) & foot
        n_other = int(sup.sum())
        inter = int((mask & sup).sum())
        jac = inter / max(int((mask | sup).sum()), 1)
        if n_other > 1_500_000:
            rows.append({"comparator": name, "n_other": n_other, "jaccard": jac,
                         "class": "space-filling/dense (excluded under R1, listed)",
                         "cand_within3": None, "density_spearman": density_spearman(mask, sup, foot)})
            continue
        oy, ox = np.nonzero(sup)
        tree = cKDTree(np.c_[oy, ox].astype(np.float64))
        d, _ = tree.query(pts, workers=2)
        rows.append({"comparator": name, "n_other": n_other, "jaccard": float(jac),
                     "class": "sparse", "cand_within3": float((d <= 3.0).mean()) if len(d) else 0.0,
                     "density_spearman": density_spearman(mask, sup, foot)})
    sparse = [r for r in rows if r["class"] == "sparse"]
    return {"rows": rows,
            "max_cand_within3_sparse": max((r["cand_within3"] for r in sparse), default=None),
            "worst_sparse": max(sparse, key=lambda r: r["cand_within3"])["comparator"] if sparse else None,
            "max_jaccard": max((r["jaccard"] for r in rows), default=None),
            "max_abs_density_spearman": max((abs(r["density_spearman"]) for r in rows if r["density_spearman"] is not None), default=None)}


def density_matched(mask01_map: dict, foot, gt):
    comp, n_comp = ndi.label(gt, structure=np.ones((3, 3), bool))
    sizes = np.bincount(comp.ravel())
    ids = np.arange(1, n_comp + 1)
    out = {}
    for target_px in (8430, 12691, 15672):
        vals = {k: [] for k in mask01_map}
        for seed in range(12):
            rng = np.random.default_rng(10_000 + seed)
            order = rng.permutation(ids.size)
            keep, tot = [], 0
            for i in order:
                if tot >= target_px:
                    break
                keep.append(ids[i]); tot += int(sizes[ids[i]])
            evd = M.FastDTI(np.isin(comp, keep), valid=foot)
            for k, a in mask01_map.items():
                vals[k].append(evd.evaluate(a)["dti"])
        out[str(target_px)] = {k: {"mean": float(np.mean(v)), "p2.5": float(np.percentile(v, 2.5)),
                                   "p97.5": float(np.percentile(v, 97.5))} for k, v in vals.items()}
    return {"label": "PROXY-DTI (density-matched SGMC segments; same seeds as audit)", "by_target": out}


def evaluate_candidate(name, dots, ctx, foot, gt_proxy, comparators, control_seed=99):
    mask01 = dots.astype(np.float32)
    hr = HO.evaluate_hide_and_recover(dots, ctx, b_visible_px=SQRT5, name=name)
    # strata-shuffled control: same cat-stratum counts, random positions >= spacing ignored (pure random in stratum)
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]])
    _, labels = grid()
    rng = np.random.default_rng(control_seed)
    bins_edges = [2.24, 3.01, 5.01, 10.01, 20.01, 50.01, 1e9]
    ctrl = np.zeros_like(dots)
    lo = 2.24
    for hi in bins_edges[1:]:
        stratum = foot & ~labels & (d_cat >= lo) & (d_cat < hi)
        k = int((dots & stratum).sum())
        if k:
            idxs = np.flatnonzero(stratum.ravel())
            sel = rng.choice(idxs, size=min(k, idxs.size), replace=False)
            ctrl.ravel()[sel] = True
        lo = hi
    hr_c = HO.evaluate_hide_and_recover(ctrl, ctx, b_visible_px=SQRT5, name=f"{name}_strata_control")
    delta = hr["_boots"] - hr_c["_boots"]
    dm = density_matched({name: mask01,
                          "champion_GEMSDOE32": load_float(ROOT / ".cache/focus/GEMSDOE32.tif"),
                          "skarpline_union": load_float(ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif")},
                         foot, gt_proxy)
    res = {
        "name": name, "n_dots": int(dots.sum()),
        "holdout": {"label": "HOLDOUT-DTI (fold-legal: catalogue-free fields; trim applied to VISIBLE faults only)",
                    "evaluator_version": hr["evaluator_version"], "n_withheld_positives": hr["n_withheld_positives"],
                    "pooled_dti": hr["pooled_dti"], "ci95": hr["ci95_cluster_bootstrap"],
                    "per_quadrant": hr["per_quadrant_dti"]},
        "strata_control": {"pooled_dti": hr_c["pooled_dti"], "ci95": hr_c["ci95_cluster_bootstrap"],
                           "paired_delta": float(hr["pooled_dti"] - hr_c["pooled_dti"]),
                           "paired_delta_ci95": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
                           "p_delta_le_0": float((delta <= 0).mean())},
        "lst": lst_project(mask01),
        "density_matched": dm,
        "uniqueness": uniqueness(dots, comparators),
    }
    return res


def comparator_subset(full=False):
    comps = []
    idx = json.load(open(ROOT / "data/ledger/index.json"))
    ok = [r for r in idx if r["status"] == "verified"]
    ok.sort(key=lambda r: -r["score"])
    sel = ok if full else ok[:30]
    for r in sel:
        comps.append((f"{r['site']}::{r['submission']}", ROOT / r["local"]))
    for nm, rel in [("skarpline_union", "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
                    ("cspes_edgestab", "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif"),
                    ("lst1_hybrid", "submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif"),
                    ("hce1_congruence", "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif")]:
        comps.append((nm, ROOT / rel))
    return comps


# ---------------------------------------------------------------- surfaces
def surface_e1():
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    lvalid = np.load(SESS / "lidar_valid.npy")
    dom = lvalid & foot & ~labels
    r = {nm: rank01(np.asarray(stack[ix[f"lidar_{nm}"]]), dom)
         for nm in ("lapneg_max", "lappos_max", "upface_max", "downface_max", "step_max")}
    up = np.nan_to_num(np.asarray(stack[ix["lidar_upface_max"]]))
    dn = np.nan_to_num(np.asarray(stack[ix["lidar_downface_max"]]))
    cr = np.nan_to_num(np.asarray(stack[ix["lidar_cross_max"]]))
    coh = np.nan_to_num(np.asarray(stack[ix["lidar_coh100"]]))
    r_face = np.maximum(r["upface_max"], r["downface_max"])
    cross_dom = cr / (up + dn + cr + 1e-9)
    geo = (np.maximum(r["lapneg_max"], 1e-4) * np.maximum(r["lappos_max"], 1e-4)
           * np.maximum(r_face, 1e-4) * np.maximum(r["step_max"], 1e-4)) ** 0.25
    S = (geo * (0.5 + 0.5 * coh) * (1.0 - 0.5 * cross_dom)).astype(np.float32)
    S[~dom] = 0.0
    return S


def _shift(a, dy, dx):
    out = np.zeros_like(a)
    H, W = a.shape
    ys0, ys1 = max(0, dy), min(H, H + dy)
    xs0, xs1 = max(0, dx), min(W, W + dx)
    out[ys0:ys1, xs0:xs1] = a[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)]
    return out


def segment_coherence(S, half=4):
    """Max over 4 orientations of the along-line mean of S over ±`half` cells."""
    best = np.zeros_like(S)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        acc = S.copy(); n = 1
        for t in range(1, half + 1):
            acc += _shift(S, t * dy, t * dx) + _shift(S, -t * dy, -t * dx); n += 2
        best = np.maximum(best, acc / n)
    return best.astype(np.float32)


def surface_e2():
    """E2 (amended preregistration): dipole x segment-coherence x piedmont-setting, suppressed."""
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    lvalid = np.load(SESS / "lidar_valid.npy")
    dom = lvalid & foot & ~labels
    S1 = surface_e1()
    coh = segment_coherence(S1)
    r_dip = rank01(S1, dom & (S1 > 0))
    r_coh = rank01(coh, dom & (S1 > 0))
    base = np.sqrt(np.maximum(r_dip, 1e-4) * np.maximum(r_coh, 1e-4)).astype(np.float32)
    base[~dom] = 0.0
    # piedmont setting prior (fixed, not ledger-fitted): penalise bedrock-interior relief/slope
    r_relief = rank01(np.asarray(stack[ix["lidar_relief"]]), dom)
    r_slope = rank01(np.asarray(stack[ix["de_slope2"]]), foot & ~labels)
    setting = ((1.0 - 0.75 * r_relief) * (1.0 - 0.5 * r_slope)).astype(np.float32)
    road = np.asarray(stack[ix["road_dist_m"]])
    road_f = np.clip(np.nan_to_num(road, nan=1e4) / 300.0, 0.15, 1.0).astype(np.float32)
    adz = rank01(np.asarray(stack[ix["along_dz"]]), dom)
    contour_f = (0.6 + 0.4 * adz).astype(np.float32)
    S2 = base * setting * road_f * contour_f
    # 100 m fallback where lidar invalid: detrended-elevation ridge crests, prior-scaled 0.85
    fb_rank = rank01(np.asarray(stack[ix["de_log2"]]), foot & ~labels & ~lvalid)
    nms = P.ridge_nms(fb_rank, foot)
    fb = np.where(nms & ~lvalid & foot & ~labels, 0.85 * fb_rank * setting * road_f, 0.0).astype(np.float32)
    return np.maximum(S2, fb).astype(np.float32)


def run_experiment(tag, surface, K=40_000, spacing=2.83, full_uniq=False, avoid_quota=0.0):
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]])
    allowed = foot & ~labels & (d_cat >= SQRT5) & (surface > 0)
    # pre-placement surface check vs two densest local surfaces (density Spearman on thresholded top-100k)
    thr = np.quantile(surface[allowed], 1 - 100_000 / max(int(allowed.sum()), 1)) if allowed.any() else 0
    surf_bin = allowed & (surface >= thr)
    pre = {}
    for nm, rel in [("skarpline_union", "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
                    ("champion", ".cache/focus/GEMSDOE32.tif"),
                    ("h19_5_continuous", ".cache/upstream/x24/inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif")]:
        pre[nm] = density_spearman(surf_bin, load_float(ROOT / rel) > 0, foot)
    log(f"[{tag}] pre-placement density-Spearman vs surfaces: {pre}")
    dots = greedy_dots(surface, allowed, K, spacing)
    log(f"[{tag}] placed {int(dots.sum()):,} dots (K={K}, spacing={spacing})")
    np.save(SESS / f"{tag}_dots.npy", dots)
    ctx = HO.load_holdout_context(RAW)
    gt = V.sgmc_only_gt(foot)
    res = evaluate_candidate(tag, dots, ctx, foot, gt, comparator_subset(full=full_uniq))
    res["preplacement_density_spearman"] = pre
    (SESS / f"{tag}_result.json").write_text(json.dumps(res, indent=1, default=float))
    log(f"[{tag}] HOLDOUT-DTI={res['holdout']['pooled_dti']:.4f} CI={res['holdout']['ci95']} "
        f"control={res['strata_control']['pooled_dti']:.4f} dCI={res['strata_control']['paired_delta_ci95']}")
    log(f"[{tag}] LST projection={res['lst']['projection']:.4f} (LOO MAE {res['lst']['model_loo_mae']:.4f}) "
        f"uniq max_within3={res['uniqueness']['max_cand_within3_sparse']} worst={res['uniqueness']['worst_sparse']}")
    return res




def run_e3():
    """E3 frontier hybrid (amendment 2): 50% corridor (d_h19<=2) + 50% novel off-network, unique-forced."""
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]]); d_h = np.asarray(stack[ix["d_h19"]])
    S = np.load(SESS / "E2_surface.npy")
    champ = (load_float(ROOT / ".cache/focus/GEMSDOE32.tif") > 0) & foot
    skarp = (load_float(ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif") > 0) & foot
    d_ch = ndi.distance_transform_edt(~champ); d_sk = ndi.distance_transform_edt(~skarp)
    base_allowed = foot & ~labels & (d_cat >= SQRT5) & (S > 0)
    K, spacing = 40_000, 2.83
    # Pool B first (novel): off-network, >3px from champion and skarpline
    pool_b = base_allowed & (d_h > 2.0) & (d_ch > 3.0) & (d_sk > 3.0)
    dots_b = greedy_dots(S, pool_b, K // 2, spacing)
    near_b = ndi.distance_transform_edt(~dots_b) < spacing
    # Pool A (corridor): lidar-verified strands on/near the H19-5 network
    pool_a = base_allowed & (d_h <= 2.0) & ~near_b & ~dots_b
    dots_a = greedy_dots(S, pool_a, K - int(dots_b.sum()), spacing)
    dots = dots_a | dots_b
    log(f"[E3_hybrid] poolA(corridor)={int(dots_a.sum()):,} poolB(novel)={int(dots_b.sum()):,} total={int(dots.sum()):,}")
    log(f"[E3_hybrid] frac within3 champion={float((d_ch[dots]<=3).mean()):.3f} skarpline={float((d_sk[dots]<=3).mean()):.3f}")
    np.save(SESS / "E3_hybrid_dots.npy", dots)
    np.save(SESS / "E3_hybrid_dotsA.npy", dots_a); np.save(SESS / "E3_hybrid_dotsB.npy", dots_b)
    ctx = HO.load_holdout_context(RAW)
    gt = V.sgmc_only_gt(foot)
    res = evaluate_candidate("E3_hybrid", dots, ctx, foot, gt, comparator_subset(full=True))
    res["pools"] = {"A_corridor_dots": int(dots_a.sum()), "B_novel_dots": int(dots_b.sum()),
                    "frac_within3_champion": float((d_ch[dots] <= 3).mean()),
                    "frac_within3_skarpline": float((d_sk[dots] <= 3).mean()),
                    "frac_dh_gt2": float((d_h[dots] > 2).mean())}
    (SESS / "E3_hybrid_result.json").write_text(json.dumps(res, indent=1, default=float))
    log(f"[E3_hybrid] HOLDOUT-DTI={res['holdout']['pooled_dti']:.4f} CI={res['holdout']['ci95']} control={res['strata_control']['pooled_dti']:.4f}")
    log(f"[E3_hybrid] LST={res['lst']['projection']:.4f} uniq max_within3={res['uniqueness']['max_cand_within3_sparse']} worst={res['uniqueness']['worst_sparse']}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["fields", "canary", "lst", "e1", "e2", "e3"])
    a = ap.parse_args()
    if a.phase == "fields":
        build_fields()
    elif a.phase == "canary":
        canary()
    elif a.phase == "lst":
        lst_build()
    elif a.phase == "e1":
        run_experiment("E1_dipole", surface_e1(), K=40_000, spacing=2.83)
    elif a.phase == "e2":
        S = surface_e2()
        np.save(SESS / "E2_surface.npy", S)
        run_experiment("E2_dipole_suppressed", S, K=40_000, spacing=2.83, avoid_quota=0.60)
    elif a.phase == "e3":
        run_e3()


if __name__ == "__main__":
    main()
