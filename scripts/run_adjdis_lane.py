#!/usr/bin/env python3
"""Execute the preregistered 3-experiment `ADJDIS` lane end-to-end (frozen plan:

`knowledge/preregistration-2026-10-28-adjdis.md`, written before any experiment).

Lane (single method paragraph): two-phase, fold-legal emission.
  * Phase A (`adjacency quota`): up to `s*K` dots on a Gaussian visibility-adjacency ridge
    `band(d) = exp(-0.5((d-d0)/sigma)^2)` computed ONLY from each holdout cell's visible
    catalogue (full public catalogue only at full-map export), restricted to
    `2.0 < d_vis <= 10.0 px`.
  * Phase B (`discovery`): the remaining `(1-s)*K` dots strictly at `d_vis > 10.0 px`, ranked by
    the reused FCHD zero-catalogue physical OOF posterior (`predict_oof_surfaces`).
Both phases run through the shared `celf_knapsack_allocate` (per-phase cap 0.635), the shared
evaluator `GEMSDOE32-HIDE-RECOVER-v3.0` and the shared `vendor.gems57.submission_writer`.

Experiments (budget 3/3):
  E1 `ADJDIS-E1-BAND`      : s=0.60, d0=4.0, sigma=2.5, K=38,000, Phase-B = physical E1 OOF.
  E2 `ADJDIS-E2-FUSION-GRID`: Phase-B = physical+NCM OOF; Draw-20 grid s x d0 (3x3); select on
                              Draw-20 only, verify on Draw-21.
  E3 `ADJDIS-E3-BUDGET`    : E2 winner x budget sweep {35k, 38k, 42k} on Draw-20; the single
                              selected configuration is emitted, validated, audited and carded.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.fchd.features import FEATURE_NAMES, build_or_load_static_features
from src.fchd.model import predict_oof_surfaces, run_fchd_leakage_canaries, sharpen_dti_weight
from src.fchd.registry_full import (
    audit_dots_against_full_registry,
    build_or_load_full_registry,
    celf_knapsack_allocate,
    check_surface_correlations,
    discover_all_comparator_tifs,
)
from src.gemsdoe.validation import SGMC_OFF_CATALOGUE_PX, score_from_profile
from src.gemsw.holdout import (
    DRAWS,
    ESTIMATED_LB_HIDDEN_TRUTH_PX,
    FOLDS,
    evaluate_hide_and_recover,
    evaluate_sgmc_with_ci,
    load_holdout_context,
)
from vendor.gems57.submission_writer import write_submission

from run_fchd_lane import verify_portal_geotiff_bytes  # shared byte validator, no private fork

# ------------------------------------------------------------------ frozen constants (prereg)
LANE = "ADJDIS"
BAND_D0_DEFAULT = 4.0
BAND_SIGMA = 2.5
D_INNER = 2.0          # visible-fault evaluation gate (b_visible_px), also Phase-A inner bound
D_OUTER = 10.0         # Phase-A outer bound / Phase-B inner bound (px, 100 m px => 1.0 km)
CAP = 0.635            # per-phase multi-comparator knapsack cap (FCHD-proven value)
K_DEFAULT = 38_000
GATE1_BASELINE = None  # filled by fresh measurement of the champion proxy
E2_GRID_S = (0.45, 0.60, 0.70)
E2_GRID_D0 = (3.5, 4.0, 5.0)
E3_BUDGETS = (35_000, 38_000, 42_000)
DOT_MIN, DOT_MAX = 15_000, 50_000

EV = ROOT / "evidence"
WORK = ROOT / "data" / "work"
RAW = ROOT / "data" / "raw"


def log(msg: str) -> None:
    print(msg, flush=True)


def band_of(d: np.ndarray, d0: float = BAND_D0_DEFAULT, sigma: float = BAND_SIGMA) -> np.ndarray:
    """Gaussian visibility-adjacency ridge; fold-legal because `d` is distance to VISIBLE faults."""
    d = np.asarray(d, dtype=np.float32)
    return np.exp(-0.5 * ((d - np.float32(d0)) / np.float32(sigma)) ** 2).astype(np.float32)


def sharpen_cell(cell_prob: np.ndarray, foot_sub: np.ndarray) -> np.ndarray:
    """Same per-cell sharpening contract as FCHD's allocate (bg q20, gamma 1.25)."""
    vals = cell_prob[foot_sub]
    q_bg = float(np.quantile(vals, 0.20))
    p_hi = float(np.quantile(vals, 0.9995))
    denom = max(p_hi - q_bg, 1e-6)
    w = np.power(np.clip((cell_prob - q_bg) / denom, 0.0, 1.5), 1.25).astype(np.float32)
    w[~foot_sub] = 0.0
    return w


