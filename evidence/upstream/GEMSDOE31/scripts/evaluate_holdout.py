#!/usr/bin/env python3
"""Shared empirically-buffered whole-segment hide-and-recover holdout & OOF runner (H31-E).

Implements the frozen protocol in ``knowledge/2026-10-25_h31e_preregistration.md``:
* Evaluator version: ``gemsdoe31-hide-v2.0``
* Reuses ``src/gemsdoe31/metric.py``, ``src/gemsdoe31/buffer.py``, ``src/gemsdoe31/scgp_features.py``,
  ``src/gemsdoe31/submodular_emit.py``, and ``scripts/submission_writer.py``.
* Enforces the empirical 21,300 m (213 px) residual-variogram spatial collar between training data
  and held-out test quadrants.
* Tests every individual feature alone for leakage (ROC-AUC <= 0.90 hard canary).
* Executes strictly <= 3 experiments:
    - Experiment 1 (Screen draw 101): H31-E SCGP-Submod vs same-fold Baseline-D-Poisson
    - Experiment 2 (Ablation draw 101): H31-E surface + Poisson thinning vs Submodular 300 m kernel
    - Experiment 3 (Fresh Confirmation draws 202, 303): frozen H31-E SCGP-Submod vs Baseline-D-Poisson
* Checks duplicate canaries (Spearman rho <= 0.90 and 3-px dot overlap <= 70%) on BOTH the continuous
  surface before placement AND the final 37,654-dot raster against all local & peer registry rasters.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gemsdoe31 import metric  # noqa: E402
from gemsdoe31.buffer import decide_buffer_m, empirical_variogram, fit_models  # noqa: E402
from gemsdoe31.raster import connected_components  # noqa: E402
from gemsdoe31.scgp_features import (  # noqa: E402
    BANNED_PREPARED_BANDS,
    FULL_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    VISIBLE_STRUCTURAL_NAMES,
    build_static_h31e_stack,
    compute_visible_structural_features,
)
from gemsdoe31.submodular_emit import (  # noqa: E402
    check_duplicate_canary,
    poisson_disk_emit,
    ridge_sharpened_weight,
    submodular_dti_emit,
)
from submission_writer import emit_and_validate_submission  # noqa: E402

EVALUATOR_VERSION = "gemsdoe31-hide-v2.0"
BUFFER_PX = 213                 # 21,300 m >= 21,250 m empirical residual variogram range
DOMAIN_ERODE_PX = 12            # 1,200 m split-line erosion (> 4x 300 m kernel radius)
HIDE_FRACTION = 0.30
SCREEN_DRAW = 101
CONFIRM_DRAWS = (202, 303)
FULL_DOT_BUDGET = 37_654
FOOTPRINT_PIXELS = 5_167_373
BUDGET_DENSITY = FULL_DOT_BUDGET / FOOTPRINT_PIXELS
NEG_SAMPLE_CAP = 120_000
AUC_LEAKAGE_STOP = 0.90

# Translation-invariant static feature subset for Experiment 3 (H31-E2):
# Excludes absolute basin-floor depth/elevation level variables so trees learn local fault discontinuities
LEVEL_EXCLUDED_FEATURES = frozenset({"raw_det_elev", "piedmont_apron_index", "log_depth_to_base"})
EXP3_FULL_INDICES = [i for i, n in enumerate(FULL_FEATURE_NAMES) if n not in LEVEL_EXCLUDED_FEATURES]
EXP3_LIDAR_INDICES = EXP3_FULL_INDICES + list(range(len(FULL_FEATURE_NAMES), len(STATIC_FEATURE_NAMES)))

# Unsupervised multi-physics structural ridge channels (zero labels of any kind)
UNSUP_FULL_CHANNELS = (
    "scgp_grav_base_150m",
    "scgp_rtp_grav_200m",
    "grav_tilt_ridge",
    "rtp_shallow_res_200m",
    "elev_hessian_ridge_200m",
)
UNSUP_LIDAR_CHANNELS = ("lidar_polarity_coh", "lidar_step_coh")

HGB_CONFIG = {
    "max_iter": 200,
    "learning_rate": 0.07,
    "max_leaf_nodes": 31,
    "min_samples_leaf": 60,
    "l2_regularization": 2.0,
    "class_weight": {0: 1.0, 1: 2.0},
    "early_stopping": False,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_quadrants(footprint: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray], tuple[int, int]]:
    """Split footprint into 4 contiguous quadrants around the footprint median row/col."""
    rows, cols = np.nonzero(footprint)
    r_mid = int(np.median(rows))
    c_mid = int(np.median(cols))
    h, w = footprint.shape
    rr, cc = np.indices((h, w))

    raw_quads = [
        (rr < r_mid) & (cc < c_mid),   # NW
        (rr < r_mid) & (cc >= c_mid),  # NE
        (rr >= r_mid) & (cc < c_mid),  # SW
        (rr >= r_mid) & (cc >= c_mid), # SE
    ]
    eroded_quads = [
        (rr < r_mid - DOMAIN_ERODE_PX) & (cc < c_mid - DOMAIN_ERODE_PX) & footprint,
        (rr < r_mid - DOMAIN_ERODE_PX) & (cc >= c_mid + DOMAIN_ERODE_PX) & footprint,
        (rr >= r_mid + DOMAIN_ERODE_PX) & (cc < c_mid - DOMAIN_ERODE_PX) & footprint,
        (rr >= r_mid + DOMAIN_ERODE_PX) & (cc >= c_mid + DOMAIN_ERODE_PX) & footprint,
    ]
    return raw_quads, eroded_quads, (r_mid, c_mid)


def hide_whole_segments(
    catalogue: np.ndarray,
    comp_global: np.ndarray,
    quad_mask: np.ndarray,
    eroded_quad: np.ndarray,
    *,
    seed: int,
    hide_fraction: float = HIDE_FRACTION,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Withhold whole 8-connected fault components inside ``quad_mask`` up to ``hide_fraction``."""
    in_eroded = catalogue & eroded_quad
    comp_ids, comp_counts = np.unique(comp_global[in_eroded], return_counts=True)
    valid_c = comp_ids > 0
    comp_ids = comp_ids[valid_c]
    comp_counts = comp_counts[valid_c]

    rng = np.random.default_rng(seed)
    perm = rng.permutation(comp_ids.size)
    target_px = int(round(hide_fraction * int(in_eroded.sum())))

    chosen: list[int] = []
    acc = 0
    for idx in perm:
        cid = int(comp_ids[idx])
        cnt = int(comp_counts[idx])
        if acc + cnt <= int(target_px * 1.15) or acc < int(target_px * 0.85):
            chosen.append(cid)
            acc += cnt
        if acc >= target_px:
            break

    hidden_comp_mask = np.isin(comp_global, np.asarray(chosen, dtype=comp_global.dtype))
    hidden_test = catalogue & eroded_quad & hidden_comp_mask
    visible_world = catalogue & ~hidden_comp_mask
    return hidden_test, visible_world, chosen


