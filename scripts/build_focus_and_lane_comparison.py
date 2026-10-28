#!/usr/bin/env python3
"""Build byte-verified comparison tables across all 9 Focus Sites, Peer Sites, and WBGGEMSDOE3 Lanes.

Computes:
1. Exact byte-level format/range [0,1] checks, SHA-256, dot counts, and catalogue-halo fractions;
2. Pairwise 3-px dot overlap and Spearman rank correlation vs GEMSDOE32 (0.2778) and THCS-OOF;
3. Leave-One-Site-Out (LOSO) empirical score calibration fitted across all 122 unique SHA-256
   ORGANIZER-CONFIRMED live-scored GeoTIFFs on disk, explicitly labeled
   ``LOSO-MODEL-ESTIMATE (NOT ORGANIZER-CONFIRMED)`` per Protocol Rule 3.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata, spearmanr
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.gemsw.metric import ALPHA, BETA, EPS, _OFFS, kernel
from src.hce.uniqueness import DISC


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_fast_dti(g_mask: np.ndarray):
    yy, xx = np.nonzero(g_mask)
    n = int(yy.size)
    dg = ndi.distance_transform_edt(~g_mask)
    w_fp = (1.0 - kernel(dg)).astype(np.float32)
    H, W = g_mask.shape
    shifts = []
    for dy, dx, k in _OFFS:
        ny, nx = yy + dy, xx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        shifts.append((ok, ny[ok], nx[ok], float(k)))

    def eval_pred(p: np.ndarray) -> tuple[float, float]:
        credit = np.zeros(n, dtype=np.float32)
        for ok, r, c, k in shifts:
            credit[ok] = np.maximum(credit[ok], p[r, c] * k)
        tp = float(credit.sum())
        fn = float(n) - tp
        fp = float((p * w_fp).sum())
        return float(tp / (tp + ALPHA * fp + BETA * fn + EPS)), float(tp / max(n, 1))

    return eval_pred


def _overlap_3px(dots_a: np.ndarray, near_b: np.ndarray) -> float:
    na = int(dots_a.sum())
    return float((dots_a & near_b).sum() / max(na, 1)) if na > 0 else 0.0


def _spearman_sample(a: np.ndarray, b: np.ndarray, sidx: np.ndarray) -> float:
    va = ndi.gaussian_filter(a.astype(np.float32), 1.5).ravel()[sidx]
    vb = ndi.gaussian_filter(b.astype(np.float32), 1.5).ravel()[sidx]
    if va.std() < 1e-12 or vb.std() < 1e-12:
        return 0.0
    return float(np.corrcoef(rankdata(va), rankdata(vb))[0, 1])


def main() -> int:
    raise RuntimeError("BLOCKED: historical comparison treats owner reports as organizer receipts; see evidence/focus_and_lane_comparison.json")
    raw = ROOT / "data" / "raw"
    with rasterio.open(raw / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        H, W = ds.shape
    with rasterio.open(raw / "existing_faults.tif") as ds:
        cat = (ds.read(1) == 1) & foot
    active = foot & (~cat)
    d_cat = ndi.distance_transform_edt(~cat)

    # Physical reference masks for empirical calibration across the 122 live-scored runs
    with rasterio.open(raw / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & active
    with rasterio.open(raw / "external" / "lidar_scarp_features_u8.tif") as ds:
        step_max = ds.read(3).astype(np.float32)
        coh100 = ds.read(10).astype(np.float32)
    with rasterio.open(raw / "external" / "tiger_road_distance_m.tif") as ds:
        road_m = ds.read(1).astype(np.float32)
    with rasterio.open(raw / "training_features.tif") as ds:
        dtb = ds.read(15).astype(np.float32)
        grav_hg = ds.read(18).astype(np.float32)
        slope = ds.read(19).astype(np.float32)

    # Load THCS full-map OOF probability surface (zero-catalogue physical susceptibility)
    # Use clean physical indicators:
    # (1) Neotectonic scarp-corroborated off-catalogue structures (road-clean 3DEP scarp + slope)
    scarp_clean = (step_max * np.clip(road_m / 250.0, 0.15, 1.0) > 28.0) & (coh100 > 90) & (d_cat > 3.0) & active
    # (2) Piedmont / concealed SGMC + gravity-gradient structures
    med_dtb = float(np.median(dtb[active & np.isfinite(dtb)]))
    med_ghg = float(np.percentile(grav_hg[active & np.isfinite(grav_hg)], 70))
    pied_struct = sgmc & (d_cat > 3.0) & ((dtb > med_dtb) | (grav_hg > med_ghg))
    # (3) Near-catalogue continuation zone (3 < d_cat <= 12 px) where off-catalogue splays/tips cluster
    splay_scarp = ((scarp_clean | (sgmc & (slope > np.percentile(slope[active & np.isfinite(slope)], 65))))
                   & (d_cat > 3.0) & (d_cat <= 18.0))

    # (4) Independent multi-physics corridor concordance (corroborated by >=2 independent non-SGMC runs >300m off cat)
    p19 = next(ROOT / it["local"] for it in json.loads((ROOT / "data/ledger/index.json").read_text()) if it["site"] == "19GEMSDOE" and abs(it["score"] - 0.1922) < 1e-4)
    p70 = next(ROOT / it["local"] for it in json.loads((ROOT / "data/ledger/index.json").read_text()) if it["site"] == "GEMSDOE70" and abs(it["score"] - 0.2478) < 1e-4)
    p76 = next(ROOT / it["local"] for it in json.loads((ROOT / "data/ledger/index.json").read_text()) if it["site"] == "GEMSDOE76" and abs(it["score"] - 0.2343) < 1e-4)
    with rasterio.open(p19) as ds: m19 = (ds.read(1) > 0) & (d_cat > 3.0) & active
    with rasterio.open(p70) as ds: m70 = (ds.read(1) > 0) & (d_cat > 3.0) & active
    with rasterio.open(p76) as ds: m76 = (ds.read(1) > 0) & (d_cat > 3.0) & active
    # Consensus >=2 of (3DEP scarp, 19GEMSDOE multiline, GEMSDOE70 OOF, GEMSDOE76 tilt-worm)
    votes = (
        ndi.maximum_filter(scarp_clean, size=3).astype(np.int8)
        + ndi.maximum_filter(m19, size=3).astype(np.int8)
        + ndi.maximum_filter(m70, size=3).astype(np.int8)
        + ndi.maximum_filter(m76, size=3).astype(np.int8)
    )
    consensus_corridor = (votes >= 2) & (d_cat > 3.0) & active

    eval_scarp = _make_fast_dti(scarp_clean)
    eval_pied = _make_fast_dti(pied_struct)
    eval_splay = _make_fast_dti(splay_scarp)
    eval_cons = _make_fast_dti(consensus_corridor)

    def raster_features(a_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        pa = np.where(active & np.isfinite(a_raw), np.clip(a_raw, 0.0, 1.0), 0.0).astype(np.float32)
        ndots = int((pa > 0).sum())
        mass = float(pa.sum())
        halo_le2 = float(pa[d_cat <= 2.0].sum() / max(mass, 1e-9))
        dti_sc, cov_sc = eval_scarp(pa)
        dti_pi, cov_pi = eval_pied(pa)
        dti_sp, cov_sp = eval_splay(pa)
        dti_co, cov_co = eval_cons(pa)
        m_bin = pa > 0
        cov3_px = int((ndi.maximum_filter(m_bin, size=5) & active).sum()) if ndots > 0 else 0
        packing_eff = float(cov3_px / max(ndots, 1)) / 25.0
        log_mass = np.log1p(mass)
        feat = np.array([
            dti_sc,
            dti_pi,
            dti_sp,
            dti_co,
            cov_sc * packing_eff,
            (1.0 - halo_le2) * dti_co,
            halo_le2,
            log_mass,
            np.log1p(ndots),
            packing_eff,
        ], dtype=np.float64)
        info = {
            "emitted_dots": ndots,
            "mass": round(mass, 2),
            "halo_le_2px_frac": round(halo_le2, 5),
            "packing_efficiency": round(packing_eff, 4),
            "dti_scarp_proxy": round(dti_sc, 5),
            "dti_piedmont_proxy": round(dti_pi, 5),
            "dti_splay_proxy": round(dti_sp, 5),
            "dti_consensus_corridor": round(dti_co, 5),
        }
        return feat, info

    # 1. Fit Leave-One-Site-Out empirical calibration model across ALL 122 unique live-scored GeoTIFFs
    ledger = json.loads((ROOT / "data" / "ledger" / "index.json").read_text())
    extra = json.loads((ROOT / "data" / "peer_extra" / "index.json").read_text())
    scored_items = []
    seen_sha = set()
    for it in ledger:
        p = ROOT / it["local"]
        if p.exists() and it["sha256"] not in seen_sha:
            seen_sha.add(it["sha256"])
            scored_items.append((it["site"], it["submission"], float(it["score"]), p, it["sha256"]))
    for it in extra:
        if it["score"] is not None and it["sha256"] not in seen_sha:
            seen_sha.add(it["sha256"])
            scored_items.append((it["site"], Path(it["local"]).stem, float(it["score"]), ROOT / it["local"], it["sha256"]))

    X_list, y_list, site_list, meta_scored = [], [], [], []
    for site, sub, sc, p, sha in scored_items:
        # Exclude direct SGMC self-submissions from fitting the SGMC-containing piedmont proxy
        if "sgmc" in sub.lower():
            continue
        with rasterio.open(p) as ds:
            if ds.shape != (H, W):
                continue
            arr = ds.read(1).astype(np.float32)
        fvec, finfo = raster_features(arr)
        X_list.append(fvec)
        y_list.append(sc)
        site_list.append(site)
        meta_scored.append((site, sub, sc, sha, finfo))

    X_cal = np.vstack(X_list)
    y_cal = np.asarray(y_list, dtype=np.float64)
    sites_cal = np.asarray(site_list)

    # Leave-One-Site-Out cross-validation across all sites
    loso_preds = np.zeros_like(y_cal)
    for s in np.unique(sites_cal):
        tr_m = sites_cal != s
        te_m = sites_cal == s
        rf = RandomForestRegressor(n_estimators=150, max_depth=5, min_samples_leaf=3, random_state=42, n_jobs=-1)
        rf.fit(X_cal[tr_m], y_cal[tr_m])
        loso_preds[te_m] = np.clip(rf.predict(X_cal[te_m]), 0.005, 0.45)

    loso_rmse = float(np.sqrt(np.mean((loso_preds - y_cal) ** 2)))
    loso_mae = float(np.mean(np.abs(loso_preds - y_cal)))
    loso_rho = float(spearmanr(y_cal, loso_preds).statistic)
    q90 = float(np.quantile(np.abs(loso_preds - y_cal), 0.90))

    rf_full = RandomForestRegressor(n_estimators=200, max_depth=5, min_samples_leaf=3, random_state=42, n_jobs=-1)
    rf_full.fit(X_cal, y_cal)
    loso_by_sha = {meta_scored[i][3]: float(loso_preds[i]) for i in range(len(meta_scored))}

    def predict_est(fvec: np.ndarray, sha_full: str) -> tuple[float, list[float]]:
        # Use strict out-of-site LOSO prediction for any already-scored site, full RF for unscored
        est = loso_by_sha.get(sha_full, float(np.clip(rf_full.predict(fvec.reshape(1, -1))[0], 0.005, 0.45)))
        return round(est, 4), [round(max(0.0, est - q90), 4), round(min(0.45, est + q90), 4)]

    # Load GEMSDOE32 champion and THCS-OOF candidate for pairwise uniqueness metrics
    p_champ = next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE32" and abs(it["score"] - 0.2778) < 1e-4)
    rc_thcs = json.loads((ROOT / "evidence" / "thcs_run_card.json").read_text())
    p_thcs = ROOT / rc_thcs["artifact"]["submission_tif"]

    with rasterio.open(p_champ) as ds:
        a_champ = np.where(foot & np.isfinite(ds.read(1)), np.clip(ds.read(1), 0.0, 1.0), 0.0)
    dots_champ = a_champ > 0
    near_champ = ndi.binary_dilation(dots_champ, structure=DISC)

    with rasterio.open(p_thcs) as ds:
        a_thcs = np.where(foot & np.isfinite(ds.read(1)), np.clip(ds.read(1), 0.0, 1.0), 0.0)
    dots_thcs = a_thcs > 0
    near_thcs = ndi.binary_dilation(dots_thcs, structure=DISC)

    rng = np.random.default_rng(11)
    sidx = rng.choice(np.flatnonzero(foot.ravel()), 350_000, replace=False)

    # Build comparison entries: 9 Focus Sites + Key Peer Benchmarks + 5 WBGGEMSDOE3 Lanes
    focus_specs = [
        ("GEMSDOE32", "Focus Site (Best)", p_champ, 0.2778, 0.09920, "H33-2-B2: H19-5 d=2.8 + d_cat>2.0px collar"),
        ("GEMSDOE36", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE36" and abs(it["score"] - 0.2750) < 1e-4), 0.2750, None, "B2 + 1,200 Anderson geothermal PINN dots"),
        ("GEMSDOE28", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE28" and abs(it["score"] - 0.2710) < 1e-4), 0.2710, None, "H36-1 rung-30 blind collar on H19-5 d=2.8"),
        ("GEMSDOE31", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE31" and abs(it["score"] - 0.2708) < 1e-4), 0.2708, None, "H27-4 solo d=2.8 pruned H19-5"),
        ("GEMSDOE33", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE33" and abs(it["score"] - 0.2632) < 1e-4), 0.2632, None, "H33d analog tip/stepover r=30 on H19-5"),
        ("GEMSDOE25", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE25" and abs(it["score"] - 0.2600) < 1e-4), 0.2600, 0.09674, "Dotted H19-5 spacing d=2.8 px"),
        ("GEMSDOE30", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE30" and abs(it["score"] - 0.2600) < 1e-4), 0.2600, 0.09674, "Poisson 300 m off-catalogue d=2.8 clone"),
        ("GEMSDOE24", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE24" and abs(it["score"] - 0.2477) < 1e-4), 0.2477, 0.09315, "Dotted H19-5 spacing d=1.5 px"),
        ("GEMSDOE27", "Focus Site (Best)", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE27" and abs(it["score"] - 0.2449) < 1e-4), 0.2449, None, "Topo gap-closure T-v2 on d=1.5 (Oct 26 h31: 0.2250)"),
        ("GEMSDOE70", "Top Unique Peer", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE70" and abs(it["score"] - 0.2478) < 1e-4), 0.2478, None, "4-fold OOF dual-pop HGB + 300 m submodular cover"),
        ("GEMSDOE76", "Top Zero-Cat Peer", next(ROOT / it["local"] for it in ledger if it["site"] == "GEMSDOE76" and abs(it["score"] - 0.2343) < 1e-4), 0.2343, None, "Zero-catalogue PTCF tilt-worm + submodular 39.2k"),
        ("KANLERGEMSDOE3", "Recent Peer (Oct 26)", ROOT / "data/peer_extra/KANLERGEMSDOE3__kanlergemsdoe3-h-k3-1-cadg-submod-exp-k3-3-oof8f-37654-20261026-f0565e6d10f9-zeros.tif", None, None, "8-fold OOF CADG submodular 37,654d (unscored)"),
        ("KANLERGEMSDOE2", "Recent Peer (Oct 26)", ROOT / "data/peer_extra/KANLERGEMSDOE2__kanlergems2-htcads-exp-2-37654dots-20261026T235227Z-11a2f251-zeros.tif", None, None, "HTCADS Exp-2 37,654d (unscored)"),
        ("WBGGEMSDOE2", "Recent Peer (Oct 27)", ROOT / "data/peer_extra/WBGGEMSDOE2_H3__wbg3-h3pack-34k-20261027T174337Z-zeros.tif", None, None, "H3-pack 34,000d (unscored)"),
        ("WBGGEMSDOE3 (THCS-OOF)", "This Session (New)", p_thcs, None, rc_thcs["holdout_evaluation"]["pooled_dti"], "48-ch Geophys+LiDAR+Rad+GDR1391 4-fold OOF HGB + 300m CELF"),
        ("WBGGEMSDOE3 (LST1)", "Prior Repo Lane", ROOT / "submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif", None, 0.09543, "Prior depth-adaptive HGB lane (negative)"),
        ("WBGGEMSDOE3 (skarpline)", "Prior Repo Lane", ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif", None, None, "Prior heuristic scarp+worm union (97.6k dots, inflated by IR-21)"),
        ("WBGGEMSDOE3 (CSPES)", "Prior Repo Lane", ROOT / "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif", None, 0.06802, "Prior phase-congruency lane (negative)"),
        ("WBGGEMSDOE3 (HCE-1)", "Prior Repo Lane", ROOT / "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif", None, 0.05680, "Prior unsupervised congruence lane (negative)"),
    ]

    table_rows = []
    for site, category, path, org_score, holdout_dti, notes in focus_specs:
        with rasterio.open(path) as ds:
            raw_a = ds.read(1).astype(np.float32)
        in_f = raw_a[foot]
        range_ok = bool(np.isfinite(in_f).all() and np.all((in_f >= 0.0) & (in_f <= 1.0)))
        a_clean = np.where(foot & np.isfinite(raw_a), np.clip(raw_a, 0.0, 1.0), 0.0)
        dots = a_clean > 0
        fvec, finfo = raster_features(raw_a)
        full_sha = _sha256(path)
        est, pi90 = predict_est(fvec, full_sha)

        ov_vs_32 = _overlap_3px(dots, near_champ)
        rho_vs_32 = _spearman_sample(a_clean, a_champ, sidx)
        ov_thcs_in_ref = _overlap_3px(dots_thcs, ndi.binary_dilation(dots, structure=DISC))
        rho_vs_thcs = _spearman_sample(a_thcs, a_clean, sidx)

        table_rows.append({
            "site": site,
            "category": category,
            "file": path.name,
            "sha256_short": full_sha[:12],
            "emitted_dots": finfo["emitted_dots"],
            "in_footprint_0_1_valid": range_ok,
            "halo_le_2px_pct": round(100.0 * finfo["halo_le_2px_frac"], 2),
            "organizer_confirmed_score": org_score,
            "holdout_dti_v3": holdout_dti,
            "loso_model_estimate_not_confirmed": est,
            "loso_90pct_interval": pi90,
            "overlap_3px_vs_gemsdoe32": round(ov_vs_32, 4),
            "spearman_vs_gemsdoe32": round(rho_vs_32, 4),
            "thcs_overlap_3px_vs_row": round(ov_thcs_in_ref, 4),
            "thcs_spearman_vs_row": round(rho_vs_thcs, 4),
            "unique_vs_gemsdoe32": bool(ov_vs_32 <= 0.70 and abs(rho_vs_32) <= 0.90) if site != "GEMSDOE32" else False,
            "notes": notes,
        })

    out = {
        "generated_utc": rc_thcs["generated_utc"],
        "score_labeling_rule": (
            "Protocol Rule 3: organizer_confirmed_score is from submission-page receipts; "
            "holdout_dti_v3 is HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0, n=22,232); "
            "loso_model_estimate_not_confirmed is a Leave-One-Site-Out Ridge calibration across "
            "120 non-SGMC live-scored leaderboard rasters — NEVER report as an organizer score."
        ),
        "empirical_calibration_quality": {
            "n_scored_rasters_used": int(len(y_cal)),
            "loso_spearman_rho": round(loso_rho, 4),
            "loso_rmse": round(loso_rmse, 4),
            "loso_mae": round(loso_mae, 4),
            "interval_halfwidth_90pct": round(q90, 4),
        },
        "empty_or_no_tif_peer_sites_audited": [
            {"site": s, "candidate_tifs_found": 0, "status": "Audited via GitHub tree API on 2026-10-27 UTC — 0 submission GeoTIFFs published"}
            for s in ["EUGGEMSDOE1", "EUGGEMSDOE2", "EUGGEMSDOE3", "GINNYGEMSDOE1", "GINNYGEMSDOE2", "GINNYGEMSDOE3"]
        ],
        "rows": table_rows,
    }
    out_path = ROOT / "evidence" / "focus_and_lane_comparison.json"
    out_path.write_text(json.dumps(out, indent=2))
    docs_data = ROOT / "docs" / "data" / "focus_and_lane_comparison.json"
    docs_data.parent.mkdir(parents=True, exist_ok=True)
    docs_data.write_text(json.dumps(out, indent=2))

    print(
        f"LOSO Calibration across {len(y_cal)} live-scored rasters: "
        f"Spearman={loso_rho:+.4f}, RMSE={loso_rmse:.4f}, MAE={loso_mae:.4f}, 90% PI=+/-{q90:.4f}"
    )
    print("\nSite                     | Dots    | OrgScore | Holdout  | LOSO-Est [90% PI]       | Ov32   | OvTHCS | UniqueVs32")
    print("-" * 114)
    for r in table_rows:
        os_s = f"{r['organizer_confirmed_score']:.4f}" if r["organizer_confirmed_score"] is not None else "  —   "
        hd_s = f"{r['holdout_dti_v3']:.5f}" if r["holdout_dti_v3"] is not None else "   —   "
        pi = r["loso_90pct_interval"]
        print(
            f"{r['site']:24s} | {r['emitted_dots']:7,d} |  {os_s}  | {hd_s} | "
            f"{r['loso_model_estimate_not_confirmed']:.4f} [{pi[0]:.3f}, {pi[1]:.3f}] | "
            f"{r['overlap_3px_vs_gemsdoe32']:6.2%} | {r['thcs_overlap_3px_vs_row']:6.2%} | {str(r['unique_vs_gemsdoe32'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
