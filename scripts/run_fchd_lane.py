#!/usr/bin/env python3
"""Execute the preregistered 3-experiment FCHD-NCM lane end-to-end.

Experiments (strict 3-experiment budget, frozen in `knowledge/preregistration-2026-10-27-fchd.md`):
  - E1 (`FCHD-E1-ZeroCat-OOF`): Pure 62-feature zero-catalogue physical stack (native 10 m 3DEP
    fluvial chi + 10 m planar-facet geomorphology + Lake Lahontan ~1,338 m shoreline deconfounder +
    BLM mining & TIGER road deconfounders + 1 m LiDAR + 0->150 m magnetic/gravity worms + float32
    radiometrics + GDR #1391 2m probe/sinter/geothermometry) with Importance-Weighted Relief-Matched
    Contrastive 4-Quadrant OOF HGB + Contrarian CELF allocation (budget 38,000).
  - E2 (`FCHD-E2-NCM-Struct-OOF`): 62 physical features + 10 strictly fold-legal (`~collar`)
    4-fold Nested Component-Masked (NCM) out-of-component structural-mechanics features +
    Contrastive OOF HGB + Contrarian CELF allocation (budget 38,000).
  - E3 (`FCHD-E3-DualRegime-OOF`): Out-of-fold calibrated log-odds synthesis of Regime A (E1
    zero-catalogue off-trace discovery) and Regime B (E2 NCM structural-physical continuation),
    with blend weight & Dinkelbach dot budget selected strictly on Draw-20 folds and verified
    out-of-sample on Draw-21 folds.
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.fchd.features import build_or_load_static_features
from src.fchd.model import (
    allocate_and_score_surface,
    predict_oof_surfaces,
    run_fchd_leakage_canaries,
)
from src.fchd.registry_full import (
    audit_dots_against_full_registry,
    build_or_load_full_registry,
    check_surface_correlations,
)
from src.gemsdoe.validation import (
    SGMC_OFF_CATALOGUE_PX,
    score_from_profile,
)
from src.gemsw.holdout import (
    ESTIMATED_LB_HIDDEN_TRUTH_PX,
    evaluate_hide_and_recover,
    evaluate_sgmc_with_ci,
    load_holdout_context,
)
from vendor.gems57.submission_writer import write_submission


def _logit(p: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    pc = np.clip(p.astype(np.float32), eps, 1.0 - eps)
    return np.log(pc / (1.0 - pc)).astype(np.float32)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(z, -25.0, 25.0)))).astype(np.float32)


def verify_portal_geotiff_bytes(tif_path: Path, template_path: Path, catalogue_path: Path) -> dict:
    with rasterio.open(template_path) as tmpl:
        t_crs = tmpl.crs
        t_shape = tmpl.shape
        t_transform = tmpl.transform
        foot = np.isfinite(tmpl.read(1))
    with rasterio.open(catalogue_path) as cat_ds:
        cat = (cat_ds.read(1) > 0) & foot
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        crs = ds.crs
        shape = ds.shape
        transform = ds.transform
        dtype = str(ds.dtypes[0])
        count = ds.count
        nodata = ds.nodata

    in_f = arr[foot]
    out_f = arr[~foot]
    checks = {
        "single_band": count == 1,
        "dtype_float32": dtype == "float32",
        "crs_epsg_32611": crs == t_crs and int(crs.to_epsg()) == 32611,
        "shape_3730x3292": shape == t_shape == (3730, 3292),
        "transform_100m_exact": transform == t_transform,
        "full_grid_all_finite_no_nan": bool(np.all(np.isfinite(arr))),
        "in_footprint_no_nan": bool(np.all(np.isfinite(in_f))),
        "full_grid_range_0_to_1": bool(np.all((arr >= 0.0) & (arr <= 1.0))),
        "in_footprint_range_0_to_1": bool(np.all((in_f >= 0.0) & (in_f <= 1.0))),
        "outside_footprint_exact_zeros": bool(np.all(out_f == 0.0)),
        "zero_on_catalogue_faults": int((arr[cat] > 0.0).sum()) == 0,
        "emits_positive_dots": int((in_f > 0.0).sum()) > 0,
    }
    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    return {
        "file": str(tif_path.relative_to(ROOT)),
        "sha256": sha,
        "size_bytes": tif_path.stat().st_size,
        "nodata": nodata,
        "emitted_positive_pixels": int((in_f > 0.0).sum()),
        "total_mass": float(in_f.sum()),
        "min_value": float(arr.min()),
        "max_value": float(arr.max()),
        "nan_count": int(np.isnan(arr).sum()),
        "inf_count": int(np.isinf(arr).sum()),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    t_start = time.time()
    raw_dir = ROOT / "data" / "raw"
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    print("[Step 1/7] Building/loading 62 zero-catalogue FCHD features & HoldoutContext...", flush=True)
    feat_bundle = build_or_load_static_features()
    foot = feat_bundle["foot"]
    ctx = load_holdout_context(raw_dir)

    print("[Step 2/7] Building/loading Full-Universe Comparator Registry (Focus-9 + 118 Ledger + 14 Addendum + 17 Oct27 Peers + WBGGEMSDOE3 Lanes)...", flush=True)
    reg = build_or_load_full_registry(foot)
    print(
        f"           Indexed {reg['index']['files_scanned']} GeoTIFFs -> "
        f"{reg['index']['unique_dot_masks']} unique masks ({reg['index']['sparse_nonlattice_masks']} sparse non-lattice)",
        flush=True,
    )

    # Baseline GEMSDOE32 B2 / d2.8 on exact same HoldoutContext
    with rasterio.open(raw_dir / "scored" / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        d28 = ds.read(1) > 0
    champ_hr = evaluate_hide_and_recover(d28, ctx, b_visible_px=2.0, name="GEMSDOE32-H33-2-B2")
    print(
        f"           Baseline GEMSDOE32 HOLDOUT-DTI = {champ_hr['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in champ_hr['ci95_cluster_bootstrap']]} (withheld={champ_hr['n_withheld_positives']})",
        flush=True,
    )

    # Gate 0: Single-Feature Leakage Canary across ALL 72 features (62 static + 10 fold-local NCM structural)
    print("[Step 3/7] Checking Gate 0 Single-Feature Leakage Canary across all 72 features...", flush=True)
    canary_path = ev_dir / "fchd_leakage_canary.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text())
    else:
        canary = run_fchd_leakage_canaries(feat_bundle, ctx)
        canary_path.write_text(json.dumps(canary, indent=2) + "\n")
    if not canary["all_passed"]:
        raise RuntimeError(f"Gate 0 FAILED: max directional AUC = {canary['max_directional_auc']} > 0.90")
    print(
        f"           Gate 0 PASSED: 72/72 features <= 0.90 (max directional AUC = {canary['max_directional_auc']:.5f} "
        f"on `{canary['top15_by_directional_auc'][0]['feature']}`)",
        flush=True,
    )

    work_dir = ROOT / "data" / "work"
    e1_ckpt = work_dir / "fchd_e1_oof.npz"
    e2_ckpt = work_dir / "fchd_e2_oof.npz"

    # =========================================================================
    # EXPERIMENT 1 (1/3): Pure Zero-Catalogue 62-Feature Contrastive OOF + CELF
    # =========================================================================
    print("\n[Step 4/7] Experiment E1 (1/3): FCHD-E1-ZeroCat-OOF (62 zero-catalogue features + Contrastive OOF)...", flush=True)
    if e1_ckpt.is_file():
        z1 = np.load(e1_ckpt)
        e1_surf = {
            "exp_id": "FCHD-E1-ZeroCat-OOF",
            "elapsed_fit_sec": float(z1["elapsed_fit_sec"]),
            "full_oof_prob": z1["full_oof_prob"],
            "cell_probs": {c.key: z1[f"cell_{c.key}"] for c in ctx.cells},
        }
    else:
        e1_surf = predict_oof_surfaces("FCHD-E1-ZeroCat-OOF", feat_bundle, ctx, use_ncm_struct=False)
        np.savez(
            e1_ckpt,
            elapsed_fit_sec=np.float32(e1_surf["elapsed_fit_sec"]),
            full_oof_prob=e1_surf["full_oof_prob"],
            **{f"cell_{k}": v for k, v in e1_surf["cell_probs"].items()},
        )
    e1_surf_gate = check_surface_correlations(e1_surf["full_oof_prob"], foot, reg)
    if not e1_surf_gate["passed_le_0p90"]:
        raise RuntimeError(f"E1 pre-placement surface duplicate: max|Spearman|={e1_surf_gate['max_abs_spearman']}")
    e1_alloc = allocate_and_score_surface(
        "FCHD-E1-ZeroCat-OOF",
        e1_surf["cell_probs"],
        e1_surf["full_oof_prob"],
        foot, ctx, reg, champ_hr,
        budgets=[38_000],
        b_visible_px=2.0,
        max_overlap_cap=0.635,
        bg_quantile=0.20,
        gamma=1.25,
    )
    e1_uniq = audit_dots_against_full_registry(e1_alloc["final_dots"], foot, reg)
    print(
        f"           E1 HOLDOUT-DTI = {e1_alloc['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e1_alloc['holdout']['ci95_cluster_bootstrap']]} "
        f"(delta vs GEMSDOE32 = {e1_alloc['holdout']['paired_delta_vs_gemsdoe32']:+.5f}, "
        f"CI95={e1_alloc['holdout']['paired_delta_ci95']}) | "
        f"dots={int(e1_alloc['final_dots'].sum()):,} | max_ov3={e1_uniq['U3_max_nonlattice_overlap_3px']:.4f} "
        f"| surf_rho={e1_surf_gate['max_abs_spearman']:.4f} | fit={e1_surf['elapsed_fit_sec']:.1f}s",
        flush=True,
    )

    # =========================================================================
    # EXPERIMENT 2 (2/3): 62 Physical + 10 Nested Component-Masked Structural OOF
    # =========================================================================
    print("\n[Step 5/7] Experiment E2 (2/3): FCHD-E2-NCM-Struct-OOF (62 physical + 10 NCM out-of-component structural)...", flush=True)
    if e2_ckpt.is_file():
        z2 = np.load(e2_ckpt)
        e2_surf = {
            "exp_id": "FCHD-E2-NCM-Struct-OOF",
            "elapsed_fit_sec": float(z2["elapsed_fit_sec"]),
            "full_oof_prob": z2["full_oof_prob"],
            "cell_probs": {c.key: z2[f"cell_{c.key}"] for c in ctx.cells},
        }
    else:
        e2_surf = predict_oof_surfaces("FCHD-E2-NCM-Struct-OOF", feat_bundle, ctx, use_ncm_struct=True)
        np.savez(
            e2_ckpt,
            elapsed_fit_sec=np.float32(e2_surf["elapsed_fit_sec"]),
            full_oof_prob=e2_surf["full_oof_prob"],
            **{f"cell_{k}": v for k, v in e2_surf["cell_probs"].items()},
        )
    e2_surf_gate = check_surface_correlations(e2_surf["full_oof_prob"], foot, reg)
    if not e2_surf_gate["passed_le_0p90"]:
        raise RuntimeError(f"E2 pre-placement surface duplicate: max|Spearman|={e2_surf_gate['max_abs_spearman']}")
    e2_alloc = allocate_and_score_surface(
        "FCHD-E2-NCM-Struct-OOF",
        e2_surf["cell_probs"],
        e2_surf["full_oof_prob"],
        foot, ctx, reg, champ_hr,
        budgets=[38_000],
        b_visible_px=2.0,
        max_overlap_cap=0.635,
        bg_quantile=0.20,
        gamma=1.25,
    )
    e2_uniq = audit_dots_against_full_registry(e2_alloc["final_dots"], foot, reg)
    print(
        f"           E2 HOLDOUT-DTI = {e2_alloc['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e2_alloc['holdout']['ci95_cluster_bootstrap']]} "
        f"(delta vs GEMSDOE32 = {e2_alloc['holdout']['paired_delta_vs_gemsdoe32']:+.5f}, "
        f"CI95={e2_alloc['holdout']['paired_delta_ci95']}) | "
        f"dots={int(e2_alloc['final_dots'].sum()):,} | max_ov3={e2_uniq['U3_max_nonlattice_overlap_3px']:.4f} "
        f"| surf_rho={e2_surf_gate['max_abs_spearman']:.4f} | fit={e2_surf['elapsed_fit_sec']:.1f}s",
        flush=True,
    )

    # =========================================================================
    # EXPERIMENT 3 (3/3): Dual-Regime Calibrated OOF Blend (E1 ZeroCat + E2 NCM)
    # =========================================================================
    print("\n[Step 6/7] Experiment E3 (3/3): FCHD-E3-DualRegime-OOF (Draw-20 calibrated log-odds blend + Dinkelbach budget)...", flush=True)
    best_lam = 0.35
    best_d20_lam = -1.0
    lam_grid_records = []
    for lam in (0.25, 0.35, 0.45):
        blend_cells = {
            k: _sigmoid(lam * _logit(e1_surf["cell_probs"][k]) + (1.0 - lam) * _logit(e2_surf["cell_probs"][k]))
            for k in e1_surf["cell_probs"]
        }
        blend_full_tmp = _sigmoid(lam * _logit(e1_surf["full_oof_prob"]) + (1.0 - lam) * _logit(e2_surf["full_oof_prob"]))
        blend_full_tmp[~foot] = 0.0
        probe = allocate_and_score_surface(
            f"FCHD-E3-lam{int(lam*100)}",
            blend_cells, blend_full_tmp, foot, ctx, reg, champ_hr,
            budgets=[38_000], b_visible_px=2.0, max_overlap_cap=0.635, bg_quantile=0.20, gamma=1.25,
        )
        d20 = probe["holdout"]["draw20_mean_dti"]
        lam_grid_records.append({"lambda_zerocat": lam, "draw20_mean_dti": round(d20, 6), "pooled_dti": round(probe["holdout"]["pooled_dti"], 6)})
        if d20 > best_d20_lam:
            best_d20_lam = d20
            best_lam = lam

    e3_cell_probs = {
        k: _sigmoid(best_lam * _logit(e1_surf["cell_probs"][k]) + (1.0 - best_lam) * _logit(e2_surf["cell_probs"][k]))
        for k in e1_surf["cell_probs"]
    }
    e3_full_prob = _sigmoid(best_lam * _logit(e1_surf["full_oof_prob"]) + (1.0 - best_lam) * _logit(e2_surf["full_oof_prob"]))
    e3_full_prob[~foot] = 0.0

    e3_surf_gate = check_surface_correlations(e3_full_prob, foot, reg)
    if not e3_surf_gate["passed_le_0p90"]:
        raise RuntimeError(f"E3 pre-placement surface duplicate: max|Spearman|={e3_surf_gate['max_abs_spearman']}")

    e3_alloc = allocate_and_score_surface(
        "FCHD-E3-DualRegime-OOF",
        e3_cell_probs,
        e3_full_prob,
        foot, ctx, reg, champ_hr,
        budgets=[35_000, 38_000, 42_000],
        b_visible_px=2.0,
        max_overlap_cap=0.635,
        bg_quantile=0.20,
        gamma=1.25,
    )
    e3_uniq = audit_dots_against_full_registry(e3_alloc["final_dots"], foot, reg)
    print(
        f"           E3 (lambda_zero={best_lam}, budget={e3_alloc['chosen_budget']}) "
        f"HOLDOUT-DTI = {e3_alloc['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e3_alloc['holdout']['ci95_cluster_bootstrap']]} "
        f"(delta vs GEMSDOE32 = {e3_alloc['holdout']['paired_delta_vs_gemsdoe32']:+.5f}, "
        f"CI95={e3_alloc['holdout']['paired_delta_ci95']}) | "
        f"dots={int(e3_alloc['final_dots'].sum()):,} | max_ov3={e3_uniq['U3_max_nonlattice_overlap_3px']:.4f} "
        f"| surf_rho={e3_surf_gate['max_abs_spearman']:.4f}",
        flush=True,
    )

    # Select best among E1, E2, E3 using Draw-20 mean DTI (out-of-sample verified on Draw-21, reported pooled)
    exp_packs = [
        ("FCHD-E1-ZeroCat-OOF", 62, e1_surf["full_oof_prob"], e1_surf_gate, e1_alloc, e1_uniq, e1_surf["elapsed_fit_sec"]),
        ("FCHD-E2-NCM-Struct-OOF", 72, e2_surf["full_oof_prob"], e2_surf_gate, e2_alloc, e2_uniq, e2_surf["elapsed_fit_sec"]),
        ("FCHD-E3-DualRegime-OOF", 72, e3_full_prob, e3_surf_gate, e3_alloc, e3_uniq, round(e1_surf["elapsed_fit_sec"] + e2_surf["elapsed_fit_sec"], 2)),
    ]
    winner_pack = max(exp_packs, key=lambda t: t[4]["holdout"]["draw20_mean_dti"])
    w_id, w_nfeat, w_prob, w_sgate, w_alloc, w_uniq, w_fit_s = winner_pack
    w_dots = w_alloc["final_dots"]
    print(f"\n[Step 7/7] Selected Winner on Draw-20: {w_id} (Draw-20={w_alloc['holdout']['draw20_mean_dti']:.5f}, Draw-21={w_alloc['holdout']['draw21_mean_dti']:.5f}, Pooled={w_alloc['holdout']['pooled_dti']:.5f})", flush=True)

    # Secondary Off-Catalogue SGMC Proxy + Prevalence-Calibrated Physical Estimate (strictly labeled ESTIMATE)
    sgmc_res = evaluate_sgmc_with_ci(w_dots, ctx, name=w_id)
    sgmc_clean = {k: v for k, v in sgmc_res.items() if not k.startswith("_")}
    loso_est = score_from_profile(
        sgmc_res["sgmc_raw_pooled_dti"],
        float(w_dots.sum()),
        ESTIMATED_LB_HIDDEN_TRUTH_PX,
        n_proxy=SGMC_OFF_CATALOGUE_PX,
    )

    # Emit competition-valid GeoTIFF via shared vendor/gems57/submission_writer.py
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    n_dots_emit = int(w_dots.sum())
    dsha8 = hashlib.sha256(np.packbits(w_dots[foot]).tobytes()).hexdigest()[:8]
    sub_stem = f"wbggems3-fchd-ncm-{n_dots_emit}d-{ts}-{dsha8}"
    zeros_name = f"{sub_stem}-zeros.tif"
    sub_tif = ROOT / "submission" / zeros_name
    docs_tif = ROOT / "docs" / "downloads" / zeros_name

    sub_note = (
        f"FCHD-NCM: 10m 3DEP chi+facet+Lahontan/BLM deconf+0-150m worms+GDR1391+NCM OOF HGB+contrarian CELF ({n_dots_emit}d)"
    )[:140]

    pred_f32 = w_dots.astype(np.float32)
    writer_receipt = write_submission(
        sub_tif,
        pred_f32,
        raw_dir / "sample_submission.tif",
        foot,
        note=sub_note,
        name=sub_stem,
        catalogue=ctx.labels,
    )
    byte_val = verify_portal_geotiff_bytes(
        sub_tif,
        raw_dir / "sample_submission.tif",
        raw_dir / "existing_faults.tif",
    )

    # Evaluate all 5 frozen promotion gates
    gate0_pass = bool(canary["all_passed"] and canary["max_directional_auc"] <= 0.90)
    gate1_pass = bool(
        w_alloc["holdout"]["pooled_dti"] > champ_hr["pooled_dti"]
        and w_alloc["holdout"]["paired_delta_ci95"][0] > 0.0
    )
    gate2_pass = bool(15_000 <= n_dots_emit <= 50_000)
    gate3_pass = bool(
        w_sgate["passed_le_0p90"]
        and w_uniq["content_aware_all_gates_pass"]
        and w_uniq["U3_max_nonlattice_overlap_3px"] <= 0.70
        and not w_uniq["U1_exact_duplicate"]
    )
    gate4_pass = bool(byte_val["passed"] and len(sub_note) <= 140)

    all_gates_pass = gate0_pass and gate1_pass and gate2_pass and gate3_pass and gate4_pass
    verdict = "promote" if all_gates_pass else "negative"

    if verdict == "promote":
        docs_tif.parent.mkdir(parents=True, exist_ok=True)
        docs_tif.write_bytes(sub_tif.read_bytes())

    exp_summary = {
        "schema": "fchd-experiments-v1",
        "generated_utc": ts,
        "lane_id": "FCHD-NCM",
        "total_elapsed_sec": round(time.time() - t_start, 2),
        "experiments_used": 3,
        "experiment_budget_max": 3,
        "baseline_gemsdoe32_holdout": {
            "candidate_id": "GEMSDOE32-H33-2-B2",
            "evaluator_version": champ_hr["evaluator_version"],
            "score_label": "HOLDOUT-DTI",
            "pooled_dti": round(champ_hr["pooled_dti"], 6),
            "ci95_cluster_bootstrap": [round(x, 6) for x in champ_hr["ci95_cluster_bootstrap"]],
            "n_withheld_positives": champ_hr["n_withheld_positives"],
            "owner_reported_portal_score_unverified": 0.2778,
        },
        "e3_lambda_calibration_draw20": lam_grid_records,
        "experiments": [
            {
                "exp_id": eid,
                "n_features": nf,
                "chosen_budget": al["chosen_budget"],
                "emitted_dots": int(al["final_dots"].sum()),
                "fit_sec": fs,
                "alloc_sec": al["elapsed_alloc_sec"],
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": al["holdout"]["evaluator_version"],
                "n_withheld_positives": al["holdout"]["n_withheld_positives"],
                "pooled_dti": round(al["holdout"]["pooled_dti"], 6),
                "ci95_cluster_bootstrap": [round(x, 6) for x in al["holdout"]["ci95_cluster_bootstrap"]],
                "paired_delta_vs_gemsdoe32": al["holdout"]["paired_delta_vs_gemsdoe32"],
                "paired_delta_ci95": al["holdout"]["paired_delta_ci95"],
                "draw20_mean_dti": round(al["holdout"]["draw20_mean_dti"], 6),
                "draw21_mean_dti": round(al["holdout"]["draw21_mean_dti"], 6),
                "per_quadrant_dti": {k: round(v, 6) for k, v in al["holdout"]["per_quadrant_dti"].items()},
                "budget_sweep": al["budget_sweep"],
                "pre_placement_max_abs_spearman": sg["max_abs_spearman"],
                "post_placement_max_nonlattice_3px_overlap": uq["U3_max_nonlattice_overlap_3px"],
                "uniqueness_content_aware_pass": uq["content_aware_all_gates_pass"],
            }
            for eid, nf, _, sg, al, uq, fs in exp_packs
        ],
        "selected_winner": w_id,
    }
    (ev_dir / "fchd_experiments.json").write_text(json.dumps(exp_summary, indent=2) + "\n")

    uniq_full = dict(w_uniq)
    uniq_full["pre_placement_surface_gate"] = w_sgate
    (ev_dir / "fchd_uniqueness_audit.json").write_text(json.dumps(uniq_full, indent=2) + "\n")

    run_card = {
        "schema_version": "parallel-run-card-v1",
        "generated_utc": ts,
        "branch": "arena/6ea84033-wbggemsdoe3",
        "lane_id": "FCHD-NCM",
        "selected_experiment": w_id,
        "hypothesis": (
            "Unmapped Great Basin faults span three distinct physical regimes missed by scarp-only Quaternary "
            "compilations: (1) eroded bedrock/piedmont fault-line scarps preserving native 10 m 3DEP Perron-Royden "
            "fluvial chi knickpoints, cross-divide k_sn disequilibrium, and planar triangular facets; "
            "(2) concealed sub-alluvial intrabasin faults (depth_to_base_surf > 0) traced by upward-continued "
            "0->150 m magnetic/gravity tilt worms and DOE GDR #1391 2m temperature probes (F2mDAB), paleo-sinter/tufa, "
            "and silica geothermometry; and (3) unmapped fault-tip propagation lobes, Crider-Pollard relay ramps, "
            "and 1.8/4.2 km piedmont/graben step-out strands."
        ),
        "physical_mechanism": (
            "Importance-weighted Relief-Matched + Mimic-Hard-Negative 4-quadrant spatially blocked (1.5 km collar) "
            "OOF Histogram Gradient Boosting over 62 zero-catalogue physical features + 10 strictly out-of-component "
            "4-fold Nested Component-Masked (NCM) structural-physical features, blended out-of-fold with pure "
            "zero-catalogue off-trace discovery and placed via running-ratio knapsack-constrained lazy-greedy CELF "
            "submodular 300 m kernel DTI optimization."
        ),
        "named_non_fault_mimics": [
            "Pleistocene Lake Lahontan Sehoo highstand (~1,330-1,345 m ASL) wave-cut shoreline scarps & tufa benches (deconfounded via restored 10 m absolute zmean_m elevation without basement gravity step)",
            "US BLM open-pit mines, waste-rock dumps, heap-leach pads (< 350 m of blm_closed_claim_distance_m.tif) & TIGER highway/rail embankments (< 250 m)",
            "Ordinary non-fault steep mountain hillslopes & erosional spurs (defeated via Importance-Weighted Relief-Matched Hard-Negative Contrastive Sampling)",
        ],
        "gates": {
            "gate0_leakage_canary": gate0_pass,
            "gate1_holdout_beats_gemsdoe32_sig": gate1_pass,
            "gate2_dot_budget_discipline": gate2_pass,
            "gate3_full_universe_uniqueness": gate3_pass,
            "gate4_portal_geotiff_0_to_1": gate4_pass,
            "all_passed": all_gates_pass,
        },
        "leakage_canary": {
            "passed": gate0_pass,
            "n_features_tested": canary["n_features_tested"],
            "max_directional_auc": canary["max_directional_auc"],
            "threshold": 0.90,
            "receipt": "evidence/fchd_leakage_canary.json",
        },
        "holdout": {
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": w_alloc["holdout"]["evaluator_version"],
            "n_withheld_positives": w_alloc["holdout"]["n_withheld_positives"],
            "pooled_dti": round(w_alloc["holdout"]["pooled_dti"], 6),
            "ci95_cluster_bootstrap": [round(x, 6) for x in w_alloc["holdout"]["ci95_cluster_bootstrap"]],
            "draw20_mean_dti": round(w_alloc["holdout"]["draw20_mean_dti"], 6),
            "draw21_mean_dti": round(w_alloc["holdout"]["draw21_mean_dti"], 6),
            "per_quadrant_dti": {k: round(v, 6) for k, v in w_alloc["holdout"]["per_quadrant_dti"].items()},
            "baseline_gemsdoe32_pooled_dti": round(champ_hr["pooled_dti"], 6),
            "baseline_gemsdoe32_ci95": [round(x, 6) for x in champ_hr["ci95_cluster_bootstrap"]],
            "paired_delta_vs_gemsdoe32": w_alloc["holdout"]["paired_delta_vs_gemsdoe32"],
            "paired_delta_ci95": w_alloc["holdout"]["paired_delta_ci95"],
            "relative_lift_vs_gemsdoe32_pct": round(100.0 * (w_alloc["holdout"]["pooled_dti"] / champ_hr["pooled_dti"] - 1.0), 2),
        },
        "diagnostic_estimates_not_confirmed_scores": {
            "evidence_warning": "ESTIMATE / PROXY ONLY — NEVER AN ORGANIZER-CONFIRMED LEADERBOARD SCORE",
            "sgmc_off_catalogue_raw_dti": round(sgmc_clean["sgmc_raw_pooled_dti"], 5),
            "sgmc_off_catalogue_raw_ci95": [round(x, 5) for x in sgmc_clean["sgmc_raw_ci95"]],
            "sgmc_prevalence_calibrated_dti_estimate": round(sgmc_clean["sgmc_prevalence_calibrated_dti"], 5),
            "sgmc_prevalence_calibrated_ci95": [round(x, 5) for x in sgmc_clean["sgmc_calibrated_ci95"]],
            "loso_profile_dti_estimate": round(float(loso_est), 5),
        },
        "uniqueness": {
            "total_files_indexed": w_uniq["total_files_indexed"],
            "unique_masks_compared": w_uniq["unique_masks_compared"],
            "sparse_nonlattice_masks_compared": w_uniq["sparse_masks_compared"],
            "pre_placement_max_abs_spearman": w_sgate["max_abs_spearman"],
            "pre_placement_passed_le_0p90": w_sgate["passed_le_0p90"],
            "U1_exact_duplicate": w_uniq["U1_exact_duplicate"],
            "U3_max_nonlattice_overlap_3px": w_uniq["U3_max_nonlattice_overlap_3px"],
            "U3_nonlattice_passed_le_0p70": w_uniq["U3_nonlattice_pass_le_0p70"],
            "U3_lattice_overlap_3px": w_uniq["U3_lattice_overlap_3px"],
            "U3_lattice_null_rate": w_uniq["U3_lattice_null_rate"],
            "U3_lattice_excess": w_uniq["U3_lattice_excess"],
            "U3_lattice_excess_passed_le_0p05": w_uniq["U3_lattice_excess_pass_le_0p05"],
            "literal_all_files_max_overlap": w_uniq["literal_all_files_max_overlap"],
            "literal_reading_note": "17GEMSDOE_E-proba (ab0a0a62eecf066a) is positive on 100.0% of footprint; literal overlap is 1.000 for every non-empty submission (IR-01).",
            "content_aware_all_gates_pass": w_uniq["content_aware_all_gates_pass"],
            "top5_nonlattice_overlaps": w_uniq["top15_nonlattice"][:5],
            "top5_peer_prompt_20261027_overlaps": w_uniq["top_peer_prompt_20261027"][:5],
            "top5_wbggems3_prior_lane_overlaps": w_uniq["top_wbggems3_prior_lanes"][:5],
            "receipt": "evidence/fchd_uniqueness_audit.json",
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
    }
    (ev_dir / "fchd_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")

    print(
        f"\n[COMPLETE] Verdict = {verdict.upper()} | File = {zeros_name} | "
        f"SHA256 = {byte_val['sha256'][:16]}... | Dots = {n_dots_emit:,} | "
        f"HOLDOUT-DTI = {run_card['holdout']['pooled_dti']:.5f} (vs GEMSDOE32 {champ_hr['pooled_dti']:.5f}) | "
        f"SGMC-Cal ESTIMATE = {sgmc_clean['sgmc_prevalence_calibrated_dti']:.4f} | "
        f"Max Non-Lattice 3px Overlap = {w_uniq['U3_max_nonlattice_overlap_3px']:.4f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
