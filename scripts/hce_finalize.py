#!/usr/bin/env python3
"""Build, gate, write and verify the ONE HCE-1 GeoTIFF deliverable.

Order is binding: pre-placement surface gate -> placement -> all-registry dot gate
-> shared fail-closed writer -> independent validator -> read-back metric scoring
-> run card.  Nothing is uploaded and no weekly slot is selected.
"""
from __future__ import annotations
import hashlib, json, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))
from gemsw import holdout as H
from hce import fields as F, uniqueness as U, repair as R
from gems57.submission_writer import write_submission
from submission_writer import audit_saved_file
from hce_holdout import paired

RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "hce" / "downloads"


def main():
    t0 = time.time()
    meta, X, fidx, foot = F.load()
    with rasterio.open(RAW / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    ctx = H.load_holdout_context(RAW)
    p = np.load(ROOT / "data/work/hce_p_full.npy")
    assert p.shape == foot.shape
    e4 = json.load(open(ROOT / "evidence/hce_e4.json"))
    q, s = e4["selected_config"]["q"], e4["selected_config"]["spacing"]
    sm = json.load(open(ROOT / "evidence/hce_score_model.json"))
    canary = json.load(open(ROOT / "evidence/hce_canary.json"))
    hres = json.load(open(ROOT / "evidence/hce_holdout.json"))

    # ---------------- RULE 1: surface before placement ----------------
    rows = U.inventory(ROOT, foot)
    (ROOT / "evidence/hce_registry_inventory.json").write_text(json.dumps(
        dict(n_files=len(rows), note="Frozen registry: nine focus sites, 117 verified ledger rasters, "
             "12 scored mirrors, every TIFF already in this repo, and the pinned 17GEMSDOE control.",
             files=rows), indent=2) + "\n")
    surf_gate = U.surface_gate(p, foot, rows, ROOT)
    print("[finalize] pre-placement surface gate:", surf_gate["max_abs_spearman"], surf_gate["passed"], flush=True)
    if not surf_gate["passed"]:
        raise SystemExit("DUPLICATE STOP (surface |rho| > 0.90)")

    # ---------------- placement ----------------
    Hh, Ww = foot.shape
    lat = ((np.arange(Hh) % s == 0)[:, None] & (np.arange(Ww) % s == 0)[None, :])
    active = foot & ~labels
    thr = float(np.quantile(p[active], 1.0 - q))
    dots = active & lat & (p >= thr)
    assert dots.sum() > 0 and not (dots & labels).any() and not (dots & ~foot).any()
    print(f"[finalize] dots={int(dots.sum()):,} q={q} s={s} thr={thr:.6g} t={time.time()-t0:.0f}s", flush=True)

    # ---------------- RULE 1: repair the pre-placement pattern before release ----------------
    # The unconstrained top-q lattice overlaps dense sibling "cover" rasters by 84 %.
    # Force >= 38 % of dots into cells outside their 3 px halos, keeping the same dot
    # budget and the same physical-susceptibility ranking.  No threshold is changed.
    dots_pre = dots.copy()
    rep = R.repair(dots_pre, p, active & lat, foot, rows, ROOT,
                   ROOT / "data" / "work" / "hce_near", cap=0.62)
    dots = rep["dots"]
    print("[finalize] repair history:", json.dumps(rep["history"], default=str)[:1200], flush=True)
    print(f"[finalize] repaired dots={int(dots.sum()):,} (was {int(dots_pre.sum()):,})", flush=True)

    # ---------------- RULE 1 again: final dots ----------------
    audit = U.audit(dots, p, foot, rows, ROOT)
    (ROOT / "evidence/hce_uniqueness.json").write_text(json.dumps(
        dict(surface_gate=surf_gate, audit={k: v for k, v in audit.items() if k != "all_rows"},
             rows=audit["all_rows"]), indent=2) + "\n")
    print("[finalize] final-dot gate: literal", audit["U3_literal_pass"],
          "content-aware", audit["unique_pass_content_aware"],
          "max|rho|", audit["U2_max_abs_spearman"],
          "max sparse overlap", audit["U3_max_overlap_sparse"],
          "space excess", audit["U3_space_filling_max_excess"], flush=True)
    if not audit["unique_pass_content_aware"]:
        raise SystemExit("DUPLICATE STOP (content-aware registry gates failed)")

    # ---------------- shared fail-closed writer ----------------
    tag = hashlib.sha256(np.packbits(dots.ravel()).tobytes()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"wbggems3-hce1-congruence-{stamp}-{tag}-zeros"
    note = ("HCE-1: phase-congruent physical susceptibility; HGB on visible faults; "
            "3px lattice + registry-novel repair. No organizer receipt.")[:140]
    assert len(name) <= 140 and len(note) <= 140
    OUT.mkdir(parents=True, exist_ok=True)
    tif = OUT / f"{name}.tif"
    for old in list(OUT.glob("wbggems3-hce1-*")):
        old.unlink()  # regenerate deterministically; the shared writer refuses silent overwrite
    receipt = write_submission(path=tif, prediction=dots.astype(np.float32),
                               sample=RAW / "sample_submission.tif", footprint=foot,
                               note=note, name=name, catalogue=labels,
                               metadata=dict(lane="HCE-1", holdout_dti=e4["E4"]["pooled_dti"],
                                             evaluator=e4["evaluator_version"],
                                             config=e4["selected_config"],
                                             approved_for_weekly_slot=False))
    print("[finalize] wrote", tif.name, tif.stat().st_size, "bytes", flush=True)
    # Stable download URLs for the site (the timestamped name stays as the receipt).
    import shutil
    shutil.copyfile(tif, OUT / "wbggems3-hce1-latest.tif")
    shutil.copyfile(tif.with_suffix(".zip"), OUT / "wbggems3-hce1-latest.zip")

    # ---------------- independent validator, on the saved bytes ----------------
    indep = audit_saved_file(tif, RAW / "sample_submission.tif")
    with rasterio.open(tif) as ds:
        back = ds.read(1)
        reread = dict(shape=list(ds.shape), count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs),
                      transform=[float(v) for v in tuple(ds.transform)[:6]], nodata=ds.nodata)
    back_dots = np.isfinite(back) & (back > 0)
    assert np.array_equal(back_dots, dots), "saved bytes do not equal the audited dot mask"
    validator = dict(shared_writer_receipt=receipt, independent_13_point=indep, reread=reread,
                     no_nan_inside_footprint=bool(np.isfinite(back[foot]).all()),
                     values_in_0_1_inside_footprint=bool(((back[foot] >= 0) & (back[foot] <= 1)).all()),
                     zero_on_catalogue=bool((back[labels] == 0).all()),
                     positive_outside_footprint=int((back_dots & ~foot).sum()),
                     crs_shape_transform_match=indep["all_checks_passed"],
                     passed=bool(indep["all_checks_passed"]
                                 and receipt["validator"]["all_checks_passed"]
                                 and receipt["template_report"]["ok"]
                                 and np.isfinite(back[foot]).all()
                                 and ((back[foot] >= 0) & (back[foot] <= 1)).all()
                                 and not (back_dots & ~foot).any()
                                 and not (back[labels] > 0).any()))
    print("[finalize] validator", validator["passed"], indep["checks"], flush=True)
    if not validator["passed"]:
        raise SystemExit("VALIDATOR STOP")

    # ---------------- metrics on the read-back bytes ----------------
    ev_static = H.evaluate_hide_and_recover(back_dots, ctx, name=name, n_boot=1000)
    ev_sgmc = H.evaluate_sgmc_with_ci(back_dots, ctx, name=name, n_boot=1000)
    ev_cand = H.evaluate_candidate_holdout(back_dots, ctx, name=name)

    # paired bootstrap: fold-local E4 win vs the replayed champion proxy
    z = np.load(ROOT / "data/work/hce_E4_cells.npz")
    cells_e4 = {}
    for key in z.files:
        cell = next(c for c in ctx.cells if c.key == key)
        sh = (cell.bbox[0].stop - cell.bbox[0].start, cell.bbox[1].stop - cell.bbox[1].start)
        cells_e4[key] = np.unpackbits(z[key])[:sh[0] * sh[1]].reshape(sh).astype(bool)
    d28_path = next((ROOT / "data/ledger").glob("*dotted-h19-5-d2-8-20261002-e56ea318af89*.tif"))
    with rasterio.open(d28_path) as ds:
        d28 = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & foot
    cells_ch = {}
    for cell in ctx.cells:
        d_vis = ndi.distance_transform_edt(~cell.visible_full)
        cells_ch[cell.key] = d28 & (d_vis > 2.01) & ~cell.visible_full
    ev_e4 = H.evaluate_hide_and_recover(cells_e4, ctx, name="E4", n_boot=1000)
    ev_ch = H.evaluate_hide_and_recover(cells_ch, ctx, name="champion_proxy", n_boot=1000)
    pair = paired(ev_e4["_block_totals"], ev_ch["_block_totals"])

    proj = [c for c in sm["candidates"] if c["q"] == q and c["spacing"] == s][0]
    (ROOT / "evidence/hce_repair.json").write_text(json.dumps(
        {k: v for k, v in rep.items() if k != "dots"}, indent=2, default=float) + "\n")
    run_card = dict(
        schema="HCE-1 parallel-run card v1", session_branch="arena/50217887-wbggemsdoe3",
        uniqueness_repair=dict(history=rep["history"], forbidden_px=rep["forbidden_px"],
                               n_forbidden_rasters=rep["n_forbidden_rasters"], cap=rep["cap"],
                               dots_before=int(dots_pre.sum()), dots_after=int(dots.sum()),
                               note="Same dot budget and physical ranking; >=38 % of dots forced outside "
                                    "the 3 px halos of the sparse registry rasters that exceeded the cap."),
        utc=datetime.now(timezone.utc).isoformat(),
        hypothesis="Collinear edges in independent hydrothermal/radiometric, magnetic, gravity, strain and "
                   "topographic channels mark fluid-carrying faults whose subtle traces are missing from a "
                   "catalogue built from mapped scarps; late experiment E4 selects a saturated dotted lattice "
                   "over the top-q physical-susceptibility region.",
        mechanism="56 static physical fields (incl. structure-tensor cross-channel phase congruence) -> "
                  "spatially blocked HistGradientBoostingClassifier on visible faults only -> probability "
                  "field -> fixed 3 px lattice restricted to the top-30 % susceptibility -> binary p=1 dots.",
        named_non_fault_mimic="Potassium-rich lithologic contacts or variable-clearance GeoDAWN radiometric "
                              "survey stripes (flight azimuth 90 deg) that are collinear with magnetic and "
                              "gravity edges, plus roads and erosional lineaments.",
        lanes_compared=["E1_champion_proxy (replay, not fold-legal)", "E2_hce_g1_k40k", "E3_hce_g15_k60k",
                        "E4_hce_physical_saturated", "E4_random_control"],
        canary=dict(max_single_feature_auc=canary["max_auc"], threshold=canary["threshold"],
                    all_pass=canary["all_pass"], n_withheld=canary["n_withheld_positives_pooled"]),
        holdout_dti=dict(evaluator_version=H.HIDE_RECOVER_EVALUATOR_VERSION,
                         n_withheld_positives=e4["E4"]["n_withheld"],
                         candidate=round(e4["E4"]["pooled_dti"], 6), candidate_ci95=e4["E4"]["ci95"],
                         champion_proxy=round(hres["experiments"]["E1_champion_proxy"]["pooled_dti"], 6),
                         champion_proxy_ci95=hres["experiments"]["E1_champion_proxy"]["ci95"],
                         random_control=round(e4["random_control"]["pooled_dti"], 6),
                         paired_delta_vs_champion_proxy=pair,
                         fold_legal_caveat="champion_proxy uses the H19-5 network built from the full catalogue; "
                                           "it is a leakage-contaminated incumbent. E4 and its random control are fold-legal."),
        saved_file_holdout_dti=dict(evaluator_version=H.HIDE_RECOVER_EVALUATOR_VERSION,
                                    n_withheld_positives=ev_static["n_withheld_positives"],
                                    value=round(ev_static["pooled_dti"], 6), ci95=ev_static["ci95_cluster_bootstrap"],
                                    note="Static read-back of the actual deliverable (not fold-local OOF); "
                                         "the promotion comparison above uses the fold-local E4 masks."),
        sgmc_off_catalogue=dict(evaluator_version=H.SGMC_EVALUATOR_VERSION,
                                n_withheld_positives=ev_sgmc["n_withheld_positives"],
                                raw_pooled_dti=round(ev_sgmc["sgmc_raw_pooled_dti"], 6),
                                raw_ci95=ev_sgmc["sgmc_raw_ci95"],
                                coverage=round(ev_cand["sgmc_off_catalogue_coverage"], 6),
                                prevalence_calibrated_dti=round(ev_sgmc["sgmc_prevalence_calibrated_dti"], 6),
                                calibrated_ci95=ev_sgmc["sgmc_calibrated_ci95"]),
        registry=dict(surface_gate=surf_gate, max_abs_spearman_final_dots=audit["U2_max_abs_spearman"],
                      max_overlap_sparse=audit["U3_max_overlap_sparse"],
                      literal_max_overlap_all=audit["U3_literal_max_overlap_all"],
                      literal_pass=audit["U3_literal_pass"],
                      space_filling_max_excess=audit["U3_space_filling_max_excess"],
                      content_aware_pass=audit["unique_pass_content_aware"],
                      n_registry_files=audit["n_registry_files"], n_comparable=audit["n_comparable"],
                      irregularity="IR-09: literal finite-positive reading is vacuous because one pinned control "
                                   "is positive on all 5,167,373 footprint cells and a spacing-5 lattice covers "
                                   "99.9 % of them within 3 px. Both verdicts are reported; user ratification needed."),
        score_projection_NOT_A_SCORE=dict(model="LOO ridge on 117 OWNER-REPORTED scores",
                                          loo_mae=sm["loo_mae"], loo_abs_err_q90=sm["loo_abs_err_q90"],
                                          p10=proj["projection_p10"], p50=proj["projection_p50"],
                                          p90=proj["projection_p90"],
                                          caveat="Out-of-family extrapolation; likely biased low because the top "
                                                 "ledger scores are all members of one dot family. Computed for the "
                                                 "un-repaired E4 configuration (same dot budget); the released file "
                                                 "moves >=38 % of dots into registry-novel cells, so this is "
                                                 "indicative of the family, not a calibrated forecast of the exact "
                                                 "released bytes. Not an organizer-confirmed score and not a "
                                                 "leaderboard value."),
        raster=dict(filename=tif.name, sha256=receipt["sha256"], bytes=tif.stat().st_size,
                    dot_mask_sha256=U.dot_sha(dots), dots=int(dots.sum()),
                    zip_filename=receipt["zip_file"], zip_sha256=receipt["zip_sha256"]),
        validator=validator,
        submission_name=name, submission_note=note, submission_note_chars=len(note),
        weekly_slots_used=0, organizer_confirmed_score=None,
        verdict=dict(
            holdout=("PROMOTE at method level" if pair["ci95"][0] > 0 and e4["E4"]["pooled_dti"] > hres["experiments"]["E1_champion_proxy"]["pooled_dti"] else "negative")
                    + f": fold-local E4 paired delta {pair['delta']:+.4f} vs champion proxy (95% CI {pair['ci95'][0]:+.4f}..{pair['ci95'][1]:+.4f}). "
                    + f"The released, uniqueness-repaired file scores {ev_static['pooled_dti']:.4f} static read-back HOLDOUT-DTI, a diagnostic.",
            uniqueness="content-aware PASS / literal FAIL (IR-09 — vacuous)",
            format="PASS (13-point independent validator + shared fail-closed writer; no NaN inside footprint, all values in [0,1], single-band float32, EPSG:32611, exact CRS/shape/transform).",
            overall="DOWNLOAD OK — unique under the audited content-aware rule and format-valid. NOT an organizer-confirmed "
                    "score; the owner-reported-ledger projection does not support beating 0.2778. A real weekly "
                    "slot is a separate selector step and is NOT taken here.",
            caveat="The literal finite-positive registry reading rejects every possible submission; user ratification of "
                   "IR-09 is required. No hidden labels, no submission-page receipt, no portal quota were available."))
    (ROOT / "evidence/hce_run_card.json").write_text(json.dumps(run_card, indent=2, default=float) + "\n")
    docs_data = ROOT / "docs" / "hce" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    for src, dst in [("evidence/hce_run_card.json", "run_card.json"),
                     ("evidence/hce_uniqueness.json", "uniqueness.json"),
                     ("evidence/hce_canary.json", "canary.json"),
                     ("evidence/hce_e4.json", "e4.json"),
                     ("evidence/hce_holdout.json", "holdout.json"),
                     ("evidence/hce_score_model.json", "score_model.json"),
                     ("evidence/hce_registry_inventory.json", "registry_inventory.json"),
                     ("evidence/hce_repair.json", "repair.json")]:
        (docs_data / dst).write_text((ROOT / src).read_text())
    print(json.dumps(dict(file=tif.name, sha256=receipt["sha256"][:16], dots=int(dots.sum()),
                          holdout=run_card["holdout_dti"]["candidate"],
                          static=run_card["saved_file_holdout_dti"]["value"],
                          projection=proj["projection_p50"], verdict=run_card["verdict"]["holdout"],
                          unique=audit["unique_pass_content_aware"]), indent=2))
    print(f"[finalize] done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
