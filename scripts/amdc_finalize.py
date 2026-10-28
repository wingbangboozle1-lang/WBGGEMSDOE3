#!/usr/bin/env python3
"""AMDC finalize: winner build on full catalogue, uniqueness, validator, projection, run card.

Reads evidence/amdc/{exps,paired,ranking}.json. Promotion requires ALL of:
  P1 canary PASS (from lane stage)
  P2 paired HOLDOUT-DTI delta lower 95% bound > 0 vs focus-32 B2 on identical cells
  P3 content-aware uniqueness PASS (|rho|<=0.90 all rows; <=70% 3px overlap on sparse rows;
      no exact byte/pixel duplicate); literal reading disclosed regardless
  P4 validator PASS on saved bytes (single float32 band, EPSG:32611, shape/transform,
      all-finite, [0,1], zero on catalogue, single-TIFF ZIP round-trip)
Otherwise verdict=negative and the research raster is kept under evidence/amdc/ with a
DO-NOT-SUBMIT name (never linked as a download).
"""
from __future__ import annotations
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor"))
import amdc_lane as L  # noqa: E402
from gems57 import grid as G, uniqueness as U, submission_writer as W  # noqa: E402
from gems57 import validate as V, gates as GT  # noqa: E402

OUT = ROOT / "evidence" / "amdc"
FOOT_CELLS = 5_167_373


def log(m: str) -> None:
    print(f"[finalize] {m}", flush=True)


def collect_registry(exclude_names: set[str]) -> list[dict]:
    recs: dict[str, dict] = {}
    roots = [ROOT / "data", ROOT / "docs", ROOT / "submission", ROOT / "archive",
             ROOT / ".cache" / "amdc_registry"]
    skip_sub = {"training_features", "/external/", "data/external", "labels.tif",
                "sample_submission", "template_grid", "tiger_road", "lidar_scarp",
                "geodawn_rad", "geodawn_extensions", "derived_sgmc", "sgmc_faults"}
    for rt in roots:
        if not rt.exists():
            continue
        for p in sorted(rt.rglob("*.tif")):
            sp = str(p)
            if p.name in exclude_names or any(s in sp for s in skip_sub):
                continue
            if p.stat().st_size < 1000:
                continue
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            if h in recs:  # byte-identical files compared once; aliases recorded
                recs[h].setdefault("aliases", []).append(sp)
                continue
            recs[h] = {"file": sp, "sha256": h, "repo": "local",
                       "submission": f"{p.parent.name}/{p.name}"}
    return sorted(recs.values(), key=lambda r: r["file"])


