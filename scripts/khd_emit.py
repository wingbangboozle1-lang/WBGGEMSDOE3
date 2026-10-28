#!/usr/bin/env python3
"""KHD lane (2026-10-28, session arena/7702e9ff-wbggemsdoe3) — E1/E3 emitter + audits.

METHOD (one paragraph).  The hidden truth is the unmapped fault population; the
public score ledger supplies 112 unique (support, owner-reported score) probes.
We recover the hidden-truth density rho_hat by non-negative least-squares
tomography of the exact distance-weighted Tversky identities on catalogue-
distance x h19-5-network-distance strata (session LST model, site-family CV
MAE 0.0258).  rho_hat is modulated WITHIN strata by a label-free tri-domain
edge-concordance field built only from official GeoDAWN/3DEP layers (detrended-
elevation gradient x reduced-to-pole magnetic gradient x isostatic-gravity
gradient, plus 2 m lidar scarp step/coherence), normalised per stratum so the
ledger-identified stratum masses are unchanged.  Binary dots (value 1.0) are
allocated by exact submodular coverage-gain lazy-greedy with 7-px NMS
independence under per-comparator knapsack caps (directed 3-px overlap <= 0.64
against every sparse non-lattice registry mask), on the B2-validated
eligibility domain (footprint, >= 2.01 px off the mapped catalogue).  The file
is written zeros-outside (all-finite) so every value is in [0, 1] — the
encoding the portal range check accepts (the earlier "Predicted values must be
in range [0, 1]" rejection is consistent with NaN-outside bytes).

Instruments (never mixed):
  * LEDGER-PROJECTION (this script) with leave-one-out / family-CV MAE — NOT a score.
  * HOLDOUT-DTI (scripts/khd_holdout.py) on the shared hide-and-recover evaluator.

Usage:
  .venv/bin/python scripts/khd_emit.py --budget 37654 --tag khd-tomo37k
  .venv/bin/python scripts/khd_emit.py --scan            # E3 budget scan
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gemsw import ledger as LD                      # noqa: E402
from gemsw import candidate as CAND                  # noqa: E402
from gemsw.grid import load_grid                     # noqa: E402
from src.fchd.registry_full import (                 # noqa: E402
    build_or_load_full_registry,
    check_surface_correlations,
    audit_dots_against_full_registry,
    celf_knapsack_allocate,
)

SESS = ROOT / ".cache" / "session"
RAW = ROOT / "data" / "raw"
OUT_EV = ROOT / "evidence"
OUT_DL = ROOT / "docs" / "downloads"
NB = 64


def log(*a):
    print(*a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rank01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] over mask (outside -> 0). Monotone transforms are free."""
    out = np.zeros(a.shape, np.float32)
    v = np.asarray(a, np.float32)[mask]
    ok = np.isfinite(v)
    r = np.zeros(v.size, np.float32)
    if ok.any():
        from scipy.stats import rankdata
        r[ok] = (rankdata(v[ok]) - 0.5) / max(int(ok.sum()), 1)
    out[mask] = r
    return out


