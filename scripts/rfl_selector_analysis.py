#!/usr/bin/env python3
"""Selector analysis (Pass 2, session arena/bd44f94b): one calibration, every candidate.

1) Reproduce the skarpline lane's SGMC-proxy calibration (src/gemsdoe/validation.py,
   reused unchanged) from locally byte-verified files; check the published 0.4284 estimate.
2) Same-model leaderboard-scale ESTIMATEs (never scores) for skarpline, HCE-1, CSPES,
   RFL final dots and the nine focus leaders, with M-sensitivity.
3) Which local evaluator ranks owner-reported scores?  Spearman of static HOLDOUT-DTI,
   SGMC hit-rate h, SGMC proxy DTI and the calibrated estimate vs the 118 owner-scored
   ledger rasters (data/ledger/index.json; scores OWNER-REPORTED, no receipts).
4) Full rebuilt-registry (120 unique masks) uniqueness re-audit of the two saved files
   currently presented as downloadable (skarpline was previously checked vs 20 files).

Output: evidence/rfl_selector_analysis.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gemsw import grid as G, holdout as H  # noqa: E402
from gemsdoe import validation as V  # noqa: E402
from run_rfl import uniqueness  # noqa: E402

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


def load_pred(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1).astype(np.float32)
    return np.where(np.isfinite(a), a, 0.0)


def main() -> int:
    g = G.load_grid(ROOT / "data/raw")
    foot, labels = g.foot, g.labels
    # SGMC proxy truth exactly as gemsdoe.validation.sgmc_only_gt defines it.
    with rasterio.open(ROOT / "data/raw/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1) > 0
    d_cat = ndi.distance_transform_edt(~labels)
    gt = sgmc & (d_cat > 3.0) & foot
    log(f"SGMC off-catalogue proxy positives: {int(gt.sum()):,}")

    # ---- 1) calibration reproduction -------------------------------------
    S = ROOT / "data/raw/scored"
    obs_spec = [
        ("GEMSDOE32 h33-2-b2 (champion)", 0.2778, ROOT / "data/GEMSDOE32.tif"),
        ("GEMSDOE25 dotted-h19-5-d2-8", 0.2600, S / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
        ("GEMSDOE24 dotted-h19-5-d1-5", 0.2477, S / "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
        ("GEMSDOE19 h19-5 powerlaw", 0.1922, S / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"),
        ("GEMSDOE19 h19-4 multiline", 0.1894, S / "gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif"),
        ("GEMSDOE10 h28 dotted-ridge", 0.1839, S / "gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif"),
        ("8GEMSDOE Hedge-v2", 0.1563, S / "8GEMSDOE_Hedge-v2_submission.tif"),
        ("GEMSDOE ens12 adopted", 0.1563, S / "gemsdoe-ens12-adopted-7f00890a.tif"),
        ("GEMSDOE10 h25 ctx-ridge", 0.1280, S / "gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif"),
        ("13GEMSDOE lattice s5", 0.0904, S / "13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"),
        ("GEMSDOE9 placeholder", 0.0107, S / "gemsdoe9-PLACEHOLDER-2314b599.tif"),
    ]
    obs = []
    for label, rep, p in obs_spec:
        pr = V.profile(load_pred(p), gt, foot)
        obs.append({"label": label, "reported": rep, "path": str(p.relative_to(ROOT)),
                    "mass": pr["mass"], "hit_rate": pr["hit_rate"],
                    "dti_proxy": pr["dti_proxy"], "capture": pr["capture"]})
        log(f"calib {label:34s} mass={pr['mass']:8.0f} h={pr['hit_rate']:.4f} proxy={pr['dti_proxy']:.4f} reported={rep}")
    fit = V.fit_gt_size(obs, robust=True)
    m_fit = fit["M_trimmed"]
    log(f"fit |G|={m_fit:.1f} used {fit['n_used']}/{fit['n_total']} R2={fit['r2']:.3f} "
        f"Spearman={fit['spearman']:.3f} LOO rms={fit['loo_rms']:.4f} LOO Spearman={fit['loo_spearman']:.3f}")
    published = json.loads((ROOT / "evidence/gemsdoe_run_card.json").read_text())["estimate"]
    repro = {"published_M": published["gt_size_fitted_px"], "reproduced_M": round(m_fit, 1),
             "published_primary_estimate_skarpline": published["primary_estimate"]}

    # ---- 2) same-model estimates for every candidate ----------------------
    rfl_dots = np.unpackbits(np.load(ROOT / ".cache/rfl/final_dots.npy"))[: foot.size].reshape(foot.shape).astype(bool)
    cands = {
        "skarpline_union_610acf58": load_pred(ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
        "hce1_bc1edfe6": load_pred(ROOT / "docs/hce/downloads/wbggems3-hce1-latest.tif"),
        "cspes_9e28c697": load_pred(ROOT / "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif"),
        "rfl_final_dots_research_only": rfl_dots.astype(np.float32),
    }
    for s in ("24", "25", "27", "28", "30", "31", "32", "33", "36"):
        cands[f"GEMSDOE{s}_leader"] = load_pred(ROOT / f"data/GEMSDOE{s}.tif")
    estimates = {}
    for name, pred in cands.items():
        pr = V.profile(pred, gt, foot)
        est = V.score_from_profile(pr["hit_rate"], pr["mass"], m_fit)
        estimates[name] = {
            "evidence_class": "ESTIMATE (SGMC-proxy calibrated; NOT an organizer score)",
            "mass": pr["mass"], "hit_rate": pr["hit_rate"], "capture": pr["capture"],
            "dti_proxy_sgmc": pr["dti_proxy"], "estimate_at_M_fit": est,
            "sensitivity_over_gt_size": {str(int(m)): V.score_from_profile(pr["hit_rate"], pr["mass"], m)
                                          for m in (8430, m_fit, 22938, 30000)}}
        log(f"est {name:32s} mass={pr['mass']:8.0f} h={pr['hit_rate']:.4f} proxy={pr['dti_proxy']:.4f} EST={est:.4f}")
    repro["reproduced_estimate_skarpline"] = estimates["skarpline_union_610acf58"]["estimate_at_M_fit"]
    repro["abs_difference"] = abs(repro["reproduced_estimate_skarpline"] - published["primary_estimate"])
    log(f"skarpline estimate reproduction: published {published['primary_estimate']} vs reproduced "
        f"{repro['reproduced_estimate_skarpline']:.4f} (diff {repro['abs_difference']:.4f})")

    # ---- 3) evaluator ranking vs owner-reported ledger scores -------------
    ctx = H.load_holdout_context(ROOT / "data/raw")
    led = json.loads((ROOT / "data/ledger/index.json").read_text())
    rows = []
    for r in led:
        if r.get("status") != "verified" or r.get("local") is None or r.get("score") is None:
            continue
        p = ROOT / r["local"]
        if not p.exists():
            continue
        pred = load_pred(p)
        pr = V.profile(pred, gt, foot)
        ev = H.evaluate_hide_and_recover((pred > 0) & foot, ctx, name=r["submission"], n_boot=100)
        rows.append({"site": r["site"], "submission": r["submission"], "owner_reported": float(r["score"]),
                     "mass": pr["mass"], "h": pr["hit_rate"], "dti_proxy_sgmc": pr["dti_proxy"],
                     "estimate": V.score_from_profile(pr["hit_rate"], pr["mass"], m_fit),
                     "static_holdout_dti": ev["pooled_dti"]})
    log(f"ledger ranking rows: {len(rows)}")
    owner = np.array([r["owner_reported"] for r in rows])
    def sp(key):
        v = np.array([r[key] for r in rows], dtype=float)
        ok = np.isfinite(v)
        return float(spearmanr(owner[ok], v[ok]).statistic)
    ranking = {"n_files": len(rows), "score_class": "OWNER-REPORTED (no organizer receipts)",
               "spearman_vs_owner": {"static_holdout_dti": sp("static_holdout_dti"),
                                     "sgmc_hit_rate_h": sp("h"), "sgmc_proxy_dti": sp("dti_proxy_sgmc"),
                                     "calibrated_estimate": sp("estimate"), "mass": sp("mass")}}
    log(f"Spearman vs owner-reported: {ranking['spearman_vs_owner']}")

    # ---- 4) full-registry uniqueness re-audit of presented downloads ------
    uniq = {}
    for name, p in [("skarpline_union_saved", ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
                    ("hce1_saved", ROOT / "docs/hce/downloads/wbggems3-hce1-latest.tif")]:
        a = G.read_band(p)
        dots = np.isfinite(a) & (a > 0) & foot
        # remove the file's own mask from consideration is NOT done silently: exact self-hit is reported.
        u = uniqueness(dots, dots.astype(np.float32), foot, f"reaudit_{name}")
        uniq[name] = u
        log(f"uniq {name}: sparsePass={u['sparse_gate']['pass']} nonLat={u['sparse_gate']['max_overlap_within3px_nonlattice']:.3f} "
            f"rho={u['sparse_gate']['max_abs_spearman']:.3f} (self-mask present in registry: see rows)")

    out = {"analysis": "rfl_selector_analysis (arena/bd44f94b, 2026-10-27)",
           "calibration_fit": {k: v for k, v in fit.items() if k != "observations"},
           "calibration_observations": fit["observations"], "skarpline_reproduction": repro,
           "estimates": estimates, "evaluator_ranking": ranking, "ledger_rows": rows,
           "uniqueness_reaudit": uniq, "elapsed_s": round(time.time() - T0, 1)}
    (ROOT / "evidence/rfl_selector_analysis.json").write_text(json.dumps(out, indent=1))
    log("wrote evidence/rfl_selector_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