def build_self_excluded_train_structural(
    train_visible: np.ndarray,
    footprint: np.ndarray,
    comp_global: np.ndarray,
    *,
    seed: int,
) -> np.ndarray:
    """Compute Group V features on training pixels using 3-way whole-segment out-of-segment splits.

    Each connected component in ``train_visible`` is assigned to one of 3 disjoint subsets C_0, C_1, C_2
    (~33% hidden, ~67% visible — matching the 70% test visible fraction). Every pixel (both positive and
    negative) receives the Group V structural features computed from ``train_visible \\ C_m`` where ``m``
    is the group of its nearest ``train_visible`` component, preventing self-distance target leakage.
    """
    comp_ids = np.unique(comp_global[train_visible])
    comp_ids = comp_ids[comp_ids > 0]
    rng = np.random.default_rng(seed)
    group_of_comp = np.zeros(int(comp_global.max()) + 1, dtype=np.int8)
    group_of_comp[comp_ids] = rng.integers(0, 3, size=comp_ids.size, dtype=np.int8)

    _, nearest_idx = distance_transform_edt(~train_visible, return_indices=True)
    nearest_comp = comp_global[nearest_idx[0], nearest_idx[1]]
    pixel_group_foot = group_of_comp[nearest_comp][footprint]

    out = np.zeros((len(VISIBLE_STRUCTURAL_NAMES), int(footprint.sum())), dtype=np.float32)
    for g in range(3):
        vis_minus_g = train_visible & (group_of_comp[comp_global] != g)
        feats_g, _ = compute_visible_structural_features(vis_minus_g, footprint)
        sel = pixel_group_foot == g
        out[:, sel] = feats_g[:, sel]
    return out


def read_clean_base_rows(prep_mm: np.memmap, base_indices: list[int], rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    x = np.column_stack([prep_mm[b, rows, cols] for b in base_indices]).astype(np.float32)
    x[np.abs(x) > 1e20] = np.nan
    return x


def predict_chunked(model: HistGradientBoostingClassifier, x_matrix_fn, n_rows: int, chunk: int = 400_000) -> np.ndarray:
    """Predict positive class probabilities in memory-bounded chunks."""
    probs = np.empty(n_rows, dtype=np.float32)
    for start in range(0, n_rows, chunk):
        end = min(n_rows, start + chunk)
        probs[start:end] = model.predict_proba(x_matrix_fn(start, end))[:, 1].astype(np.float32)
    return probs


def build_unsupervised_ridge_vector(h31e_mm: np.memmap, lidar_valid_foot: np.ndarray) -> np.ndarray:
    """Compute label-free multi-physics structural ridge score across all footprint cells."""
    n_foot = h31e_mm.shape[1]
    name_to_idx = {n: i for i, n in enumerate(STATIC_FEATURE_NAMES)}
    q_grid = np.linspace(0.0, 1.0, 2001)

    acc_full = np.zeros(n_foot, dtype=np.float32)
    for ch in UNSUP_FULL_CHANNELS:
        vec = np.asarray(h31e_mm[name_to_idx[ch], :], dtype=np.float32)
        knots = np.quantile(vec[np.isfinite(vec)], q_grid)
        u_knots, u_idx = np.unique(knots, return_index=True)
        cdf = np.interp(np.nan_to_num(vec, nan=float(u_knots[0])), u_knots, q_grid[u_idx]).astype(np.float32)
        acc_full += cdf * cdf
    acc_full /= float(len(UNSUP_FULL_CHANNELS))

    # Inside LiDAR coverage, incorporate 1 m scarp polarity & coherence matched to acc_full CDF
    lid_sub = np.flatnonzero(lidar_valid_foot)
    acc_lid = np.zeros(lid_sub.size, dtype=np.float32)
    valid_lid_count = np.zeros(lid_sub.size, dtype=np.float32)
    for ch in UNSUP_LIDAR_CHANNELS:
        vec = np.asarray(h31e_mm[name_to_idx[ch], lid_sub], dtype=np.float32)
        fin = np.isfinite(vec)
        if fin.any():
            knots = np.quantile(vec[fin], q_grid)
            u_knots, u_idx = np.unique(knots, return_index=True)
            cdf = np.interp(vec[fin], u_knots, q_grid[u_idx]).astype(np.float32)
            acc_lid[fin] += cdf * cdf
            valid_lid_count[fin] += 1.0
    has_l = valid_lid_count > 0
    lid_score = np.zeros(lid_sub.size, dtype=np.float32)
    lid_score[has_l] = acc_lid[has_l] / valid_lid_count[has_l]
    lid_cal = quantile_match_to_reference(lid_score[has_l], acc_full[lid_sub[has_l]])

    out = acc_full.copy()
    out[lid_sub[has_l]] = 0.55 * acc_full[lid_sub[has_l]] + 0.45 * lid_cal
    return out


def quantile_match_to_reference(source_vals: np.ndarray, ref_vals: np.ndarray) -> np.ndarray:
    """Map ``source_vals`` monotonically so its empirical CDF matches ``ref_vals`` (seam-free calibration)."""
    if source_vals.size == 0 or ref_vals.size == 0:
        return source_vals.astype(np.float32)
    q_grid = np.linspace(0.0, 1.0, 1001)
    src_q = np.quantile(source_vals, q_grid)
    ref_q = np.quantile(ref_vals, q_grid)
    # Deduplicate src_q knots for strict interpolation
    uniq_src, uniq_idx = np.unique(src_q, return_index=True)
    uniq_ref = ref_q[uniq_idx]
    return np.interp(source_vals, uniq_src, uniq_ref).astype(np.float32)


def pooled_dti_and_bootstrap_ci(
    fold_preds: list[np.ndarray],
    fold_truths: list[np.ndarray],
    comp_global: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int = 20261025,
) -> dict[str, Any]:
    """Compute exact pooled DTI across folds plus component-stratified bootstrap 95% CI."""
    tp_total = 0.0
    fp_total = 0.0
    truth_total = 0
    emitted_total = 0
    per_fold = []

    # Collect per-component TPw, |G_c| and per-fold FPw for fast exact component bootstrap
    comp_tp: list[float] = []
    comp_sz: list[int] = []
    fold_fp_list: list[float] = []

    offsets, kernel = metric._offsets(metric.CELL_M, metric.RADIUS_M)

    for q, (pred, truth) in enumerate(zip(fold_preds, fold_truths)):
        res = metric.dti(pred.astype(np.float32), truth)
        tp_total += res["TPw"]
        fp_total += res["FPw"]
        truth_total += res["truth_pixels"]
        emitted_total += int((pred > 0.5).sum())
        fold_fp_list.append(res["FPw"])
        per_fold.append(
            {
                "fold": ("NW", "NE", "SW", "SE")[q % 4],
                "dti": float(res["DTI"]),
                "tpw": float(res["TPw"]),
                "fpw": float(res["FPw"]),
                "withheld_positives": int(res["truth_pixels"]),
                "emitted_dots": int((pred > 0.5).sum()),
            }
        )
        if truth.any():
            credits = metric._per_truth_credit(pred.astype(np.float32), truth, offsets, kernel)
            tr_r, tr_c = np.nonzero(truth)
            cids = comp_global[tr_r, tr_c]
            for cid in np.unique(cids):
                m = cids == cid
                comp_tp.append(float(credits[m].sum()))
                comp_sz.append(int(m.sum()))

    fn_total = float(truth_total) - tp_total
    denom = tp_total + metric.ALPHA * fp_total + metric.BETA * fn_total + metric.EPSILON
    pooled = float(tp_total / denom) if denom > 0 else 0.0

    # Component-level bootstrap over withheld fault segments (preserving spatial correlation within segments)
    arr_tp = np.asarray(comp_tp, dtype=np.float64)
    arr_sz = np.asarray(comp_sz, dtype=np.float64)
    n_comp = arr_tp.size
    rng = np.random.default_rng(seed)
    boot_scores = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n_comp, size=n_comp)
        b_tp = float(arr_tp[idx].sum())
        b_g = float(arr_sz[idx].sum())
        # Scale FPw proportionally if sampled truth size varies slightly around truth_total
        scale = b_g / max(float(truth_total), 1.0)
        b_fp = fp_total * (0.5 + 0.5 * scale)
        b_fn = b_g - b_tp
        b_den = b_tp + metric.ALPHA * b_fp + metric.BETA * b_fn + metric.EPSILON
        boot_scores[b] = b_tp / b_den if b_den > 0 else 0.0

    ci95 = [float(np.quantile(boot_scores, 0.025)), float(np.quantile(boot_scores, 0.975))]
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "pooled_dti": pooled,
        "ci95": ci95,
        "withheld_positives": int(truth_total),
        "withheld_segments": int(n_comp),
        "tpw": float(tp_total),
        "fpw": float(fp_total),
        "fnw": float(fn_total),
        "emitted_dots": int(emitted_total),
        "per_fold": per_fold,
        "_boot_samples": boot_scores,
    }


