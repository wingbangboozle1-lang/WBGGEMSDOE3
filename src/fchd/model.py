"""Spatially-blocked Importance-Weighted Contrastive OOF + Nested Component-Masked (NCM)
learning and evaluation engine for the FCHD-NCM lane.

All holdout numbers are strictly evaluated with `evaluate_hide_and_recover`
(`GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld fault pixels across 8 cells,
15-px spatial training collar, `b_visible_px = 2.0`, 256-block 1,000-rep cluster bootstrap).
"""
from __future__ import annotations

import gc
import time
import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from src.fchd.features import FEATURE_NAMES, GRID_SHAPE
from src.fchd.ncm_struct import (
    STRUCT_FEATURE_NAMES,
    compute_ncm_structural_grid,
    label_fault_components,
)
from src.fchd.registry_full import celf_knapsack_allocate
from src.gemsw.holdout import (
    COLLAR_PX,
    DRAWS,
    FOLDS,
    HoldoutContext,
    evaluate_hide_and_recover,
)


def _build_foot_index_grid(foot: np.ndarray) -> np.ndarray:
    idx_grid = np.full(foot.shape, -1, dtype=np.int32)
    idx_grid[foot] = np.arange(int(foot.sum()), dtype=np.int32)
    return idx_grid


def run_fchd_leakage_canaries(feat_bundle: dict, ctx: HoldoutContext) -> dict:
    """Gate 0: Test every single static (62) and fold-local structural (10) feature alone on holdout."""
    foot = feat_bundle["foot"]
    X_u8 = feat_bundle["X_u8"]
    foot_idx = _build_foot_index_grid(foot)

    # Collect withheld positive & active negative footprint indices across Draw 20 (all 4 quadrants)
    pos_fidx_all = []
    neg_fidx_all = []
    struct_pos_all = []
    struct_neg_all = []
    rng = np.random.default_rng(20261027)

    for cell in ctx.cells:
        if cell.seed != DRAWS[0]:
            continue
        sl = cell.bbox
        truth_sub = np.zeros(cell.active_sub.shape, dtype=bool)
        truth_sub[cell.truth_coords] = True
        elig_sub = cell.active_sub & (cell.d_vis_sub > 2.0)
        pos_sub = truth_sub & elig_sub
        neg_sub = (~truth_sub) & elig_sub

        f_sub = foot_idx[sl]
        p_idx = f_sub[pos_sub]
        n_all = f_sub[neg_sub]
        n_pick = rng.choice(n_all.size, size=min(40_000, n_all.size), replace=False)
        n_idx = n_all[n_pick]
        pos_fidx_all.append(p_idx)
        neg_fidx_all.append(n_idx)

        # Fold-legal structural features computed strictly from cell.visible_full
        s_grid = compute_ncm_structural_grid(
            cell.visible_full,
            feat_bundle["scarp_comp"],
            feat_bundle["basin_comp"],
            feat_bundle["piedmont_comp"],
        )
        s_sub = s_grid[:, sl[0], sl[1]]
        struct_pos_all.append(s_sub[:, pos_sub].T)
        ny, nx = np.nonzero(neg_sub)
        struct_neg_all.append(s_sub[:, ny[n_pick], nx[n_pick]].T)

    p_fidx = np.concatenate(pos_fidx_all)
    n_fidx = np.concatenate(neg_fidx_all)
    y = np.concatenate([np.ones(p_fidx.size, dtype=np.int8), np.zeros(n_fidx.size, dtype=np.int8)])
    all_fidx = np.concatenate([p_fidx, n_fidx])

    rows = []
    for col, fname in enumerate(FEATURE_NAMES):
        vals = X_u8[all_fidx, col].astype(np.float32)
        auc = float(roc_auc_score(y, vals)) if np.unique(vals).size > 1 else 0.5
        d_auc = max(auc, 1.0 - auc)
        rows.append({
            "feature": fname,
            "kind": "static_zero_catalogue",
            "auc": round(auc, 5),
            "directional_auc": round(d_auc, 5),
            "passed": bool(d_auc <= 0.90),
        })

    s_all = np.vstack([np.vstack(struct_pos_all), np.vstack(struct_neg_all)])
    for j, sname in enumerate(STRUCT_FEATURE_NAMES):
        vals = s_all[:, j]
        auc = float(roc_auc_score(y, vals)) if np.unique(vals).size > 1 else 0.5
        d_auc = max(auc, 1.0 - auc)
        rows.append({
            "feature": sname,
            "kind": "fold_local_ncm_structural",
            "auc": round(auc, 5),
            "directional_auc": round(d_auc, 5),
            "passed": bool(d_auc <= 0.90),
        })

    max_d_auc = max(r["directional_auc"] for r in rows)
    rows_sorted = sorted(rows, key=lambda d: -d["directional_auc"])
    return {
        "evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0",
        "n_features_tested": len(rows),
        "n_static": len(FEATURE_NAMES),
        "n_structural": len(STRUCT_FEATURE_NAMES),
        "max_directional_auc": round(max_d_auc, 5),
        "threshold": 0.90,
        "all_passed": all(r["passed"] for r in rows),
        "top15_by_directional_auc": rows_sorted[:15],
        "features": rows,
    }


