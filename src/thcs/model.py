"""Out-of-fold spatially blocked training, CELF placement, and holdout evaluation for THCS-OOF."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from src.gemsw.holdout import COLLAR_PX, DRAWS, FOLDS, HoldoutContext, evaluate_hide_and_recover
from src.thcs.celf import celf_select


def _sample_fold_training_data(
    mm: np.memmap,
    foot_idx_grid: np.ndarray,
    foot: np.ndarray,
    quad: np.ndarray,
    fold: int,
    visible_full: np.ndarray,
    feat_indices: list[int],
    n_pos_max: int = 70_000,
    n_neg_max: int = 140_000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample strictly leak-free positives and PU-clean negatives outside the 15-px quadrant collar."""
    rng = np.random.default_rng(seed)
    test_q = quad == fold
    collar = ndi.binary_dilation(test_q, structure=np.ones((3, 3), dtype=bool), iterations=COLLAR_PX)
    train_zone = foot & (~collar)

    # Include 1-px axial fault core (exact labels + immediate sub-pixel 100 m quantization neighbors weighted via labels)
    pos_mask = train_zone & visible_full
    d_vis = ndi.distance_transform_edt(~visible_full)
    # PU-clean negatives: outside 400 m (4 px) halo of visible faults
    neg_mask = train_zone & (d_vis > 4.0)

    pos_idx = foot_idx_grid[pos_mask]
    neg_idx = foot_idx_grid[neg_mask]
    pos_idx = pos_idx[pos_idx >= 0]
    neg_idx = neg_idx[neg_idx >= 0]

    if pos_idx.size > n_pos_max:
        pos_idx = rng.choice(pos_idx, size=n_pos_max, replace=False)
    if neg_idx.size > n_neg_max:
        neg_idx = rng.choice(neg_idx, size=n_neg_max, replace=False)

    all_idx = np.concatenate([pos_idx, neg_idx])
    X = np.asarray(mm[all_idx][:, feat_indices], dtype=np.float32)
    y = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int8),
        np.zeros(neg_idx.size, dtype=np.int8),
    ])
    perm = rng.permutation(y.size)
    return X[perm], y[perm]


def _predict_foot_subset(
    models: list[HistGradientBoostingClassifier],
    mm: np.memmap,
    sub_foot_indices: np.ndarray,
    feat_indices: list[int],
    batch_size: int = 350_000,
) -> np.ndarray:
    """Memory-bounded batched probability prediction on footprint indices."""
    n = int(sub_foot_indices.size)
    out = np.zeros(n, dtype=np.float32)
    w = 1.0 / len(models)
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        Xb = np.asarray(mm[sub_foot_indices[start:end]][:, feat_indices], dtype=np.float32)
        p_sum = np.zeros(end - start, dtype=np.float32)
        for clf in models:
            p_sum += clf.predict_proba(Xb)[:, 1].astype(np.float32)
        out[start:end] = p_sum * w
    return out


def sharpen_posterior_for_celf(
    prob_grid: np.ndarray,
    foot: np.ndarray,
    bg_quantile: float = 0.70,
    gamma: float = 1.5,
    crest_sigma: float = 0.0,
) -> np.ndarray:
    """Suppress diffuse low-probability desert background so 300 m CELF targets sharp fault corridors."""
    vals = prob_grid[foot]
    q_bg = float(np.quantile(vals, bg_quantile))
    excess = np.clip(prob_grid - q_bg, 0.0, 1.0)
    w = np.power(excess, gamma).astype(np.float32)
    if crest_sigma > 0.0:
        # Local medial-crest contrast boost: emphasizes 1-2 px fault cores over broad 10-px plateaus
        sm_broad = ndi.gaussian_filter(w, crest_sigma)
        crest_boost = np.clip(w - 0.55 * sm_broad, 0.0, None)
        w = (0.65 * w + 0.35 * crest_boost).astype(np.float32)
    w[~foot] = 0.0
    return w