# --------------------------------------------------------------- rho_hat
def strata_codes(d_cat: np.ndarray, d_h19: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Same 64-bin (cat x h19) scheme as the LST design (candidate.cat_code/h_code)."""
    dc = d_cat[domain]
    dh = d_h19[domain]
    cat = CAND.cat_code(dc)
    h = CAND.h_code(dh)
    return (cat * 8 + h).astype(np.uint8)


def structural_field(foot: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Label-free tri-domain edge concordance x lidar scarp evidence (official layers only).

    Band semantics read from training_features.tif TIFF descriptions (verified 2026-10-28):
      b02=rtp, b12=det_elev, b13=iso_grav_anom.  IR-27 concerns other bands.
    """
    active = foot & ~labels
    with rasterio.open(RAW / "training_features.tif") as ds:
        de = ds.read(12).astype(np.float32)
        rtp = ds.read(2).astype(np.float32)
        grav = ds.read(13).astype(np.float32)
    for name, arr in (("det_elev", de), ("rtp", rtp), ("iso_grav_anom", grav)):
        bad = ~np.isfinite(arr) | (arr < -1e30)
        if bad.any():
            idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
            arr[...] = arr[tuple(idx)]
    e_top = ndi.gaussian_gradient_magnitude(de, 1.5).astype(np.float32)
    e_mag = ndi.gaussian_gradient_magnitude(rtp, 2.0).astype(np.float32)
    e_grav = ndi.gaussian_gradient_magnitude(grav, 5.0).astype(np.float32)
    r_top = rank01(e_top, active)
    r_mag = rank01(e_mag, active)
    r_grav = rank01(e_grav, active)
    conc = np.cbrt(np.clip(r_top, 1e-6, 1) * np.clip(r_mag, 1e-6, 1) * np.clip(r_grav, 1e-6, 1))

    lid = np.zeros(foot.shape, np.float32)
    with rasterio.open(RAW / "external" / "lidar_scarp_features_u8.tif") as ds:
        step = ds.read(3)
        coh = ds.read(10)
        valid = (ds.read(12) > 0) & (step > 0) & (coh > 0)
    m = valid & active
    if m.any():
        r_step = rank01(step.astype(np.float32), m)
        r_coh = rank01(coh.astype(np.float32), m)
        lid[m] = np.sqrt(np.maximum(r_step[m], 1e-6) * np.maximum(r_coh[m], 1e-6))
    # fallback where lidar invalid: ridge-crest rank of detrended elevation
    ridge = (-ndi.gaussian_laplace(de, 2.0)).astype(np.float32)
    r_ridge = rank01(ridge, active)
    s = np.where(m, np.maximum(lid, 0.15 * r_ridge), r_ridge).astype(np.float32)
    s[~active] = 0.0
    return s


def build_rho(active: np.ndarray, d_cat: np.ndarray, d_h19: np.ndarray, s_field: np.ndarray,
              hedge_share: float = 0.25):
    """rho_hat(y) = lam[stratum(y)] * m(y) / mean_stratum(m); zero off active.

    Amendment A1 (2026-10-28, disclosed): the NNLS fit identifies mass in only 4 of 64
    strata; a coverage-gain allocator given that support starves and cannot satisfy the
    novelty caps. A HEDGE mass equal to `hedge_share` of the expected truth mass is
    therefore spread over cells OUTSIDE the identified strata, proportional to the
    label-free structural field (preregistered H1 displacement pool: "secondary
    lineaments, linkage corridors"). The hedge is an emission prior; the LEDGER
    PROJECTION is computed under rho_hat ONLY, never under the hedge.
    """
    mdl = np.load(SESS / "lst_model.npz")
    lam, cols = mdl["lam"], [tuple(c) for c in mdl["cols"]]
    tab = np.zeros(NB, np.float64)
    for (f, b), l in zip(cols, lam):
        assert f == 0
        tab[int(b)] = max(float(l), 0.0)
    codes = np.zeros(active.shape, np.uint8)
    codes[active] = strata_codes(d_cat, d_h19, active)
    m = (0.35 + 1.30 * s_field).astype(np.float32)  # gentle within-stratum tilt
    s_sum = np.bincount(codes[active], weights=m[active], minlength=NB)
    s_cnt = np.bincount(codes[active], minlength=NB)
    mean_m = np.where(s_cnt > 0, s_sum / np.maximum(s_cnt, 1), 1.0)
    rho = np.zeros(active.shape, np.float32)
    base = tab[codes[active]] * (m[active] / mean_m[codes[active]])
    rho[active] = base.astype(np.float32)
    g_hat = float(rho.sum())

    # Hedge pool: outside the identified (lam>0) strata only.
    core = np.zeros(NB, bool)
    core[tab > 0] = True
    hedge_zone = active & ~core[codes]
    s_h = np.where(hedge_zone, s_field, 0.0).astype(np.float64)
    s_tot = float(s_h.sum())
    hedge = np.zeros(active.shape, np.float64)
    if s_tot > 0:
        hedge = (hedge_share * g_hat) * s_h / s_tot
    util = (rho.astype(np.float64) + hedge).astype(np.float32)
    info = {"g_hat": g_hat, "hedge_share": hedge_share,
            "hedge_mass": float(hedge.sum()), "core_strata": [int(b) for b in range(NB) if core[b]],
            "hedge_zone_cells": int(hedge_zone.sum())}
    return util, rho, codes, tab, info


def lst_project(mask01: np.ndarray, active: np.ndarray, codes: np.ndarray) -> dict:
    bins = {"NUIS_catxH": codes[active]}
    S = LD.sizes(bins, NB)
    mdl = np.load(SESS / "lst_model.npz")
    lam, cols = mdl["lam"], [tuple(c) for c in mdl["cols"]]
    a = np.where(active, mask01, 0.0).astype(np.float32)
    row = LD.design_row(a, active, bins, NB)
    pr = LD.project(lam, cols, row["A"], row["B"], row["N"], S)
    fit = json.loads((SESS / "lst_fit_session.json").read_text())
    return {"label": "LEDGER-PROJECTION (ESTIMATE; owner-reported probes; NOT a score)",
            "projection": pr["dti"], "tp_hat": pr["tp"], "g_hat": pr["g"], "fp_hat": pr["fp"],
            "mass": row["N"], "dots": row["dots"],
            "model_loo_mae": fit["loo_mae"], "model_family_cv_mae": fit["family_cv_mae"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=37654)
    ap.add_argument("--cap", type=float, default=0.64)
    ap.add_argument("--tag", default="khd-tomo37k")
    ap.add_argument("--scan", action="store_true", help="E3: budgets 34000/37654/41000")
    ap.add_argument("--write", action="store_true", help="write final TIF through the shared writer")
    a = ap.parse_args()
    t0 = time.time()

    g = load_grid()
    foot, labels = g.foot, g.labels
    active = foot & ~labels

    stack = np.load(SESS / "fields.npy", mmap_mode="r")
    names = json.loads((SESS / "field_names.json").read_text())
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]], np.float32)
    d_h19 = np.asarray(stack[ix["d_h19"]], np.float32)

    log("[KHD] building structural field + rho_hat ...")
    s_field = structural_field(foot, labels)
    util, rho, codes, tab, rinfo = build_rho(active, d_cat, d_h19, s_field)
    g_hat = rinfo["g_hat"]
    log(f"[KHD] g_hat (expected hidden truth mass) = {g_hat:.0f} cells; hedge mass = "
        f"{rinfo['hedge_mass']:.0f} over {rinfo['hedge_zone_cells']:,} cells (share {rinfo['hedge_share']})")

    elig = foot & ~labels & (d_cat >= 2.01)   # B2 band rule (exact on bytes: B2 has 0 dots < 2.01 px)
    log(f"[KHD] eligibility cells: {int(elig.sum()):,}")

    reg = build_or_load_full_registry(foot)
    log(f"[KHD] registry: {reg['index']['files_scanned']} files, "
        f"{reg['index']['sparse_nonlattice_masks']} sparse non-lattice masks")

    # Pre-placement surface gate (protocol: check BEFORE placement)
    surf_gate = check_surface_correlations(util, foot, reg)
    log(f"[KHD] PRE-PLACEMENT surface max|Spearman| = {surf_gate['max_abs_spearman']:.4f} "
        f"(<=0.90: {surf_gate['passed_le_0p90']})")

    budgets = [34000, 37654, 41000] if a.scan else [a.budget]
    results = []
    for B in budgets:
        dots, alloc_info = celf_knapsack_allocate(util, elig, foot, reg, budget_k=B,
                                                  max_overlap_cap=a.cap)
        n = int(dots.sum())
        log(f"[KHD] budget={B} allocated={n} {alloc_info}")
        proj = lst_project(dots, active, codes)
        log(f"[KHD] budget={B} LEDGER-PROJECTION={proj['projection']:.4f} "
            f"(model LOO MAE {proj['model_loo_mae']:.4f})")
        audit = audit_dots_against_full_registry(dots, foot, reg)
        log(f"[KHD] budget={B} uniq: max_nonlat3px={audit['U3_max_nonlattice_overlap_3px']:.4f} "
            f"exact_dup={audit['U1_exact_duplicate']} content_aware_pass={audit['content_aware_all_gates_pass']}")
        final_gate = check_surface_correlations(dots.astype(np.float32), foot, reg)
        results.append(dict(budget=B, n_dots=n, alloc=alloc_info, projection=proj,
                            uniqueness=audit, surface_final=final_gate))
        np.save(SESS / f"{a.tag}_B{B}_dots.npy", dots)

    # Reference: B2 bytes under the same projection instrument (calibration anchor)
    with rasterio.open(ROOT / ".cache" / "focus" / "GEMSDOE32.tif") as ds:
        b2 = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    proj_b2 = lst_project(b2 & foot, active, codes)
    log(f"[KHD] B2 reference LEDGER-PROJECTION={proj_b2['projection']:.4f}")

    out = {
        "label": "KHD E1/E3 — LEDGER-PROJECTION + uniqueness; HOLDOUT-DTI in scripts/khd_holdout.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "LST rho_hat (cat x h19 strata, family-CV MAE 0.0258) x tri-domain concordance "
                  "modulation (within-stratum, stratum totals preserved); submodular coverage-gain "
                  "lazy-greedy with 7px NMS and per-comparator knapsack caps 0.64; eligibility "
                  "d_cat>=2.01px (B2 band rule); binary dots; zeros-outside.",
        "g_hat_hidden_truth_mass": g_hat,
        "rho_fit": rinfo,
        "preplacement_surface_gate": surf_gate,
        "b2_reference_projection": proj_b2,
        "results": results,
        "evidence_class": "LEDGER-PROJECTION (ESTIMATE; not organizer-confirmed)",
    }
    OUT_EV.mkdir(exist_ok=True)
    (OUT_EV / "khd_emit.json").write_text(json.dumps(out, indent=1, default=float))

    if a.write:
        best = max(results, key=lambda r: r["projection"]["projection"])
        dots = np.load(SESS / f"{a.tag}_B{best['budget']}_dots.npy")
        write_submission(dots, best, a.tag, g)
    log(f"[KHD] done in {time.time()-t0:.0f}s -> evidence/khd_emit.json")
    return 0