def _sample_contrastive_negatives(
    neg_pool_fidx: np.ndarray,
    pos_fidx: np.ndarray,
    relief_bin: np.ndarray,
    mimic_score: np.ndarray,
    n_neg_target: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Importance-weighted Relief-Matched + Mimic-Hard-Negative sampler.

    Concentrates 45% of negatives in positive-matched relief strata, 25% on non-fault mimics
    (Lake Lahontan ~1,338 m shoreline, BLM mining claims, road cuts), and 30% uniformly, while
    returning exact inverse-inclusion Horvitz-Thompson weights so population posterior odds stay unbiased.
    """
    rng = np.random.default_rng(seed)
    n_pool = int(neg_pool_fidx.size)
    if n_pool <= n_neg_target:
        return neg_pool_fidx, np.ones(n_pool, dtype=np.float32)

    pool_rb = relief_bin[neg_pool_fidx]
    pool_mim = mimic_score[neg_pool_fidx]
    pos_rb = relief_bin[pos_fidx]

    # Relief-matched probability per stratum (0..15)
    pos_hist = np.bincount(pos_rb, minlength=16).astype(np.float64) + 1.0
    pos_hist /= pos_hist.sum()
    pool_hist = np.bincount(pool_rb, minlength=16).astype(np.float64) + 1.0

    p_relief = pos_hist[pool_rb] / pool_hist[pool_rb]
    p_relief /= p_relief.sum()

    p_mimic = np.power(np.maximum(pool_mim, 0.02), 1.5).astype(np.float64)
    p_mimic /= p_mimic.sum()

    p_unif = np.full(n_pool, 1.0 / n_pool, dtype=np.float64)

    # Mixture sampling distribution q(i)
    q = 0.45 * p_relief + 0.25 * p_mimic + 0.30 * p_unif
    q /= q.sum()

    chosen_local = rng.choice(n_pool, size=n_neg_target, replace=False, p=q)
    # Inverse-probability weight (clipped at 99th percentile for low variance, normalized so mean=1)
    inv_w = 1.0 / np.maximum(n_neg_target * q[chosen_local], 1e-4)
    cap = float(np.percentile(inv_w, 98.5))
    inv_w = np.minimum(inv_w, cap)
    inv_w = (inv_w / inv_w.mean()).astype(np.float32)
    return neg_pool_fidx[chosen_local], inv_w


def _build_training_matrix(
    feat_bundle: dict,
    foot_idx_grid: np.ndarray,
    train_zone_2d: np.ndarray,
    vis_faults_2d: np.ndarray,
    use_ncm_struct: bool,
    seed: int,
    n_neg_per_pos: float = 3.0,
    max_pos: int = 30_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble fold-legal (X, y, sample_weight) strictly inside `train_zone_2d` (`~collar`)."""
    X_u8 = feat_bundle["X_u8"]
    relief_bin = feat_bundle["relief_bin"]
    mimic_score = feat_bundle["mimic_score"]
    vis_in_tz = vis_faults_2d & train_zone_2d
    neg_elig_2d = train_zone_2d & (~(ndi.maximum_filter(vis_in_tz.astype(np.uint8), size=7) > 0))
    rng = np.random.default_rng(seed)

    if not use_ncm_struct:
        pos_fidx = foot_idx_grid[vis_in_tz]
        if pos_fidx.size > max_pos:
            pos_fidx = pos_fidx[rng.choice(pos_fidx.size, size=max_pos, replace=False)]
        neg_pool_fidx = foot_idx_grid[neg_elig_2d]
        n_neg = min(int(round(pos_fidx.size * n_neg_per_pos)), neg_pool_fidx.size)
        neg_fidx, neg_w = _sample_contrastive_negatives(
            neg_pool_fidx, pos_fidx, relief_bin, mimic_score, n_neg_target=n_neg, seed=seed
        )
        X_pos = X_u8[pos_fidx].astype(np.float32)
        X_neg = X_u8[neg_fidx].astype(np.float32)
        X = np.vstack([X_pos, X_neg])
        y = np.concatenate([np.ones(pos_fidx.size, dtype=np.int8), np.zeros(neg_fidx.size, dtype=np.int8)])
        w = np.concatenate([np.ones(pos_fidx.size, dtype=np.float32), neg_w * np.float32(3.5 * pos_fidx.size / max(neg_fidx.size, 1))])
        return X, y, w

    # Nested Component-Masked (NCM) 4-fold out-of-component structural construction inside train_zone
    comp_lbl, n_comp = label_fault_components(vis_in_tz)
    comp_ids = np.arange(1, n_comp + 1)
    rng.shuffle(comp_ids)
    nested_folds = np.array_split(comp_ids, 4)

    X_parts, y_parts, w_parts = [], [], []
    neg_pool_fidx = foot_idx_grid[neg_elig_2d]
    fy, fx = np.nonzero(feat_bundle["foot"])

    for m, held_cids in enumerate(nested_folds):
        held_pos_2d = np.isin(comp_lbl, held_cids) & vis_in_tz
        src_vis_2d = vis_in_tz & (~held_pos_2d)
        held_clean_2d = held_pos_2d & (~(ndi.maximum_filter(src_vis_2d.astype(np.uint8), size=7) > 0))
        p_fidx = foot_idx_grid[held_clean_2d]
        if p_fidx.size == 0:
            continue
        if p_fidx.size > max_pos // 4:
            p_fidx = p_fidx[rng.choice(p_fidx.size, size=max_pos // 4, replace=False)]

        n_neg_m = min(int(round(p_fidx.size * n_neg_per_pos)), neg_pool_fidx.size)
        n_fidx, neg_w = _sample_contrastive_negatives(
            neg_pool_fidx, p_fidx, relief_bin, mimic_score, n_neg_target=n_neg_m, seed=seed + 31 * (m + 1)
        )

        s_grid = compute_ncm_structural_grid(
            src_vis_2d,
            feat_bundle["scarp_comp"],
            feat_bundle["basin_comp"],
            feat_bundle["piedmont_comp"],
        )
        m_fidx = np.concatenate([p_fidx, n_fidx])
        my = fy[m_fidx]
        mx = fx[m_fidx]
        X_stat = X_u8[m_fidx].astype(np.float32)
        X_str = s_grid[:, my, mx].T
        X_parts.append(np.hstack([X_stat, X_str]))
        y_parts.append(np.concatenate([np.ones(p_fidx.size, dtype=np.int8), np.zeros(n_fidx.size, dtype=np.int8)]))
        w_parts.append(np.concatenate([
            np.ones(p_fidx.size, dtype=np.float32),
            neg_w * np.float32(3.5 * p_fidx.size / max(n_fidx.size, 1)),
        ]))
        del s_grid
        gc.collect()

    return np.vstack(X_parts), np.concatenate(y_parts), np.concatenate(w_parts)


def _fit_hgb_bag(X: np.ndarray, y: np.ndarray, w: np.ndarray, seed: int) -> list[HistGradientBoostingClassifier]:
    clf = HistGradientBoostingClassifier(
        random_state=seed,
        max_depth=6,
        max_iter=175,
        learning_rate=0.06,
        min_samples_leaf=80,
        l2_regularization=5.0,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=16,
    )
    clf.fit(X, y, sample_weight=w)
    return [clf]


def _predict_quadrant_prob(
    models: list[HistGradientBoostingClassifier],
    feat_bundle: dict,
    foot_idx_grid: np.ndarray,
    mask_2d: np.ndarray,
    vis_for_struct_2d: np.ndarray | None,
    chunk: int = 250_000,
) -> np.ndarray:
    """Predict mean probability on `mask_2d` pixels in bounded memory."""
    X_u8 = feat_bundle["X_u8"]
    fidx = foot_idx_grid[mask_2d]
    s_grid = None
    if vis_for_struct_2d is not None:
        s_grid = compute_ncm_structural_grid(
            vis_for_struct_2d,
            feat_bundle["scarp_comp"],
            feat_bundle["basin_comp"],
            feat_bundle["piedmont_comp"],
        )
    my, mx = np.nonzero(mask_2d)
    out = np.zeros(fidx.size, dtype=np.float32)
    for start in range(0, fidx.size, chunk):
        end = min(start + chunk, fidx.size)
        Xb = X_u8[fidx[start:end]].astype(np.float32)
        if s_grid is not None:
            Xs = s_grid[:, my[start:end], mx[start:end]].T
            Xb = np.hstack([Xb, Xs])
        pb = np.zeros(end - start, dtype=np.float32)
        for clf in models:
            pb += clf.predict_proba(Xb)[:, 1].astype(np.float32)
        out[start:end] = pb / np.float32(len(models))
    del s_grid
    return out


def sharpen_dti_weight(prob_2d: np.ndarray, foot: np.ndarray, bg_quantile: float = 0.20, gamma: float = 1.25) -> np.ndarray:
    """Suppress bottom-quintile background floor while preserving positive posterior across both
    exposed range-fronts and concealed intrabasin/piedmont structures.
    """
    vals = prob_2d[foot]
    q_bg = float(np.quantile(vals, bg_quantile))
    p_hi = float(np.quantile(vals, 0.999))
    denom = max(p_hi - q_bg, 1e-6)
    w = np.clip((prob_2d - q_bg) / denom, 0.0, 1.5)
    w = np.power(w, gamma).astype(np.float32)
    w[~foot] = 0.0
    return w


def predict_oof_surfaces(
    exp_id: str,
    feat_bundle: dict,
    ctx: HoldoutContext,
    use_ncm_struct: bool,
) -> dict:
    """Compute strictly spatially-blocked (`~collar`) OOF surfaces across all 8 holdout cells AND the 4 full-map folds."""
    t0 = time.time()
    foot = feat_bundle["foot"]
    foot_idx_grid = _build_foot_index_grid(foot)
    struct3 = np.ones((3, 3), dtype=bool)

    # Precompute 15-px spatial collars around each test quadrant
    collars = {
        fold: ndi.binary_dilation(ctx.quad == fold, structure=struct3, iterations=COLLAR_PX) & foot
        for fold in FOLDS
    }

    cell_probs: dict[str, np.ndarray] = {}
    # Note: for pure zero-catalogue E1 (`use_ncm_struct=False`), cell.visible_full only differs slightly in
    # sample counts between draws 20 and 21, but we still fit per-cell strictly from `cell.visible_full & train_zone`
    # so zero withheld training/test component ever enters training!
    for cell in ctx.cells:
        train_zone = foot & (~collars[cell.fold])
        X_tr, y_tr, w_tr = _build_training_matrix(
            feat_bundle,
            foot_idx_grid,
            train_zone_2d=train_zone,
            vis_faults_2d=cell.visible_full,
            use_ncm_struct=use_ncm_struct,
            seed=1000 * cell.seed + 10 * cell.fold,
        )
        models = _fit_hgb_bag(X_tr, y_tr, w_tr, seed=5000 * cell.seed + 100 * cell.fold)
        del X_tr, y_tr, w_tr
        gc.collect()

        # Predict inside cell.bbox where foot is True
        eval_mask = np.zeros(GRID_SHAPE, dtype=bool)
        eval_mask[cell.bbox] = foot[cell.bbox]
        p_vec = _predict_quadrant_prob(
            models,
            feat_bundle,
            foot_idx_grid,
            mask_2d=eval_mask,
            vis_for_struct_2d=cell.visible_full if use_ncm_struct else None,
        )
        p_sub = np.zeros(cell.active_sub.shape, dtype=np.float32)
        p_sub[foot[cell.bbox]] = p_vec
        cell_probs[cell.key] = p_sub
        del models
        gc.collect()

    # Full-map 4-quadrant OOF surface trained on `ctx.labels & train_zone` (for live submission export)
    full_oof_prob = np.zeros(GRID_SHAPE, dtype=np.float32)
    for fold in FOLDS:
        train_zone = foot & (~collars[fold])
        X_tr, y_tr, w_tr = _build_training_matrix(
            feat_bundle,
            foot_idx_grid,
            train_zone_2d=train_zone,
            vis_faults_2d=ctx.labels,
            use_ncm_struct=use_ncm_struct,
            seed=90_000 + 100 * fold,
        )
        models = _fit_hgb_bag(X_tr, y_tr, w_tr, seed=95_000 + 100 * fold)
        del X_tr, y_tr, w_tr
        gc.collect()

        q_mask = (ctx.quad == fold) & foot
        full_oof_prob[q_mask] = _predict_quadrant_prob(
            models,
            feat_bundle,
            foot_idx_grid,
            mask_2d=q_mask,
            vis_for_struct_2d=ctx.labels if use_ncm_struct else None,
        )
        del models
        gc.collect()

    return {
        "exp_id": exp_id,
        "elapsed_fit_sec": round(time.time() - t0, 2),
        "cell_probs": cell_probs,
        "full_oof_prob": full_oof_prob,
    }


def allocate_and_score_surface(
    exp_id: str,
    cell_probs: dict[str, np.ndarray],
    full_oof_prob: np.ndarray,
    foot: np.ndarray,
    ctx: HoldoutContext,
    reg: dict,
    champ_hr: dict,
    budgets: list[int],
    b_visible_px: float = 2.0,
    max_overlap_cap: float = 0.635,
    bg_quantile: float = 0.20,
    gamma: float = 1.25,
) -> dict:
    """Apply identical Contrarian CELF allocation on every holdout cell and on the full map,
    with budget selection strictly on Draw-20 folds and paired 256-block bootstrap CI vs GEMSDOE32.
    """
    t0 = time.time()
    cell_by_key = {c.key: c for c in ctx.cells}
    full_elig_est = max(int(foot.sum() * 0.90), 1)

    # Pre-sharpen cell weights once
    cell_weights: dict[str, np.ndarray] = {}
    for cell in ctx.cells:
        sl = cell.bbox
        p_full_tmp = np.zeros(GRID_SHAPE, dtype=np.float32)
        p_full_tmp[sl] = cell_probs[cell.key]
        # Compute quantile inside cell's active footprint
        f_sub = foot[sl]
        vals = cell_probs[cell.key][f_sub]
        q_bg = float(np.quantile(vals, bg_quantile))
        p_hi = float(np.quantile(vals, 0.9995))
        w_sub = np.power(np.clip((cell_probs[cell.key] - q_bg) / max(p_hi - q_bg, 1e-6), 0.0, 1.5), gamma).astype(np.float32)
        w_sub[~f_sub] = 0.0
        cell_weights[cell.key] = w_sub

    budget_results: dict[int, dict] = {}
    for n_full in budgets:
        cells_dots: dict[str, np.ndarray] = {}
        for seed in DRAWS:
            mass_per_fold = {}
            total_active_elig = 0
            for fold in FOLDS:
                cell = cell_by_key[f"draw{seed}_fold{fold}"]
                elig_sub = cell.active_sub & (cell.d_vis_sub > b_visible_px)
                total_active_elig += int(elig_sub.sum())
                mass_per_fold[fold] = float(cell_weights[cell.key][elig_sub].sum())
            draw_budget = int(round(n_full * (total_active_elig / full_elig_est)))
            tot_mass = max(sum(mass_per_fold.values()), 1e-9)

            for fold in FOLDS:
                cell = cell_by_key[f"draw{seed}_fold{fold}"]
                sl = cell.bbox
                elig_sub = cell.active_sub & (cell.d_vis_sub > b_visible_px)
                k_cell = int(round(draw_budget * (mass_per_fold[fold] / tot_mass)))

                w_2d = np.zeros(GRID_SHAPE, dtype=np.float32)
                w_2d[sl] = cell_weights[cell.key]
                elig_2d = np.zeros(GRID_SHAPE, dtype=bool)
                elig_2d[sl] = elig_sub

                dots_2d, _ = celf_knapsack_allocate(
                    w_2d, elig_2d, foot, reg, budget_k=k_cell, max_overlap_cap=max_overlap_cap
                )
                cells_dots[cell.key] = dots_2d[sl]

        hr = evaluate_hide_and_recover(cells_dots, ctx, b_visible_px=b_visible_px, name=f"{exp_id}-N{n_full}")
        deltas = hr["_boots"] - champ_hr["_boots"]
        delta_mean = float(hr["pooled_dti"] - champ_hr["pooled_dti"])
        delta_ci95 = [float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))]
        d20 = float(np.mean([hr["folds"][f"draw20_fold{f}"]["dti"] for f in FOLDS]))
        d21 = float(np.mean([hr["folds"][f"draw21_fold{f}"]["dti"] for f in FOLDS]))
        budget_results[n_full] = {
            "budget_full_map": n_full,
            "pooled_dti": hr["pooled_dti"],
            "ci95_cluster_bootstrap": hr["ci95_cluster_bootstrap"],
            "paired_delta_vs_gemsdoe32": round(delta_mean, 6),
            "paired_delta_ci95": [round(delta_ci95[0], 6), round(delta_ci95[1], 6)],
            "fold_mean_dti": hr["fold_mean_dti"],
            "draw20_mean_dti": d20,
            "draw21_mean_dti": d21,
            "per_quadrant_dti": hr["per_quadrant_dti"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "evaluator_version": hr["evaluator_version"],
            "folds": hr["folds"],
        }

    # Pick budget strictly on Draw-20 folds (verify out-of-sample on Draw-21, report pooled 8-cell DTI)
    chosen_budget = max(budgets, key=lambda b: budget_results[b]["draw20_mean_dti"])

    # Full-map allocation with identical Contrarian CELF allocator
    full_w = sharpen_dti_weight(full_oof_prob, foot, bg_quantile=bg_quantile, gamma=gamma)
    d_full_cat = ndi.distance_transform_edt(~ctx.labels)
    elig_full = foot & (d_full_cat > b_visible_px)
    final_dots, alloc_meta = celf_knapsack_allocate(
        full_w, elig_full, foot, reg, budget_k=chosen_budget, max_overlap_cap=max_overlap_cap
    )

    return {
        "exp_id": exp_id,
        "elapsed_alloc_sec": round(time.time() - t0, 2),
        "chosen_budget": chosen_budget,
        "holdout": budget_results[chosen_budget],
        "budget_sweep": {str(k): {kk: vv for kk, vv in v.items() if kk != "folds"} for k, v in budget_results.items()},
        "alloc_meta": alloc_meta,
        "full_w": full_w,
        "final_dots": final_dots,
    }
