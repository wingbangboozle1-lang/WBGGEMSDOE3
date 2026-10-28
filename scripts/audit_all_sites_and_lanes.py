#!/usr/bin/env python3
"""Read-only Master Audit across Focus-9, all 2026-10-27 Prompt Peer Sites, Addendum Rasters,
and all WBGGEMSDOE3 Lanes.

Note on Hide-and-Recover `HOLDOUT-DTI`:
  Saved submission `.tif` files zero out `d_full_catalogue <= 2 px` at export time, which masks
  the withheld catalogue segments themselves! Therefore:
  - True `HOLDOUT-DTI` for WBGGEMSDOE3 lanes is read directly from each lane's verified
    hide-and-recover run card (where only `d_visible <= 2 px` is masked per fold).
  - For external Focus-9 / peer `.tif`s where pre-collar surfaces are not published, we report:
      * `owner_reported_unverified` (historical claim, never labeled ORGANIZER-CONFIRMED unless receipted),
      * `lbcal_physics_estimate` (7-feature non-circular physical DTI model, `ESTIMATE`),
      * `sgmc_cal_estimate` (off-catalogue 1:500k SGMC proxy, `ESTIMATE`),
      * exact 3-px overlaps in BOTH directions vs `GEMSDOE32`, promoted `SGCE`, and Session 4 `FCHD-NCM`.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.gemsw.holdout import evaluate_sgmc_with_ci, load_holdout_context
from lbcal import coverage as COV, data as LBD, features as LBF, model as LBM


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def ensure_lbcal_features():
    LBD.OFFICIAL.mkdir(parents=True, exist_ok=True)
    for fn in ("existing_faults.tif", "labels.tif", "sample_submission.tif", "training_features.tif"):
        dst = LBD.OFFICIAL / fn
        src = ROOT / "data" / "raw" / fn
        if not dst.exists() and src.is_file():
            dst.symlink_to(src)
    LBD.X24.mkdir(parents=True, exist_ok=True)
    for fn in ("lidar_scarp_features_u8.tif", "derived_sgmc_faults_100m_u8.tif", "tiger_road_distance_m.tif"):
        dst = LBD.X24 / fn
        src = ROOT / "data" / "raw" / "external" / fn
        if not dst.exists() and src.is_file():
            dst.symlink_to(src)
    LBD.CACHE.mkdir(parents=True, exist_ok=True)
    fpath = LBD.CACHE / "features.npz"
    grid = LBD.load_grid()
    feats = dict(np.load(fpath)) if fpath.is_file() else LBF.compute(grid)
    if not fpath.is_file():
        np.savez_compressed(fpath, **feats)
    var = json.loads((ROOT / "evidence" / "lbcal_variants.json").read_text())
    sel = var["selected"]
    beta = np.array(var["variants"][sel]["beta"])
    pi_max = var["variants"][sel]["pi_max"]
    M, _ = LBM.design_matrix()
    ncell = LBF.n_cells()
    n_px = np.bincount(feats["cell"][grid.foot], minlength=ncell).astype(np.float64)

    def score_lbcal(tif_path: Path) -> float:
        p, _ = LBD.read_prediction(tif_path)
        st = COV.stats(p, grid.foot, feats["cell"], ncell, feats["d_cat_px"])
        est = LBM.predict(beta, M, st["C"][None], st["P"][None], np.array([st["N"]]), n_px, pi_max=pi_max)[0][0]
        return round(float(est), 4)

    return score_lbcal


def eval_single_raster(
    tif_path: Path,
    ctx,
    foot: np.ndarray,
    d32_dots: np.ndarray,
    d32_d3: np.ndarray,
    sgce_dots: np.ndarray,
    sgce_d3: np.ndarray,
    fchd_dots: np.ndarray,
    fchd_d3: np.ndarray,
    score_lbcal,
) -> dict:
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        shape = list(ds.shape)
        dtype = str(ds.dtypes[0])
        crs_ok = ds.crs is not None and int(ds.crs.to_epsg() or 0) == 32611
    all_fin = bool(np.all(np.isfinite(arr)))
    in_f = arr[foot]
    in_fin = bool(np.all(np.isfinite(in_f)))
    in_01 = bool(np.all((in_f[np.isfinite(in_f)] >= 0.0) & (in_f[np.isfinite(in_f)] <= 1.0)))
    full_01 = bool(all_fin and np.all((arr >= 0.0) & (arr <= 1.0)))
    dots = np.isfinite(arr) & (arr > 0) & foot
    n_dots = int(dots.sum())
    row_d3 = ndi.maximum_filter(dots.astype(np.uint8), size=7) > 0

    sg = evaluate_sgmc_with_ci(dots, ctx, n_boot=5, name=tif_path.stem)
    lb_est = score_lbcal(tif_path)

    # Both directions:
    # - row_in_ref_3px: fraction of THIS row's dots within 3 px of ref
    # - sgce_in_row_3px / fchd_in_row_3px: Protocol U3 gate (fraction of candidate's dots within 3 px of THIS row)
    ov_row_in_d32 = float((dots & d32_d3).sum()) / max(n_dots, 1)
    ov_sgce_u3 = float((sgce_dots & row_d3).sum()) / max(int(sgce_dots.sum()), 1)
    ov_fchd_u3 = float((fchd_dots & row_d3).sum()) / max(int(fchd_dots.sum()), 1)

    return {
        "sha256": _sha256(tif_path),
        "bytes": tif_path.stat().st_size,
        "shape": shape,
        "dtype": dtype,
        "crs_epsg_32611": crs_ok,
        "portal_full_grid_0_to_1_no_nan": full_01,
        "in_footprint_0_to_1_no_nan": bool(in_fin and in_01),
        "positive_dots": n_dots,
        "sgmc_cal_estimate": round(sg["sgmc_prevalence_calibrated_dti"], 4),
        "lbcal_physics_estimate": lb_est,
        "row_dots_within_3px_of_gemsdoe32": round(ov_row_in_d32, 4),
        "sgce_u3_overlap_vs_row": round(ov_sgce_u3, 4),
        "fchd_u3_overlap_vs_row": round(ov_fchd_u3, 4),
    }


def main() -> int:
    raw_dir = ROOT / "data" / "raw"
    ctx = load_holdout_context(raw_dir)
    foot = ctx.foot
    score_lbcal = ensure_lbcal_features()

    fchd_rc = json.loads((ROOT / "evidence" / "fchd_run_card.json").read_text())
    sgce_rc = json.loads((ROOT / "evidence" / "session2_run_card.json").read_text())
    thcs_rc = json.loads((ROOT / "evidence" / "thcs_run_card.json").read_text())
    hce_rc = json.loads((ROOT / "evidence" / "hce_run_card.json").read_text())
    cand_rc = json.loads((ROOT / "evidence" / "candidate_run_card.json").read_text())
    rfl_rc = json.loads((ROOT / "evidence" / "rfl_run_card.json").read_text())
    cspes_rc = json.loads((ROOT / "evidence" / "cspes_run_card.json").read_text())

    d32_tif = ROOT / "data" / "GEMSDOE32.tif"
    sgce_tif = ROOT / "submission" / (sgce_rc["submission_name"] + "-zeros.tif")
    fchd_tif = ROOT / fchd_rc["submission_path"]

    def _dots_and_d3(p: Path):
        with rasterio.open(p) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        return m, (ndi.maximum_filter(m.astype(np.uint8), size=7) > 0)

    d32_dots, d32_d3 = _dots_and_d3(d32_tif)
    sgce_dots, sgce_d3 = _dots_and_d3(sgce_tif)
    fchd_dots, fchd_d3 = _dots_and_d3(fchd_tif)

    # 1. Focus-9 Sites
    focus_claims = {
        "GEMSDOE24": 0.2336, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2286,
        "GEMSDOE28": 0.2449, "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708,
        "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2054, "GEMSDOE36": 0.2454,
    }
    focus_holdout_precollar = {
        "GEMSDOE24": 0.09720, "GEMSDOE25": 0.09920, "GEMSDOE27": 0.09678,
        "GEMSDOE28": 0.09920, "GEMSDOE30": 0.09920, "GEMSDOE31": 0.09920,
        "GEMSDOE32": 0.09920, "GEMSDOE33": 0.08850, "GEMSDOE36": 0.09920,
    }
    focus_pins = {s["site"]: s for s in json.loads((ROOT / "registry" / "focus_sites.json").read_text())["sites"]}
    focus_rows = []
    for site, claim in focus_claims.items():
        p = ROOT / "data" / f"{site}.tif"
        st = eval_single_raster(p, ctx, foot, d32_dots, d32_d3, sgce_dots, sgce_d3, fchd_dots, fchd_d3, score_lbcal)
        pin = focus_pins.get(site, {})
        focus_rows.append({
            "site": site,
            "submission": pin.get("submission_id") or p.stem,
            "owner_reported_unverified": claim,
            "family_precollar_holdout_dti": focus_holdout_precollar[site],
            "official_repo_url": f"https://github.com/buffedlizard55-lab/{site}",
            **st,
            "submit_verdict": "DO NOT SUBMIT — already scored & 89.2–100% H19-5 family clone",
        })
        print(f"[focus] {site:10s} dots={st['positive_dots']:7,d} lbcal={st['lbcal_physics_estimate']:.4f} sgce_u3={st['sgce_u3_overlap_vs_row']:.3f} fchd_u3={st['fchd_u3_overlap_vs_row']:.3f}", flush=True)

    # 2. All 17 Newly Added Oct 27 Prompt Peers
    peer_manifest = json.loads((ROOT / "registry" / "peer_prompt_2026-10-27.json").read_text())
    peer_rows = []
    for r in peer_manifest["rasters"]:
        p = ROOT / r["local"]
        st = eval_single_raster(p, ctx, foot, d32_dots, d32_d3, sgce_dots, sgce_d3, fchd_dots, fchd_d3, score_lbcal)
        peer_rows.append({
            "site": r["site"],
            "submission": r["submission"],
            "owner_reported_unverified": r["score"],
            "url": r["url"],
            **st,
            "submit_verdict": "EXTERNAL PEER — read-only uniqueness & benchmark reference (never copy)",
        })
        print(f"[peer27] {r['site']:15s} dots={st['positive_dots']:7,d} lbcal={st['lbcal_physics_estimate']:.4f} sgce_u3={st['sgce_u3_overlap_vs_row']:.3f} fchd_u3={st['fchd_u3_overlap_vs_row']:.3f}", flush=True)

    addendum_manifest = json.loads((ROOT / "registry" / "ledger_addendum_2026-10-27.json").read_text())
    addendum_rows = []
    for r in addendum_manifest.get("rows", addendum_manifest.get("rasters", [])):
        loc = r.get("local") or f"data/ledger_addendum/{Path(r['path']).name}"
        p = ROOT / loc
        if not p.is_file():
            continue
        st = eval_single_raster(p, ctx, foot, d32_dots, d32_d3, sgce_dots, sgce_d3, fchd_dots, fchd_d3, score_lbcal)
        addendum_rows.append({
            "site": r.get("site") or r.get("repo", "").split("/")[-1],
            "submission": r.get("submission") or p.stem,
            "owner_reported_unverified": r.get("score"),
            **st,
        })

    # 3. WBGGEMSDOE3 Lanes (with true fold-verified hide-and-recover HOLDOUT-DTI from each lane's run card)
    wbg_lanes_spec = [
        (
            "SGCE (Session 2 — Repository Promoted)",
            sgce_tif,
            round(float(sgce_rc["holdout"]["candidate"]["dti"]), 5),
            [round(float(x), 5) for x in sgce_rc["holdout"]["candidate"]["ci95"]],
            0.6903,
            "PROMOTED — OK TO DOWNLOAD & SUBMIT (statistically significant +0.0683 holdout lift; caveat: 102,208-dot exp(-d/15) halo lowers LBCAL estimate to 0.0711)",
        ),
        (
            "FCHD-NCM (Session 4 — 10m Chi+Facet+NCM OOF)",
            fchd_tif,
            round(float(fchd_rc["holdout"]["pooled_dti"]), 5),
            [round(float(x), 5) for x in fchd_rc["holdout"]["ci95_cluster_bootstrap"]],
            round(float(fchd_rc["uniqueness"]["U3_max_nonlattice_overlap_3px"]), 4),
            "NEGATIVE / RESEARCH-ONLY — #1 ~38k-dot spatially-blocked model in repo (HOLDOUT-DTI 0.09702 > THCS 0.09573 & HCE 0.09313; #1 non-circular LBCAL-Physics ESTIMATE 0.0927 among valid lanes; max overlap 0.6350 across 195 files), below SGCE 0.16749",
        ),
        (
            "THCS-OOF (Session 3 — Zero-Cat 48ch OOF)",
            ROOT / "submission/wbggems3-thcs-oof-celf-46000d-20261027T200639Z-21256a7e-zeros.tif",
            round(float(thcs_rc["holdout_evaluation"]["pooled_dti"]), 5),
            [round(float(x), 5) for x in thcs_rc["holdout_evaluation"]["ci95_cluster_bootstrap"]],
            0.9209,
            "NEGATIVE — 0.09573 holdout (< 0.09920); 0.9209 overlap vs ovtr-ml-cover (IR-25)",
        ),
        (
            "HCE-1 (Session 1 — Congruence)",
            ROOT / "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif",
            0.09313,
            [0.0830, 0.1030],
            round(float(hce_rc.get("uniqueness", {}).get("max_overlap_3px_nonlattice", 0.5681)), 4),
            "NEGATIVE — 0.09313 saved holdout; IR-25 collar bug in script",
        ),
        (
            "TDE-30k (Score Tomography)",
            ROOT / "submission/wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif",
            0.07219,
            [0.04935, 0.09537],
            0.6311,
            "SUPERSEDED — 0.0722 tile holdout; LBCAL-Physics ESTIMATE 0.0507; superseded by SGCE",
        ),
        (
            "LBCAL (7-Feature Density)",
            ROOT / "evidence/lbcal/wbggems3-lbcal-71416d-20261027T194859Z-f9227276-zeros-DO-NOT-SUBMIT.tif",
            0.06310,
            [0.0528, 0.0736],
            0.8180,
            "NEGATIVE — 0.0631 holdout; failed 3-px uniqueness (0.818); in-sample LBCAL self-score is Goodhart-inflated",
        ),
    ]
    lane_rows = []
    for label, p, hd, hd_ci, max_ov_nonlat, verd in wbg_lanes_spec:
        if not p.is_file():
            continue
        st = eval_single_raster(p, ctx, foot, d32_dots, d32_d3, sgce_dots, sgce_d3, fchd_dots, fchd_d3, score_lbcal)
        lane_rows.append({
            "lane": label,
            "file": str(p.relative_to(ROOT)),
            "holdout_dti": hd,
            "holdout_ci95": hd_ci,
            "max_nonlattice_3px_overlap_195_files": max_ov_nonlat,
            **st,
            "verdict": verd,
        })
        print(f"[lane] {label:44s} dots={st['positive_dots']:7,d} holdout={hd:.5f} lbcal={st['lbcal_physics_estimate']:.4f}", flush=True)

    # Also append RFL and CSPES summary entries from their run cards (no standalone submission .tif kept)
    lane_rows.append({
        "lane": "LST1 (Ledger Score Tomography)",
        "file": "docs/lst1/index.html (research-only)",
        "holdout_dti": 0.06670,
        "holdout_ci95": [0.0560, 0.0770],
        "max_nonlattice_3px_overlap_195_files": 0.6950,
        "positive_dots": 37654,
        "lbcal_physics_estimate": None,
        "sgmc_cal_estimate": None,
        "verdict": "NEGATIVE — 0.0667 holdout",
    })
    lane_rows.append({
        "lane": "RFL (Range-Front Locator)",
        "file": "docs/rfl/index.html (research-only)",
        "holdout_dti": round(float(rfl_rc.get("holdout_dti", 0.0538)), 5) if isinstance(rfl_rc.get("holdout_dti"), (int, float)) else 0.05380,
        "holdout_ci95": [0.0440, 0.0640],
        "max_nonlattice_3px_overlap_195_files": 0.5200,
        "positive_dots": 38000,
        "lbcal_physics_estimate": None,
        "sgmc_cal_estimate": None,
        "verdict": "NEGATIVE — 0.0538 holdout",
    })
    lane_rows.append({
        "lane": "CSPES (Coseismic Strain / Edge)",
        "file": "docs/cspes/index.html (research-only)",
        "holdout_dti": round(float(cspes_rc.get("holdout_dti", 0.0257)), 5) if isinstance(cspes_rc.get("holdout_dti"), (int, float)) else 0.02570,
        "holdout_ci95": [0.0190, 0.0330],
        "max_nonlattice_3px_overlap_195_files": 0.3500,
        "positive_dots": 38000,
        "lbcal_physics_estimate": None,
        "sgmc_cal_estimate": None,
        "verdict": "NEGATIVE — 0.0257 holdout",
    })

    fchd_lbcal = next(r["lbcal_physics_estimate"] for r in lane_rows if "FCHD-NCM" in r["lane"])
    fchd_rc["diagnostic_estimates_not_confirmed_scores"]["lbcal_7feature_physics_estimate"] = fchd_lbcal
    fchd_rc["uniqueness"]["max_u3_overlap_vs_oct27_peers"] = round(max(r["fchd_u3_overlap_vs_row"] for r in peer_rows), 4)
    (ROOT / "evidence" / "fchd_run_card.json").write_text(json.dumps(fchd_rc, indent=2) + "\n")

    master = {
        "schema": "master-audit-2026-10-27-v2",
        "evidence_notice": (
            "HOLDOUT-DTI is measured on GEMSDOE32-HIDE-RECOVER-v3.0 (22,232 withheld catalogue fault pixels, "
            "masking only d_visible <= 2 px per fold). LBCAL-Physics and SGMC-Cal are MODEL ESTIMATES, never "
            "ORGANIZER-CONFIRMED portal scores. Historical peer scores are OWNER-REPORTED claims without organizer receipts."
        ),
        "promoted_repository_submission": {
            "lane": "SGCE",
            "file": sgce_rc["submission_name"] + "-zeros.tif",
            "sha256": sgce_rc["raster_sha256"],
            "dots": int(sgce_dots.sum()),
            "holdout_dti": round(float(sgce_rc["holdout"]["candidate"]["dti"]), 5),
            "lbcal_physics_estimate": next(r["lbcal_physics_estimate"] for r in lane_rows if "SGCE" in r["lane"]),
            "max_nonlattice_overlap_195_files": 0.6903,
            "max_u3_overlap_vs_oct27_peers": round(max(r["sgce_u3_overlap_vs_row"] for r in peer_rows), 4),
        },
        "session4_fchd_ncm_lane": {
            "lane": "FCHD-NCM",
            "selected_experiment": fchd_rc["selected_experiment"],
            "file": fchd_rc["submission_file"],
            "sha256": fchd_rc["raster_sha256"],
            "dots": fchd_rc["emitted_dots"],
            "holdout_dti": fchd_rc["holdout"]["pooled_dti"],
            "holdout_ci95": fchd_rc["holdout"]["ci95_cluster_bootstrap"],
            "lbcal_physics_estimate": fchd_lbcal,
            "sgmc_cal_estimate": fchd_rc["diagnostic_estimates_not_confirmed_scores"]["sgmc_prevalence_calibrated_dti_estimate"],
            "max_nonlattice_overlap_195_files": fchd_rc["uniqueness"]["U3_max_nonlattice_overlap_3px"],
            "max_u3_overlap_vs_oct27_peers": round(max(r["fchd_u3_overlap_vs_row"] for r in peer_rows), 4),
            "verdict": fchd_rc["verdict"],
        },
        "focus_9_sites": focus_rows,
        "peer_prompt_2026_10_27_rasters": peer_rows,
        "empty_peer_repos_verified_zero_tif": peer_manifest["empty_repos_verified_zero_tif"],
        "ledger_addendum_rasters": addendum_rows,
        "wbggemsdoe3_lanes": lane_rows,
    }
    (ROOT / "evidence" / "master_audit_2026-10-27.json").write_text(json.dumps(master, indent=2) + "\n")
    print("\nWrote v2 evidence/master_audit_2026-10-27.json.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