def adjdis_allocate(
    exp_id: str,
    cell_phase_b_prob: dict[str, np.ndarray],
    full_phase_b_prob: np.ndarray,
    foot: np.ndarray,
    ctx,
    reg: dict,
    champ_hr: dict,
    s_split: float,
    d0: float,
    budgets: list[int],
    with_full: bool = True,
) -> dict:
    """Two-phase Contrarian CELF allocation (shared allocator called once per phase) with the
    same budget-mass bookkeeping, paired CI and Draw-20/21 reporting as FCHD's allocate."""
    t0 = time.time()
    cell_by_key = {c.key: c for c in ctx.cells}
    d_full = ndi.distance_transform_edt(~ctx.labels)
    a_full_mask = foot & (d_full > D_INNER) & (d_full <= D_OUTER)
    b_full_mask = foot & (d_full > D_OUTER)
    a_full_count = max(int(a_full_mask.sum()), 1)
    b_full_count = max(int(b_full_mask.sum()), 1)

    # Per-cell Phase-A eligibility/weights and Phase-B eligibility/weights (fold-legal: d_vis_sub
    # is EDT of the cell's VISIBLE catalogue only).
    phase_a: dict[str, tuple[np.ndarray, np.ndarray, tuple[slice, slice]]] = {}
    phase_b: dict[str, tuple[np.ndarray, np.ndarray, tuple[slice, slice]]] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        d_vis = cell.d_vis_sub
        a_elig = cell.active_sub & (d_vis > D_INNER) & (d_vis <= D_OUTER)
        b_elig = cell.active_sub & (d_vis > D_OUTER)
        w_a = np.where(a_elig, band_of(d_vis, d0), 0.0).astype(np.float32)
        w_b = sharpen_cell(cell_phase_b_prob[cell.key], foot[sl]) * b_elig
        phase_a[cell.key] = (w_a, a_elig, sl)
        phase_b[cell.key] = (w_b, b_elig, sl)

    budget_results: dict[int, dict] = {}
    for n_full in budgets:
        k_a_total = int(round(s_split * n_full))
        k_b_total = n_full - k_a_total
        cells_dots: dict[str, np.ndarray] = {}
        for seed in DRAWS:
            draw_cells = [cell_by_key[f"draw{seed}_fold{f}"] for f in FOLDS]
            a_cells_px = sum(int(phase_a[c.key][1].sum()) for c in draw_cells)
            b_cells_px = sum(int(phase_b[c.key][1].sum()) for c in draw_cells)
            draw_a = int(round(k_a_total * min(1.0, a_cells_px / a_full_count)))
            draw_b = int(round(k_b_total * min(1.0, b_cells_px / b_full_count)))
            a_mass = {c.key: float(phase_a[c.key][0][phase_a[c.key][1]].sum()) for c in draw_cells}
            b_mass = {c.key: float(phase_b[c.key][0][phase_b[c.key][1]].sum()) for c in draw_cells}
            a_tot = max(sum(a_mass.values()), 1e-9)
            b_tot = max(sum(b_mass.values()), 1e-9)
            for cell in draw_cells:
                w_a, elig_a, sl = phase_a[cell.key]
                w_b, elig_b, _ = phase_b[cell.key]
                k_a = int(round(draw_a * (a_mass[cell.key] / a_tot)))
                k_b = int(round(draw_b * (b_mass[cell.key] / b_tot)))
                dots = np.zeros(foot.shape, dtype=bool)
                if k_a > 0 and elig_a.any():
                    w2 = np.zeros(foot.shape, dtype=np.float32)
                    e2 = np.zeros(foot.shape, dtype=bool)
                    w2[sl], e2[sl] = w_a, elig_a
                    d_a, _ = celf_knapsack_allocate(w2, e2, foot, reg, budget_k=k_a, max_overlap_cap=CAP)
                    dots |= d_a
                if k_b > 0 and elig_b.any():
                    w2 = np.zeros(foot.shape, dtype=np.float32)
                    e2 = np.zeros(foot.shape, dtype=bool)
                    w2[sl], e2[sl] = w_b, elig_b
                    d_b, _ = celf_knapsack_allocate(w2, e2, foot, reg, budget_k=k_b, max_overlap_cap=CAP)
                    dots |= d_b
                cells_dots[cell.key] = dots[sl]

        hr = evaluate_hide_and_recover(cells_dots, ctx, b_visible_px=D_INNER, name=f"{exp_id}-N{n_full}")
        deltas = hr["_boots"] - champ_hr["_boots"]
        delta_mean = float(hr["pooled_dti"] - champ_hr["pooled_dti"])
        delta_ci95 = [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))]
        d20 = float(np.mean([hr["folds"][f"draw20_fold{f}"]["dti"] for f in FOLDS]))
        d21 = float(np.mean([hr["folds"][f"draw21_fold{f}"]["dti"] for f in FOLDS]))
        budget_results[n_full] = {
            "budget_full_map": n_full,
            "phase_split_s": s_split,
            "band_d0": d0,
            "pooled_dti": hr["pooled_dti"],
            "ci95_cluster_bootstrap": hr["ci95_cluster_bootstrap"],
            "paired_delta_vs_gemsdoe32": round(delta_mean, 6),
            "paired_delta_ci95": [round(delta_ci95[0], 6), round(delta_ci95[1], 6)],
            "draw20_mean_dti": d20,
            "draw21_mean_dti": d21,
            "per_quadrant_dti": hr["per_quadrant_dti"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "evaluator_version": hr["evaluator_version"],
            "folds": hr["folds"],
        }

    chosen_budget = max(budgets, key=lambda b: budget_results[b]["draw20_mean_dti"])

    final_dots = None
    if with_full:
        k_a_total = int(round(s_split * chosen_budget))
        k_b_total = chosen_budget - k_a_total
        w_a_full = np.where(a_full_mask, band_of(d_full, d0), 0.0).astype(np.float32)
        w_b_full = sharpen_dti_weight(full_phase_b_prob, foot) * b_full_mask
        d_a, meta_a = celf_knapsack_allocate(
            w_a_full, a_full_mask, foot, reg, budget_k=k_a_total, max_overlap_cap=CAP)
        d_b, meta_b = celf_knapsack_allocate(
            w_b_full, b_full_mask, foot, reg, budget_k=k_b_total, max_overlap_cap=CAP)
        final_dots = d_a | d_b
        full_meta = {"phase_a": meta_a, "phase_b": meta_b,
                     "k_a": k_a_total, "k_b": k_b_total,
                     "phase_a_dots": int(d_a.sum()), "phase_b_dots": int(d_b.sum())}
    else:
        full_meta = None

    return {
        "exp_id": exp_id,
        "elapsed_alloc_sec": round(time.time() - t0, 2),
        "chosen_budget": chosen_budget,
        "holdout": budget_results[chosen_budget],
        "budget_sweep": {str(k): {kk: vv for kk, vv in v.items() if kk != "folds"}
                         for k, v in budget_results.items()},
        "final_dots": final_dots,
        "full_meta": full_meta,
    }


def load_oof(exp_id: str, feat_bundle: dict, ctx, use_ncm: bool) -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    ck = WORK / f"adjdis_{exp_id}.npz"
    if ck.is_file():
        z = np.load(ck)
        return {
            "exp_id": exp_id,
            "elapsed_fit_sec": float(z["elapsed_fit_sec"]),
            "full_oof_prob": z["full_oof_prob"],
            "cell_probs": {c.key: z[f"cell_{c.key}"] for c in ctx.cells},
        }
    surf = predict_oof_surfaces(exp_id, feat_bundle, ctx, use_ncm_struct=use_ncm)
    np.savez(
        ck,
        elapsed_fit_sec=np.float32(surf["elapsed_fit_sec"]),
        full_oof_prob=surf["full_oof_prob"],
        **{f"cell_{k}": v for k, v in surf["cell_probs"].items()},
    )
    return surf


def band_canary_rows(ctx) -> list[dict]:
    """Gate-0 rows for the new adjacency-band feature (same pos/neg protocol as FCHD canary)."""
    rng = np.random.default_rng(20261028)
    pos_all, val_pos_all, neg_all, val_neg_all = [], [], [], []
    for cell in ctx.cells:
        if cell.seed != DRAWS[0]:
            continue
        sl = cell.bbox
        truth_sub = np.zeros(cell.active_sub.shape, dtype=bool)
        truth_sub[cell.truth_coords] = True
        elig = cell.active_sub & (cell.d_vis_sub > D_INNER)
        pos = truth_sub & elig
        neg = (~truth_sub) & elig
        band = band_of(cell.d_vis_sub)
        py, px = np.nonzero(pos)
        ny, nx = np.nonzero(neg)
        if ny.size == 0:
            continue
        pick = rng.choice(ny.size, size=min(40_000, ny.size), replace=False)
        val_pos_all.append(band[py, px])
        val_neg_all.append(band[ny[pick], nx[pick]])
        pos_all.append(np.ones(py.size, dtype=np.int8))
        neg_all.append(np.zeros(pick.size, dtype=np.int8))
    y = np.concatenate(pos_all + neg_all)
    v = np.concatenate(val_pos_all + val_neg_all)
    auc = float(roc_auc_score(y, v)) if np.unique(v).size > 1 else 0.5
    d_auc = max(auc, 1.0 - auc)
    return [{
        "feature": "adjacency_band(d0=4.0,sigma=2.5) from fold-visible catalogue",
        "kind": "fold_local_adjacency_band",
        "auc": round(auc, 5),
        "directional_auc": round(d_auc, 5),
        "passed": bool(d_auc <= 0.90),
    }]


def main() -> int:
    t_start = time.time()
    EV.mkdir(parents=True, exist_ok=True)

    log("[1/9] Feature stack + holdout context ...")
    feat = build_or_load_static_features()
    foot = feat["foot"]
    ctx = load_holdout_context(RAW)

    log("[2/9] Full comparator registry ...")
    reg = build_or_load_full_registry(foot)
    log(f"      scanned={reg['index']['files_scanned']} unique_masks={reg['index']['unique_dot_masks']} "
        f"sparse={reg['index']['sparse_nonlattice_masks']} continuous={reg['index']['continuous_surfaces_sampled']}")

    # Fresh champion baseline — must reproduce FCHD's 0.099202 exactly or stop.
    with rasterio.open(RAW / "scored" / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        d28 = ds.read(1) > 0
    champ_hr = evaluate_hide_and_recover(d28, ctx, b_visible_px=D_INNER, name="GEMSDOE32-H33-2-B2")
    champ_val = round(champ_hr["pooled_dti"], 6)
    if champ_val != 0.099202:
        raise RuntimeError(f"champion baseline drift: {champ_val} != 0.099202 — stop and investigate")
    log(f"      champion proxy HOLDOUT-DTI = {champ_val} "
        f"CI={[round(x, 6) for x in champ_hr['ci95_cluster_bootstrap']]} (reproduced)")

    log("[3/9] Gate 0 leakage canary (62 static + 10 NCM + new band) ...")
    canary_path = EV / "adjdis_leakage_canary.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text())
    else:
        canary = run_fchd_leakage_canaries(feat, ctx)
        band_rows = band_canary_rows(ctx)
        canary["features"] = canary["features"] + band_rows
        canary["n_features_tested"] = len(canary["features"])
        canary["max_directional_auc"] = round(max(r["directional_auc"] for r in canary["features"]), 5)
        canary["all_passed"] = all(r["passed"] for r in canary["features"])
        canary["lane"] = LANE
        canary["band_rows"] = band_rows
        canary_path.write_text(json.dumps(canary, indent=2) + "\n")
    band_row = next(r for r in canary["features"] if r["feature"].startswith("adjacency_band"))
    if not canary["all_passed"] or band_row["directional_auc"] > 0.90:
        raise RuntimeError(f"Gate 0 FAILED: band AUC={band_row['directional_auc']} "
                           f"max={canary['max_directional_auc']}")
    log(f"      Gate 0 PASSED: {canary['n_features_tested']} features, "
        f"max directional AUC = {canary['max_directional_auc']} (band = {band_row['directional_auc']})")

    log("[4/9] Physical OOF surfaces (reused FCHD trainer, checkpointed) ...")
    surf_e1 = load_oof("e1_phys", feat, ctx, use_ncm=False)
    log(f"      E1-physical fit {surf_e1['elapsed_fit_sec']:.1f}s cached")
    surf_e2 = load_oof("e2_ncm", feat, ctx, use_ncm=True)
    log(f"      E2-NCM fit {surf_e2['elapsed_fit_sec']:.1f}s cached")

    # Pre-placement surface gates: band surface, Phase-B surface, piecewise fused surface.
    d_full = ndi.distance_transform_edt(~ctx.labels)
    band_surf = np.where(foot & (d_full > D_INNER) & (d_full <= D_OUTER), band_of(d_full), 0.0).astype(np.float32)
    phys_surf = surf_e2["full_oof_prob"]
    piecewise = np.where(foot & (d_full > D_INNER) & (d_full <= D_OUTER), band_surf,
                         np.where(foot & (d_full > D_OUTER),
                                  sharpen_dti_weight(phys_surf, foot), 0.0)).astype(np.float32)
    surf_gates = {
        "band_surface": check_surface_correlations(band_surf, foot, reg),
        "phase_b_surface_ncm": check_surface_correlations(phys_surf, foot, reg),
        "piecewise_fused_surface": check_surface_correlations(piecewise, foot, reg),
    }
    surf_pass = all(g["passed_le_0p90"] for g in surf_gates.values())
    log(f"      surface gates: " + ", ".join(f"{k}={v['max_abs_spearman']:.4f}" for k, v in surf_gates.items())
        + ("" if surf_pass else "  <-- FAIL"))

    # ================================================================== EXPERIMENT 1 (1/3)
    log("[5/9] E1 (1/3): ADJDIS-E1-BAND — s=0.60 d0=4.0 K=38000, Phase-B = physical E1 ...")
    e1 = adjdis_allocate(
        "ADJDIS-E1-BAND", surf_e1["cell_probs"], surf_e1["full_oof_prob"], foot, ctx, reg, champ_hr,
        s_split=0.60, d0=BAND_D0_DEFAULT, budgets=[K_DEFAULT], with_full=True,
    )
    e1_h = e1["holdout"]
    log(f"      E1 pooled={e1_h['pooled_dti']:.5f} CI={[round(x,5) for x in e1_h['ci95_cluster_bootstrap']]} "
        f"delta={e1_h['paired_delta_vs_gemsdoe32']:+.5f} D20={e1_h['draw20_mean_dti']:.5f} "
        f"D21={e1_h['draw21_mean_dti']:.5f} dots={int(e1['final_dots'].sum()):,} "
        f"(A={e1['full_meta']['phase_a_dots']:,} B={e1['full_meta']['phase_b_dots']:,})")

    # ================================================================== EXPERIMENT 2 (2/3)
    log("[6/9] E2 (2/3): ADJDIS-E2-FUSION-GRID — Draw-20 grid s x d0 on NCM Phase-B ...")
    grid_rows = []
    best = None
    for s in E2_GRID_S:
        for d0 in E2_GRID_D0:
            probe = adjdis_allocate(
                f"ADJDIS-E2-s{int(s*100)}-d{int(d0*10)}", surf_e2["cell_probs"], surf_e2["full_oof_prob"],
                foot, ctx, reg, champ_hr, s_split=s, d0=d0, budgets=[K_DEFAULT], with_full=False,
            )
            row = {
                "s": s, "d0": d0,
                "draw20_mean_dti": round(probe["holdout"]["draw20_mean_dti"], 6),
                "draw21_mean_dti": round(probe["holdout"]["draw21_mean_dti"], 6),
                "pooled_dti": round(probe["holdout"]["pooled_dti"], 6),
            }
            grid_rows.append(row)
            if best is None or row["draw20_mean_dti"] > best["draw20_mean_dti"]:
                best = row
            log(f"      s={s} d0={d0}: D20={row['draw20_mean_dti']:.5f} D21={row['draw21_mean_dti']:.5f} "
                f"pooled={row['pooled_dti']:.5f}")
    log(f"      E2 winner on Draw-20: s={best['s']} d0={best['d0']} (D21 verify={best['draw21_mean_dti']:.5f})")

    # ================================================================== EXPERIMENT 3 (3/3)
    log("[7/9] E3 (3/3): ADJDIS-E3-BUDGET — winner x budget sweep on Draw-20, full emission ...")
    e3 = adjdis_allocate(
        "ADJDIS-E3-FINAL", surf_e2["cell_probs"], surf_e2["full_oof_prob"], foot, ctx, reg, champ_hr,
        s_split=best["s"], d0=best["d0"], budgets=list(E3_BUDGETS), with_full=True,
    )
    e3_h = e3["holdout"]
    n_dots_emit = int(e3["final_dots"].sum())
    log(f"      E3 winner K={e3['chosen_budget']}: pooled={e3_h['pooled_dti']:.5f} "
        f"CI={[round(x,5) for x in e3_h['ci95_cluster_bootstrap']]} "
        f"delta={e3_h['paired_delta_vs_gemsdoe32']:+.5f} CI_delta={e3_h['paired_delta_ci95']} "
        f"D20={e3_h['draw20_mean_dti']:.5f} D21={e3_h['draw21_mean_dti']:.5f} "
        f"dots={n_dots_emit:,} (A={e3['full_meta']['phase_a_dots']:,} B={e3['full_meta']['phase_b_dots']:,})")

    # ================================================================== gates
    log("[8/9] Gates, uniqueness audit, writer, byte validator ...")
    gate0_pass = bool(canary["all_passed"] and band_row["directional_auc"] <= 0.90)
    gate1_pass = bool(e3_h["pooled_dti"] > 0.099202 and e3_h["paired_delta_ci95"][0] > 0.0)
    gate2_pass = bool(DOT_MIN <= n_dots_emit <= DOT_MAX)

    # Registry uniqueness: shared audit on the union of both phases + direct FCHD-file measurement
    # (discover_all_comparator_tifs excludes the "wbggems3-fchd" substring by construction).
    uniq = audit_dots_against_full_registry(e3["final_dots"], foot, reg)
    fchd_files = sorted((ROOT / "submission").glob("wbggems3-fchd-*.tif")) + \
                 sorted((ROOT / "docs" / "fchd" / "downloads").glob("wbggems3-fchd-*.tif"))
    fchd_direct = []
    dots_flat = e3["final_dots"][foot]
    n_dots_flat = int(dots_flat.sum())
    seen_sha: set[str] = set()
    for p in fchd_files:
        sha_p = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha_p in seen_sha:
            continue
        seen_sha.add(sha_p)
        with rasterio.open(p) as ds:
            fchd_mask = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
        dil = ndi.binary_dilation(fchd_mask, structure=np.ones((7, 7), bool))
        ov = float(dil[foot][dots_flat].mean()) if n_dots_flat else 0.0
        fchd_direct.append({"file": str(p.relative_to(ROOT)), "sha256": sha_p,
                            "overlap_3px": round(ov, 6)})
    fchd_max = max((r["overlap_3px"] for r in fchd_direct), default=0.0)
    gate3_pass = bool(
        surf_pass
        and uniq["content_aware_all_gates_pass"]
        and uniq["U3_max_nonlattice_overlap_3px"] <= 0.70
        and not uniq["U1_exact_duplicate"]
        and fchd_max <= 0.70
    )

    # ================================================================== emit
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dsha8 = hashlib.sha256(np.packbits(e3["final_dots"][foot]).tobytes()).hexdigest()[:8]
    sub_stem = f"wbggems3-adjdis-{n_dots_emit}d-{ts}-{dsha8}"
    zeros_name = f"{sub_stem}-zeros.tif"
    sub_tif = ROOT / "submission" / zeros_name
    sub_note = (
        f"ADJDIS: fold-legal {best['d0']:.1f}px adjacency-band quota s={best['s']} + NCM physical "
        f"discovery >10px, CELF cap {CAP} ({n_dots_emit}d)"
    )[:140]

    pred_f32 = e3["final_dots"].astype(np.float32)
    writer_receipt = write_submission(
        sub_tif, pred_f32, RAW / "sample_submission.tif", foot,
        note=sub_note, name=sub_stem, catalogue=ctx.labels,
    )
    byte_val = verify_portal_geotiff_bytes(sub_tif, RAW / "sample_submission.tif", RAW / "existing_faults.tif")
    gate4_pass = bool(byte_val["passed"] and len(sub_note) <= 140)

    all_gates = gate0_pass and gate1_pass and gate2_pass and gate3_pass and gate4_pass
    verdict = "promote" if all_gates else "negative"

    docs_tif = ROOT / "docs" / "downloads" / zeros_name
    if verdict == "promote":
        docs_tif.parent.mkdir(parents=True, exist_ok=True)
        docs_tif.write_bytes(sub_tif.read_bytes())

    # Secondary diagnostics — strictly labeled ESTIMATE, never a score.
    sgmc_res = evaluate_sgmc_with_ci(e3["final_dots"], ctx, name="ADJDIS-E3-FINAL")
    sgmc_cal = sgmc_res["sgmc_prevalence_calibrated_dti"]
    loso_est = score_from_profile(
        sgmc_res["sgmc_raw_pooled_dti"], float(n_dots_emit),
        ESTIMATED_LB_HIDDEN_TRUTH_PX, n_proxy=SGMC_OFF_CATALOGUE_PX,
    )

    # ================================================================== evidence + run card
    exp_doc = {
        "schema": "adjdis-experiments-v1",
        "generated_utc": ts,
        "lane_id": LANE,
        "preregistration": "knowledge/preregistration-2026-10-28-adjdis.md",
        "total_elapsed_sec": round(time.time() - t_start, 2),
        "experiments_used": 3,
        "experiment_budget_max": 3,
        "baseline_gemsdoe32_holdout": {
            "candidate_id": "GEMSDOE32-H33-2-B2-proxy-d2.8",
            "evaluator_version": champ_hr["evaluator_version"],
            "score_label": "HOLDOUT-DTI",
            "pooled_dti": champ_val,
            "ci95_cluster_bootstrap": [round(x, 6) for x in champ_hr["ci95_cluster_bootstrap"]],
            "n_withheld_positives": champ_hr["n_withheld_positives"],
            "owner_reported_portal_score_unverified": 0.2600,
            "reproduced_fchd_value": 0.099202,
        },
        "e1": {"pooled_dti": round(e1_h["pooled_dti"], 6), "draw20": round(e1_h["draw20_mean_dti"], 6),
               "draw21": round(e1_h["draw21_mean_dti"], 6), "dots": int(e1["final_dots"].sum()),
               "phase_a_dots": e1["full_meta"]["phase_a_dots"], "phase_b_dots": e1["full_meta"]["phase_b_dots"],
               "paired_delta_ci95": e1_h["paired_delta_ci95"]},
        "e2_grid": grid_rows,
        "e2_selected_on_draw20": best,
        "e3": {"chosen_budget": e3["chosen_budget"], "s": best["s"], "d0": best["d0"],
               "pooled_dti": round(e3_h["pooled_dti"], 6),
               "ci95_cluster_bootstrap": [round(x, 6) for x in e3_h["ci95_cluster_bootstrap"]],
               "draw20": round(e3_h["draw20_mean_dti"], 6), "draw21": round(e3_h["draw21_mean_dti"], 6),
               "paired_delta_vs_gemsdoe32": e3_h["paired_delta_vs_gemsdoe32"],
               "paired_delta_ci95": e3_h["paired_delta_ci95"],
               "n_withheld_positives": e3_h["n_withheld_positives"],
               "evaluator_version": e3_h["evaluator_version"],
               "dots": n_dots_emit, "phase_a_dots": e3["full_meta"]["phase_a_dots"],
               "phase_b_dots": e3["full_meta"]["phase_b_dots"],
               "per_quadrant_dti": e3_h["per_quadrant_dti"],
               "budget_sweep": e3["budget_sweep"]},
        "surface_gates": {k: v for k, v in surf_gates.items()},
    }
    (EV / "adjdis_experiments.json").write_text(json.dumps(exp_doc, indent=2) + "\n")

    uniq_doc = dict(uniq)
    uniq_doc["pre_placement_surface_gates"] = surf_gates
    uniq_doc["fchd_direct_excluded_by_substring"] = fchd_direct
    uniq_doc["fchd_direct_max_overlap_3px"] = fchd_max
    uniq_doc["literal_dense_witness_note"] = (
        "IR-01/IR-09: registered 17GEMSDOE_E-proba (ab0a0a62...) is positive on 100% of the "
        "footprint, so the LITERAL all-registry 70% reading fails for every non-empty raster; "
        "reported, not waived."
    )
    (EV / "adjdis_uniqueness_audit.json").write_text(json.dumps(uniq_doc, indent=2) + "\n")

    run_card = {
        "schema_version": "parallel-run-card-v1",
        "generated_utc": ts,
        "branch": "arena/6984642c-wbggemsdoe3",
        "lane_id": LANE,
        "preregistration": "knowledge/preregistration-2026-10-28-adjdis.md",
        "selected_experiment": "ADJDIS-E3-FINAL",
        "hypothesis": (
            "Hidden strands cluster just beyond mapped traces: a fold-legal Gaussian visibility-"
            "adjacency ridge (peak 4 px off VISIBLE faults, support 2-10 px) reproduces the only "
            "mechanism with score-like ledger evidence (focus family 0.2449-0.2778 owner-reported) "
            "under the registry uniqueness caps, while a strictly >10 px zero-catalogue physical "
            "discovery phase recovers strands the family's 300 m kernel reach cannot touch."
        ),
        "physical_mechanism": (
            "Two-phase Contrarian submodular DTI-gain allocation through the shared 7x7-NMS CELF "
            "knapsack allocator (per-phase multi-comparator cap 0.635): Phase A places the "
            "adjacency quota on the band ridge computed only from each fold's visible catalogue; "
            "Phase B places discovery dots on the sharpened reused FCHD physical+NCM OOF posterior."
        ),
        "named_non_fault_mimics": [
            "Colluvial wedges and faceted-spur base-of-slope channel incision along range fronts "
            "(band phase: deconfounded by restricting to 2-10 px and by the visible gate).",
            "Playa-margin risers and Lake Lahontan Sehoo shoreline benches near mapped traces.",
            "Ordinary hillslopes and drainage dissection beyond 10 px (discovery phase is trained "
            "with Relief-Matched Hard-Negative Contrastive sampling from the reused FCHD stack).",
        ],
        "leakage_canary": {
            "passed": gate0_pass,
            "n_features_tested": canary["n_features_tested"],
            "max_directional_auc": canary["max_directional_auc"],
            "band_directional_auc": band_row["directional_auc"],
            "threshold": 0.90,
            "receipt": "evidence/adjdis_leakage_canary.json",
        },
        "holdout": {
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": e3_h["evaluator_version"],
            "n_withheld_positives": e3_h["n_withheld_positives"],
            "pooled_dti": round(e3_h["pooled_dti"], 6),
            "ci95_cluster_bootstrap": [round(x, 6) for x in e3_h["ci95_cluster_bootstrap"]],
            "draw20_mean_dti": round(e3_h["draw20_mean_dti"], 6),
            "draw21_mean_dti": round(e3_h["draw21_mean_dti"], 6),
            "per_quadrant_dti": e3_h["per_quadrant_dti"],
            "baseline_gemsdoe32_pooled_dti": champ_val,
            "baseline_gemsdoe32_ci95": [round(x, 6) for x in champ_hr["ci95_cluster_bootstrap"]],
            "paired_delta_vs_gemsdoe32": e3_h["paired_delta_vs_gemsdoe32"],
            "paired_delta_ci95": e3_h["paired_delta_ci95"],
            "internal_incumbent_fchd_e2_pooled_dti": 0.097024,
        },
        "diagnostic_estimates_not_confirmed_scores": {
            "evidence_warning": "ESTIMATE / PROXY ONLY — NEVER AN ORGANIZER-CONFIRMED LEADERBOARD SCORE",
            "sgmc_prevalence_calibrated_dti_estimate": round(sgmc_cal, 5),
            "loso_profile_dti_estimate": round(float(loso_est), 5),
        },
        "gates": {
            "gate0_leakage_canary": gate0_pass,
            "gate1_holdout_beats_gemsdoe32_sig": gate1_pass,
            "gate2_dot_budget_discipline": gate2_pass,
            "gate3_full_universe_uniqueness": gate3_pass,
            "gate4_portal_geotiff_0_to_1": gate4_pass,
            "all_passed": all_gates,
        },
        "uniqueness": {
            "total_files_indexed": uniq["total_files_indexed"],
            "unique_masks_compared": uniq["unique_masks_compared"],
            "sparse_nonlattice_masks_compared": uniq["sparse_masks_compared"],
            "pre_placement_max_abs_spearman": max(g["max_abs_spearman"] for g in surf_gates.values()),
            "U1_exact_duplicate": uniq["U1_exact_duplicate"],
            "U3_max_nonlattice_overlap_3px": uniq["U3_max_nonlattice_overlap_3px"],
            "U3_nonlattice_passed_le_0p70": uniq["U3_nonlattice_pass_le_0p70"],
            "U3_lattice_excess": uniq["U3_lattice_excess"],
            "fchd_direct_max_overlap_3px": fchd_max,
            "content_aware_all_gates_pass": uniq["content_aware_all_gates_pass"],
            "literal_all_files_max_overlap": uniq["literal_all_files_max_overlap"],
            "literal_dense_witness_note": uniq_doc["literal_dense_witness_note"],
            "receipt": "evidence/adjdis_uniqueness_audit.json",
        },
        "submission_name": sub_stem,
        "submission_file": zeros_name,
        "submission_path": str(sub_tif.relative_to(ROOT)),
        "docs_download_path": str(docs_tif.relative_to(ROOT)) if verdict == "promote" else None,
        "raster_sha256": byte_val["sha256"],
        "emitted_dots": n_dots_emit,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "validator_output": byte_val,
        "writer_receipt": writer_receipt,
        "experiments_used": 3,
        "experiment_budget_max": 3,
        "slots_spent": 0,
        "organizer_receipt": None,
        "selector_approval": False,
        "ok_to_download": bool(verdict == "promote"),
        "verdict": verdict,
        "verdict_scope": (
            "Method-level only. Even a promote leaves the published site decision at DO-NOT-SUBMIT "
            "until (a) the user ratifies the content-aware IR-01/IR-09 reading of the literal "
            "70%/3-px rule (the dense witness blocks every non-empty raster), and (b) a separate "
            "selector with the live weekly cap approves a real slot. No portal upload was attempted."
        ),
    }
    (EV / "adjdis_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")

    log(f"\n[9/9/COMPLETE] verdict={verdict.upper()} file={zeros_name} "
        f"sha={byte_val['sha256'][:16]}… dots={n_dots_emit:,} "
        f"HOLDOUT-DTI={e3_h['pooled_dti']:.5f} (vs champion {champ_val:.5f}, "
        f"delta CI={e3_h['paired_delta_ci95']}) "
        f"maxU3={uniq['U3_max_nonlattice_overlap_3px']:.4f} fchd_direct={fchd_max:.4f} "
        f"SGMC-Cal ESTIMATE={sgmc_cal:.4f} elapsed={time.time() - t_start:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
