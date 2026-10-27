#!/usr/bin/env python3
"""Execute the preregistered 3-experiment THCS-OOF lane end-to-end with all automated gates."""

from __future__ import annotations

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

from src.gemsw.holdout import evaluate_hide_and_recover, evaluate_sgmc_with_ci, load_holdout_context
from src.hce.uniqueness import audit as uniqueness_audit, inventory as registry_inventory, surface_gate
from src.thcs.canary import run_leakage_canaries
from src.thcs.features import BLOCK_AB_INDICES, BLOCK_A_INDICES, build_or_load_feature_cache
from src.thcs.model import run_oof_experiment
from vendor.gems57.submission_writer import write_submission


def verify_saved_geotiff_bytes(tif_path: Path, template_path: Path, labels_path: Path) -> dict:
    """Re-open saved GeoTIFF bytes from disk and verify every portal format & [0, 1] invariant."""
    with rasterio.open(template_path) as tpl:
        t_shape, t_crs, t_tr = tpl.shape, tpl.crs, tpl.transform
        foot = np.isfinite(tpl.read(1))
    with rasterio.open(labels_path) as lds:
        cat = (lds.read(1) == 1) & foot
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        count = ds.count
        dtype = ds.dtypes[0]
        shape = ds.shape
        crs = ds.crs
        tr = ds.transform
        nodata = ds.nodata

    in_f = arr[foot]
    out_f = arr[~foot]
    checks = {
        "single_band": count == 1,
        "dtype_float32": dtype == "float32",
        "shape_3730x3292": shape == (3730, 3292) and shape == t_shape,
        "crs_epsg_32611": crs is not None and crs.to_epsg() == 32611 and crs == t_crs,
        "transform_exact_100m": tr.almost_equals(t_tr, precision=1e-6),
        "all_pixels_finite_no_nan": int(np.isnan(arr).sum()) == 0,
        "all_pixels_no_inf": int(np.isinf(arr).sum()) == 0,
        "all_pixels_no_neg_sentinel": int((arr < -1e30).sum()) == 0,
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
    cache_dir = ROOT / "data" / "cache_thcs"
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    print("[1/6] Loading cached zero-catalogue features & HoldoutContext...")
    mm, foot, feat_meta = build_or_load_feature_cache(raw_dir, cache_dir)
    ctx = load_holdout_context(raw_dir)

    # Baseline Champion reference on exact same evaluator
    with rasterio.open(raw_dir / "scored" / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif") as ds:
        d28 = ds.read(1) > 0
    champ_hr = evaluate_hide_and_recover(d28, ctx, b_visible_px=2.0, name="GEMSDOE32-H33-2-B2")
    print(
        f"      Baseline GEMSDOE32 HOLDOUT-DTI = {champ_hr['pooled_dti']:.5f} "
        f"CI95={champ_hr['ci95_cluster_bootstrap']} (withheld={champ_hr['n_withheld_positives']})"
    )

    # Gate 0: Leakage canary
    canary_path = ev_dir / "thcs_leakage_canary.json"
    if canary_path.exists():
        canary = json.loads(canary_path.read_text())
    else:
        canary = run_leakage_canaries(mm, foot, feat_meta["feature_names"], ctx)
        canary_path.write_text(json.dumps(canary, indent=2))
    if not canary["all_passed"]:
        raise RuntimeError(f"Gate 0 FAILED: feature leakage detected ({canary['max_directional_auc']})")
    print(f"      Gate 0 Leakage Canary PASSED (48/48 features, max directional AUC = {canary['max_directional_auc']:.5f} <= 0.90)")

    # Experiment 1: Core cover-stratified geophysics + true tilt + float32 radiometrics + road-clean LiDAR
    hgb_base = [{
        "max_depth": 6,
        "max_iter": 210,
        "learning_rate": 0.06,
        "min_samples_leaf": 80,
        "l2_regularization": 4.0,
        "early_stopping": True,
        "validation_fraction": 0.1,
        "n_iter_no_change": 18,
    }]
    print("\n[2/6] Running Experiment E1 (Block A: 38 zero-catalogue geophysical/LiDAR/radiometric features)...")
    e1 = run_oof_experiment(
        "THCS-E1-geophys-rad-lidar",
        mm, foot, ctx,
        feat_indices=BLOCK_A_INDICES,
        hgb_configs=hgb_base,
        budgets_to_eval=[38_000],
        bg_quantile=0.70,
        gamma=1.5,
        crest_sigma=0.0,
        b_visible_px=2.0,
    )
    print(
        f"      E1 HOLDOUT-DTI = {e1['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e1['holdout']['ci95_cluster_bootstrap']]} "
        f"({e1['elapsed_sec']:.1f}s)"
    )

    # Experiment 2: Adding INGENIOUS GDR #1391 2m temperature probes, paleo-sinter/tufa, well geothermometry, vents
    print("\n[3/6] Running Experiment E2 (Block A+B: 48 features incl. GDR #1391 2m probes, sinter, thermal wells)...")
    e2 = run_oof_experiment(
        "THCS-E2-plus-gdr1391-hydrothermal",
        mm, foot, ctx,
        feat_indices=BLOCK_AB_INDICES,
        hgb_configs=hgb_base,
        budgets_to_eval=[38_000],
        bg_quantile=0.70,
        gamma=1.5,
        crest_sigma=0.0,
        b_visible_px=2.0,
    )
    print(
        f"      E2 HOLDOUT-DTI = {e2['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e2['holdout']['ci95_cluster_bootstrap']]} "
        f"delta_vs_E1={e2['holdout']['pooled_dti'] - e1['holdout']['pooled_dti']:+.5f} ({e2['elapsed_sec']:.1f}s)"
    )

    # Select stronger feature block for E3
    best_feat_indices = BLOCK_AB_INDICES if e2["holdout"]["pooled_dti"] >= e1["holdout"]["pooled_dti"] else BLOCK_A_INDICES
    hgb_ens = [
        {
            "max_depth": 7,
            "max_iter": 220,
            "learning_rate": 0.055,
            "min_samples_leaf": 70,
            "l2_regularization": 3.0,
            "early_stopping": True,
            "validation_fraction": 0.1,
            "n_iter_no_change": 18,
        },
        {
            "max_depth": 5,
            "max_iter": 200,
            "learning_rate": 0.065,
            "min_samples_leaf": 120,
            "l2_regularization": 6.0,
            "early_stopping": True,
            "validation_fraction": 0.1,
            "n_iter_no_change": 18,
        },
    ]
    print("\n[4/6] Running Experiment E3 (Dual-capacity OOF HGB ensemble + medial-crest boost + CELF budget sweep)...")
    e3 = run_oof_experiment(
        "THCS-E3-ensemble-crest-celf",
        mm, foot, ctx,
        feat_indices=best_feat_indices,
        hgb_configs=hgb_ens,
        budgets_to_eval=[34_000, 38_000, 42_000, 46_000],
        bg_quantile=0.72,
        gamma=1.55,
        crest_sigma=2.5,
        b_visible_px=2.0,
    )
    print(
        f"      E3 HOLDOUT-DTI = {e3['holdout']['pooled_dti']:.5f} "
        f"CI95={[round(x, 5) for x in e3['holdout']['ci95_cluster_bootstrap']]} "
        f"chosen_budget={e3['chosen_budget']} ({e3['elapsed_sec']:.1f}s)"
    )

    candidates = [e1, e2, e3]
    winner = max(candidates, key=lambda c: c["holdout"]["pooled_dti"])
    print(f"\n[5/6] Selected best experiment: {winner['exp_id']} (HOLDOUT-DTI = {winner['holdout']['pooled_dti']:.5f})")

    # Secondary diagnostic: off-catalogue SGMC with CI (labeled DIAGNOSTIC-PROXY-ONLY)
    sgmc_diag = evaluate_sgmc_with_ci(winner["final_dots"], ctx, name=winner["exp_id"])
    sgmc_diag_clean = {k: v for k, v in sgmc_diag.items() if not k.startswith("_")}

    # Gate 1: Frozen-registry uniqueness audit (pre-placement surface AND post-placement final dots)
    print("      Running frozen-registry uniqueness audit across all ledger, peer, comparator, and repo rasters...")
    inv_rows = registry_inventory(ROOT, foot)
    surf_gate = surface_gate(winner["full_oof_prob"], foot, inv_rows, ROOT)
    dot_audit = uniqueness_audit(winner["final_dots"], winner["full_oof_prob"], foot, inv_rows, ROOT)
    print(
        f"      Surface Gate: max|Spearman| = {surf_gate['max_abs_spearman']:.5f} (pass={surf_gate['passed']}); "
        f"Post-Placement Sparse Overlap: max = {dot_audit['U3_max_overlap_sparse']:.5f} (pass={dot_audit['U3_pass_sparse']}); "
        f"Unique Content-Aware = {dot_audit['unique_pass_content_aware']} across {dot_audit['n_comparable']} unique rasters"
    )

    # Gate 2: Write submission GeoTIFF via shared vendor/gems57/submission_writer.py & re-verify bytes
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prelim_bytes = np.packbits(winner["final_dots"].ravel()).tobytes()
    dsha8 = hashlib.sha256(prelim_bytes).hexdigest()[:8]
    sub_stem = f"wbggems3-thcs-oof-celf-{int(winner['final_dots'].sum())}d-{ts}-{dsha8}-zeros"
    sub_tif = ROOT / "submission" / f"{sub_stem}.tif"
    docs_tif = ROOT / "docs" / "thcs" / "downloads" / f"{sub_stem}.tif"
    latest_docs_tif = ROOT / "docs" / "thcs" / "downloads" / "wbggems3-thcs-oof-latest.tif"

    sub_note = (
        f"THCS-OOF: 48ch geophys+LiDAR+float32 rad+GDR1391 2m/sinter/geotherm 4-fold OOF HGB + 300m CELF ({int(winner['final_dots'].sum())}d)"
    )[:140]

    pred_f32 = winner["final_dots"].astype(np.float32)
    writer_receipt = write_submission(
        sub_tif,
        pred_f32,
        raw_dir / "sample_submission.tif",
        foot,
        note=sub_note,
        name=sub_stem,
        catalogue=ctx.labels,
    )
    docs_tif.parent.mkdir(parents=True, exist_ok=True)
    docs_tif.write_bytes(sub_tif.read_bytes())
    latest_docs_tif.write_bytes(sub_tif.read_bytes())

    byte_val = verify_saved_geotiff_bytes(
        sub_tif,
        raw_dir / "sample_submission.tif",
        raw_dir / "existing_faults.tif",
    )
    print(f"      Portal Byte Validator: passed={byte_val['passed']}, sha256={byte_val['sha256'][:16]}..., dots={byte_val['emitted_positive_pixels']:,}")

    beats_champion = winner["holdout"]["pooled_dti"] > champ_hr["pooled_dti"]
    all_gates_ok = (
        canary["all_passed"]
        and surf_gate["passed"]
        and dot_audit["unique_pass_content_aware"]
        and byte_val["passed"]
    )
    verdict = "promote" if (all_gates_ok and beats_champion) else "negative"

    # Save experiments summary + uniqueness audit + Rule 5 JSON Run Card
    exp_summary = {
        "lane": "THCS-OOF",
        "generated_utc": ts,
        "total_elapsed_sec": round(time.time() - t_start, 2),
        "baseline_champion_holdout": {
            "candidate_id": "GEMSDOE32-H33-2-B2",
            "evaluator_version": champ_hr["evaluator_version"],
            "score_label": "HOLDOUT-DTI",
            "pooled_dti": champ_hr["pooled_dti"],
            "ci95_cluster_bootstrap": champ_hr["ci95_cluster_bootstrap"],
            "n_withheld_positives": champ_hr["n_withheld_positives"],
            "organizer_confirmed_live_score": 0.2778,
        },
        "experiments": [
            {
                "exp_id": c["exp_id"],
                "n_features": c["n_features"],
                "chosen_budget": c["chosen_budget"],
                "elapsed_sec": c["elapsed_sec"],
                "score_label": "HOLDOUT-DTI",
                "evaluator_version": c["holdout"]["evaluator_version"],
                "n_withheld_positives": c["holdout"]["n_withheld_positives"],
                "pooled_dti": c["holdout"]["pooled_dti"],
                "ci95_cluster_bootstrap": c["holdout"]["ci95_cluster_bootstrap"],
                "fold_mean_dti": c["holdout"]["fold_mean_dti"],
                "per_quadrant_dti": c["holdout"]["per_quadrant_dti"],
                "budget_sweep": c["budget_sweep"],
                "celf_full_map": c["celf_full_map"],
            }
            for c in candidates
        ],
        "selected_experiment": winner["exp_id"],
        "sgmc_diagnostic_proxy": sgmc_diag_clean,
    }
    (ev_dir / "thcs_experiments.json").write_text(json.dumps(exp_summary, indent=2))

    uniq_slim = {k: v for k, v in dot_audit.items() if k != "all_rows"}
    uniq_slim["pre_placement_surface_gate"] = surf_gate
    (ev_dir / "thcs_uniqueness_audit.json").write_text(json.dumps(uniq_slim, indent=2))

    run_card = {
        "schema_version": "parallel-run-card-v1",
        "generated_utc": ts,
        "branch": "arena/f226cee3-wbggemsdoe3",
        "lane_id": "THCS-OOF",
        "selected_experiment": winner["exp_id"],
        "hypothesis": (
            "Unmapped Great Basin faults split across exposed range-front regimes (3DEP LiDAR scarps + "
            "topographic local relief + potassic K/Th & float32 gamma-ray radiometrics) and concealed "
            "alluvial/playa regimes (depth_to_base_surf > 0, where scarps vanish and blind permeable "
            "conduits manifest in DOE GDR #1391 2m temperature probes F2mDAB, paleo-sinter/travertine/tufa, "
            "well silica/cation geothermometry, shallow electrical conductivity, and true magnetic/gravity tilt edges)."
        ),
        "physical_mechanism": (
            "4-quadrant spatially blocked (1.5 km collar) zero-catalogue Out-of-Fold Histogram Gradient Boosting "
            "fusing 48 physical channels (resolving IR-20 by pairing true float32 GeoDAWN radiometric Total Count "
            "with analytic magnetic/gravity tilt derivatives and GDR #1391 hydrothermal plumes), followed by "
            "exact 300 m triangular-kernel submodular facility-location (CELF) dot placement outside the 200 m "
            "zero-credit catalogue halo."
        ),
        "named_non_fault_mimics": [
            "US-50 / I-80 / railway highway cut-and-fill embankments in 3DEP LiDAR (damped within 250 m of TIGER roads)",
            "USGS GeoDAWN E-W 200/400 m airborne flight-line leveling striping (suppressed via directional ripple notch)",
            "Circular Oligocene-Miocene caldera ring margins & flat-basin saline playa brines (filtered by linear structure-tensor anisotropy & gravity-step interaction)",
        ],
        "leakage_canary_gate": {
            "passed": canary["all_passed"],
            "n_features_tested": canary["n_features_tested"],
            "max_directional_auc": canary["max_directional_auc"],
            "threshold": canary["threshold"],
            "receipt": "evidence/thcs_leakage_canary.json",
        },
        "holdout_evaluation": {
            "score_label": "HOLDOUT-DTI",
            "evaluator_version": winner["holdout"]["evaluator_version"],
            "n_withheld_positives": winner["holdout"]["n_withheld_positives"],
            "pooled_dti": round(winner["holdout"]["pooled_dti"], 5),
            "ci95_cluster_bootstrap": [round(x, 5) for x in winner["holdout"]["ci95_cluster_bootstrap"]],
            "per_quadrant_dti": {k: round(v, 5) for k, v in winner["holdout"]["per_quadrant_dti"].items()},
            "baseline_gemsdoe32_pooled_dti": round(champ_hr["pooled_dti"], 5),
            "baseline_gemsdoe32_ci95": [round(x, 5) for x in champ_hr["ci95_cluster_bootstrap"]],
            "delta_vs_gemsdoe32": round(winner["holdout"]["pooled_dti"] - champ_hr["pooled_dti"], 5),
            "relative_lift_pct": round(100.0 * (winner["holdout"]["pooled_dti"] / champ_hr["pooled_dti"] - 1.0), 2),
        },
        "uniqueness_vs_registry": {
            "n_unique_rasters_compared": dot_audit["n_comparable"],
            "n_sparse_rasters": dot_audit["n_sparse"],
            "n_space_filling_controls": dot_audit["n_space_filling"],
            "pre_placement_surface_max_abs_spearman": surf_gate["max_abs_spearman"],
            "pre_placement_surface_passed": surf_gate["passed"],
            "post_placement_max_abs_spearman": dot_audit["U2_max_abs_spearman"],
            "post_placement_max_sparse_3px_overlap": dot_audit["U3_max_overlap_sparse"],
            "post_placement_sparse_passed": dot_audit["U3_pass_sparse"],
            "exact_duplicate": dot_audit["U1_exact_duplicate"],
            "space_filling_max_excess_over_null": dot_audit["U3_space_filling_max_excess"],
            "literal_all_rasters_reading": dot_audit["verdict"]["literal_reading"],
            "content_aware_reading": dot_audit["verdict"]["content_aware_reading"],
            "top5_sparse_overlaps": [r for r in dot_audit["top10_by_overlap"] if r["cls"] == "sparse"][:5],
            "receipt": "evidence/thcs_uniqueness_audit.json",
        },
        "artifact": {
            "submission_tif": str(sub_tif.relative_to(ROOT)),
            "submission_zip": str(sub_tif.with_suffix(".zip").relative_to(ROOT)),
            "docs_download_tif": str(docs_tif.relative_to(ROOT)),
            "docs_latest_alias": str(latest_docs_tif.relative_to(ROOT)),
            "raster_sha256": byte_val["sha256"],
            "emitted_dots": byte_val["emitted_positive_pixels"],
            "submission_name": sub_stem,
            "submission_note_140c": sub_note,
            "submission_note_len": len(sub_note),
        },
        "validator_output": byte_val,
        "writer_receipt": writer_receipt,
        "experiments_used": 3,
        "experiment_budget_max": 3,
        "verdict": verdict,
        "status_banner": "OK TO DOWNLOAD & SUBMIT (ALL AUTOMATED GATES PASSED)" if verdict == "promote" else "DO NOT SUBMIT (NEGATIVE / GATE FAILURE)",
    }
    (ev_dir / "thcs_run_card.json").write_text(json.dumps(run_card, indent=2))
    docs_data = ROOT / "docs" / "thcs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    (docs_data / "thcs_run_card.json").write_text(json.dumps(run_card, indent=2))

    print(f"\n[6/6] COMPLETE! Verdict = {verdict.upper()} | Banner = {run_card['status_banner']}")
    print(f"      Artifact: {run_card['artifact']['submission_tif']}")
    print(f"      Note ({len(sub_note)}/140 chars): {sub_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