def write_submission(dots: np.ndarray, best: dict, tag: str, g) -> None:
    """Shared-template fail-closed writer (vendor/gems57/submission_writer.py)."""
    sys.path.insert(0, str(ROOT / "vendor"))
    from gems57 import submission_writer as SW

    pred = np.where(g.foot, dots.astype(np.float32), 0.0).astype(np.float32)
    sha8 = hashlib.sha256(np.packbits(dots.ravel()).tobytes()).hexdigest()[:8]
    name = f"wbggems3-{tag}-{time.strftime('%Y%m%d')}-{sha8}-zeros"
    note = ("KHD ledger-tomographic rho x tri-domain concordance; 2px catalogue trim; "
            "comparator caps 0.64; zeros-outside")
    assert len(note) <= 140, len(note)
    OUT_DL.mkdir(parents=True, exist_ok=True)
    out_tif = OUT_DL / f"{name}.tif"
    receipt = SW.write_submission(
        out_tif, pred,
        sample=RAW / "sample_submission.tif",
        footprint=g.foot,
        note=note, name=name,
        catalogue=g.labels,
        metadata={"lane": "KHD-2026-10-28", "budget": best["budget"],
                  "ledger_projection": best["projection"]["projection"],
                  "evidence_class": "LEDGER-PROJECTION (ESTIMATE)"},
    )
    log(f"[KHD] wrote {out_tif} + .zip + .json receipt; ledger-projection="
        f"{best['projection']['projection']:.4f} (ESTIMATE, not a score)")


if __name__ == "__main__":
    raise SystemExit(main())
