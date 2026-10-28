#!/usr/bin/env python3
"""Out-of-sample calibration of the design estimate.

The design maximises the tomographic posterior, so its raw model score is optimistically
biased (the optimizer's curse).  This script measures that bias on data the design did not
choose: for every one of the 98 scored sibling rasters it computes

    predicted_T_r = T_champion * (credit_per_dot_r / credit_per_dot_champion)

using the same posterior, compares it with the coverage T_r implied by that raster's
*published* score, and reports the calibration (slope, intercept, R^2, residual sd, MAE).
The fitted relation is then applied to the design's predicted T with a 95% prediction
interval.  Everything remains an ESTIMATE, never a score.

Usage: python scripts/design_calibration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import grid as G                    # noqa: E402
from gemsw import exact as EX                  # noqa: E402

ALPHA, BETA = 0.2, 0.8
M_TRUTH = 15_200.0
T_CHAMPION = 5_470.0
FACTOR = 4


def credit_per_dot(rho: np.ndarray, support: np.ndarray) -> float:
    k = EX.kernel_credit_field(support)
    return float((k * rho).sum() / max(int(support.sum()), 1))


def main() -> int:
    g = G.load_grid()
    rho_b = np.load(ROOT / "data" / "work" / "rho_blocks.npy")
    up = np.repeat(np.repeat(rho_b, FACTOR, axis=0), FACTOR, axis=1)
    rho = np.zeros(g.foot.shape, np.float64)
    h = min(g.foot.shape[0], up.shape[0])
    w = min(g.foot.shape[1], up.shape[1])
    rho[:h, :w] = up[:h, :w]

    with rasterio.open(ROOT / "data" / "work" / "champion_ref.tif") as ds:
        champ = ds.read(1) > 0
    c_champ = credit_per_dot(rho, champ)

    ladder = json.loads((ROOT / "evidence" / "probe_ladder.json").read_text())
    rows = []
    for p in ladder["probes"]:
        path = Path(p.get("path", ""))
        if not path.is_file():
            hits = sorted(Path("/tmp").glob(f"{p['site']}/**/{p['submission']}*.tif"))
            if not hits:
                continue
            path = hits[0]
        with rasterio.open(path) as ds:
            a = ds.read(1).astype(np.float64)
        a = np.where(np.isfinite(a), np.clip(a, 0.0, 1.0), 0.0)
        sup = a > 0
        c = credit_per_dot(rho, sup)
        rows.append({"site": p["site"], "submission": p["submission"], "score": p["score"],
                     "n": int(sup.sum()), "pred_T": T_CHAMPION * c / c_champ,
                     "implied_T": p["score"] * (ALPHA * p["n_pos"] + BETA * M_TRUTH)})

    pred = np.array([r["pred_T"] for r in rows])
    obs = np.array([r["implied_T"] for r in rows])
    A = np.vstack([pred, np.ones_like(pred)]).T
    (slope, intercept), *_ = np.linalg.lstsq(A, obs, rcond=None)
    fit = slope * pred + intercept
    resid = obs - fit
    dof = max(len(obs) - 2, 1)
    s2 = float((resid ** 2).sum() / dof)
    r2 = 1.0 - float((resid ** 2).sum() / ((obs - obs.mean()) ** 2).sum())
    out = {
        "evidence_class": "ESTIMATE calibration (owner-reported scores as targets; not a score)",
        "n": len(rows),
        "credit_per_dot_champion_posterior": c_champ,
        "calibration": {"slope": float(slope), "intercept": float(intercept),
                        "r2": r2, "resid_sd_T": float(np.sqrt(s2)),
                        "mae_T": float(np.abs(resid).mean()),
                        "spearman_pred_vs_implied": float(spearmanr(pred, obs).statistic)},
        "model": "implied_T = slope * pred_T + intercept;  DTI = T / (0.2 N + 0.8 * 15200)",
    }
    design = json.loads((ROOT / "evidence" / "design_estimate.json").read_text())
    st = design["stats"]
    pred_T = st["T_hat_anchor_scaled"]
    T_cal = slope * pred_T + intercept
    n = st["n_dots"]
    dti = T_cal / (ALPHA * n + BETA * M_TRUTH)
    ci_T = 1.96 * np.sqrt(s2)
    out["design"] = {
        "n_dots": n, "pred_T_posterior": pred_T,
        "T_calibrated": float(T_cal),
        "DTI_estimate_calibrated": float(dti),
        "DTI_95pi_from_T": [
            float(max(T_cal - ci_T, 0.0) / (ALPHA * n + BETA * M_TRUTH)),
            float((T_cal + ci_T) / (ALPHA * n + BETA * M_TRUTH))],
        "DTI_estimate_equal_yield_floor": st["DTI_estimate_equal_yield"],
        "DTI_estimate_raw_posterior_ceiling": st["DTI_estimate_anchor"],
        "note": ("calibrated value shrinks the posterior estimate by the measured "
                 "optimistic bias of the same predictor on 98 sibling rasters"),
    }
    (ROOT / "evidence" / "design_calibration.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["calibration"], indent=1))
    print(json.dumps(out["design"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