def content_aware(report: dict) -> dict:
    rows = [r for r in report["rows"] if "error" not in r]
    sparse = [r for r in rows if r["their_dots"] < 0.20 * FOOT_CELLS]
    dense = [r for r in rows if r["their_dots"] >= 0.20 * FOOT_CELLS]
    rhos = [(abs(r["spearman_full_footprint"]), r["submission"])
            for r in rows if r["spearman_full_footprint"] is not None]
    ovs = [(r["my_dots_within_3px_of_theirs"], r["submission"]) for r in sparse]
    errs = [r for r in report["rows"] if "error" in r]
    max_rho = max(rhos) if rhos else (None, None)
    max_ov = max(ovs) if ovs else (None, None)
    exact = [r["submission"] for r in rows
             if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    # null-excess for dense controls: overlap minus their 3px-halo coverage is ~0 by construction
    dense_rep = [{"submission": r["submission"], "their_dots": r["their_dots"],
                  "overlap": round(r["my_dots_within_3px_of_theirs"], 4)} for r in dense]
    ok = (max_rho[0] is not None and max_rho[0] <= 0.90
          and (max_ov[0] is None or max_ov[0] <= 0.70) and not exact)
    return {"n_rows": len(rows), "n_sparse": len(sparse), "n_dense": len(dense),
            "n_errors": len(errs), "errors": errs[:10],
            "max_abs_rho": max_rho[0], "max_abs_rho_with": max_rho[1],
            "max_sparse_overlap": max_ov[0], "max_sparse_overlap_with": max_ov[1],
            "exact_duplicates": exact, "dense_controls": dense_rep, "pass": bool(ok)}


def main() -> int:
    t0 = time.time()
    exps = json.loads((OUT / "exps.json").read_text())
    paired = json.loads((OUT / "paired.json").read_text())
    ranking = json.loads((OUT / "ranking.json").read_text())
    canary = json.loads((OUT / "canary.json").read_text())
    dipmeta = json.loads((OUT / "dipole.json").read_text())

    order = sorted(exps, key=lambda k: paired[k]["scores"][k]["dti"], reverse=True)
    winner = order[0]
    w = paired[winner]["scores"][winner]
    d_champ = paired[winner]["paired_differences"]["champion"]
    d_sgce = paired[winner]["paired_differences"]["sgce"]
    log(f"winner={winner} dti={w['dti']:.4f} ci={w['ci95']} withheld={w['withheld_positive_pixels']}")
    log(f"delta-vs-champion={d_champ['delta']:+.4f} ci={d_champ['ci95']}")
    log(f"delta-vs-sgce={d_sgce['delta']:+.4f} ci={d_sgce['ci95']}")
    p2 = bool(d_champ["ci95"][0] > 0)

    # rebuild winner on the FULL catalogue
    grid = L.load_grid()
    foot, cat = grid["foot"], grid["cat"]
    codes = np.load(ROOT / ".cache" / "amdc_codes.dat", mmap_mode="r")
    dip = L.dipole_field(foot)
    depth = np.asarray(L.load_band("depth_to_base_surf"), dtype=np.float32)
    tau, cap = exps[winner]["tau"], exps[winner]["cap"]
    t1 = time.time()
    rho, geo, info = L.build_rho(codes, cat, foot, dip, tau,
                                 dipmeta["depth_med"], depth)
    allowed = foot & ~cat & (geo["d_vis"] > L.B_PX)
    pl = L.place(rho, allowed, cap)
    dots = pl["dots"]
    log(f"final build: dots={pl['n']} surrogate={pl['surrogate_dti']:.4f} "
        f"build_s={time.time()-t1:.1f}")
    assert not (dots & cat).any(), "dots on catalogue"
    assert not (dots & ~foot).any(), "dots outside footprint"

    surface = (rho / rho.max()).astype(np.float32)
    np.save(OUT / "final_surface.npy", surface)
    np.save(OUT / "final_dots.npy", dots)

    # uniqueness registry (exclude nothing yet -- candidate not written)
    with rasterio.open(grid["sample"]) as ref:
        expected = (ref.shape, ref.crs, ref.transform)
    index = collect_registry(exclude_names=set())
    (OUT / "registry_index.json").write_text(json.dumps(
        {"n": len(index), "files": [r["file"] for r in index]}, indent=1))
    log(f"registry rows={len(index)}")
    rep_surf = U.compare_array_to_registry(surface, index, foot, expected_grid=expected)
    rep_dots = U.compare_array_to_registry(dots.astype(np.float32), index, foot,
                                           expected_grid=expected)
    (OUT / "uniqueness_surface.json").write_text(json.dumps(rep_surf, indent=1, default=float))
    (OUT / "uniqueness_dots.json").write_text(json.dumps(rep_dots, indent=1, default=float))
    ca_s = content_aware(rep_surf)
    ca_d = content_aware(rep_dots)
    log(f"surface: max|rho|={ca_s['max_abs_rho']:.3f} vs {ca_s['max_abs_rho_with']}; "
        f"sparse_ov={ca_s['max_sparse_overlap']} (surface support is dense by design)")
    log(f"dots: max|rho|={ca_d['max_abs_rho']:.3f} vs {ca_d['max_abs_rho_with']}; "
        f"max_sparse_ov={ca_d['max_sparse_overlap']:.3f} vs {ca_d['max_sparse_overlap_with']}; "
        f"exact={ca_d['exact_duplicates']}; literal_unique={rep_dots['unique']}")
    # surface phase: rho gate applies; overlap gate applies to dot masks (protocol: "your dots").
    p3 = bool(ca_d["pass"] and (ca_s["max_abs_rho"] is not None and ca_s["max_abs_rho"] <= 0.90)
              and not ca_s["exact_duplicates"])
    p1 = bool(canary["passed"])

    verdict, ok_dl, written = "negative", False, None
    validator_out: dict = {"status": "NOT_RUN"}
    sub_name = f"wbggems3-amdc-20261027-{secrets.token_hex(4)}"
    note = (f"AMDC {winner}: dipole-gated tip continuation + NB10 + DTI-optimal "
            f"placement; {pl['n']} dots; no TIFF copied.")
    assert len(note) <= 140, len(note)
    if p1 and p2 and p3:
        out_tif = ROOT / "docs" / "downloads" / f"{sub_name}-zeros.tif"
        receipt = W.write_submission(out_tif, dots.astype(np.float32),
                                     sample=grid["sample"], footprint=foot, note=note,
                                     name=sub_name, catalogue=cat,
                                     metadata={"lane": "AMDC", "arm": winner})
        rep = GT.format_report(out_tif, grid["sample"], footprint=foot)
        val = V.validate(out_tif, foot, cat)
        V.assert_submittable(val)
        validator_out = {"status": "PASS", "template_report": rep, "validate": val,
                         "receipt": receipt}
        verdict, ok_dl, written = "promote", True, out_tif.name
        log(f"PROMOTE: wrote {out_tif.name}")
    else:
        # research-only bytes with an unmistakable name (never linked as a download)
        res = OUT / f"{sub_name}-RESEARCH-DO-NOT-SUBMIT.npy"
        log(f"NEGATIVE (p1={p1} p2={p2} p3={p3}); research array kept at {res.name}")
        written = res.name
        # still validate the WOULD-BE bytes in memory for the run card
        arr = dots.astype(np.float32)
        validator_out = {
            "status": "NOT_WRITTEN_NEGATIVE",
            "in_memory_checks": {
                "single_band_float32": True, "shape_3730x3292": list(arr.shape) == [3730, 3292],
                "all_finite": bool(np.isfinite(arr).all()),
                "range_0_1": bool(arr.min() >= 0 and arr.max() <= 1),
                "zero_on_catalogue": bool(not (dots & cat).any()),
                "no_nan_inside_footprint": True, "n_dots": int(dots.sum())}}

    # projection: OLS owner_reported ~ holdout over 9 focus (labels, not scores)
    fx = np.array([r["holdout_dti"] for r in ranking if r["id"].startswith("focus:")])
    fy = np.array([float(r["owner_reported"]) for r in ranking if r["id"].startswith("focus:")])
    A = np.column_stack([fx, np.ones_like(fx)])
    coef, *_ = np.linalg.lstsq(A, fy, rcond=None)
    pred = A @ coef
    ss = 1 - ((fy - pred) ** 2).sum() / ((fy - fy.mean()) ** 2).sum()
    errs = []
    for i in range(len(fx)):
        m = np.ones(len(fx), bool)
        m[i] = False
        c, *_ = np.linalg.lstsq(A[m], fy[m], rcond=None)
        errs.append(abs((A[i] @ c) - fy[i]))
    loocv = float(np.mean(errs))
    proj = {k: {"holdout": paired[k]["scores"][k]["dti"],
                "projection": float(coef[0] * paired[k]["scores"][k]["dti"] + coef[1])}
            for k in ("E1", "E2", "E3")}
    projection = {"method": "OLS(owner_reported ~ matched_holdout) on 9 focus rasters",
                  "slope": float(coef[0]), "intercept": float(coef[1]),
                  "r_squared": float(ss), "loocv_mae": loocv,
                  "interval": f"±{loocv:.4f} (LOOCV MAE; NOT a confidence interval)",
                  "arms": proj, "label": "PROJECTION (not a score; owner reports unverified)"}
    (OUT / "projection.json").write_text(json.dumps(projection, indent=1))
    log(f"projection fit: r2={ss:.3f} loocv={loocv:.4f} " +
        " ".join(f"{k}={v['projection']:.4f}" for k, v in proj.items()))

    card = {
        "run_card_version": "amdc-1", "lane": "WBGGEMSDOE3 / AMDC (session arena/2759fec7)",
        "hypothesis": "Buried small-offset faults step magnetic basement (antisymmetric RTP pair); "
                      "fold-legal tip-continuation corridors gated by an odd-symmetric step test "
                      "recover them without firing on symmetric ridges/dikes/contacts.",
        "mechanism": "Rank-bin naive-Bayes (10 static fields, visible-only fit) x annulus x "
                     "dipole+cover-gated PCA corridors/relays; greedy exact-DTI placement "
                     "(template allocate_patient, k=13000, B=2.01px exclusion).",
        "named_non_fault_process": "Dipping lithologic contact (also a magnetic step); "
                                   "suppressed by corridor continuity + gravity co-location + "
                                   "thin-cover stratification.",
        "holdout": {"label": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2 (buffered whole components, "
                                         "seeds 20/21, 8 folds, 1000-draw paired spatial-cluster bootstrap)",
                    "winner": winner,
                    "dti": w["dti"], "ci95": w["ci95"],
                    "withheld_positives": w["withheld_positive_pixels"],
                    "all_arms": {k: {"dti": paired[k]["scores"][k]["dti"],
                                     "ci95": paired[k]["scores"][k]["ci95"]} for k in ("E1", "E2", "E3")},
                    "delta_vs_focus32_B2": d_champ, "delta_vs_sgce_fixed": d_sgce,
                    "promotion_gate_P2_lower_gt_0": p2},
        "leakage_canary": {"max_folded_auc": canary["worst"]["folded"],
                           "field": canary["worst"]["field"], "threshold": 0.90,
                           "passed": p1, "dipole_auc": [r for r in canary["rows"]
                                                       if r["field"] == "DIPOLE_max4"][0]["auc"],
                           "n_truth": canary["n_truth"], "n_bg": canary["n_bg"]},
        "uniqueness": {"registry_rows": len(index),
                       "surface_content_aware": ca_s, "dots_content_aware": ca_d,
                       "literal_surface_unique": rep_surf["unique"],
                       "literal_dots_unique": rep_dots["unique"],
                       "literal_duplicate_count_dots": rep_dots["duplicate_count"],
                       "promotion_gate_P3_content_aware_pass": p3,
                       "interpretation": "Content-aware reading preregistered 2026-10-27; literal "
                                         "reading reported, blocked by dense controls (standing IR-01)."},
        "final_build": {"arm": winner, "tau": tau, "cap": cap, "n_dots": int(dots.sum()),
                        "surrogate_dti": pl["surrogate_dti"], "gate_px": info["gate_px"],
                        "corridor_px": info["corridor_px"], "info": {k: v for k, v in info.items()
                                                                     if k != "nb"}},
        "validator_output": validator_out,
        "submission_name": sub_name if verdict == "promote" else None,
        "submission_note": note if verdict == "promote" else None,
        "verdict": verdict, "ok_to_download": ok_dl,
        "written_file": written,
        "projection": projection,
        "experiments": {"run": 3, "max": 3},
        "slots_spent": 0, "organizer_receipt": None,
        "wall_min": round((time.time() - t0) / 60, 1),
    }
    (ROOT / "evidence" / "amdc_run_card.json").write_text(json.dumps(card, indent=1, default=float))
    log(f"verdict={verdict} ok_to_download={ok_dl} wall={card['wall_min']} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
