#!/usr/bin/env python3
"""Run the one frozen A33-L1 analog-transfer experiment end to end.

The shared numerical evaluator and writer are pinned template snapshots. This
script adds only the lane-specific feature/model construction and orchestration.
It performs no DrivenData upload and cannot spend a weekly slot.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gemsdoe33 import (  # noqa: E402
    analog,
    analog_invariant,
    analog_novelty,
    csht_transfer,
    emission,
    grid,
    promotion,
)
from submission_writer import write_pair  # noqa: E402
from validate_submission import audit as audit_submission  # noqa: E402
from vendor.gems24_template.holdout import SegmentHoldout  # noqa: E402
from vendor.gems24_template.validator import sha256_file  # noqa: E402

EVIDENCE = ROOT / "evidence" / "a33_l1_experiment.json"
RUN_CARD = ROOT / "evidence" / "a33_l1_run_card.json"
DOCS_CARD = ROOT / "docs" / "data" / "a33_l1_run_card.json"
PREREG = ROOT / "evidence" / "analog_lane_preregistration_20261025.json"
PREREG_SHA = "fa30ed9c567a9802cd6053ff1831e18ce0556f78a1e62f9f769e812d4ad4a06d"

R2_PREREG = ROOT / "evidence" / "a33_r2_preregistration_20261026.json"
R2_PREREG_SHA = "f6144c2b6e0cd5bddb0966d9321697be3bb5a070808559a94f38eddcd2a70268"
R2_MANIFEST = ROOT / "registry" / "focus_rasters_20261026.json"
R2_MANIFEST_SHA = "6e71453c77dd4b2bbb5f1d7e36db74f6641f9a47f6ecfb87b099db21ea8f1500"
R2_EVIDENCE = ROOT / "evidence" / "a33_r2_experiment_20261026.json"
R2_UNIQUENESS = ROOT / "evidence" / "a33_r2_uniqueness_20261026.json"
R2_VALIDATOR = ROOT / "evidence" / "a33_r2_validator_20261026.json"
R2_PROMO_INPUT = ROOT / "evidence" / "a33_r2_promotion_evidence_20261026.json"
R2_PROMO_ASSESS = ROOT / "evidence" / "a33_r2_promotion_assessment_20261026.json"
R2_RUN_CARD = ROOT / "evidence" / "a33_r2_run_card_20261026.json"
R2_DOCS_CARD = ROOT / "docs" / "data" / "a33_r2_run_card_20261026.json"
R2_DATE = "20261026"

R3_PREREG = ROOT / "evidence" / "a33_r3_lchc_preregistration_20261026.json"
R3_PREREG_SHA = "bc4ecef34e3b81e19f41c9422fba60d99ed4c8a6c06eadb4617198753dd63a6e"
R3_MANIFEST = ROOT / "registry" / "focus_rasters_20261026.json"
R3_MANIFEST_SHA = "6e71453c77dd4b2bbb5f1d7e36db74f6641f9a47f6ecfb87b099db21ea8f1500"
R3_EVIDENCE = ROOT / "evidence" / "a33_r3_lchc_experiment_20261026.json"
R3_PROMO_INPUT = ROOT / "evidence" / "a33_r3_lchc_promotion_evidence_20261026.json"
R3_RUN_CARD = ROOT / "evidence" / "a33_r3_lchc_run_card_20261026.json"

FULL_DOT_BUDGET = 37_654
MIN_SPACING_PX = 2.8
CATALOGUE_EXCLUSION_PX = 2.0
BUFFER_PX = 15
DATE = "20261025"


def _json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def _verify_preregistration() -> None:
    actual = sha256_file(PREREG)
    if actual != PREREG_SHA:
        raise SystemExit(
            f"Frozen preregistration changed: {actual} != {PREREG_SHA}; refusing to run"
        )


def _restore_registry() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cache_focus_registry.py")],
        cwd=ROOT,
        check=True,
    )


def _emit(score: np.ndarray, eligible: np.ndarray, budget: int) -> np.ndarray:
    dots = emission.dot_thin(
        eligible,
        MIN_SPACING_PX,
        priority=score,
        max_dots=budget,
    )
    if int(dots.sum()) != budget:
        raise RuntimeError(f"Emission underfilled: {int(dots.sum())} != {budget}")
    return dots


def _fit_scores(
    arrays: dict[str, np.ndarray],
    masks: analog.AnalogMasks,
    domain: np.ndarray,
    train: np.ndarray,
    visible: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, np.ndarray], dict]:
    distance = distance_transform_edt(~visible)
    regional = analog_invariant.fit_regional_expert(
        arrays, train, visible, distance, seed=seed + 1
    )
    raw = analog_invariant.fit_raw_analog_expert(
        arrays, train, visible, distance, masks, seed=seed + 2
    )
    adapted = analog_invariant.fit_adapted_analog_expert(
        arrays, train, visible, distance, masks, seed=seed + 3
    )
    regional_score = analog_invariant.predict(regional, arrays, domain)
    raw_score = analog_invariant.predict(raw, arrays, domain)
    adapted_score = analog_invariant.predict(adapted, arrays, domain)
    candidate = analog_invariant.fuse(regional_score, adapted_score, domain)
    return (
        {
            "B0_raw_analog": raw_score,
            "B1_regional": regional_score,
            "A33_L1": candidate,
        },
        {
            "B0_raw_analog": raw.report,
            "B1_regional": regional.report,
            "A33_L1_adapted_expert": adapted.report,
        },
    )


def _verify_recorded() -> int:
    if not EVIDENCE.is_file() or not RUN_CARD.is_file():
        raise SystemExit("No recorded A33-L1 experiment to verify")
    evidence = json.loads(EVIDENCE.read_text())
    card = json.loads(RUN_CARD.read_text())
    artifact = ROOT / "docs" / "downloads" / card["submission"]["file"]
    checks = {
        "evidence_exists": True,
        "run_card_exists": True,
        "artifact_exists": artifact.is_file(),
        "artifact_sha256_matches": artifact.is_file()
        and sha256_file(artifact) == card["raster_sha256"],
        "preregistration_sha256_matches": sha256_file(PREREG) == PREREG_SHA,
        "recorded_verdict_matches": evidence["verdict"] == card["verdict"],
    }
    print(json.dumps({"checks": checks, "pass": all(checks.values())}, indent=2))
    return 0 if all(checks.values()) else 2


def _verify_a33_r2() -> int:
    if not R2_EVIDENCE.is_file() or not R2_RUN_CARD.is_file() or not R2_PROMO_INPUT.is_file():
        raise SystemExit("No recorded A33-R2-CSHT experiment to verify")
    evidence = json.loads(R2_EVIDENCE.read_text())
    card = json.loads(R2_RUN_CARD.read_text())
    promo_in = json.loads(R2_PROMO_INPUT.read_text())
    artifact = ROOT / "docs" / "downloads" / card["submission"]["file"]
    zip_artifact = ROOT / "docs" / "downloads" / card["submission"]["zip"]
    fmt = audit_submission(artifact, ROOT / "data" / "sample_submission.tif")
    assessment = promotion.assess(promo_in, fmt, card["raster_sha256"])
    expected_card_verdict = (
        "leakage"
        if "all_feature_canaries" in assessment["failed_gates"]
        else "duplicate"
        if (
            "surface_not_duplicate" in assessment["failed_gates"]
            or "final_dots_not_duplicate" in assessment["failed_gates"]
        )
        else assessment["verdict"]
    )
    checks = {
        "evidence_exists": True,
        "run_card_exists": True,
        "artifact_exists": artifact.is_file(),
        "zip_exists": zip_artifact.is_file(),
        "artifact_sha256_matches": artifact.is_file()
        and sha256_file(artifact) == card["raster_sha256"],
        "preregistration_sha256_matches": sha256_file(R2_PREREG) == R2_PREREG_SHA,
        "manifest_sha256_matches": sha256_file(R2_MANIFEST) == R2_MANIFEST_SHA,
        "recorded_verdict_matches_promotion_assessor": (
            evidence["verdict"] == card["verdict"] == expected_card_verdict
        ),
        "format_valid": bool(card["validator_output"]["format_valid"] and fmt.get("pass")),
    }
    print(
        json.dumps(
            {"checks": checks, "assessment": assessment, "pass": all(checks.values())},
            indent=2,
        )
    )
    return 0 if all(checks.values()) else 2


def _verify_a33_r3_lchc() -> int:
    if not R3_EVIDENCE.is_file() or not R3_RUN_CARD.is_file() or not R3_PROMO_INPUT.is_file():
        raise SystemExit("No recorded A33-R3-LCHC experiment to verify")
    evidence = json.loads(R3_EVIDENCE.read_text())
    card = json.loads(R3_RUN_CARD.read_text())
    promo_in = json.loads(R3_PROMO_INPUT.read_text())
    artifact = ROOT / "docs" / "downloads" / card["submission"]["file"]
    zip_artifact = ROOT / "docs" / "downloads" / card["submission"]["zip"]
    fmt = audit_submission(artifact, ROOT / "data" / "sample_submission.tif")
    assessment = promotion.assess(promo_in, fmt, card["raster_sha256"])
    expected_card_verdict = (
        "leakage"
        if "all_feature_canaries" in assessment["failed_gates"]
        else "duplicate"
        if (
            "surface_not_duplicate" in assessment["failed_gates"]
            or "final_dots_not_duplicate" in assessment["failed_gates"]
        )
        else assessment["verdict"]
    )
    checks = {
        "evidence_exists": True,
        "run_card_exists": True,
        "artifact_exists": artifact.is_file(),
        "zip_exists": zip_artifact.is_file(),
        "artifact_sha256_matches": artifact.is_file()
        and sha256_file(artifact) == card["raster_sha256"],
        "preregistration_sha256_matches": sha256_file(R3_PREREG) == R3_PREREG_SHA,
        "manifest_sha256_matches": sha256_file(R3_MANIFEST) == R3_MANIFEST_SHA,
        "recorded_verdict_matches_promotion_assessor": (
            evidence["verdict"] == card["verdict"] == expected_card_verdict == "negative"
        ),
        "format_valid": bool(card["validator_output"]["format_valid"] and fmt.get("pass")),
        "ok_to_submit_is_false": card["submission"]["ok_to_submit"] is False,
    }
    print(
        json.dumps(
            {"checks": checks, "assessment": assessment, "pass": all(checks.values())},
            indent=2,
        )
    )
    return 0 if all(checks.values()) else 2


def _run_a33_r2() -> int:
    if R2_EVIDENCE.exists() or R2_RUN_CARD.exists():
        raise SystemExit(
            "A33-R2-CSHT is already recorded; no rerun or post-hoc tuning allowed. "
            "Use --verify-a33-r2."
        )
    actual_prereg = sha256_file(R2_PREREG)
    if actual_prereg != R2_PREREG_SHA:
        raise SystemExit(
            f"Frozen A33-R2 preregistration modified: {actual_prereg} != {R2_PREREG_SHA}"
        )
    actual_manifest = sha256_file(R2_MANIFEST)
    if actual_manifest != R2_MANIFEST_SHA:
        raise SystemExit(
            f"Pinned 21-raster manifest modified: {actual_manifest} != {R2_MANIFEST_SHA}"
        )

    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _restore_registry()

    footprint = grid.template_footprint()
    catalogue = grid.load_labels() & footprint
    l1_arrays = analog_invariant.load_feature_arrays()
    masks = analog.build_analog_masks(footprint)
    base_arrays, contrast_arrays, hydro_dist, seed_meta = (
        csht_transfer.build_or_load_csht_features(footprint)
    )

    screen_holdout = SegmentHoldout(footprint, catalogue, buffer_px=BUFFER_PX)
    confirm_holdout = csht_transfer.DiagonalSegmentHoldout(footprint, catalogue, buffer_px=20)

    # 1. Per-feature leakage canary across ALL 34 base + 16 local-contrast channels
    print("[1/5] Leakage canaries for all 50 CSHT channels (34 base + 16 contrast)", flush=True)
    all_canary_features = {**base_arrays, **contrast_arrays}
    canary_bundle = screen_holdout.canary(all_canary_features)
    canary_rows = []
    for fname, fmeta in canary_bundle["features"].items():
        max_f = float(max(max(d["auc"], 1.0 - d["auc"]) for d in fmeta["folds"]))
        two_sided_pooled = float(max(fmeta["pooled_auc"], 1.0 - fmeta["pooled_auc"]))
        canary_rows.append(
            {
                "feature": fname,
                "max_fold_auc": max_f,
                "pooled_auc": two_sided_pooled,
                "raw_pooled_auc": float(fmeta["pooled_auc"]),
                "leakage_suspect": bool(fmeta["leakage_suspected"]),
            }
        )
    leakage_hit = not bool(canary_bundle["passed"])
    if leakage_hit:
        raise SystemExit("LEAKAGE CANARY TRIPPED (>0.90 two-sided AUC); halting A33-R2-CSHT.")

    # 2. Experiment 2 of 3: Primary quadrant-buffered-15px-v1 screen
    print("[2/5] Experiment 2/3: Primary screen (quadrant-buffered-15px-v1)", flush=True)
    n_fp = int(footprint.sum())
    screen_preds: dict[str, list[np.ndarray]] = {
        "matched_random": [],
        "B0_raw_analog": [],
        "B1_regional": [],
        "A33_R2_CSHT": [],
    }
    screen_fold_reports = []
    for fold in screen_holdout.folds:
        f_id = int(fold["id"])
        valid = fold["valid"]
        train = fold["train"]
        visible = fold["visible"]
        if (train & valid).any() or (visible & fold["truth"]).any():
            raise RuntimeError(f"Leakage invariant violated in screen fold {fold['name']}")
        d_vis = distance_transform_edt(~visible)
        eligible = valid & (d_vis > CATALOGUE_EXCLUSION_PX)
        budget = int(round(FULL_DOT_BUDGET * int(valid.sum()) / n_fp))

        rng = np.random.default_rng(20261026 + 50 * f_id)
        screen_preds["matched_random"].append(
            _emit(rng.random(footprint.shape, dtype=np.float32), eligible, budget).astype(np.uint8)
        )
        reg_m = analog_invariant.fit_regional_expert(
            l1_arrays, train, visible, d_vis, seed=20261025 + 100 * f_id + 1
        )
        raw_m = analog_invariant.fit_raw_analog_expert(
            l1_arrays, train, visible, d_vis, masks, seed=20261025 + 100 * f_id + 2
        )
        reg_s = analog_invariant.predict(reg_m, l1_arrays, valid)
        raw_s = analog_invariant.predict(raw_m, l1_arrays, valid)
        screen_preds["B1_regional"].append(_emit(reg_s, eligible, budget).astype(np.uint8))
        screen_preds["B0_raw_analog"].append(_emit(raw_s, eligible, budget).astype(np.uint8))

        csht_b = csht_transfer.fit_csht_models(
            base_arrays,
            contrast_arrays,
            hydro_dist,
            train,
            visible,
            d_vis,
            seed=20261026 + 1000 * f_id,
        )
        csht_s = csht_transfer.predict_csht_surface(csht_b, base_arrays, contrast_arrays, valid)
        csht_dots = csht_transfer.celf_emit_300m(
            csht_s, eligible, budget, min_self_spacing_px=2.5
        )
        screen_preds["A33_R2_CSHT"].append(csht_dots.astype(np.uint8))
        screen_fold_reports.append(
            {
                "fold": fold["name"],
                "dot_budget": budget,
                "eligible_cells": int(eligible.sum()),
                "withheld_positives": int(fold["truth"].sum()),
                "csht_models": csht_b.report,
            }
        )

    screen_results = {
        name: screen_holdout.summarize(preds, ci_draws=1999)
        for name, preds in screen_preds.items()
    }
    screen_comparisons = {
        name: screen_holdout.compare_paired(
            screen_preds["A33_R2_CSHT"], screen_preds[name], ci_draws=1999, seed=20261026
        )
        for name in ("matched_random", "B0_raw_analog", "B1_regional")
    }

    print(
        f"  screen A33_R2_CSHT={screen_results['A33_R2_CSHT']['dti']:.6f} vs "
        f"B1_regional={screen_results['B1_regional']['dti']:.6f}",
        flush=True,
    )

    # 3. Experiment 3 of 3: Frozen independent diagonal-wedge-buffered-20px-confirm-v1
    print("[3/5] Experiment 3/3: Independent confirmation (diagonal-wedge-buffered-20px-confirm-v1)", flush=True)
    confirm_preds: dict[str, list[np.ndarray]] = {
        "B1_regional": [],
        "A33_R2_CSHT": [],
    }
    confirm_fold_reports = []
    for fold in confirm_holdout.folds:
        f_id = int(fold["id"])
        valid = fold["valid"]
        train = fold["train"]
        visible = fold["visible"]
        if (train & valid).any() or (visible & fold["truth"]).any():
            raise RuntimeError(f"Leakage invariant violated in confirm fold {fold['name']}")
        d_vis = distance_transform_edt(~visible)
        eligible = valid & (d_vis > CATALOGUE_EXCLUSION_PX)
        budget = int(round(FULL_DOT_BUDGET * int(valid.sum()) / n_fp))

        reg_m = analog_invariant.fit_regional_expert(
            l1_arrays, train, visible, d_vis, seed=20261026 + 300 * f_id + 1
        )
        reg_s = analog_invariant.predict(reg_m, l1_arrays, valid)
        confirm_preds["B1_regional"].append(_emit(reg_s, eligible, budget).astype(np.uint8))

        csht_b = csht_transfer.fit_csht_models(
            base_arrays,
            contrast_arrays,
            hydro_dist,
            train,
            visible,
            d_vis,
            seed=20261026 + 5000 + 1000 * f_id,
        )
        csht_s = csht_transfer.predict_csht_surface(csht_b, base_arrays, contrast_arrays, valid)
        csht_dots = csht_transfer.celf_emit_300m(
            csht_s, eligible, budget, min_self_spacing_px=2.5
        )
        confirm_preds["A33_R2_CSHT"].append(csht_dots.astype(np.uint8))
        confirm_fold_reports.append(
            {
                "fold": fold["name"],
                "dot_budget": budget,
                "eligible_cells": int(eligible.sum()),
                "withheld_positives": int(fold["truth"].sum()),
                "csht_models": csht_b.report,
            }
        )

    confirm_results = {
        name: confirm_holdout.summarize(preds, ci_draws=1999)
        for name, preds in confirm_preds.items()
    }
    confirm_vs_b1 = confirm_holdout.compare_paired(
        confirm_preds["A33_R2_CSHT"], confirm_preds["B1_regional"], ci_draws=1999, seed=20261026
    )

    print(
        f"  confirm A33_R2_CSHT={confirm_results['A33_R2_CSHT']['dti']:.6f} vs "
        f"B1_regional={confirm_results['B1_regional']['dti']:.6f}",
        flush=True,
    )

    # 4. Full-footprint deployment model, CELF-300m placement, and 21-raster uniqueness screen
    print("[4/5] Full-footprint CSHT surface, CELF-300m placement & 21-raster uniqueness", flush=True)
    d_full_cat = distance_transform_edt(~catalogue)
    full_eligible = footprint & (d_full_cat > CATALOGUE_EXCLUSION_PX)
    full_bundle = csht_transfer.fit_csht_models(
        base_arrays,
        contrast_arrays,
        hydro_dist,
        footprint,
        catalogue,
        d_full_cat,
        seed=20261026 + 9999,
    )
    full_surface = csht_transfer.predict_csht_surface(
        full_bundle, base_arrays, contrast_arrays, footprint
    )
    # True pre-placement surface level set: top FULL_DOT_BUDGET raw eligible surface pixels
    # before any spacing/thinning dot-placement operator is applied.
    elig_flat = np.flatnonzero(full_eligible)
    elig_scores = full_surface.ravel()[elig_flat]
    top_idx = elig_flat[np.argsort(-elig_scores, kind="mergesort")[:FULL_DOT_BUDGET]]
    surface_preview_dots = np.zeros(footprint.shape, dtype=bool)
    surface_preview_dots.ravel()[top_idx] = True

    final_dots = csht_transfer.celf_emit_300m(
        full_surface, full_eligible, FULL_DOT_BUDGET, min_self_spacing_px=2.5
    )

    uniq = csht_transfer.audit_uniqueness_against_manifest(
        full_surface,
        surface_preview_dots,
        final_dots,
        footprint,
        R2_MANIFEST,
        root=ROOT,
    )

    # Determine incumbent comparator ceiling (must beat both recorded 0.113244 and in-run B1_regional)
    recorded_b1 = 0.11324405875705776
    incumbent_best = float(max(screen_results["B1_regional"]["dti"], recorded_b1))
    confirm_baseline_ceil = float(max(confirm_results["B1_regional"]["dti"], recorded_b1))
    screen_vs_b1 = screen_comparisons["B1_regional"]
    screen_split_id = "quadrant-buffered-15px-v1"
    confirm_split_id = confirm_results["A33_R2_CSHT"]["split_id"]

    prelim_promote = (
        screen_results["A33_R2_CSHT"]["dti"] > incumbent_best
        and screen_vs_b1["ci95_strictly_positive"]
        and screen_vs_b1["fold_wins"] >= 3
        and confirm_results["A33_R2_CSHT"]["dti"] > confirm_baseline_ceil
        and confirm_vs_b1["ci95_strictly_positive"]
        and confirm_vs_b1["fold_wins"] >= 3
        and uniq["surface"]["passed"]
        and uniq["final_dots"]["passed"]
        and not leakage_hit
    )
    prelim_verdict = (
        "duplicate"
        if not (uniq["surface"]["passed"] and uniq["final_dots"]["passed"])
        else ("promote" if prelim_promote else "negative")
    )

    print("[5/5] GeoTIFF emission, saved-byte format audit & promotion gate check", flush=True)
    note_template = (
        "GEMS33 A33-R2-CSHT: cover+hydrothermal transfer + 300m CELF 37654d | gate "
        + ("PROMOTE" if prelim_verdict == "promote" else prelim_verdict.upper())
        + " | {cid}"
    )
    receipt = write_pair(
        final_dots.astype(np.float32),
        template=ROOT / "data" / "sample_submission.tif",
        catalogue=catalogue,
        footprint=footprint,
        outdir=ROOT / "docs" / "downloads",
        family="gemsdoe33",
        hypothesis="a33-r2-csht-transfer-37654",
        date=R2_DATE,
        note_template=note_template,
        scientific_verdict=prelim_verdict,
    )

    cand_sha = receipt["primary_zero_outside"]["sha256"]
    zero_path = ROOT / "docs" / "downloads" / receipt["primary_zero_outside"]["file"]
    fmt_audit = audit_submission(zero_path, ROOT / "data" / "sample_submission.tif")
    zval = receipt["primary_zero_outside"]["validator"]
    elapsed = round(time.monotonic() - started, 2)
    manifest_entries = json.loads(R2_MANIFEST.read_text())["rasters"]

    uniq["final_dots"]["candidate_sha256"] = cand_sha
    _json_write(R2_UNIQUENESS, uniq)
    _json_write(R2_VALIDATOR, receipt)

    evaluator_sha = sha256_file(ROOT / "vendor" / "gems24_template" / "holdout.py")
    writer_sha = sha256_file(ROOT / "vendor" / "gems24_template" / "submission.py")
    source_manifest_sha = sha256_file(ROOT / "vendor" / "gems24_template" / "SOURCE.json")
    best_sha = sha256_file(EVIDENCE)
    cache_hash_map = {
        k: sha256_file(ROOT / ".cache" / "features" / f"{k}.npy")
        for k in csht_transfer.CACHED_FEATURE_NAMES
    }
    feature_cache_digest = csht_transfer.sha256_bytes(
        json.dumps(cache_hash_map, sort_keys=True).encode("utf-8")
    )

    promo_evidence = {
        "candidate_sha256": cand_sha,
        "current_holdout_best_sha256": best_sha,
        "lane": "GEMSDOE33 analog-field and hydrothermal-conduit structural transfer",
        "shared_template": {
            "source_manifest_sha256": source_manifest_sha,
            "feature_cache_sha256": feature_cache_digest,
            "evaluator_sha256": evaluator_sha,
            "writer_sha256": writer_sha,
        },
        "screen": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": screen_results["A33_R2_CSHT"]["evaluator_version"],
            "evaluator_sha256": evaluator_sha,
            "candidate_sha256": cand_sha,
            "baseline_sha256": best_sha,
            "withheld_positives": int(
                screen_results["A33_R2_CSHT"]["n_withheld_positive_pixels"]
            ),
            "whole_segments_with_buffer": True,
            "all_catalogue_features_visible_only": True,
            "visible_faults_masked_pixel_exactly": True,
            "alpha": 0.2,
            "beta": 0.8,
            "kernel": "triangular",
            "radius_m": 300,
            "candidate_pooled_dti": float(screen_results["A33_R2_CSHT"]["dti"]),
            "baseline_pooled_dti": incumbent_best,
            "in_run_b1_regional_dti": float(screen_results["B1_regional"]["dti"]),
            "pooled_delta_ci95": [float(v) for v in screen_vs_b1["paired_delta_ci95"]],
            "ci_estimand": "pooled paired delta",
            "split_id": screen_split_id,
            "fold_wins": int(screen_vs_b1["fold_wins"]),
            "n_folds": int(screen_vs_b1["n_folds"]),
        },
        "confirmation": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": confirm_results["A33_R2_CSHT"]["evaluator_version"],
            "evaluator_sha256": evaluator_sha,
            "candidate_sha256": cand_sha,
            "baseline_sha256": best_sha,
            "withheld_positives": int(
                confirm_results["A33_R2_CSHT"]["n_withheld_positive_pixels"]
            ),
            "whole_segments_with_buffer": True,
            "all_catalogue_features_visible_only": True,
            "visible_faults_masked_pixel_exactly": True,
            "alpha": 0.2,
            "beta": 0.8,
            "kernel": "triangular",
            "radius_m": 300,
            "candidate_pooled_dti": float(confirm_results["A33_R2_CSHT"]["dti"]),
            "baseline_pooled_dti": confirm_baseline_ceil,
            "in_run_confirm_b1_regional_dti": float(confirm_results["B1_regional"]["dti"]),
            "pooled_delta_ci95": [float(v) for v in confirm_vs_b1["paired_delta_ci95"]],
            "ci_estimand": "pooled paired delta",
            "split_id": confirm_split_id,
            "independent_of_screen": True,
            "frozen_before_screen_results": True,
            "fold_wins": int(confirm_vs_b1["fold_wins"]),
            "n_folds": int(confirm_vs_b1["n_folds"]),
        },
        "feature_names": [r["feature"] for r in canary_rows],
        "feature_canaries": [
            {
                "feature": r["feature"],
                "holdout_auc": float(max(r["max_fold_auc"], r["pooled_auc"])),
                "max_fold_auc": float(r["max_fold_auc"]),
                "pooled_auc": float(r["pooled_auc"]),
                "split_id": screen_split_id,
                "visible_only": True,
            }
            for r in canary_rows
        ],
        "registry_sha256": R2_MANIFEST_SHA,
        "registry_complete": True,
        "registry_raster_sha256s": [e["sha256"] for e in manifest_entries],
        "duplicates": {
            "surface": uniq["surface"],
            "final_dots": uniq["final_dots"],
        },
        "submission_note": receipt["note"],
        "experiments": 3,
        "elapsed_seconds": elapsed,
    }
    _json_write(R2_PROMO_INPUT, promo_evidence)
    assessment = promotion.assess(promo_evidence, fmt_audit, cand_sha)
    _json_write(R2_PROMO_ASSESS, assessment)

    final_verdict = (
        "duplicate"
        if not (uniq["surface"]["passed"] and uniq["final_dots"]["passed"])
        else assessment["verdict"]
    )
    eligible_for_selector = bool(assessment["eligible_for_selector"] and final_verdict == "promote")

    run_card = {
        "schema": 2,
        "campaign": "A33-R2",
        "hypothesis": (
            "A33-R2-CSHT: Cover-stratified multi-physics + INGENIOUS hydrothermal-conduit "
            "analog transfer with 300 m submodular CELF crest allocation recovers concealed "
            "and LiDAR-void fault segments better than the B1_regional incumbent."
        ),
        "mechanism": (
            "Fix shared-stack LiDAR void NaN fabrication (IR-33-LIDAR-VOID-01); fuse a "
            "34-channel regional HGB, a 24-channel topography-free basin-upweighted subsurface "
            "HGB, and a 16-channel 3 km local-contrast hydrothermal-conduit HGB trained across "
            "1,116 INGENIOUS thermal/vent cells (d_neg > 800 m) with LiDAR-void adaptive weights; "
            "allocate 37,654 dots via lazy-greedy 300 m triangular-kernel submodular coverage."
        ),
        "named_non_fault_process_that_could_mimic_it": (
            "Buried plutonic/caldera intrusive margins, Lake Lahontan paleo-shoreline benches, "
            "or stratiform volcanic-sedimentary contacts producing coincident density, magnetic, "
            "and argillic conductivity gradients without Quaternary fault slip."
        ),
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "primary_screen": {
                "evaluator_version": screen_results["A33_R2_CSHT"]["evaluator_version"],
                "split_id": screen_split_id,
                "withheld_positives": screen_results["A33_R2_CSHT"]["n_withheld_positive_pixels"],
                "candidate": screen_results["A33_R2_CSHT"]["dti"],
                "candidate_95pct_ci": screen_results["A33_R2_CSHT"]["ci95"]["interval"],
                "incumbent_b1_regional": screen_results["B1_regional"]["dti"],
                "incumbent_95pct_ci": screen_results["B1_regional"]["ci95"]["interval"],
                "recorded_a33_l1_b1_regional": recorded_b1,
                "paired_delta_vs_b1": screen_vs_b1["paired_delta_dti"],
                "paired_delta_95pct_ci": screen_vs_b1["paired_delta_ci95"],
                "fold_wins_vs_b1": f"{screen_vs_b1['fold_wins']}/{screen_vs_b1['n_folds']}",
            },
            "independent_confirmation": {
                "evaluator_version": confirm_results["A33_R2_CSHT"]["evaluator_version"],
                "split_id": confirm_split_id,
                "frozen_before_screen_results": True,
                "withheld_positives": confirm_results["A33_R2_CSHT"]["n_withheld_positive_pixels"],
                "candidate": confirm_results["A33_R2_CSHT"]["dti"],
                "candidate_95pct_ci": confirm_results["A33_R2_CSHT"]["ci95"]["interval"],
                "incumbent_b1_regional": confirm_results["B1_regional"]["dti"],
                "incumbent_95pct_ci": confirm_results["B1_regional"]["ci95"]["interval"],
                "paired_delta_vs_b1": confirm_vs_b1["paired_delta_dti"],
                "paired_delta_95pct_ci": confirm_vs_b1["paired_delta_ci95"],
                "fold_wins_vs_b1": f"{confirm_vs_b1['fold_wins']}/{confirm_vs_b1['n_folds']}",
            },
            "qualification": (
                "Mapped-catalogue whole-segment hide-and-recover proxy (HOLDOUT-DTI), NOT "
                "private organizer expert truth and NOT an ORGANIZER-CONFIRMED competition score."
            ),
        },
        "correlation_overlap_vs_registry": {
            "scope": "21 SHA-256-pinned focus-site and local GEMSDOE33 rasters (registry/focus_rasters_20261026.json)",
            "registry_sha256": R2_MANIFEST_SHA,
            "surface_max_abs_spearman": uniq["surface"]["max_abs_spearman_rho"],
            "surface_max_3px_overlap": uniq["surface"]["max_preview_fraction_within_3px"],
            "surface_passed": uniq["surface"]["passed"],
            "final_dots_max_abs_spearman": uniq["final_dots"]["max_abs_spearman_rho"],
            "final_dots_max_3px_overlap": uniq["final_dots"]["max_candidate_fraction_within_3px"],
            "final_dots_passed": uniq["final_dots"]["passed"],
        },
        "raster_sha256": cand_sha,
        "validator_output": {
            "format_valid": bool(zval["format_valid"] and fmt_audit.get("pass")),
            "hard_failures": zval["hard_failures"],
            "no_nan_inside_footprint": bool(zval["checks"]["footprint_all_finite"]["pass"]),
            "values_in_0_1": bool(zval["checks"]["footprint_range_0_1"]["pass"]),
            "whole_array_all_finite_0_1": bool(
                zval["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"]
            ),
            "crs_matches_epsg_32611": bool(zval["checks"]["crs_epsg_32611"]["pass"]),
            "shape_matches_3730x3292": bool(zval["checks"]["shape_matches_template"]["pass"]),
            "geotransform_matches_template": bool(
                zval["checks"]["geotransform_matches_template"]["pass"]
            ),
            "predicted_positive_dots": int(final_dots.sum()),
            "catalogue_overlap_dots": int((final_dots & catalogue).sum()),
        },
        "submission": {
            "name": receipt["submission_name"],
            "file": receipt["primary_zero_outside"]["file"],
            "zip": receipt["primary_zero_outside"]["zip"],
            "nan_twin": receipt["official_text_nan_outside_twin"]["file"],
            "nan_twin_zip": receipt["official_text_nan_outside_twin"]["zip"],
            "note": receipt["note"],
            "note_characters": receipt["note_characters"],
            "ok_to_download": bool(zval["format_valid"] and fmt_audit.get("pass")),
            "eligible_for_weekly_selector": eligible_for_selector,
            "ok_to_submit": False,
            "selector_notice": (
                "PROMOTE TO WEEKLY SELECTOR: all 12/12 automated scientific, confirmation, "
                "canary, uniqueness & GeoTIFF format gates PASSED; ok_to_submit remains False "
                "in automated tooling until the separate human/cross-lane weekly-slot selector runs."
                if eligible_for_selector
                else f"DO NOT SUBMIT: failed automated promotion gates {assessment['failed_gates']}."
            ),
        },
        "promotion_assessment": assessment,
        "verdict": final_verdict,
        "experiments_run": 3,
        "elapsed_seconds": elapsed,
        "submission_slots_used": 0,
    }
    _json_write(R2_RUN_CARD, run_card)
    _json_write(R2_DOCS_CARD, run_card)

    full_report = {
        "schema": 2,
        "started_utc": started_utc,
        "completed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "COMPLETED",
        "campaign": "A33-R2",
        "hypothesis_id": "A33-R2-CSHT",
        "preregistration": str(R2_PREREG.relative_to(ROOT)),
        "preregistration_sha256": R2_PREREG_SHA,
        "shared_stack_bugfix": "IR-33-LIDAR-VOID-01 (preserved 1,272,913 LiDAR void cells as lid_valid=0 and lid_*=NaN)",
        "hydrothermal_seed_metadata": seed_meta,
        "feature_canary_summary": {
            "tested_channels": len(canary_rows),
            "stop_threshold_two_sided_auc": 0.90,
            "max_pooled_auc": float(max(r["pooled_auc"] for r in canary_rows)),
            "max_fold_auc": float(max(r["max_fold_auc"] for r in canary_rows)),
            "any_leakage_suspect": leakage_hit,
            "rows": canary_rows,
        },
        "screen_fold_reports": screen_fold_reports,
        "screen_results": screen_results,
        "screen_paired_comparisons": screen_comparisons,
        "confirm_fold_reports": confirm_fold_reports,
        "confirm_results": confirm_results,
        "confirm_paired_vs_b1": confirm_vs_b1,
        "full_deployment_models": full_bundle.report,
        "uniqueness_summary": {
            "manifest": str(R2_MANIFEST.relative_to(ROOT)),
            "registry_sha256": R2_MANIFEST_SHA,
            "registry_count": len(manifest_entries),
            "surface_passed": uniq["surface"]["passed"],
            "surface_max_abs_spearman": uniq["surface"]["max_abs_spearman_rho"],
            "surface_max_3px_overlap": uniq["surface"]["max_preview_fraction_within_3px"],
            "final_dots_passed": uniq["final_dots"]["passed"],
            "final_dots_max_abs_spearman": uniq["final_dots"]["max_abs_spearman_rho"],
            "final_dots_max_3px_overlap": uniq["final_dots"]["max_candidate_fraction_within_3px"],
        },
        "submission_receipt": receipt,
        "promotion_assessment": assessment,
        "verdict": final_verdict,
        "experiments_run": 3,
        "elapsed_seconds": elapsed,
        "submission_slots_used": 0,
    }
    _json_write(R2_EVIDENCE, full_report)

    print(
        json.dumps(
            {
                "verdict": final_verdict,
                "eligible_for_selector": eligible_for_selector,
                "failed_gates": assessment["failed_gates"],
                "file": receipt["primary_zero_outside"]["file"],
                "zip": receipt["primary_zero_outside"]["zip"],
                "sha256": cand_sha,
                "screen_HOLDOUT_DTI": screen_results["A33_R2_CSHT"]["dti"],
                "screen_B1_regional": screen_results["B1_regional"]["dti"],
                "screen_paired_delta_ci95": screen_vs_b1["paired_delta_ci95"],
                "screen_fold_wins": screen_vs_b1["fold_wins"],
                "confirm_HOLDOUT_DTI": confirm_results["A33_R2_CSHT"]["dti"],
                "confirm_B1_regional": confirm_results["B1_regional"]["dti"],
                "confirm_paired_delta_ci95": confirm_vs_b1["paired_delta_ci95"],
                "confirm_fold_wins": confirm_vs_b1["fold_wins"],
                "max_final_abs_spearman": uniq["final_dots"]["max_abs_spearman_rho"],
                "max_final_3px_overlap": uniq["final_dots"]["max_candidate_fraction_within_3px"],
                "elapsed_seconds": elapsed,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recorded", action="store_true")
    parser.add_argument("--run-a33-r2", action="store_true")
    parser.add_argument("--verify-a33-r2", action="store_true")
    parser.add_argument("--verify-a33-r3-lchc", action="store_true")
    args = parser.parse_args()
    if args.verify_recorded:
        return _verify_recorded()
    if args.verify_a33_r2:
        return _verify_a33_r2()
    if args.verify_a33_r3_lchc:
        return _verify_a33_r3_lchc()
    if args.run_a33_r2:
        return _run_a33_r2()
    if EVIDENCE.exists() or RUN_CARD.exists():
        raise SystemExit(
            "A33-L1 is already recorded; no implicit rerun or tuning. Use --verify-recorded."
        )

    started = time.monotonic()
    _verify_preregistration()
    _restore_registry()
    footprint = grid.template_footprint()
    catalogue = grid.load_labels() & footprint
    arrays = analog_invariant.load_feature_arrays()
    masks = analog.build_analog_masks(footprint)
    context = SegmentHoldout(footprint, catalogue, buffer_px=BUFFER_PX)

    report: dict = {
        "schema": 1,
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "RUNNING",
        "experiment_number": 1,
        "maximum_experiments": 3,
        "submission_slots_used": 0,
        "hypothesis": "A33-L1 target-aligned, field-balanced structural transfer",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": PREREG_SHA,
        "evaluator": {
            "version": "gems-segment-pooled-v1",
            "source": "vendor/gems24_template/holdout.py",
            "source_manifest": "vendor/gems24_template/SOURCE.json",
        },
        "input_provenance": (
            "SHA-256-pinned GitHub owner mirrors; not independently organizer-authenticated"
        ),
        "feature_names": list(analog_invariant.FEATURE_NAMES),
        "feature_cache_sha256": analog_invariant.feature_source_hashes(),
        "analog_inventory": analog.analog_inventory(masks, catalogue, footprint),
        "fold_integrity": [
            {
                "fold": fold["name"],
                "withheld_positive_pixels": int(fold["truth"].sum()),
                "withheld_components": int(len(fold["hidden_component_ids"])),
                "visible_fault_pixels": int(fold["visible"].sum()),
                "training_pixels": int(fold["train"].sum()),
                "training_validation_overlap": bool((fold["train"] & fold["valid"]).any()),
                "truth_visible_overlap": int((fold["truth"] & fold["visible"]).sum()),
            }
            for fold in context.folds
        ],
    }
    _json_write(EVIDENCE, report)

    print("[1/6] Leakage canaries for all 12 frozen source features", flush=True)
    report["leakage_canary"] = context.canary(arrays)
    _json_write(EVIDENCE, report)
    if not report["leakage_canary"]["passed"]:
        report.update(
            status="STOPPED_LEAKAGE_CANARY",
            verdict="negative",
            verdict_reason="At least one feature-alone AUC exceeded 0.90",
            elapsed_seconds=round(time.monotonic() - started, 2),
        )
        _json_write(EVIDENCE, report)
        raise SystemExit("Leakage canary failed; stopped before surface fitting/placement")

    print("[2/6] Full-data A33-L1 score and pre-placement registry guard", flush=True)
    full_scores, full_fit = _fit_scores(
        arrays,
        masks,
        footprint,
        footprint,
        catalogue,
        seed=3300,
    )
    full_surface = full_scores["A33_L1"]
    np.save(ROOT / ".cache" / "a33_l1_full_surface.npy", full_surface)
    report["full_fit"] = full_fit
    report["surface_duplicate_guard"] = analog_novelty.compare_surface(full_surface, footprint)
    _json_write(EVIDENCE, report)
    if not report["surface_duplicate_guard"]["passed"]:
        report.update(
            status="STOPPED_DUPLICATE_SURFACE",
            verdict="negative",
            verdict_reason="Surface Spearman duplicate threshold exceeded",
            elapsed_seconds=round(time.monotonic() - started, 2),
        )
        _json_write(EVIDENCE, report)
        raise SystemExit("Surface duplicate guard triggered; stopped before placement")

    print("[3/6] Four buffered whole-component folds; matched operators/budgets", flush=True)
    predictions = {"B0_raw_analog": [], "B1_regional": [], "A33_L1": [], "matched_random": []}
    fold_fits = []
    fold_budgets = []
    for fold_index, fold in enumerate(context.folds):
        scores, fits = _fit_scores(
            arrays,
            masks,
            fold["valid"],
            fold["train"],
            fold["visible"],
            seed=3310 + fold_index * 10,
        )
        d_visible = distance_transform_edt(~fold["visible"])
        eligible = fold["valid"] & (d_visible > CATALOGUE_EXCLUSION_PX)
        budget = int(round(FULL_DOT_BUDGET * fold["valid"].sum() / footprint.sum()))
        fold_budgets.append(budget)
        for name in ("B0_raw_analog", "B1_regional", "A33_L1"):
            predictions[name].append(_emit(scores[name], eligible, budget))
        rng = np.random.default_rng(20261025 + fold_index)
        random_score = np.zeros(footprint.shape, dtype=np.float32)
        random_score[eligible] = rng.random(int(eligible.sum()), dtype=np.float32)
        predictions["matched_random"].append(_emit(random_score, eligible, budget))
        fold_fits.append({"fold": fold["name"], "budget": budget, "models": fits})
        print(f"  {fold['name']}: budget={budget:,}", flush=True)
    report["fold_model_fits"] = fold_fits
    report["fold_budgets"] = fold_budgets

    print("[4/6] Pooled HOLDOUT-DTI and paired spatial-block bootstrap", flush=True)
    results = {
        name: context.summarize(preds)
        for name, preds in predictions.items()
    }
    comparisons = {
        name: context.compare_paired(predictions["A33_L1"], predictions[name])
        for name in ("B0_raw_analog", "B1_regional")
    }
    best_baseline = max(
        ("B0_raw_analog", "B1_regional"),
        key=lambda name: results[name]["dti"],
    )
    best_comparison = comparisons[best_baseline]
    scientific_gate = {
        "beats_B0_raw_analog": results["A33_L1"]["dti"] > results["B0_raw_analog"]["dti"],
        "beats_B1_regional": results["A33_L1"]["dti"] > results["B1_regional"]["dti"],
        "best_comparable_baseline": best_baseline,
        "paired_delta_ci95_strictly_positive": best_comparison["ci95_strictly_positive"],
        "fold_wins_at_least_3_of_4": best_comparison["fold_wins"] >= 3,
        "leakage_canary_passed": report["leakage_canary"]["passed"],
        "surface_uniqueness_passed": report["surface_duplicate_guard"]["passed"],
    }
    scientific_gate["passed_before_final_uniqueness"] = all(
        scientific_gate[key]
        for key in (
            "beats_B0_raw_analog",
            "beats_B1_regional",
            "paired_delta_ci95_strictly_positive",
            "fold_wins_at_least_3_of_4",
            "leakage_canary_passed",
            "surface_uniqueness_passed",
        )
    )
    report["holdout_results"] = results
    report["paired_comparisons"] = comparisons
    report["scientific_gate"] = scientific_gate
    _json_write(EVIDENCE, report)
    for name in ("B0_raw_analog", "B1_regional", "A33_L1", "matched_random"):
        row = results[name]
        print(
            f"  {name}: HOLDOUT-DTI ({row['evaluator_version']}, "
            f"n={row['n_withheld_positive_pixels']:,}, 95% CI={row['ci95']['interval']}) "
            f"{row['dti']:.6f}",
            flush=True,
        )

    print("[5/6] Final unique dots and exact registry guard", flush=True)
    d_catalogue = distance_transform_edt(~catalogue)
    final_eligible = footprint & (d_catalogue > CATALOGUE_EXCLUSION_PX)
    final_dots = _emit(full_surface, final_eligible, FULL_DOT_BUDGET)
    np.save(ROOT / ".cache" / "a33_l1_final_dots.npy", final_dots)
    report["final_duplicate_guard"] = analog_novelty.compare_final_dots(final_dots, footprint)
    _json_write(EVIDENCE, report)
    if not report["final_duplicate_guard"]["passed"]:
        report.update(
            status="STOPPED_DUPLICATE_FINAL_DOTS",
            verdict="negative",
            verdict_reason="Final-dot registry duplicate threshold exceeded; no TIFF written",
            elapsed_seconds=round(time.monotonic() - started, 2),
        )
        _json_write(EVIDENCE, report)
        raise SystemExit("Final-dot duplicate guard triggered; stopped without GeoTIFF")

    print("[6/6] Shared writer, saved-byte validation, run card", flush=True)
    promote = bool(scientific_gate["passed_before_final_uniqueness"])
    verdict = "promote" if promote else "negative"
    note_template = (
        "A33-L1 analog-CDF fusion 37654d | holdout gate "
        + ("PASS" if promote else "FAIL")
        + " | research; selector not run | {cid}"
    )
    receipt = write_pair(
        final_dots.astype(np.float32),
        template=ROOT / "data" / "sample_submission.tif",
        catalogue=catalogue,
        footprint=footprint,
        outdir=ROOT / "docs" / "downloads",
        family="gemsdoe33",
        hypothesis="a33-l1-analog-transfer-research-37654",
        date=DATE,
        note_template=note_template,
        scientific_verdict=verdict,
    )
    best = results[best_baseline]
    candidate = results["A33_L1"]
    validator = receipt["primary_zero_outside"]["validator"]
    run_card = {
        "schema": 1,
        "hypothesis": (
            "A33-L1: field-balanced source-CDF alignment plus a regional visible-fault expert "
            "may transfer a portable cross-physics fault signature from named geothermal fields."
        ),
        "mechanism": (
            "Map each source field's structural-feature marginals onto the fold-training target, "
            "equalize field loss, and fuse adapted-analog and regional score ranks at 0.20/0.80."
        ),
        "named_non_fault_process_that_could_mimic_it": (
            "Lithologic contact or basin-fill boundary can generate coincident magnetic, gravity, "
            "basement-depth and conductivity discontinuities without fault displacement."
        ),
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": candidate["evaluator_version"],
            "withheld_positives": candidate["n_withheld_positive_pixels"],
            "candidate": candidate["dti"],
            "candidate_95pct_ci": candidate["ci95"],
            "best_comparable_baseline_name": best_baseline,
            "best_comparable_baseline": best["dti"],
            "best_baseline_95pct_ci": best["ci95"],
            "paired_delta": best_comparison["paired_delta_dti"],
            "paired_delta_95pct_ci": best_comparison["paired_delta_ci95"],
            "fold_wins": best_comparison["fold_wins"],
            "qualification": (
                "Mapped-catalogue hide-and-recover proxy, not private expert truth and not an "
                "organizer score. Source labels are not independent field-verified analog labels."
            ),
        },
        "correlation_overlap_vs_registry": {
            "scope": "nine pinned focus-site owner rasters",
            "surface": report["surface_duplicate_guard"],
            "final_dots": report["final_duplicate_guard"],
        },
        "raster_sha256": receipt["primary_zero_outside"]["sha256"],
        "validator_output": {
            "format_valid": validator["format_valid"],
            "hard_failures": validator["hard_failures"],
            "no_nan_inside_footprint": validator["checks"]["footprint_all_finite"]["pass"],
            "values_in_0_1": validator["checks"]["footprint_range_0_1"]["pass"],
            "crs_matches": validator["checks"]["crs_epsg_32611"]["pass"],
            "shape_matches": validator["checks"]["shape_matches_template"]["pass"],
            "transform_matches": validator["checks"]["geotransform_matches_template"]["pass"],
            "whole_array_all_finite_0_1": validator["checks"][
                "variant_strict_whole_array_no_nan_allowed"
            ]["pass"],
            "format_validation_is_not_portal_acceptance": True,
        },
        "submission": {
            "name": receipt["submission_name"],
            "file": receipt["primary_zero_outside"]["file"],
            "nan_twin": receipt["official_text_nan_outside_twin"]["file"],
            "note": receipt["note"],
            "note_characters": receipt["note_characters"],
            "ok_to_download": True,
            "ok_to_submit": False,
            "why_not_submit": (
                "Scientific holdout gate failed; do not spend a slot."
                if not promote
                else "Technical/scientific gate passed, but the required separate weekly-slot selector has not run."
            ),
        },
        "verdict": verdict,
        "scientific_gate": scientific_gate,
        "experiments_run": 1,
        "submission_slots_used": 0,
    }
    _json_write(RUN_CARD, run_card)
    _json_write(DOCS_CARD, run_card)
    report.update(
        status="COMPLETED",
        verdict=verdict,
        run_card=str(RUN_CARD.relative_to(ROOT)),
        submission_receipt=receipt,
        elapsed_seconds=round(time.monotonic() - started, 2),
        completed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    _json_write(EVIDENCE, report)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "file": receipt["primary_zero_outside"]["file"],
                "sha256": receipt["primary_zero_outside"]["sha256"],
                "ok_to_download": True,
                "ok_to_submit": False,
                "HOLDOUT-DTI": candidate["dti"],
                "HOLDOUT-DTI_95pct_CI": candidate["ci95"]["interval"],
                "withheld_positives": candidate["n_withheld_positive_pixels"],
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