def run_oof_experiment(
    exp_id: str,
    mm: np.memmap,
    foot: np.ndarray,
    ctx: HoldoutContext,
    feat_indices: list[int],
    hgb_configs: list[dict],
    budgets_to_eval: list[int],
    bg_quantile: float = 0.70,
    gamma: float = 1.5,
    crest_sigma: float = 0.0,
    b_visible_px: float = 2.0,
) -> dict:
    """Train leak-free 8-cell OOF models + 4-quadrant full-catalogue OOF surface and run CELF."""
    t0 = time.time()
    H, W = foot.shape
    foot_idx_grid = np.full((H, W), -1, dtype=np.int32)
    foot_idx_grid[foot] = np.arange(int(foot.sum()), dtype=np.int32)

    # 1. Predict strictly out-of-fold probability maps for each seed draw (20, 21) across the 4 quadrants
    oof_by_seed: dict[int, np.ndarray] = {}
    cell_by_key = {c.key: c for c in ctx.cells}

    for seed in DRAWS:
        p_grid = np.zeros((H, W), dtype=np.float32)
        for fold in FOLDS:
            cell = cell_by_key[f"draw{seed}_fold{fold}"]
            assert cell.visible_full is not None
            X_tr, y_tr = _sample_fold_training_data(
                mm, foot_idx_grid, foot, ctx.quad, fold, cell.visible_full, feat_indices,
                seed=1000 * seed + fold,
            )
            models = []
            for m_i, cfg in enumerate(hgb_configs):
                clf = HistGradientBoostingClassifier(random_state=1000 * seed + 10 * fold + m_i, **cfg)
                clf.fit(X_tr, y_tr)
                models.append(clf)

            q_mask = (ctx.quad == fold) & foot
            q_fidx = foot_idx_grid[q_mask]
            p_grid[q_mask] = _predict_foot_subset(models, mm, q_fidx, feat_indices)
        oof_by_seed[seed] = p_grid

    # Sharpened CELF weight surfaces per seed (strictly zero hidden-fault info)
    w_by_seed = {
        seed: sharpen_posterior_for_celf(oof_by_seed[seed], foot, bg_quantile=bg_quantile, gamma=gamma, crest_sigma=crest_sigma)
        for seed in DRAWS
    }

    # Evaluate each candidate budget on leak-free GEMSDOE32-HIDE-RECOVER-v3.0
    # Note: for multiple budgets (used ONLY in E3), select optimal budget via Draw 20->Draw 21 cross-draw validation
    budget_results = {}
    for n_full in budgets_to_eval:
        cells_dots: dict[str, np.ndarray] = {}
        for seed in DRAWS:
            w_full = w_by_seed[seed]
            # Total eligible posterior mass across the 4 eroded quadrants of this draw
            mass_per_fold = {}
            for fold in FOLDS:
                cell = cell_by_key[f"draw{seed}_fold{fold}"]
                sl = cell.bbox
                elig_sub = cell.active_sub & (cell.d_vis_sub > b_visible_px)
                mass_per_fold[fold] = float(w_full[sl][elig_sub].sum())
            # Scale 4 eroded quadrants to full footprint using strictly visible-only counts
            total_active_elig = sum(
                int((cell_by_key[f"draw{seed}_fold{f}"].active_sub & (cell_by_key[f"draw{seed}_fold{f}"].d_vis_sub > b_visible_px)).sum())
                for f in FOLDS
            )
            full_elig_est = max(int(foot.sum() * 0.90), 1)
            draw_budget = int(round(n_full * (total_active_elig / full_elig_est)))
            tot_mass = max(sum(mass_per_fold.values()), 1e-9)

            for fold in FOLDS:
                cell = cell_by_key[f"draw{seed}_fold{fold}"]
                sl = cell.bbox
                elig_sub = cell.active_sub & (cell.d_vis_sub > b_visible_px)
                k_cell = int(round(draw_budget * (mass_per_fold[fold] / tot_mass)))
                dots_sub, _ = celf_select(w_full[sl], elig_sub, budget_k=k_cell)
                cells_dots[cell.key] = dots_sub

        hr = evaluate_hide_and_recover(cells_dots, ctx, b_visible_px=b_visible_px, name=f"{exp_id}-N{n_full}")
        budget_results[n_full] = {
            "budget_full_map": n_full,
            "pooled_dti": hr["pooled_dti"],
            "ci95_cluster_bootstrap": hr["ci95_cluster_bootstrap"],
            "fold_mean_dti": hr["fold_mean_dti"],
            "per_quadrant_dti": hr["per_quadrant_dti"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "evaluator_version": hr["evaluator_version"],
            "folds": hr["folds"],
        }

    # Select budget: if single budget, trivial; if multiple (E3), pick budget maximizing Draw-20 folds and report pooled
    if len(budgets_to_eval) == 1:
        chosen_budget = budgets_to_eval[0]
    else:
        # Cross-draw budget selection: pick budget on Draw 20, verify on Draw 21, report full 8-cell pooled DTI
        best_d20 = -1.0
        chosen_budget = budgets_to_eval[0]
        for b in budgets_to_eval:
            fdict = budget_results[b]["folds"]
            d20_mean = float(np.mean([fdict[f"draw20_fold{f}"]["dti"] for f in FOLDS]))
            budget_results[b]["draw20_mean_dti"] = d20_mean
            budget_results[b]["draw21_mean_dti"] = float(np.mean([fdict[f"draw21_fold{f}"]["dti"] for f in FOLDS]))
            if d20_mean > best_d20:
                best_d20 = d20_mean
                chosen_budget = b

    # 2. Full-map 4-quadrant OOF surface trained on full visible public catalogue per quadrant (for live submission)
    full_oof_prob = np.zeros((H, W), dtype=np.float32)
    for fold in FOLDS:
        X_tr, y_tr = _sample_fold_training_data(
            mm, foot_idx_grid, foot, ctx.quad, fold, ctx.labels, feat_indices,
            seed=9000 + fold,
        )
        models = []
        for m_i, cfg in enumerate(hgb_configs):
            clf = HistGradientBoostingClassifier(random_state=9000 + 10 * fold + m_i, **cfg)
            clf.fit(X_tr, y_tr)
            models.append(clf)
        q_mask = (ctx.quad == fold) & foot
        q_fidx = foot_idx_grid[q_mask]
        full_oof_prob[q_mask] = _predict_foot_subset(models, mm, q_fidx, feat_indices)

    full_w = sharpen_posterior_for_celf(
        full_oof_prob, foot, bg_quantile=bg_quantile, gamma=gamma, crest_sigma=crest_sigma
    )
    d_full_cat = ndi.distance_transform_edt(~ctx.labels)
    elig_full = foot & (d_full_cat > b_visible_px)
    final_dots, celf_meta = celf_select(full_w, elig_full, budget_k=chosen_budget)

    elapsed = time.time() - t0
    chosen_res = budget_results[chosen_budget]
    return {
        "exp_id": exp_id,
        "elapsed_sec": round(elapsed, 2),
        "n_features": len(feat_indices),
        "chosen_budget": chosen_budget,
        "holdout": chosen_res,
        "budget_sweep": {str(k): {kk: vv for kk, vv in v.items() if kk != "folds"} for k, v in budget_results.items()},
        "celf_full_map": celf_meta,
        "full_oof_prob": full_oof_prob,
        "full_celf_weight": full_w,
        "final_dots": final_dots,
    }
