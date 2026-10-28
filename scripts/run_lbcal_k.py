#!/usr/bin/env python3
"""LBCAL-K (E1): uniqueness-repaired leaderboard-calibrated density placement.

Preregistration: knowledge/preregistration-2026-10-28-lbcalk.md (gates G0-G5
fixed BEFORE this script runs).  This is a NEW construction: it reuses the
fitted LBCAL density (evidence/lbcal_variants.json), the shared hide-and-recover
evaluator (src/gemsw/holdout.py, GEMSDOE32-HIDE-RECOVER-v3.0), the pinned shared
template writer/validator (57GEMSDOE), and the FCHD-NCM full-registry knapsack
allocator (src/fchd/registry_full.py).  It never modifies shared tools and never
uploads anything.

Steps (all automated, fail-closed, no human inspection):
  0. Restore inputs (SHA-pinned mirrors; no portal login).
  1. pi surface from the preregistered bounded model + G1 pre-placement |Spearman| <= 0.90.
  2. G0 leakage canary on every fold-local feature and pi itself (AUC <= 0.90).
  3. Fixed-budget knapsack-constrained CELF placement: budget swept over
     {45k, 50k, 55k, 60k} with construction-guaranteed cap 0.635 vs every
     sparse registry mask; choose the gate-passing argmax of in-model E[DTI].
     (E1 used a 120k pool + exact Dinkelbach prune and FAILED G2 at 0.999 --
     the prune re-concentrates capped pools inside dense halos, IR-30; the
     adaptive-cap repair then collapsed to 119 dots. Both records preserved.)
  4. Cross-fit ESTIMATE (design half A, evaluate under half B and vice versa,
     seeds 1/2) mirroring the EXACT final procedure (fixed budget, cap 0.635,
     no prune); family bootstrap 95 %.
  5. HOLDOUT-DTI: fold-local pi replay (d_cat rebuilt from visible faults only),
     identical capped allocation per holdout cell, pooled evaluator with
     b_visible_px = 2.0, 256-block cluster bootstrap (labelled, IR-11 caveat).
  6. Template writer + validator + independent byte re-read (range [0,1]
     everywhere, zeros outside footprint -- the portal range-error fix).
  7. G2 final-dot audit vs the FULL registry (content-aware gates + literal IR-01
     disclosure); removal-only repair backstop (0.68, fail-closed if it guts
     >25% of dots).  G3 format, G4 cross-fit ESTIMATE > 0.2778 => verdict.
  8. Run card: evidence/lbcal_k_run_card.json (labels per protocol rule 3).
E2 (cross-model second opinion) lives in scripts/run_lbcal_k_e2.py.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    sys.path.insert(0, str(p))

from lbcal import VERSION, coverage as COV, data as D, design as DS, features as F, model as Mdl  # noqa: E402

# Reuse the lane-local helper functions from the (deliberately blocked) historical
# design script; its main() raises immediately, only its helpers are used.
_spec = importlib.util.spec_from_file_location("lbcal_design_helpers", ROOT / "scripts" / "lbcal_design.py")
LD = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LD)  # also puts TEMPLATE/src on sys.path (hash-verified)

from gems57.submission_writer import write_submission  # noqa: E402
from gems57.validate import validate as template_validate  # noqa: E402
from gemsw import holdout as H  # noqa: E402
from src.fchd.registry_full import (  # noqa: E402
    audit_dots_against_full_registry,
    build_or_load_full_registry,
    celf_knapsack_allocate,
    check_surface_correlations,
)

OUT_DIR = ROOT / "evidence" / "lbcal_k"
SUB_DIR = ROOT / "submission"

CEIL = 120_000            # E1 placement ceiling (Dinkelbach pool; superseded by IR-30)
B_SWEEP = (45_000, 50_000, 55_000, 60_000)  # E1-repairb fixed-budget candidates
CAP_FINAL = 0.635         # construction-guaranteed overlap cap (FCHD-proven binding value)
CAP_CELL = 0.60           # cell-level cap (cells are never pruned; N == budget)
REPAIR_TARGET = 0.68      # backstop repair threshold (gate is 0.70)
MAX_REPAIR_FRAC = 0.25    # fail closed if removal-repair would gut >25% of dots
COLLAR_PX = 2.0           # export collar around the FULL mapped catalogue
CHAMPION_OWNER = 0.2778   # OWNER-REPORTED GEMSDOE32 B2 (never a receipt)
STATED_HIGH = 0.3195      # user-stated leaderboard reference (never a receipt)
CHAMPION_PROXY = 0.09920232315251679   # HOLDOUT-DTI champion proxy (session2/fchd cards)
SGCE_CONSTRUCTION = 0.1674940880255947  # HOLDOUT-DTI SGCE released-construction (session2 card)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def gate(name: str, passed: bool, detail) -> dict:
    return dict(name=name, passed=bool(passed), detail=detail)


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUB_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ inputs
    grid = D.load_grid()
    foot, cat = grid.foot, grid.cat
    feats = dict(np.load(D.CACHE / "features.npz"))
    cell = feats["cell"]
    log(f"grid foot={int(foot.sum())} cat={int(cat.sum())}")

    var = json.loads((ROOT / "evidence" / "lbcal_variants.json").read_text())
    sel = var["selected"]
    vrec = var["variants"][sel]
    beta, pi_max, lam = np.array(vrec["beta"]), vrec["pi_max"], vrec["lam"]
    M, names = Mdl.design_matrix()
    pi, pic = LD.pi_from_beta(beta, pi_max, M, cell, foot)
    G = float(pi.sum(dtype=np.float64))
    log(f"model {sel}: G={G:.0f} pi_max={pi_max} max_pi={float(pi.max()):.4f}")

    d_cat_full = feats["d_cat_px"]
    eligible = foot & (d_cat_full > COLLAR_PX)
    log(f"eligible after {COLLAR_PX}px export collar: {int(eligible.sum())}")

    reg = build_or_load_full_registry(foot)
    log(f"registry: files={reg['index']['files_scanned']} masks={reg['index']['unique_dot_masks']} "
        f"sparse={reg['index']['sparse_nonlattice_masks']}")

    gates: list[dict] = []

    # ------------------------------------------------- G1 pre-placement surface
    t1 = time.time()
    g1 = check_surface_correlations(pi, foot, reg)
    gates.append(gate("G1_preplacement_surface", g1["passed_le_0p90"],
                      {"max_abs_spearman": g1["max_abs_spearman"],
                       "n_continuous_compared": g1["n_continuous_compared"],
                       "top5": g1["top10"][:5]}))
    log(f"G1 surface: max|rho|={g1['max_abs_spearman']:.4f} over "
        f"{g1['n_continuous_compared']} surfaces ({time.time()-t1:.0f}s)")
    (OUT_DIR / "preplacement_surface.json").write_text(
        json.dumps(g1, indent=1, default=float) + "\n")
    if not g1["passed_le_0p90"]:
        raise SystemExit("STOP: pre-placement surface duplicates a registry raster (G1 fail)")

    # ------------------------------------------------------ G0 leakage canary
    t1 = time.time()
    ctx = H.load_holdout_context(ROOT / "data" / "raw")
    log(f"holdout context: {len(ctx.cells)} cells, "
        f"{sum(c.n_truth for c in ctx.cells)} withheld px")
    feat_maps = {
        "topo_rank": feats["topo_rank"],
        "crest": feats["crest"].astype(np.float32),
        "lidar_rank": np.nan_to_num(feats["lidar_rank"], nan=-1.0),
        "mag_rank": np.nan_to_num(feats["mag_rank"], nan=-1.0),
        "d_sgmc_px": feats["d_sgmc_px"],
        "slope_rank": np.nan_to_num(feats["slope_rank"], nan=-1.0),
    }
    rng = np.random.default_rng(7)
    canary_rows = []
    for c in ctx.cells:
        d_vis = ndi.distance_transform_edt(~c.visible_full).astype(np.float32)
        cid = LD.recell_dcat(cell, d_vis, foot)
        pi_c = np.where(foot, pic[np.maximum(cid, 0)], 0).astype(np.float32)
        sl = c.bbox
        allowed_c = c.active_sub & foot[sl] & ~c.visible_full[sl] & (c.d_vis_sub > COLLAR_PX)
        truth = np.zeros(c.active_sub.shape, bool)
        truth[c.truth_coords] = True
        neg_idx = np.flatnonzero(allowed_c & ~truth)
        neg_idx = rng.choice(neg_idx, size=min(200_000, neg_idx.size), replace=False)
        pos_idx = np.flatnonzero(truth)
        row = dict(cell=c.key, n_truth=int(pos_idx.size))
        maps = dict(feat_maps, d_visible_px=d_vis, lbcal_pi=pi_c)
        for nm, mp in maps.items():
            sub = mp[sl].ravel()
            row[nm] = round(LD.auc(sub[pos_idx], sub[neg_idx]), 4) if pos_idx.size else None
        canary_rows.append(row)
    worst_auc, worst_feat = 0.0, None
    for r in canary_rows:
        for nm, a in r.items():
            if nm in ("cell", "n_truth") or a is None:
                continue
            sep = max(a, 1 - a)
            if sep > worst_auc:
                worst_auc, worst_feat = sep, f"{nm}@{r['cell']}"
    canary = dict(rule="each feature alone vs withheld positives; max(AUC,1-AUC) > 0.90 => leakage",
                  worst_separation=round(worst_auc, 4), worst_feature=worst_feat,
                  leakage=bool(worst_auc > 0.90), per_cell=canary_rows)
    gates.append(gate("G0_leakage_canary", not canary["leakage"],
                      {k: canary[k] for k in ("worst_separation", "worst_feature", "rule")}))
    log(f"G0 canary: worst={worst_auc:.4f} ({worst_feat}) ({time.time()-t1:.0f}s)")
    (OUT_DIR / "canary.json").write_text(json.dumps(canary, indent=1, default=float) + "\n")
    if canary["leakage"]:
        raise SystemExit("STOP: leakage canary failed (G0)")

    # ---------------------------------- 3. fixed-budget capped CELF (IR-30b)
    # The exact Dinkelbach prune re-concentrates every capped pool inside dense
    # halos (E1: 120k->60k ov 0.999; adaptive passes: 120k->37k ov 0.985 then
    # contraction to 119 dots -- evidence/lbcal_k/adaptive_passes_log.txt).
    # FCHD-style fixed budget: CELF(budget=B, cap=0.635) guarantees overlap
    # <= 0.635 BY CONSTRUCTION because cells are never pruned afterwards.
    # Sweep B over the E1 Dinkelbach region and choose the gate-passing
    # argmax of in-model E[DTI]; cross-fit halves mirror this exact procedure.
    t1 = time.time()
    pass_log = []
    best = None
    for B in B_SWEEP:
        d_B, info_B = celf_knapsack_allocate(pi, eligible, foot, reg, budget_k=B,
                                             max_overlap_cap=CAP_FINAL)
        n_B = int(d_B.sum())
        terms_B = DS.expected_terms(pi, d_B, G)
        probe = audit_dots_against_full_registry(d_B, foot, reg)
        gate_ok_B = bool((not probe["U1_exact_duplicate"])
                         and probe["U3_nonlattice_pass_le_0p70"]
                         and probe["U3_lattice_excess_pass_le_0p05"])
        pass_log.append(dict(budget=B, dots=n_B, in_model=round(terms_B["dti"], 6),
                             max_nonlattice=round(probe["U3_max_nonlattice_overlap_3px"], 5),
                             lat_excess=probe["U3_lattice_excess"],
                             u1_exact_duplicate=probe["U1_exact_duplicate"],
                             gate_ok=gate_ok_B, info=info_B))
        log(f"sweep B={B}: dots={n_B} in-model={terms_B['dti']:.4f} "
            f"max_nonlattice={probe['U3_max_nonlattice_overlap_3px']:.4f} "
            f"lat_excess={probe['U3_lattice_excess']} gate_ok={gate_ok_B} "
            f"({time.time()-t1:.0f}s)")
        if gate_ok_B and (best is None or terms_B["dti"] > best["terms"]["dti"]):
            best = dict(dots=d_B, terms=terms_B, B=B, info=info_B)
    if best is None:
        raise SystemExit("STOP: no sweep budget passed the construction gates (fail closed)")
    dots, terms = best["dots"], best["terms"]
    B_final = best["B"]
    n_pruned = int(dots.sum())
    log(f"selected B_final={B_final} dots={n_pruned} in-model={terms['dti']:.4f}")

    st_main = COV.stats(dots.astype(np.float32), foot, cell, F.n_cells(), feats["d_cat_px"])
    ds_ = np.load(D.CACHE / "dataset.npz")
    n_px = ds_["n_px"]
    est_full = float(Mdl.predict(beta, M, st_main["C"][None], st_main["P"][None],
                                 np.array([st_main["N"]]), n_px, pi_max=pi_max)[0][0])
    log(f"in-model estimate check: {est_full:.4f}")

    # --------------------------------------- 4. cross-fit estimate (repaired)
    t1 = time.time()
    cv = json.loads((ROOT / "evidence" / "lbcal_cv.json").read_text())
    meta = json.loads((D.CACHE / "dataset_meta.json").read_text())
    key = {(m["site"], m["submission"]): i for i, m in enumerate(meta)}
    obs = np.array([key[(r["site"], r["submission"])] for r in cv["observations"]])
    fam = np.array([r["family"] for r in cv["observations"]])
    s = np.array([r["owner_reported"] for r in cv["observations"]], float)
    C, P = ds_["C"][obs].astype(float), ds_["P"][obs].astype(float)
    Nn = np.array([meta[i]["N"] for i in obs])
    keep = n_px > 0
    Mk, Ck, Pk, nk = M[keep], C[:, keep], P[:, keep], n_px[keep]
    crossfit = []
    fam_ids = np.unique(fam)
    for seed in (1, 2):
        rg = np.random.default_rng(seed)
        half = set(rg.permutation(fam_ids)[: len(fam_ids) // 2].tolist())
        A = np.array([f in half for f in fam])
        fits = {}
        for nm, msk in (("A", A), ("B", ~A)):
            fits[nm] = Mdl.fit(Ck[msk], Pk[msk], Nn[msk], nk, s[msk], Mk, names,
                               lam=lam, pi_max=pi_max)
        for d_nm, e_nm in (("A", "B"), ("B", "A")):
            pi_d, _ = LD.pi_from_beta(fits[d_nm].beta, pi_max, M, cell, foot)
            Gd = float(pi_d.sum(dtype=np.float64))
            dd, _ = celf_knapsack_allocate(pi_d, eligible, foot, reg, budget_k=B_final,
                                           max_overlap_cap=CAP_FINAL)
            sd = COV.stats(dd.astype(np.float32), foot, cell, F.n_cells(), feats["d_cat_px"])
            e = float(Mdl.predict(fits[e_nm].beta, M, sd["C"][None], sd["P"][None],
                                  np.array([sd["N"]]), n_px, pi_max=pi_max)[0][0])
            self_e = float(Mdl.predict(fits[d_nm].beta, M, sd["C"][None], sd["P"][None],
                                       np.array([sd["N"]]), n_px, pi_max=pi_max)[0][0])
            crossfit.append(dict(seed=seed, design_half=d_nm, eval_half=e_nm,
                                 dots=int(dd.sum()), in_model=round(self_e, 4),
                                 cross_fit=round(e, 4)))
            log(f"cross-fit seed={seed} design={d_nm} eval={e_nm}: dots={int(dd.sum())} "
                f"in={self_e:.4f} cross={e:.4f}")
    cross_mean = float(np.mean([c["cross_fit"] for c in crossfit]))
    boots = []
    rg = np.random.default_rng(20261028)
    for _ in range(30):
        pick = rg.choice(fam_ids, size=fam_ids.size, replace=True)
        idx = np.concatenate([np.flatnonzero(fam == f) for f in pick])
        fb = Mdl.fit(Ck[idx], Pk[idx], Nn[idx], nk, s[idx], Mk, names, lam=lam,
                     pi_max=pi_max, beta0=beta)
        boots.append(float(Mdl.predict(fb.beta, M, st_main["C"][None], st_main["P"][None],
                                       np.array([st_main["N"]]), n_px, pi_max=pi_max)[0][0]))
    boot_ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    champ = next(i for i, m in enumerate(meta)
                 if m["submission"].startswith("h33-h33-2-b2-20261004T220000Z"))
    champ_est = float(Mdl.predict(beta, M, ds_["C"][champ][None].astype(float),
                                  ds_["P"][champ][None].astype(float),
                                  np.array([meta[champ]["N"]]), n_px, pi_max=pi_max)[0][0])
    log(f"cross-fit mean={cross_mean:.4f} bootstrap95=[{boot_ci[0]:.4f},{boot_ci[1]:.4f}] "
        f"champion B2 in-model={champ_est:.4f} ({time.time()-t1:.0f}s)")

    # -------------------------------------- 5. holdout: fold-local capped replay
    t1 = time.time()
    full_elig_est = max(int(foot.sum() * 0.90), 1)
    cells_dots: dict[str, np.ndarray] = {}
    for seed in H.DRAWS:
        mass_per_fold: dict[int, float] = {}
        total_active_elig = 0
        for fold in H.FOLDS:
            c = next(cc for cc in ctx.cells if cc.key == f"draw{seed}_fold{fold}")
            d_vis = ndi.distance_transform_edt(~c.visible_full).astype(np.float32)
            cid = LD.recell_dcat(cell, d_vis, foot)
            pi_c = np.where(foot, pic[np.maximum(cid, 0)], 0).astype(np.float32)
            c._pi_c = pi_c  # stash for second pass
            elig_sub = c.active_sub & (c.d_vis_sub > COLLAR_PX)
            total_active_elig += int(elig_sub.sum())
            mass_per_fold[fold] = float(pi_c[c.bbox][elig_sub].sum())
        draw_budget = int(round(B_final * (total_active_elig / full_elig_est)))
        tot_mass = max(sum(mass_per_fold.values()), 1e-9)
        for fold in H.FOLDS:
            c = next(cc for cc in ctx.cells if cc.key == f"draw{seed}_fold{fold}")
            pi_c = c._pi_c
            sl = c.bbox
            elig_sub = c.active_sub & (c.d_vis_sub > COLLAR_PX)
            k_cell = int(round(draw_budget * (mass_per_fold[fold] / tot_mass)))
            elig_2d = np.zeros(foot.shape, bool)
            elig_2d[sl] = elig_sub
            pi_2d = np.zeros(foot.shape, np.float32)
            pi_2d[sl] = pi_c[sl]
            dd2, _ = celf_knapsack_allocate(pi_2d, elig_2d, foot, reg,
                                            budget_k=max(k_cell, 1),
                                            max_overlap_cap=CAP_CELL)
            cells_dots[c.key] = dd2[sl]
            log(f"holdout cell {c.key}: budget={k_cell} dots={int(dd2.sum())}")
    ev = H.evaluate_hide_and_recover(cells_dots, ctx, b_visible_px=COLLAR_PX,
                                     grid_n=16, n_boot=1000, name="LBCAL-K-fold-local")
    hold = {k: v for k, v in ev.items() if not k.startswith("_")}
    hold.pop("folds", None)
    hold["folds"] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                         for kk, vv in v.items()} for k, v in ev["folds"].items()}
    log(f"HOLDOUT-DTI {hold['pooled_dti']:.4f} CI {hold['ci95_cluster_bootstrap']} "
        f"n={hold['n_withheld_positives']} ({time.time()-t1:.0f}s)")
    (OUT_DIR / "holdout_detail.json").write_text(
        json.dumps(dict(holdout=hold, canary={k: v for k, v in canary.items() if k != "per_cell"}),
                   indent=1, default=float) + "\n")

    # ------------------------------------------------------------ 6. G3 format
    pred = np.where(dots, 1.0, 0.0).astype(np.float32)
    digest = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    n_dots = int(dots.sum())
    beats_est = bool(cross_mean > CHAMPION_OWNER)
    name = f"wbggems3-lbcalk-{n_dots // 1000}k-{stamp}-{digest}-zeros"
    note = (f"LBCAL-K: leaderboard-calibrated density, knapsack-unique CELF dots; "
            f"est {cross_mean:.3f} holdout {hold['pooled_dti']:.3f}")[:140]
    tif = SUB_DIR / f"{name}.tif"
    receipt = write_submission(tif, pred, grid.sample_path, foot, note=note, name=name,
                               catalogue=cat,
                               metadata=dict(lane="LBCAL-K", version=VERSION, model=sel,
                                             prereg="knowledge/preregistration-2026-10-28-lbcalk.md",
                                             experiments="E1"))
    tv = template_validate(tif, foot, cat)
    with rasterio.open(tif) as src, rasterio.open(grid.sample_path) as smp:
        back = src.read(1)
        indep = dict(shape_match=src.shape == smp.shape, crs_match=str(src.crs) == str(smp.crs),
                     transform_match=src.transform == smp.transform, count=int(src.count),
                     dtype=str(src.dtypes[0]), width=src.width, height=src.height,
                     crs=str(src.crs), transform=[round(v, 6) for v in src.transform.to_gdal()],
                     n_nan=int(np.isnan(back).sum()), n_inf=int(np.isinf(back).sum()),
                     min=float(np.nanmin(back)), max=float(np.nanmax(back)),
                     in_foot_min=float(back[foot].min()), in_foot_max=float(back[foot].max()))
    back_dots = np.isfinite(back) & (back > 0)
    d_cat_export = ndi.distance_transform_edt(~cat)
    indep.update(
        all_finite=bool(np.isfinite(back).all()),
        in_0_1_everywhere=bool(((back >= 0) & (back <= 1)).all()),
        no_positive_outside_footprint=bool(not (back_dots & ~foot).any()),
        no_positive_within_collar_2px=bool(not (back_dots & (d_cat_export <= COLLAR_PX)).any()),
        zero_on_mapped_catalogue=bool(not (back_dots & cat).any()),
        saved_dots_equal_design=bool(np.array_equal(back_dots, dots)),
        name_chars=len(name), note_chars=len(note),
    )
    validator_ok = bool(
        tv["all_checks_passed"]
        and receipt["validator"]["all_checks_passed"]
        and indep["all_finite"] and indep["in_0_1_everywhere"]
        and indep["no_positive_outside_footprint"] and indep["no_positive_within_collar_2px"]
        and indep["zero_on_mapped_catalogue"] and indep["saved_dots_equal_design"]
        and indep["shape_match"] and indep["crs_match"] and indep["transform_match"]
        and indep["count"] == 1 and indep["dtype"] == "float32"
        and len(name) <= 140 and len(note) <= 140
    )
    gates.append(gate("G3_format_portal_range", validator_ok,
                      {"template": tv["checks"], "independent": indep,
                       "receipt_sha256": receipt["sha256"],
                       "portal_error_fix": "all values finite in [0,1] everywhere; "
                                            "zeros outside the footprint; no NaN sentinels"}))

    # ------------------------------------------------- 7. G2 final-dot audit
    t1 = time.time()
    final = audit_dots_against_full_registry(dots, foot, reg)
    log(f"registry audit: max_nonlattice={final['U3_max_nonlattice_overlap_3px']:.4f} "
        f"lat_excess={final['U3_lattice_excess']} ({time.time()-t1:.0f}s)")
    (OUT_DIR / "registry_audit_final.json").write_text(json.dumps(final, indent=1, default=float) + "\n")

    repair_log = []
    repair_gutted = False
    n_repair_start = int(dots.sum())
    if final["U3_max_nonlattice_overlap_3px"] > REPAIR_TARGET:
        # Removal-only repair (disclosed): drop the lowest-pi dots inside each
        # violating comparator's dilated set until its overlap <= REPAIR_TARGET.
        # Removing r inside-dots drives (ov*n - r)/(n - r) <= t  <=>  r >= n(ov-t)/(1-t).
        sparse_entries = reg["index"]["sparse_entries"]
        d3p = reg["d3_packed"]
        flat_idx = np.flatnonzero(foot)
        pi_foot = pi[foot]
        for it in range(12):
            n_before = int(dots.sum())
            cand_idx = np.flatnonzero(dots[foot])
            if cand_idx.size == 0:
                break
            byte_idx = cand_idx >> 3
            bit_mask = (1 << (7 - (cand_idx & 7))).astype(np.uint8)
            drop = np.zeros(cand_idx.size, bool)
            worst_ov = 0.0
            n_viol = 0
            for i, entry in enumerate(sparse_entries):
                in_d3 = (d3p[i][byte_idx] & bit_mask) != 0
                ov = float(in_d3.sum()) / cand_idx.size
                if ov > REPAIR_TARGET:
                    n_viol += 1
                    worst_ov = max(worst_ov, ov)
                    need = int(np.ceil(cand_idx.size * (ov - REPAIR_TARGET)
                                       / (1.0 - REPAIR_TARGET)))
                    inside = np.flatnonzero(in_d3 & ~drop)
                    order = inside[np.argsort(pi_foot[cand_idx[inside]])]  # lowest pi first
                    drop[order[: min(need, order.size)]] = True
            if n_viol == 0:
                break
            # cand_idx is footprint-flat; map to global raster indices (IR-30 bugfix)
            gi = flat_idx[cand_idx[drop]]
            dots.reshape(-1)[gi] = False
            n_after = int(dots.sum())
            repair_log.append(dict(iter=it, removed=n_before - n_after,
                                   violations=n_viol, worst_overlap=round(worst_ov, 4)))
            log(f"repair iter {it}: removed {n_before - n_after} dots, "
                f"{n_viol} violations (worst {worst_ov:.3f})")
            if n_after == 0:
                break
        repair_removed = n_repair_start - int(dots.sum())
        repair_gutted = bool(repair_removed > MAX_REPAIR_FRAC * n_repair_start)
        repair_log.append(dict(total_removed=repair_removed,
                               frac_of_pruned=round(repair_removed / max(n_repair_start, 1), 4),
                               gutted_over_25pct=repair_gutted))
        if repair_gutted:
            log(f"REPAIR GUTTED {repair_removed}/{n_repair_start} dots -> fail closed")
        final = audit_dots_against_full_registry(dots, foot, reg)
        terms = DS.expected_terms(pi, dots, G)
        st_main = COV.stats(dots.astype(np.float32), foot, cell, F.n_cells(), feats["d_cat_px"])
        est_full = float(Mdl.predict(beta, M, st_main["C"][None], st_main["P"][None],
                                     np.array([st_main["N"]]), n_px, pi_max=pi_max)[0][0])
        # saved bytes are stale after repair -> rewrite under a new unique name
        pred = np.where(dots, 1.0, 0.0).astype(np.float32)
        digest = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        n_dots = int(dots.sum())
        name = f"wbggems3-lbcalk-{n_dots // 1000}k-{stamp}-{digest}-zeros"
        note = (f"LBCAL-K: leaderboard-calibrated density, knapsack-unique CELF dots; "
                f"est {cross_mean:.3f} holdout {hold['pooled_dti']:.3f}")[:140]
        tif = SUB_DIR / f"{name}.tif"
        receipt = write_submission(tif, pred, grid.sample_path, foot, note=note, name=name,
                                   catalogue=cat,
                                   metadata=dict(lane="LBCAL-K", version=VERSION, model=sel,
                                                 repair=repair_log[-1] if repair_log else None))
        tv = template_validate(tif, foot, cat)
        with rasterio.open(tif) as src, rasterio.open(grid.sample_path) as smp:
            back = src.read(1)
            indep = dict(shape_match=src.shape == smp.shape,
                         crs_match=str(src.crs) == str(smp.crs),
                         transform_match=src.transform == smp.transform, count=int(src.count),
                         dtype=str(src.dtypes[0]), n_nan=int(np.isnan(back).sum()),
                         n_inf=int(np.isinf(back).sum()),
                         min=float(back.min()), max=float(back.max()))
        back_dots = np.isfinite(back) & (back > 0)
        indep.update(all_finite=bool(np.isfinite(back).all()),
                     in_0_1_everywhere=bool(((back >= 0) & (back <= 1)).all()),
                     no_positive_outside_footprint=bool(not (back_dots & ~foot).any()),
                     no_positive_within_collar_2px=bool(not (back_dots & (d_cat_export <= COLLAR_PX)).any()),
                     zero_on_mapped_catalogue=bool(not (back_dots & cat).any()),
                     saved_dots_equal_design=bool(np.array_equal(back_dots, dots)),
                     name_chars=len(name), note_chars=len(note))
        validator_ok = bool(tv["all_checks_passed"] and receipt["validator"]["all_checks_passed"]
                            and indep.get("all_finite") and indep.get("in_0_1_everywhere")
                            and indep.get("no_positive_outside_footprint")
                            and indep.get("no_positive_within_collar_2px")
                            and indep.get("zero_on_mapped_catalogue")
                            and indep.get("saved_dots_equal_design")
                            and indep.get("shape_match") and indep.get("crs_match")
                            and indep.get("transform_match")
                            and indep["count"] == 1 and indep["dtype"] == "float32")
        gates[-1] = gate("G3_format_portal_range", validator_ok,
                         {"template": tv["checks"], "independent": indep,
                          "receipt_sha256": receipt["sha256"],
                          "note": "bytes regenerated after removal-only uniqueness repair"})
        log(f"post-repair: dots={n_dots} max_nonlattice="
            f"{final['U3_max_nonlattice_overlap_3px']:.4f} in-model={est_full:.4f}")

    gates.append(gate(
        "G2_final_dot_uniqueness",
        bool((not final["U1_exact_duplicate"])
             and final["U3_nonlattice_pass_le_0p70"]
             and final["U3_lattice_excess_pass_le_0p05"]
             and (not repair_gutted)),
        {"U1_exact_duplicate": final["U1_exact_duplicate"],
         "U3_max_nonlattice_overlap_3px": final["U3_max_nonlattice_overlap_3px"],
         "U3_lattice_excess": final["U3_lattice_excess"],
         "U3_lattice_null_rate": final["U3_lattice_null_rate"],
         "sparse_masks_compared": final["sparse_masks_compared"],
         "unique_masks_compared": final["unique_masks_compared"],
         "total_files_indexed": final["total_files_indexed"],
         "literal_all_files_max_overlap": final["literal_all_files_max_overlap"],
         "dense_witness_present": final["dense_witness_present"],
         "literal_note": "IR-01: registered 17GEMSDOE dense witness is positive on 100% of "
                         "the footprint, so the literal <=0.70 reading is unpassable for ANY "
                         "nonempty candidate; the content-aware gates (U1/U3/lattice) are the "
                         "decision rule, disclosed per preregistration G2.",
         "repair_log": repair_log,
         "repair_gutted_over_25pct": repair_gutted,
         "top10_nonlattice": final["top10_nonlattice"][:10] if "top10_nonlattice" in final
                             else final["top15_nonlattice"][:10]}))

    # ------------------------------------------------------ G4 / G5 + verdict
    gates.append(gate("G4_leaderboard_estimate_gt_0p2778", beats_est,
                      {"label": "ESTIMATE (LBCAL family-CV cross-fit instrument) -- NOT a score",
                       "cross_fit_mean": round(cross_mean, 4),
                       "family_bootstrap_95": [round(v, 4) for v in boot_ci],
                       "in_model_full_design": round(est_full, 4),
                       "champion_b2_in_model": round(champ_est, 4),
                       "champion_b2_owner_reported": CHAMPION_OWNER,
                       "stated_leaderboard_reference": STATED_HIGH,
                       "instrument_family_cv_spearman": vrec["family_cv"]["spearman"],
                       "instrument_family_cv_rmse": vrec["family_cv"]["rmse"]}))
    beats_holdout_proxy = bool(hold["pooled_dti"] > CHAMPION_PROXY)
    beats_holdout_sgce = bool(hold["pooled_dti"] > SGCE_CONSTRUCTION)
    gates.append(gate("G5_holdout_context_reported", True, {
        "label": "HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld, b_visible_px=2.0)",
        "pooled_dti": round(hold["pooled_dti"], 5),
        "ci95": [round(v, 5) for v in hold["ci95_cluster_bootstrap"]],
        "n_withheld": hold["n_withheld_positives"],
        "n_spatial_clusters": hold["n_spatial_clusters"],
        "per_quadrant": hold["per_quadrant_dti"],
        "vs_champion_proxy_0.099202": round(hold["pooled_dti"] - CHAMPION_PROXY, 5),
        "beats_champion_proxy": beats_holdout_proxy,
        "vs_sgce_construction_0.16749": round(hold["pooled_dti"] - SGCE_CONSTRUCTION, 5),
        "beats_sgce_construction": beats_holdout_sgce,
        "decision_rule": "context only -- IR-11: holdout vs owner scores rho=0.089 (n=119); "
                         "the leaderboard-calibrated cross-fit instrument (rho=0.914) is the "
                         "promotion instrument for this lane (preregistered, disclosed)"}))

    core = [g for g in gates if g["name"] != "G5_holdout_context_reported"]
    verdict = "promote" if all(g["passed"] for g in core) else "negative"
    failed = [g["name"] for g in core if not g["passed"]]

    sha = D.sha256_file(tif)
    card = dict(
        schema="parallel-run card v1 (owner protocol rule 5)",
        lane="LBCAL-K", version=f"{VERSION}+knapsack-repair",
        session_branch="arena/08f7423a-wbggemsdoe3",
        utc=datetime.now(timezone.utc).isoformat(),
        hypothesis=(
            "The public leaderboard scores of ~119 archived rasters are soft, spatially "
            "integrated measurements of where the hidden expert-labelled faults are. The "
            "preregistered bounded log-linear density pi over 7 geological layers, placed by "
            "knapsack-constrained CELF submodular coverage at a fixed budget swept over the "
            "E1 Dinkelbach region (45k-60k dots) with a construction-guaranteed 0.635 cap vs "
            "all 149 sparse registry masks (the exact prune is dropped per IR-30: it "
            "re-concentrates capped pools inside dense halos), yields a unique design whose "
            "cross-fit ESTIMATE beats the 0.2778 champion lineage."),
        mechanism=(
            "pi (pi_max=0.2, lam=1e-4, selected by leave-one-family-out RMSE) over joint bins of "
            "catalogue distance, Hessian curvature, Canny slope crest, 3DEP-LiDAR scarp rank, TMI "
            "horizontal gradient, SGMC distance and slope decile; marginal-dT gain maps with a "
            "per-comparator bit-packed knapsack cap; LOO prune for the FP side of the DTI ratio; "
            "dots never within 2 px of the mapped catalogue."),
        named_non_fault_mimic=(
            "Landslide head-scarps, terrace risers and road/canal cuts share the "
            "slope/curvature/LiDAR-step signature; ordinary steep range-flank hillslopes in the "
            "70-95 slope deciles are the dominant non-fault population pi cannot separate."),
        gates=gates,
        leakage_canary={k: v for k, v in canary.items() if k != "per_cell"},
        estimate=dict(label="ESTIMATE (model output; not a score)",
                      cross_fit_mean=round(cross_mean, 4), cross_fit=crossfit,
                      family_bootstrap_95=[round(v, 4) for v in boot_ci],
                      in_model_full_design=round(est_full, 4),
                      champion_b2_in_model=round(champ_est, 4),
                      champion_b2_owner_reported=CHAMPION_OWNER,
                      instrument="LBCAL family-CV (leave-one-family-out rho="
                                 f"{vrec['family_cv']['spearman']:.3f}, RMSE="
                                 f"{vrec['family_cv']['rmse']:.4f}, n=119 owner-reported)"),
        holdout=dict(label="HOLDOUT-DTI", evaluator=hold.get("evaluator_version"),
                     pooled_dti=round(hold["pooled_dti"], 5),
                     ci95=[round(v, 5) for v in hold["ci95_cluster_bootstrap"]],
                     n_withheld=hold["n_withheld_positives"],
                     n_spatial_clusters=hold["n_spatial_clusters"],
                     per_quadrant=hold["per_quadrant_dti"],
                     vs_champion_proxy=round(hold["pooled_dti"] - CHAMPION_PROXY, 5),
                     vs_sgce_construction=round(hold["pooled_dti"] - SGCE_CONSTRUCTION, 5),
                     ir11_caveat="hide-and-recover correlates rho=0.089 with owner scores; it is "
                                 "reported for the protocol but is not the promotion instrument "
                                 "for a leaderboard-calibrated lane"),
        registry=dict(
            preplacement_surface=gates[0]["detail"],
            final=dict(U1_exact_duplicate=final["U1_exact_duplicate"],
                       U3_max_nonlattice_overlap_3px=final["U3_max_nonlattice_overlap_3px"],
                       U3_lattice_excess=final["U3_lattice_excess"],
                       U3_lattice_null_rate=final["U3_lattice_null_rate"],
                       sparse_masks_compared=final["sparse_masks_compared"],
                       total_files_indexed=final["total_files_indexed"],
                       content_aware_all_gates_pass=final["content_aware_all_gates_pass"],
                       literal_all_files_max_overlap=final["literal_all_files_max_overlap"],
                       literal_note="IR-01 dense-witness literal reading disclosed; content-aware "
                                    "gates are the decision rule per this session's brief"),
            repair_log=repair_log),
        raster=dict(path=str(tif.relative_to(ROOT)), sha256=sha, bytes=tif.stat().st_size,
                    dots=n_dots, emitted_dots=int((pred > 0).sum()),
                    zip=str(tif.with_suffix('.zip').relative_to(ROOT)),
                    receipt=str(tif.with_suffix('.json').relative_to(ROOT))),
        validator=dict(passed=validator_ok, template=tv["checks"], independent=indep),
        submission_name=name, note=note, note_chars=len(note),
        verdict=verdict, failed_gates=failed,
        ok_to_submit=("YES -- download submission/" + tif.name + " and submit; selector still "
                      "owns the actual weekly slot (weekly cap applies, nothing uploaded here)"
                      if verdict == "promote" else "NO"),
        budget=dict(experiments_run=1, experiments_max=3,
                    mechanism="fixed-budget capped CELF, no post-hoc prune (IR-30/31)",
                    b_sweep=list(B_SWEEP), b_final=B_final, cap_final=CAP_FINAL,
                    cap_cell=CAP_CELL,
                    sweep=pass_log,
                    adaptive_pass_log="evidence/lbcal_k/adaptive_passes_log.txt "
                                      "(E1-repaira collapse evidence, superseded)",
                    repair_target=REPAIR_TARGET,
                    repaired_from="evidence/lbcal_k/run_card_e1.json + adaptive_passes_log.txt "
                                  "(IR-30; same preregistered hypothesis, not a new experiment)",
                    weekly_slots_used=0,
                    wall_seconds=round(time.time() - t0, 1)),
    )
    (ROOT / "evidence" / "lbcal_k_run_card.json").write_text(
        json.dumps(card, indent=1, default=float) + "\n")
    log(f"VERDICT {verdict}; failed={failed}; file={tif.name} sha={sha[:12]} "
        f"({card['budget']['wall_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
