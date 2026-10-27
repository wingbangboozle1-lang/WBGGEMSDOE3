"""Protocol Rule 4 Single-Feature Leakage Canary for Lane THCS-OOF."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from src.gemsw.holdout import HoldoutContext


def run_leakage_canaries(
    mm: np.memmap,
    foot: np.ndarray,
    feature_names: list[str],
    ctx: HoldoutContext,
    max_auc_threshold: float = 0.90,
    neg_sample_per_cell: int = 40_000,
    seed: int = 20261027,
) -> dict:
    """Compute standalone ROC-AUC of every single feature on withheld holdout positives."""
    H, W = foot.shape
    foot_idx_grid = np.full((H, W), -1, dtype=np.int32)
    foot_idx_grid[foot] = np.arange(int(foot.sum()), dtype=np.int32)

    rng = np.random.default_rng(seed)
    pos_indices = []
    neg_indices = []

    for cell in ctx.cells:
        sl = cell.bbox
        idx_sub = foot_idx_grid[sl]
        ty, tx = cell.truth_coords
        p_idx = idx_sub[ty, tx]
        p_idx = p_idx[p_idx >= 0]
        pos_indices.append(p_idx)

        neg_mask = cell.active_sub & (cell.k_dg_sub == 0.0)
        if cell.d_vis_sub is not None:
            neg_mask = neg_mask & (cell.d_vis_sub > 3.0)
        ny, nx = np.nonzero(neg_mask)
        n_idx = idx_sub[ny, nx]
        n_idx = n_idx[n_idx >= 0]
        if n_idx.size > neg_sample_per_cell:
            n_idx = rng.choice(n_idx, size=neg_sample_per_cell, replace=False)
        neg_indices.append(n_idx)

    all_pos = np.concatenate(pos_indices)
    all_neg = np.concatenate(neg_indices)
    sample_idx = np.concatenate([all_pos, all_neg])
    y = np.concatenate([np.ones(all_pos.size, dtype=np.int8), np.zeros(all_neg.size, dtype=np.int8)])

    rows = []
    for j, name in enumerate(feature_names):
        vals = np.asarray(mm[sample_idx, j], dtype=np.float64)
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        if np.std(vals) < 1e-12:
            auc = 0.5
        else:
            auc = float(roc_auc_score(y, vals))
        eff_auc = max(auc, 1.0 - auc)
        rows.append({
            "feature_index": j,
            "feature": name,
            "raw_auc": round(auc, 5),
            "directional_auc": round(eff_auc, 5),
            "passed": bool(eff_auc <= max_auc_threshold),
        })

    rows_sorted = sorted(rows, key=lambda r: -r["directional_auc"])
    max_dir_auc = max(r["directional_auc"] for r in rows)
    return {
        "lane": "THCS-OOF",
        "evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0",
        "rule": "Protocol Rule 4: test each feature alone on holdout first; AUC > 0.90 means leakage until proven otherwise",
        "threshold": max_auc_threshold,
        "n_features_tested": len(rows),
        "n_withheld_positive_samples": int(all_pos.size),
        "n_withheld_negative_samples": int(all_neg.size),
        "max_directional_auc": round(max_dir_auc, 5),
        "all_passed": bool(max_dir_auc <= max_auc_threshold),
        "top10_features_by_auc": rows_sorted[:10],
        "features": rows,
    }