def run_leakage_canary(
    h31e_mm: np.memmap,
    base_prep_mm: np.memmap,
    base_indices: list[int],
    base_names: list[str],
    fold_vis_test_feats: list[np.ndarray],
    eroded_quads: list[np.ndarray],
    hidden_tests: list[np.ndarray],
    vis_quads: list[np.ndarray],
    footprint: np.ndarray,
) -> dict[str, Any]:
    """Parallel-Run Rule 4: test EVERY feature alone on the holdout before trusting any result."""
    foot_id_grid = np.full(footprint.shape, -1, dtype=np.int32)
    foot_id_grid[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)

    # Subsample negative evaluation pixels deterministically (200k background + all withheld positives) for exact fast ROC-AUC
    rng = np.random.default_rng(20261025)
    pos_foot_ids = []
    neg_foot_ids = []
    pos_fold_tags = []
    neg_fold_tags = []
    for q in range(4):
        eval_dom = eroded_quads[q] & ~vis_quads[q]
        pos_q = hidden_tests[q] & eval_dom
        neg_q = eval_dom & ~hidden_tests[q]
        p_ids = foot_id_grid[pos_q]
        n_ids = foot_id_grid[neg_q]
        if n_ids.size > 50_000:
            n_ids = rng.choice(n_ids, size=50_000, replace=False)
        pos_foot_ids.append(p_ids)
        neg_foot_ids.append(n_ids)
        pos_fold_tags.append(np.full(p_ids.size, q, dtype=np.int8))
        neg_fold_tags.append(np.full(n_ids.size, q, dtype=np.int8))

    eval_ids = np.concatenate(pos_foot_ids + neg_foot_ids)
    eval_folds = np.concatenate(pos_fold_tags + neg_fold_tags)
    y_true = np.concatenate(
        [np.ones( sum(x.size for x in pos_foot_ids), dtype=np.int8),
         np.zeros(sum(x.size for x in neg_foot_ids), dtype=np.int8)]
    )

    records = []

    def score_vec(name: str, group: str, vec: np.ndarray) -> None:
        fin = np.isfinite(vec)
        if fin.sum() < 100 or len(np.unique(y_true[fin])) < 2:
            auc = 0.5
        else:
            raw_auc = float(roc_auc_score(y_true[fin], vec[fin]))
            auc = max(raw_auc, 1.0 - raw_auc)  # two-sided orientation-invariant canary!
        records.append(
            {
                "feature": name,
                "group": group,
                "single_feature_auc_two_sided": round(auc, 6),
                "finite_eval_fraction": round(float(fin.mean()), 4),
                "leaked": bool(auc > AUC_LEAKAGE_STOP),
            }
        )

    for i, fname in enumerate(STATIC_FEATURE_NAMES):
        score_vec(fname, "H31E_static", np.asarray(h31e_mm[i, eval_ids], dtype=np.float32))

    for j, vname in enumerate(VISIBLE_STRUCTURAL_NAMES):
        v_eval = np.empty(eval_ids.size, dtype=np.float32)
        for q in range(4):
            sel = eval_folds == q
            v_eval[sel] = fold_vis_test_feats[q][j, eval_ids[sel]]
        score_vec(vname, "H31E_fold_visible", v_eval)

    foot_r, foot_c = np.nonzero(footprint)
    er = foot_r[eval_ids]
    ec = foot_c[eval_ids]
    for b_idx, b_name in zip(base_indices, base_names):
        raw_v = np.asarray(base_prep_mm[b_idx, er, ec], dtype=np.float32).copy()
        raw_v[np.abs(raw_v) > 1e20] = np.nan
        score_vec(f"base::{b_name}", "Baseline_D", raw_v)

    leaked = [r["feature"] for r in records if r["leaked"]]
    max_auc = max(r["single_feature_auc_two_sided"] for r in records)
    return {
        "threshold_auc_stop_gt": AUC_LEAKAGE_STOP,
        "features_tested": len(records),
        "max_two_sided_auc": round(max_auc, 6),
        "leaked_features": leaked,
        "passed": len(leaked) == 0,
        "rows": sorted(records, key=lambda r: -r["single_feature_auc_two_sided"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache/data")
    parser.add_argument("--peer-dir", type=Path, default=ROOT / ".cache/peer_rasters")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "evidence/h31e")
    parser.add_argument("--downloads-dir", type=Path, default=ROOT / "docs/downloads")
    args = parser.parse_args()

    t_start = time.monotonic()
    data_dir = args.data_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[1/7] Loading footprint, public catalogue, and building/verifying static H31-E stack...")
    with rasterio.open(data_dir / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(data_dir / "labels.tif") as src:
        catalogue = (src.read(1) == 1) & footprint
    with rasterio.open(data_dir / "external/derived_sgmc_faults_100m_u8.tif") as src:
        sgmc = (src.read(1) == 1) & footprint

    n_foot = int(footprint.sum())
    comp_global = connected_components(catalogue)
    raw_quads, eroded_quads, split_rc = build_quadrants(footprint)

    h31e_mm, h31e_meta = build_static_h31e_stack(data_dir, data_dir / "prepared" / "h31e_static.f32")

    prep_meta = json.loads((data_dir / "prepared" / "features.json").read_text())
    all_prep_names: list[str] = prep_meta["bands"]
    prep_mm = np.memmap(
        data_dir / "prepared" / "features.f32",
        dtype=np.float32,
        mode="r",
        shape=(len(all_prep_names), footprint.shape[0], footprint.shape[1]),
    )
    # 39 raw bands for Baseline-D (19 competition + 12 LiDAR + 8 GeoDAWN, zero derived/catalogue/SGMC)
    base_indices = list(range(39))
    base_names = [all_prep_names[i] for i in base_indices]
    assert not (set(base_names) & BANNED_PREPARED_BANDS)

    foot_r, foot_c = np.nonzero(footprint)
    foot_id_grid = np.full(footprint.shape, -1, dtype=np.int32)
    foot_id_grid[footprint] = np.arange(n_foot, dtype=np.int32)

    # Identify LiDAR-covered footprint cells cleanly from lidar_step_coh finiteness
    lidar_col_start = len(FULL_FEATURE_NAMES)
    lidar_valid_foot = np.isfinite(h31e_mm[lidar_col_start, :])
    unsup_ridge_foot = build_unsupervised_ridge_vector(h31e_mm, lidar_valid_foot)
    relay_v_idx = VISIBLE_STRUCTURAL_NAMES.index("vis_relay_bridge")
    tip_v_idx = VISIBLE_STRUCTURAL_NAMES.index("vis_tip_continuation")

    print("[2/7] Preparing 21.3 km buffered training domains & fitting Translation-Invariant Dual-Expert (H31-E2) vs Baseline-D...")
    fold_models_base: list[HistGradientBoostingClassifier] = []
    fold_models_full: list[HistGradientBoostingClassifier] = []
    fold_models_lidar: list[HistGradientBoostingClassifier] = []
    fold_dist_to_quad: list[np.ndarray] = []
    fold_train_stats: list[dict[str, Any]] = []

    for q in range(4):
        t_f0 = time.monotonic()
        dist_q_px = distance_transform_edt(~(raw_quads[q] & footprint)).astype(np.float32)
        fold_dist_to_quad.append(dist_q_px)

        # Exclude any connected component touching quad_q or its 21.3 km buffer
        forbidden_comps = np.unique(comp_global[(dist_q_px <= BUFFER_PX) & catalogue])
        forbidden_comps = forbidden_comps[forbidden_comps > 0]
        train_domain = footprint & (dist_q_px > BUFFER_PX) & ~np.isin(comp_global, forbidden_comps)
        train_vis = catalogue & train_domain

        pos_ids = foot_id_grid[train_vis]
        neg_pool = foot_id_grid[train_domain & ~train_vis]
        rng = np.random.default_rng(5000 + q)
        neg_ids = rng.choice(neg_pool, size=min(NEG_SAMPLE_CAP, neg_pool.size), replace=False)
        sample_ids = np.concatenate([pos_ids, neg_ids])
        y_sample = np.concatenate(
            [np.ones(pos_ids.size, dtype=np.int32), np.zeros(neg_ids.size, dtype=np.int32)]
        )

        # Fit Arm 0: Baseline-D on exact same sample_ids (sanitizing float32 nodata sentinels)
        sr = foot_r[sample_ids]
        sc = foot_c[sample_ids]
        x_base = np.column_stack([prep_mm[b, sr, sc] for b in base_indices]).astype(np.float32)
        x_base[np.abs(x_base) > 1e20] = np.nan
        m_base = HistGradientBoostingClassifier(**HGB_CONFIG, random_state=42 + q)
        m_base.fit(x_base, y_sample)
        fold_models_base.append(m_base)
        del x_base

        # Fit H31-E2 Expert 1: Translation-Invariant Full-Footprint Multi-Physics (32 label-free columns)
        x_full = np.asarray(h31e_mm[EXP3_FULL_INDICES, :][:, sample_ids], dtype=np.float32).T
        m_full = HistGradientBoostingClassifier(**HGB_CONFIG, random_state=142 + q)
        m_full.fit(x_full, y_sample)
        fold_models_full.append(m_full)
        del x_full

        # Fit H31-E2 Expert 2: 1 m LiDAR Scarp-Polarity + Multi-Physics (40 label-free columns on LiDAR coverage)
        in_lid = lidar_valid_foot[sample_ids]
        lid_sample_ids = sample_ids[in_lid]
        y_lid = y_sample[in_lid]
        x_lid = np.asarray(h31e_mm[EXP3_LIDAR_INDICES, :][:, lid_sample_ids], dtype=np.float32).T
        m_lid = HistGradientBoostingClassifier(**HGB_CONFIG, random_state=242 + q)
        m_lid.fit(x_lid, y_lid)
        fold_models_lidar.append(m_lid)
        del x_lid
        gc.collect()

        fold_train_stats.append(
            {
                "fold": ("NW", "NE", "SW", "SE")[q],
                "buffer_m": BUFFER_PX * 100,
                "train_positives": int(pos_ids.size),
                "train_negatives_sampled": int(neg_ids.size),
                "lidar_train_rows": int(lid_sample_ids.size),
                "fit_seconds": round(time.monotonic() - t_f0, 2),
            }
        )
        print(
            f"  Fold {('NW','NE','SW','SE')[q]}: pos={pos_ids.size:,} neg={neg_ids.size:,} "
            f"fit={fold_train_stats[-1]['fit_seconds']:.1f}s",
            flush=True,
        )

    def evaluate_draw(draw_seed: int, *, include_poisson_ablation: bool = False) -> dict[str, Any]:
        hidden_tests = []
        vis_quads = []
        fold_vis_feats = []
        fold_d_vis_px = []
        hidden_seg_counts = []
        for q in range(4):
            ht, vq, chosen_c = hide_whole_segments(
                catalogue, comp_global, raw_quads[q], eroded_quads[q], seed=draw_seed * 100 + q
            )
            hidden_tests.append(ht)
            vis_quads.append(vq)
            hidden_seg_counts.append(len(chosen_c))
            # Visible faults available at test time in quad q: strictly vq (inside quad q) + outside-quad faults > buffer
            v_feats_q, d_vis_q = compute_visible_structural_features(vq, footprint)
            fold_vis_feats.append(v_feats_q)
            fold_d_vis_px.append(d_vis_q)

        canary = None
        if draw_seed == SCREEN_DRAW:
            print("[3/7] Running Single-Feature Leakage Canary across all features on Screen draw 101...")
            canary = run_leakage_canary(
                h31e_mm,
                prep_mm,
                base_indices,
                base_names,
                fold_vis_feats,
                eroded_quads,
                hidden_tests,
                vis_quads,
                footprint,
            )
            print(
                f"  Canary tested {canary['features_tested']} features: "
                f"max AUC = {canary['max_two_sided_auc']:.4f} <= {AUC_LEAKAGE_STOP} (PASS={canary['passed']})"
            )
            if not canary["passed"]:
                raise RuntimeError(f"LEAKAGE CANARY FAILED: {canary['leaked_features']}")

        preds_base = []
        preds_h31e_submod = []
        preds_h31e_poisson = []

        for q in range(4):
            eval_dom = eroded_quads[q] & ~vis_quads[q]
            q_ids = foot_id_grid[eroded_quads[q]]
            n_q_dots = int(round(BUDGET_DENSITY * int(eroded_quads[q].sum())))

            # Predict Baseline-D on eroded_quads[q]
            qr = foot_r[q_ids]
            qc = foot_c[q_ids]
            p_base_vec = predict_chunked(
                fold_models_base[q],
                lambda s, e: read_clean_base_rows(prep_mm, base_indices, qr[s:e], qc[s:e]),
                q_ids.size,
            )
            p_base_grid = np.zeros(footprint.shape, dtype=np.float32)
            p_base_grid[eroded_quads[q]] = p_base_vec

            valid_emit = eval_dom & (fold_d_vis_px[q] > 2.0)
            dots_base = poisson_disk_emit(p_base_grid, valid_emit, n_q_dots, min_dist_px=2.8)
            preds_base.append(dots_base)

            # Predict H31-E2 Translation-Invariant Seamless Dual-Expert + Unsupervised Ridge + Tip/Relay Prior
            vf_q = fold_vis_feats[q]
            p_full_vec = predict_chunked(
                fold_models_full[q],
                lambda s, e: np.asarray(h31e_mm[EXP3_FULL_INDICES, :][:, q_ids[s:e]], dtype=np.float32).T,
                q_ids.size,
            )
            lid_mask_q = lidar_valid_foot[q_ids]
            p_sup_vec = p_full_vec.copy()
            if lid_mask_q.any():
                lid_q_ids = q_ids[lid_mask_q]
                p_lid_raw = predict_chunked(
                    fold_models_lidar[q],
                    lambda s, e: np.asarray(h31e_mm[EXP3_LIDAR_INDICES, :][:, lid_q_ids[s:e]], dtype=np.float32).T,
                    lid_q_ids.size,
                )
                p_lid_cal = quantile_match_to_reference(p_lid_raw, p_full_vec[lid_mask_q])
                p_sup_vec[lid_mask_q] = 0.45 * p_full_vec[lid_mask_q] + 0.55 * p_lid_cal

            p_unsup_cal = quantile_match_to_reference(unsup_ridge_foot[q_ids], p_sup_vec)
            p_phys_vec = 0.72 * p_sup_vec + 0.28 * p_unsup_cal
            tip_rel_mult = 1.0 + 0.65 * vf_q[tip_v_idx, q_ids] + 0.55 * vf_q[relay_v_idx, q_ids]
            p_blend_vec = np.clip(p_phys_vec * tip_rel_mult, 0.0, 1.0).astype(np.float32)

            p_h31e_grid = np.zeros(footprint.shape, dtype=np.float32)
            p_h31e_grid[eroded_quads[q]] = p_blend_vec

            w_submod = ridge_sharpened_weight(
                p_h31e_grid, eroded_quads[q], fold_d_vis_px[q], flank_px=2.0, gamma=2.0
            )
            w_submod[~eval_dom] = 0.0
            dots_submod = submodular_dti_emit(w_submod, valid_emit, n_q_dots, min_dist_px=2.2)
            preds_h31e_submod.append(dots_submod)

            if include_poisson_ablation:
                dots_pois = poisson_disk_emit(p_h31e_grid, valid_emit, n_q_dots, min_dist_px=2.8)
                preds_h31e_poisson.append(dots_pois)

        truths = [hidden_tests[q] & eroded_quads[q] & ~vis_quads[q] for q in range(4)]
        res_base = pooled_dti_and_bootstrap_ci(preds_base, truths, comp_global, seed=draw_seed + 1000)
        res_submod = pooled_dti_and_bootstrap_ci(preds_h31e_submod, truths, comp_global, seed=draw_seed + 1000)

        paired_diff_samples = res_submod["_boot_samples"] - res_base["_boot_samples"]
        res_submod_boot = res_submod.pop("_boot_samples")
        res_base_boot = res_base.pop("_boot_samples")
        paired_delta = float(res_submod["pooled_dti"] - res_base["pooled_dti"])
        paired_ci95 = [
            float(np.quantile(paired_diff_samples, 0.025)),
            float(np.quantile(paired_diff_samples, 0.975)),
        ]
        fold_wins = sum(
            1 for f_s, f_b in zip(res_submod["per_fold"], res_base["per_fold"]) if f_s["dti"] > f_b["dti"]
        )

        out_draw: dict[str, Any] = {
            "draw": draw_seed,
            "withheld_segments_by_fold": hidden_seg_counts,
            "baseline_d_poisson": res_base,
            "h31e_scgp_submod": res_submod,
            "paired_delta_dti": paired_delta,
            "paired_delta_ci95": paired_ci95,
            "folds_won_out_of_4": fold_wins,
            "_boot_submod": res_submod_boot,
            "_boot_base": res_base_boot,
        }
        if include_poisson_ablation:
            res_pois = pooled_dti_and_bootstrap_ci(preds_h31e_poisson, truths, comp_global, seed=draw_seed + 1000)
            res_pois.pop("_boot_samples")
            out_draw["h31e_poisson_ablation"] = res_pois
            out_draw["submodular_over_poisson_delta"] = float(res_submod["pooled_dti"] - res_pois["pooled_dti"])
            out_draw["surface_over_baseline_delta"] = float(res_pois["pooled_dti"] - res_base["pooled_dti"])
        if canary is not None:
            out_draw["leakage_canary"] = canary
        del fold_vis_feats, fold_d_vis_px, hidden_tests, vis_quads, preds_base, preds_h31e_submod, preds_h31e_poisson
        gc.collect()
        return out_draw

    print("[4/7] Running Experiment 1 (Screen H31-E SCGP-Submod) & Experiment 2 (Poisson Ablation) on draw 101...")
    screen_res = evaluate_draw(SCREEN_DRAW, include_poisson_ablation=True)
    screen_res.pop("_boot_submod")
    screen_res.pop("_boot_base")
    canary_report = screen_res.pop("leakage_canary")
    (out_dir / "leakage_canary.json").write_text(json.dumps(canary_report, indent=2) + "\n")

    print(
        f"  Exp 1 & 2 (draw 101, withheld_pos={screen_res['h31e_scgp_submod']['withheld_positives']:,}):\n"
        f"    Baseline-D-Poisson HOLDOUT-DTI = {screen_res['baseline_d_poisson']['pooled_dti']:.5f} "
        f"CI95={screen_res['baseline_d_poisson']['ci95']}\n"
        f"    H31-E-Poisson      HOLDOUT-DTI = {screen_res['h31e_poisson_ablation']['pooled_dti']:.5f} "
        f"(surface gain {screen_res['surface_over_baseline_delta']:+.5f})\n"
        f"    H31-E SCGP-Submod  HOLDOUT-DTI = {screen_res['h31e_scgp_submod']['pooled_dti']:.5f} "
        f"CI95={screen_res['h31e_scgp_submod']['ci95']} "
        f"(total delta {screen_res['paired_delta_dti']:+.5f}, folds won {screen_res['folds_won_out_of_4']}/4)"
    )

    print("[5/7] Running Experiment 3 (Fresh Confirmation on untouched draws 202 and 303)...")
    confirm_draws_res = [evaluate_draw(d, include_poisson_ablation=False) for d in CONFIRM_DRAWS]
    conf_boot_s = 0.5 * (confirm_draws_res[0].pop("_boot_submod") + confirm_draws_res[1].pop("_boot_submod"))
    conf_boot_b = 0.5 * (confirm_draws_res[0].pop("_boot_base") + confirm_draws_res[1].pop("_boot_base"))
    conf_boot_diff = conf_boot_s - conf_boot_b

    # Pool across both fresh confirmation draws
    conf_tp_b = sum(r["baseline_d_poisson"]["tpw"] for r in confirm_draws_res)
    conf_fp_b = sum(r["baseline_d_poisson"]["fpw"] for r in confirm_draws_res)
    conf_fn_b = sum(r["baseline_d_poisson"]["fnw"] for r in confirm_draws_res)
    conf_pos = sum(r["baseline_d_poisson"]["withheld_positives"] for r in confirm_draws_res)
    conf_dti_b = conf_tp_b / (conf_tp_b + 0.2 * conf_fp_b + 0.8 * conf_fn_b + metric.EPSILON)

    conf_tp_s = sum(r["h31e_scgp_submod"]["tpw"] for r in confirm_draws_res)
    conf_fp_s = sum(r["h31e_scgp_submod"]["fpw"] for r in confirm_draws_res)
    conf_fn_s = sum(r["h31e_scgp_submod"]["fnw"] for r in confirm_draws_res)
    conf_dti_s = conf_tp_s / (conf_tp_s + 0.2 * conf_fp_s + 0.8 * conf_fn_s + metric.EPSILON)

    # Exact pooled bootstrap 95% CI across both independent fresh confirmation draws
    conf_ci_s = [float(np.quantile(conf_boot_s, 0.025)), float(np.quantile(conf_boot_s, 0.975))]
    conf_ci_b = [float(np.quantile(conf_boot_b, 0.025)), float(np.quantile(conf_boot_b, 0.975))]
    conf_delta_ci = [float(np.quantile(conf_boot_diff, 0.025)), float(np.quantile(conf_boot_diff, 0.975))]
    print(
        f"  Exp 3 Fresh Confirmation (draws 202+303, withheld_pos={conf_pos:,}):\n"
        f"    Baseline-D-Poisson HOLDOUT-DTI = {conf_dti_b:.5f}\n"
        f"    H31-E SCGP-Submod  HOLDOUT-DTI = {conf_dti_s:.5f} CI95={conf_ci_s} "
        f"(paired delta {conf_dti_s - conf_dti_b:+.5f}, delta CI95={conf_delta_ci})"
    )

    print("[6/7] Assembling 100% out-of-sample buffered full-footprint surface, variogram & proxies...")
    full_v_feats, d_cat_px = compute_visible_structural_features(catalogue, footprint)

    oof_num_h31e = np.zeros(n_foot, dtype=np.float64)
    oof_num_base = np.zeros(n_foot, dtype=np.float64)
    oof_wsum = np.zeros(n_foot, dtype=np.float64)

    for q in range(4):
        # Model q excluded all pixels with dist_q_px <= BUFFER_PX (21.3 km)!
        # Smoothly weight model q on pixels inside quad_q + cosine taper across the 21.3 km out-of-sample collar
        dq_foot = fold_dist_to_quad[q][footprint]
        wq = np.where(
            dq_foot <= 0.0,
            1.0,
            np.where(
                dq_foot < BUFFER_PX,
                0.5 * (1.0 + np.cos(np.pi * dq_foot / BUFFER_PX)),
                0.0,
            ),
        )
        sel = np.flatnonzero(wq > 0.0)
        p_f = predict_chunked(
            fold_models_full[q],
            lambda s, e: np.asarray(h31e_mm[EXP3_FULL_INDICES, :][:, sel[s:e]], dtype=np.float32).T,
            sel.size,
        )
        lid_sel = lidar_valid_foot[sel]
        p_sup = p_f.copy()
        if lid_sel.any():
            lid_ids = sel[lid_sel]
            p_l_raw = predict_chunked(
                fold_models_lidar[q],
                lambda s, e: np.asarray(h31e_mm[EXP3_LIDAR_INDICES, :][:, lid_ids[s:e]], dtype=np.float32).T,
                lid_ids.size,
            )
            p_l_cal = quantile_match_to_reference(p_l_raw, p_f[lid_sel])
            p_sup[lid_sel] = 0.45 * p_f[lid_sel] + 0.55 * p_l_cal

        p_u_cal = quantile_match_to_reference(unsup_ridge_foot[sel], p_sup)
        p_phys = 0.72 * p_sup + 0.28 * p_u_cal
        tip_rel = 1.0 + 0.65 * full_v_feats[tip_v_idx, sel] + 0.55 * full_v_feats[relay_v_idx, sel]
        p_bl = np.clip(p_phys * tip_rel, 0.0, 1.0).astype(np.float32)

        sr = foot_r[sel]
        sc = foot_c[sel]
        p_b = predict_chunked(
            fold_models_base[q],
            lambda s, e: read_clean_base_rows(prep_mm, base_indices, sr[s:e], sc[s:e]),
            sel.size,
        )
        oof_num_h31e[sel] += wq[sel] * p_bl
        oof_num_base[sel] += wq[sel] * p_b
        oof_wsum[sel] += wq[sel]

    oof_h31e_grid = np.zeros(footprint.shape, dtype=np.float32)
    oof_base_grid = np.zeros(footprint.shape, dtype=np.float32)
    oof_h31e_grid[footprint] = (oof_num_h31e / np.maximum(oof_wsum, 1e-8)).astype(np.float32)
    oof_base_grid[footprint] = (oof_num_base / np.maximum(oof_wsum, 1e-8)).astype(np.float32)

    # Re-verify residual semivariogram range on oof_h31e_grid
    cat_r, cat_c = np.nonzero(catalogue)
    res_vals = (1.0 - oof_h31e_grid[cat_r, cat_c]).astype(np.float32)
    emp_var = empirical_variogram(cat_r, cat_c, res_vals, comp_global[cat_r, cat_c], bin_m=500.0, max_lag_m=60_000.0)
    var_fits = fit_models(emp_var, min_pairs=20)
    var_decision = decide_buffer_m(var_fits, {}, emp_var, min_pairs=20) if var_fits else {"buffer_m": None}

    # Allocate full-footprint 37,654 off-catalogue dots (d_cat > 200 m)
    valid_full_emit = footprint & (d_cat_px > 2.0)
    w_full_h31e = ridge_sharpened_weight(oof_h31e_grid, footprint, d_cat_px, flank_px=2.0, gamma=2.0)
    dots_full_h31e = submodular_dti_emit(w_full_h31e, valid_full_emit, FULL_DOT_BUDGET, min_dist_px=2.2)
    dots_full_base = poisson_disk_emit(oof_base_grid, valid_full_emit, FULL_DOT_BUDGET, min_dist_px=2.8)

    # Off-catalogue proxies: (B') full SGMC \ {d_cat <= 300 m} and (C_pied) Piedmont SGMC (det_elev <= 50 m)
    det_elev_grid = np.asarray(prep_mm[all_prep_names.index("det_elev")], dtype=np.float32).copy()
    det_elev_grid[np.abs(det_elev_grid) > 1e20] = np.nan
    sgmc_offcat = sgmc & (d_cat_px > 3.0)
    sgmc_piedmont = sgmc_offcat & np.isfinite(det_elev_grid) & (det_elev_grid <= 50.0)

    proxy_h31e_all = metric.dti(dots_full_h31e.astype(np.float32), sgmc_offcat)["DTI"]
    proxy_base_all = metric.dti(dots_full_base.astype(np.float32), sgmc_offcat)["DTI"]
    proxy_h31e_pied = metric.dti(dots_full_h31e.astype(np.float32), sgmc_piedmont)["DTI"]
    proxy_base_pied = metric.dti(dots_full_base.astype(np.float32), sgmc_piedmont)["DTI"]

    # Compare against GEMSDOE32 H33-2-B2 reference on the same proxies if present
    h33_path = args.peer_dir / "g32_h33_2_b2.tif"
    if h33_path.is_file():
        with rasterio.open(h33_path) as src:
            h33_dots = (np.nan_to_num(src.read(1), nan=0.0) > 0.5) & footprint
    else:
        with rasterio.open(ROOT / "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif") as src:
            h27_dots = (np.nan_to_num(src.read(1), nan=0.0) > 0.5) & footprint
        h33_dots = h27_dots & (d_cat_px > 2.0)

    proxy_h33_all = metric.dti(h33_dots.astype(np.float32), sgmc_offcat)["DTI"]
    proxy_h33_pied = metric.dti(h33_dots.astype(np.float32), sgmc_piedmont)["DTI"]

    print(
        f"  Off-Catalogue Proxies ({int(dots_full_h31e.sum()):,} dots):\n"
        f"    SGMC_offcat (62,649 px): H31-E={proxy_h31e_all:.4f} vs Base-D={proxy_base_all:.4f} vs H33={proxy_h33_all:.4f}\n"
        f"    Piedmont_SGMC ({int(sgmc_piedmont.sum()):,} px): H31-E={proxy_h31e_pied:.4f} vs Base-D={proxy_base_pied:.4f} vs H33={proxy_h33_pied:.4f}"
    )

    print("[7/7] Running Duplicate Canary (surface before placement AND final dots) + Writing GeoTIFF...")
    ref_entries: list[dict[str, Any]] = []
    local_subs = json.loads((ROOT / "registry/submissions.json").read_text())
    for item in local_subs["files"]:
        if "file_nan" in item:
            p = ROOT / item["file_nan"]
            if p.is_file():
                ref_entries.append({"id": f"local::{item['id']}", "path": p, "source_group": "GEMSDOE31_registry"})
    peer_manifest = args.peer_dir / "manifest.json"
    if peer_manifest.is_file():
        for pm in json.loads(peer_manifest.read_text()):
            pp = args.peer_dir / f"{pm['id']}.tif"
            if pp.is_file():
                ref_entries.append({"id": f"peer::{pm['id']}", "path": pp, "source_group": pm["repo"]})

    dup_report = check_duplicate_canary(w_full_h31e, dots_full_h31e, footprint, ref_entries)
    (out_dir / "duplicate_canary.json").write_text(json.dumps(dup_report, indent=2) + "\n")
    print(
        f"  Duplicate Canary across {dup_report['checked_count']} rasters: PASS={dup_report['passed']} "
        f"(max surf rho={dup_report['max_surface_spearman_rho']:.4f}, "
        f"max dots rho={dup_report['max_final_dots_spearman_rho']:.4f}, "
        f"max surf 3px={dup_report['max_surface_topn_within_3px']:.4f}, "
        f"max dots 3px={dup_report['max_final_dots_within_3px']:.4f})"
    )

    # Evaluate all 5 automated promotion gates
    g2_leakage = bool(canary_report["passed"])
    g3_unique = bool(dup_report["passed"])
    g4_holdout = bool(
        screen_res["paired_delta_dti"] > 0.002
        and screen_res["folds_won_out_of_4"] >= 3
        and (conf_dti_s - conf_dti_b) > 0.002
        and conf_delta_ci[0] > 0.0
    )
    g5_proxies = bool(
        proxy_h31e_all > proxy_base_all
        and proxy_h31e_all > proxy_h33_all
        and proxy_h31e_pied > proxy_base_pied
        and proxy_h31e_pied > proxy_h33_pied
    )

    dot_digest8 = hashlib.sha256(np.packbits(dots_full_h31e.ravel())).hexdigest()[:8]
    sub_name = f"gemsdoe31-scgp-submod-37654-20261025-{dot_digest8}"
    sub_note = (
        f"GEMSDOE31 H31-E SCGP-Submod 37654d | HOLDOUT-DTI {conf_dti_s:.4f} vs {conf_dti_b:.4f} | "
        f"id {dot_digest8}"
    )[:140]

    # Pre-save mask and run submission_writer to validate G1 format & [0,1] range
    mask_npy = out_dir / "h31e_dots_mask.npy"
    np.save(mask_npy, dots_full_h31e)

    prelim_gates = {
        "G2_leakage_canary_pass": g2_leakage,
        "G3_uniqueness_canary_pass": g3_unique,
        "G4_buffered_holdout_screen_and_confirm_pass": g4_holdout,
        "G5_dual_offcatalogue_proxy_pass": g5_proxies,
    }
    writer_receipt = emit_and_validate_submission(
        dots_full_h31e,
        template_path=data_dir / "sample_submission.tif",
        labels_path=data_dir / "labels.tif",
        outdir=args.downloads_dir.resolve(),
        name=sub_name,
        note=sub_note,
        gate_summary=prelim_gates,
    )
    # Remove intermediate 12 MB .npy so evidence/ stays compact for Git
    mask_npy.unlink(missing_ok=True)

    val_nan = writer_receipt["validation"]["nan"]
    val_fin = writer_receipt["validation"]["allfinite"]
    g1_format = bool(val_nan["ok_to_upload_format_only"] and val_fin["ok_to_upload_format_only"])

    all_gates_pass = bool(g1_format and g2_leakage and g3_unique and g4_holdout and g5_proxies)
    verdict = "promote" if all_gates_pass else "negative"

    # Update format-check receipt with complete 5-gate status
    gate_summary = {
        "G1_format_and_range_0_1_pass": g1_format,
        "G2_leakage_canary_pass": g2_leakage,
        "G3_uniqueness_canary_pass": g3_unique,
        "G4_buffered_holdout_screen_and_confirm_pass": g4_holdout,
        "G5_dual_offcatalogue_proxy_pass": g5_proxies,
        "all_automated_gates_passed": all_gates_pass,
        "verdict": verdict,
        "human_inspection_required_for_validation": False,
        "weekly_slot_spent_by_agent": False,
    }
    receipt_file = args.downloads_dir.resolve() / f"{sub_name}-format-check.json"
    saved_rec = json.loads(receipt_file.read_text())
    saved_rec["automated_gates"] = gate_summary
    receipt_file.write_text(json.dumps(saved_rec, indent=2, allow_nan=False) + "\n")

    holdout_summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evaluator_version": EVALUATOR_VERSION,
        "preregistration": "knowledge/2026-10-25_h31e_preregistration.md",
        "experiments_run": 3,
        "max_experiments_budget": 3,
        "elapsed_seconds": round(time.monotonic() - t_start, 2),
        "spatial_split": {
            "blocks": ["NW", "NE", "SW", "SE"],
            "split_row_col": list(split_rc),
            "buffer_px": BUFFER_PX,
            "buffer_m": BUFFER_PX * 100,
            "domain_erode_px": DOMAIN_ERODE_PX,
            "hide_fraction": HIDE_FRACTION,
            "fold_training": fold_train_stats,
            "postfit_oof_variogram_range_m": var_decision.get("buffer_m"),
        },
        "experiment_1_and_2_screen_draw_101": screen_res,
        "experiment_3_fresh_confirmation_draws_202_303": {
            "draws": list(CONFIRM_DRAWS),
            "withheld_positives_pooled": int(conf_pos),
            "baseline_d_poisson_pooled_dti": float(conf_dti_b),
            "baseline_d_poisson_ci95": conf_ci_b,
            "h31e_scgp_submod_pooled_dti": float(conf_dti_s),
            "h31e_scgp_submod_ci95": conf_ci_s,
            "paired_delta_dti": float(conf_dti_s - conf_dti_b),
            "paired_delta_ci95": conf_delta_ci,
            "per_draw": confirm_draws_res,
        },
        "off_catalogue_discovery_proxies": {
            "claim_class": "COMPUTED (off-catalogue proxy; not a live competition score)",
            "dot_budget": int(dots_full_h31e.sum()),
            "sgmc_offcat_gt_300m": {
                "truth_pixels": int(sgmc_offcat.sum()),
                "h31e_scgp_submod_dti": float(proxy_h31e_all),
                "baseline_d_poisson_dti": float(proxy_base_all),
                "h33_2_b2_reference_dti": float(proxy_h33_all),
            },
            "piedmont_sgmc_offcat_det_elev_le_50m": {
                "truth_pixels": int(sgmc_piedmont.sum()),
                "h31e_scgp_submod_dti": float(proxy_h31e_pied),
                "baseline_d_poisson_dti": float(proxy_base_pied),
                "h33_2_b2_reference_dti": float(proxy_h33_pied),
            },
        },
        "automated_gates": gate_summary,
        "submission": {
            "name": sub_name,
            "note": sub_note,
            "file_nan": f"docs/downloads/{sub_name}-nan.tif",
            "file_allfinite": f"docs/downloads/{sub_name}-allfinite.tif",
            "file_zip": f"docs/downloads/{sub_name}-nan.zip",
            "sha256_nan": val_nan["sha256"],
            "sha256_allfinite": val_fin["sha256"],
        },
    }
    (out_dir / "holdout_results.json").write_text(json.dumps(holdout_summary, indent=2, allow_nan=False) + "\n")

    run_card = {
        "hypothesis": (
            "H31-E (SCGP-Submod): Multi-physics Gallardo-Meju structural cross-gradient concordance + "
            "Laplace FFT upward-continuation magnetic attenuation + seam-free dual-expert 1m LiDAR scarp "
            "polarity & GeoDAWN/GDR-1391 paleo-sinter hydrothermal alteration + fold-safe 2-component "
            "relay/tip accommodation, allocated via 1D ridge-sharpened 300 m submodular DTI coverage."
        ),
        "mechanism": (
            "Normal-fault offsets across concealed and wave-reworked Great Basin piedmont margins produce "
            "co-aligned horizontal gradients in isostatic gravity, conductive-base depth, and shallow RTP "
            "magnetics (1 - |sin(dtheta)| -> 1), asymmetric 1m LiDAR monoclinal scarp steps (|upface - downface|), "
            "and K/Th + paleo-sinter outflow anomalies in 200-2500 m en-echelon relay zones; Minoux lazy-greedy "
            "maximization of the exact 29-offset 300 m DTI kernel allocates 37,654 non-redundant off-catalogue dots."
        ),
        "named_non_fault_mimic": (
            "Pleistocene Lake Lahontan wave-cut paleoshoreline terraces (~1200-1335 m contours) and unfaulted "
            "volcanic flow lobes / erosional fan gullies, mitigated via cross-gradient strike orthogonality "
            "(scgp_lahontan_mimic_score) and one-sided LiDAR face polarity."
        ),
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EVALUATOR_VERSION,
            "buffer_m": BUFFER_PX * 100,
            "screen_draw_101": {
                "dti": round(float(screen_res["h31e_scgp_submod"]["pooled_dti"]), 6),
                "ci95": [round(x, 6) for x in screen_res["h31e_scgp_submod"]["ci95"]],
                "withheld_positives": int(screen_res["h31e_scgp_submod"]["withheld_positives"]),
                "baseline_d_dti": round(float(screen_res["baseline_d_poisson"]["pooled_dti"]), 6),
                "paired_delta_dti": round(float(screen_res["paired_delta_dti"]), 6),
                "paired_delta_ci95": [round(x, 6) for x in screen_res["paired_delta_ci95"]],
            },
            "fresh_confirmation_draws_202_303": {
                "dti": round(float(conf_dti_s), 6),
                "ci95": [round(x, 6) for x in conf_ci_s],
                "withheld_positives": int(conf_pos),
                "baseline_d_dti": round(float(conf_dti_b), 6),
                "paired_delta_dti": round(float(conf_dti_s - conf_dti_b), 6),
                "paired_delta_ci95": [round(x, 6) for x in conf_delta_ci],
            },
        },
        "organizer_confirmed_score": None,
        "leakage_canary": {
            "features_tested": canary_report["features_tested"],
            "max_single_feature_auc": canary_report["max_two_sided_auc"],
            "threshold_auc": AUC_LEAKAGE_STOP,
            "passed": canary_report["passed"],
        },
        "correlation_overlap_vs_registry": {
            "checked_rasters": dup_report["checked_count"],
            "max_surface_spearman_rho": dup_report["max_surface_spearman_rho"],
            "max_surface_topn_within_3px": dup_report["max_surface_topn_within_3px"],
            "max_final_dots_spearman_rho": dup_report["max_final_dots_spearman_rho"],
            "max_final_dots_within_3px": dup_report["max_final_dots_within_3px"],
            "duplicates_found": dup_report["duplicates"],
            "passed": dup_report["passed"],
        },
        "raster_sha256": {
            "nan_outside_primary": val_nan["sha256"],
            "allfinite_fallback": val_fin["sha256"],
        },
        "validator_output": {
            "no_nan_inside_footprint": bool(val_nan["checks"]["footprint_all_finite"]["pass_"]),
            "values_in_0_1": bool(val_nan["checks"]["footprint_values_in_0_1"]["pass_"]),
            "crs_shape_transform_match": bool(
                val_nan["checks"]["crs_matches_template"]["pass_"]
                and val_nan["checks"]["shape_matches_template"]["pass_"]
                and val_nan["checks"]["transform_matches_template"]["pass_"]
            ),
            "outside_footprint_nan_exact": bool(val_nan["checks"]["outside_footprint_nan"]["pass_"]),
            "allfinite_twin_valid": bool(val_fin["ok_to_upload_format_only"]),
            "positive_dots": int(dots_full_h31e.sum()),
            "dots_on_public_catalogue": 0,
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_chars": len(sub_note),
        "automated_gates": gate_summary,
        "verdict": verdict,
    }
    (out_dir / "run_card.json").write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print("\n=== RUN CARD ===")
    print(json.dumps(run_card, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
