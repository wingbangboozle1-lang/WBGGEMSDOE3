#!/usr/bin/env python3
"""LBCAL experiment 2: design, gate and package one unique candidate.

Steps (all automated, fail-closed, no human inspection):
  1. pi from the pre-registered bounded model (evidence/lbcal_variants.json).
  2. Pre-placement uniqueness of the score surface vs every registry raster.
  3. Dinkelbach batch-greedy placement + exact pruning -> dots (never on catalogue).
  4. Cross-fit ESTIMATE (design on half the families, evaluate under the other half)
     and a family-bootstrap interval.  ESTIMATES, not scores.
  5. HOLDOUT-DTI: fold-local replay (visible-only catalogue distance, pixel-exact
     visible mask) through src/gemsw/holdout.evaluate_hide_and_recover
     (GEMSDOE32-HIDE-RECOVER-v3.0), compared with the current holdout best.
  6. Leakage canary: every feature alone vs the withheld positives (AUC > 0.90 = leak).
  7. Template writer (zeros outside the footprint) + template validator + independent
     re-read of the saved bytes + final-dot uniqueness on the saved bytes.
  8. Run card evidence/lbcal_run_card.json with the pre-registered verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import VERSION, coverage as COV, data as D, design as DS, features as F, model as Mdl  # noqa: E402

sys.path.insert(0, str(D.TEMPLATE / "src"))
from gems57 import uniqueness as U  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.validate import validate as template_validate  # noqa: E402

from gemsw import holdout as H  # noqa: E402

HOLDOUT_BEST = dict(name="HCE-1 (wbggems3-hce1-congruence)", pooled_dti=0.1292,
                    evaluator="GEMSDOE32-HIDE-RECOVER-v3.0", source="evidence/hce_run_card.json")
CHAMPION_OWNER_REPORTED = 0.2778
OUT_DIR = ROOT / "evidence" / "lbcal"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def registry_index(rows):
    return dict(rasters=[dict(repo_first=r["site"], sources=[r["submission"]], cache_file=str(ROOT / r["local"]),
                              sha256=r["sha256"]) for r in rows],
                complete_accessible_scan=True)


def pi_from_beta(beta, pi_max, M, cell, foot):
    pic = Mdl.link(M @ beta, pi_max)[0]
    return np.where(foot, pic[np.maximum(cell, 0)], 0).astype(np.float32), pic


def recell_dcat(cell, d_px, foot):
    """Replace the d_cat level of every joint cell id with the bin of a new distance map."""
    rest = 1
    for f in F.FEATURES[1:]:
        rest *= F.LEVELS[f]
    lvl = np.searchsorted(F.D_CAT_EDGES, d_px, side="right").astype(np.int32)
    return np.where(foot, lvl * rest + (np.maximum(cell, 0) % rest), -1).astype(np.int32)


def auc(pos, neg):
    x = np.concatenate([pos, neg])
    r = rankdata(x)
    n1, n0 = pos.size, neg.size
    a = (r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    return float(a)


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    grid = D.load_grid()
    foot, cat = grid.foot, grid.cat
    feats = dict(np.load(D.CACHE / "features.npz"))
    cell = feats["cell"]
    var = json.loads((ROOT / "evidence" / "lbcal_variants.json").read_text())
    sel = var["selected"]
    vrec = var["variants"][sel]
    beta, pi_max, lam = np.array(vrec["beta"]), vrec["pi_max"], vrec["lam"]
    M, names = Mdl.design_matrix()
    pi, pic = pi_from_beta(beta, pi_max, M, cell, foot)
    G = float(pi.sum(dtype=np.float64))
    allowed = foot & ~cat
    log(f"model {sel}: G={G:.0f} pi_max={pi_max} max_pi={pi.max():.4f}")

    rows = D.registry_rows()
    rows = [r for r in rows if (ROOT / r["local"]).is_file()]
    shapes_ok = []
    for r in rows:
        with rasterio.open(ROOT / r["local"]) as ds:
            if ds.shape == D.SHAPE:
                shapes_ok.append(r)
    index = registry_index(shapes_ok)
    n_fp = int(foot.sum())

    # ---- 2. pre-placement surface uniqueness --------------------------------------
    surf = np.where(foot, pi / pi.max(), 0).astype(np.float32)
    pre = U.compare_array_to_registry(surf, index, foot, include_reverse=False)
    pre_two = U.two_phase_summary(pre["rows"], n_fp)
    pre_rho = pre_two["literal_reading"]["worst_spearman_full_footprint"]
    log(f"pre-placement surface: worst rho={pre_rho:.3f} ({pre_two['literal_reading']['worst_spearman_submission']})")
    if pre_rho is not None and pre_rho > U.RHO_LIMIT:
        raise SystemExit("STOP: pre-placement surface duplicates a registry raster (rho > 0.90)")

    # ---- 3. design -----------------------------------------------------------------
    dots, hist = DS.place(pi, allowed, G=G, log=log)
    dots = DS.prune(pi, dots, G, log=log)
    terms = DS.expected_terms(pi, dots, G)
    st = COV.stats(dots.astype(np.float32), foot, cell, F.n_cells(), feats["d_cat_px"])
    ds_ = np.load(D.CACHE / "dataset.npz")
    n_px = ds_["n_px"]
    est_full = float(Mdl.predict(beta, M, st["C"][None], st["P"][None], np.array([st["N"]]), n_px, pi_max=pi_max)[0][0])
    log(f"design: dots={terms['N']} in-model E[DTI]={terms['dti']:.4f} (predict() check {est_full:.4f})")

    # ---- 4. cross-fit estimate + family bootstrap -----------------------------------
    cv = json.loads((ROOT / "evidence" / "lbcal_cv.json").read_text())
    meta = json.loads((D.CACHE / "dataset_meta.json").read_text())
    key = {(m["site"], m["submission"]): i for i, m in enumerate(meta)}
    obs = np.array([key[(r["site"], r["submission"])] for r in cv["observations"]])
    fam = np.array([r["family"] for r in cv["observations"]])
    s = np.array([r["owner_reported"] for r in cv["observations"]], float)
    C, P = ds_["C"][obs].astype(float), ds_["P"][obs].astype(float)
    N = np.array([meta[i]["N"] for i in obs])
    keep = n_px > 0
    Mk, Ck, Pk, nk = M[keep], C[:, keep], P[:, keep], n_px[keep]
    crossfit = []
    fam_ids = np.unique(fam)
    for seed in (1, 2):
        rng = np.random.default_rng(seed)
        half = set(rng.permutation(fam_ids)[: len(fam_ids) // 2].tolist())
        A = np.array([f in half for f in fam])
        fits = {}
        for nm, msk in (("A", A), ("B", ~A)):
            fits[nm] = Mdl.fit(Ck[msk], Pk[msk], N[msk], nk, s[msk], Mk, names, lam=lam, pi_max=pi_max)
        for d_nm, e_nm in (("A", "B"), ("B", "A")):
            pi_d, _ = pi_from_beta(fits[d_nm].beta, pi_max, M, cell, foot)
            dd, _ = DS.place(pi_d, allowed, G=float(pi_d.sum()), log=None)
            sd = COV.stats(dd.astype(np.float32), foot, cell, F.n_cells(), feats["d_cat_px"])
            e = float(Mdl.predict(fits[e_nm].beta, M, sd["C"][None], sd["P"][None], np.array([sd["N"]]), n_px,
                                  pi_max=pi_max)[0][0])
            self_e = float(Mdl.predict(fits[d_nm].beta, M, sd["C"][None], sd["P"][None], np.array([sd["N"]]),
                                       n_px, pi_max=pi_max)[0][0])
            crossfit.append(dict(seed=seed, design_half=d_nm, eval_half=e_nm, dots=int(dd.sum()),
                                 in_model=round(self_e, 4), cross_fit=round(e, 4)))
            log(f"cross-fit seed={seed} design={d_nm} eval={e_nm}: dots={int(dd.sum())} in-model={self_e:.4f} cross={e:.4f}")
    cross_mean = float(np.mean([c["cross_fit"] for c in crossfit]))
    boots = []
    rng = np.random.default_rng(20261027)
    for b in range(30):
        pick = rng.choice(fam_ids, size=fam_ids.size, replace=True)
        idx = np.concatenate([np.flatnonzero(fam == f) for f in pick])
        fb = Mdl.fit(Ck[idx], Pk[idx], N[idx], nk, s[idx], Mk, names, lam=lam, pi_max=pi_max, beta0=beta)
        boots.append(float(Mdl.predict(fb.beta, M, st["C"][None], st["P"][None], np.array([st["N"]]), n_px,
                                       pi_max=pi_max)[0][0]))
    boot_ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    champ = next(i for i, m in enumerate(meta) if m["submission"].startswith("h33-h33-2-b2-20261004T220000Z"))
    champ_est = float(Mdl.predict(beta, M, ds_["C"][champ][None].astype(float), ds_["P"][champ][None].astype(float),
                                  np.array([meta[champ]["N"]]), n_px, pi_max=pi_max)[0][0])
    log(f"cross-fit mean={cross_mean:.4f}; bootstrap 95% [{boot_ci[0]:.4f}, {boot_ci[1]:.4f}]; champion in-model={champ_est:.4f}")

    # ---- 5. holdout (fold-local replay) -----------------------------------------------
    ctx = H.load_holdout_context(ROOT / "data" / "raw")
    theta_star = terms["dti"]
    cells_dots = {}
    canary_rows = []
    feat_maps = {"topo_rank": feats["topo_rank"], "crest": feats["crest"].astype(np.float32),
                 "lidar_rank": np.nan_to_num(feats["lidar_rank"], nan=-1.0), "mag_rank": np.nan_to_num(feats["mag_rank"], nan=-1.0),
                 "d_sgmc_px": feats["d_sgmc_px"], "slope_rank": np.nan_to_num(feats["slope_rank"], nan=-1.0)}
    rng = np.random.default_rng(7)
    for c in ctx.cells:
        d_vis = ndi.distance_transform_edt(~c.visible_full).astype(np.float32)
        cid = recell_dcat(cell, d_vis, foot)
        pi_c = np.where(foot, pic[np.maximum(cid, 0)], 0).astype(np.float32)
        sl = c.bbox
        allowed_c = c.active_sub & foot[sl] & ~c.visible_full[sl]
        dd, _ = DS.place(pi_c[sl], allowed_c, theta_fixed=theta_star, G=G, log=None)
        cells_dots[c.key] = dd
        # leakage canary on this cell
        truth = np.zeros(allowed_c.shape, bool)
        truth[c.truth_coords] = True
        neg_idx = np.flatnonzero(allowed_c & ~truth)
        neg_idx = rng.choice(neg_idx, size=min(200_000, neg_idx.size), replace=False)
        pos_idx = np.flatnonzero(truth)
        row = dict(cell=c.key, n_truth=int(pos_idx.size), dots=int(dd.sum()))
        maps = dict(feat_maps, d_visible_px=d_vis, lbcal_pi=pi_c)
        for nm, mp in maps.items():
            sub = mp[sl].ravel()
            row[nm] = round(auc(sub[pos_idx], sub[neg_idx]), 4) if pos_idx.size else None
        canary_rows.append(row)
        log(f"holdout cell {c.key}: dots={int(dd.sum())} truth={pos_idx.size}")
    ev = H.evaluate_hide_and_recover(cells_dots, ctx, name="LBCAL-fold-local", n_boot=1000)
    hold = {k: v for k, v in ev.items() if not k.startswith("_")}
    hold.pop("folds", None)
    hold["folds"] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                     for k, v in ev["folds"].items()}
    log(f"HOLDOUT-DTI {hold['pooled_dti']:.4f} CI {hold['ci95_cluster_bootstrap']} vs best {HOLDOUT_BEST['pooled_dti']}")
    worst_auc = 0.0
    worst_feat = None
    for r in canary_rows:
        for nm, a in r.items():
            if nm in ("cell", "n_truth", "dots") or a is None:
                continue
            sep = max(a, 1 - a)
            if sep > worst_auc:
                worst_auc, worst_feat = sep, f"{nm}@{r['cell']}"
    canary = dict(rule="each feature alone vs withheld positives; max(AUC, 1-AUC) > 0.90 => leakage",
                  worst_separation=round(worst_auc, 4), worst_feature=worst_feat, leakage=bool(worst_auc > 0.90),
                  per_cell=canary_rows)

    # ---- 6. verdict (pre-registered) -------------------------------------------------
    beats_holdout = bool(hold["pooled_dti"] > HOLDOUT_BEST["pooled_dti"])
    beats_champion_est = bool(cross_mean > CHAMPION_OWNER_REPORTED)
    # ---- 7. write + validate + final uniqueness ----------------------------------------
    pred = np.where(dots, 1.0, 0.0).astype(np.float32)
    digest = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    promote_pending = beats_holdout and beats_champion_est and not canary["leakage"]
    suffix = "zeros" if promote_pending else "zeros-DO-NOT-SUBMIT"
    name = f"wbggems3-lbcal-{int(dots.sum())}d-{stamp}-{digest}-{suffix}"
    note = (f"LBCAL leaderboard-calibrated hidden-fault density; Dinkelbach dots; est {cross_mean:.3f} "
            f"holdout {hold['pooled_dti']:.3f}")[:140]
    tif = OUT_DIR / f"{name}.tif"
    receipt = write_submission(tif, pred, grid.sample_path, foot, note=note, name=name, catalogue=cat,
                               metadata=dict(lane="LBCAL", version=VERSION, model=sel))
    tv = template_validate(tif, foot, cat)
    with rasterio.open(tif) as src, rasterio.open(grid.sample_path) as smp:
        back = src.read(1)
        indep = dict(shape_match=src.shape == smp.shape, crs_match=src.crs == smp.crs,
                     transform_match=src.transform == smp.transform, count=src.count, dtype=src.dtypes[0])
    back_dots = np.isfinite(back) & (back > 0)
    indep.update(no_nan_in_footprint=bool(np.isfinite(back[foot]).all()),
                 in_0_1_in_footprint=bool(((back[foot] >= 0) & (back[foot] <= 1)).all()),
                 no_positive_outside_footprint=bool(not (back_dots & ~foot).any()),
                 zero_on_catalogue=bool(not (back_dots & cat).any()),
                 saved_dots_equal_design=bool(np.array_equal(back_dots, dots)))
    validator_ok = bool(tv["all_checks_passed"] and receipt["validator"]["all_checks_passed"]
                        and all(v for k, v in indep.items() if isinstance(v, bool)))
    final = U.compare_to_registry(tif, index, foot)
    final_two = U.two_phase_summary(final["rows"], n_fp)
    unique_like = not final_two["like_for_like_reading"]["duplicate"] and not (pre_rho is not None and pre_rho > U.RHO_LIMIT)
    verdict = "promote" if (validator_ok and unique_like and promote_pending) else "negative"
    failed = [nm for nm, ok in (("validator", validator_ok), ("uniqueness(like-for-like)", unique_like),
                                ("leakage canary", not canary["leakage"]),
                                (f"HOLDOUT-DTI > {HOLDOUT_BEST['pooled_dti']}", beats_holdout),
                                (f"cross-fit ESTIMATE > {CHAMPION_OWNER_REPORTED}", beats_champion_est)) if not ok]
    sha = D.sha256_file(tif)
    card = dict(
        schema="parallel-run card v1 (owner protocol rule 5)", lane="LBCAL", version=VERSION,
        session_branch="arena/88400903-wbggemsdoe3", utc=datetime.now(timezone.utc).isoformat(),
        hypothesis=("The public leaderboard scores of ~119 archived rasters are soft, spatially integrated "
                    "measurements of where the hidden expert-labelled faults are; a log-linear density over "
                    "7 binned geological layers, fitted through the exact DTI algebra, predicts held-out "
                    "families and can be optimised directly."),
        mechanism=("Hidden-fault density pi over joint bins of catalogue distance, det-elev curvature, slope "
                   "crest, det-elev slope, 3DEP-LiDAR scarp rank, TMI horizontal gradient and SGMC distance; "
                   "Dinkelbach batch-greedy max-coverage dots under pi; never on the catalogue."),
        non_fault_mimic=("Landslide head-scarps, terrace risers and road/canal cuts share the slope/curvature/"
                         "LiDAR-step signature; the density cannot separate them."),
        model=dict(selected=sel, pi_max=pi_max, lam=lam, implied_G=round(G, 1),
                   family_cv=vrec["family_cv"], unbounded_reference_cv=var["unbounded_reference"]),
        estimate=dict(label="ESTIMATE (model output; not a score)",
                      in_model=round(terms["dti"], 4), cross_fit_mean=round(cross_mean, 4), cross_fit=crossfit,
                      family_bootstrap_95=[round(v, 4) for v in boot_ci],
                      champion_b2_in_model=round(champ_est, 4), champion_b2_owner_reported=CHAMPION_OWNER_REPORTED),
        holdout=dict(label="HOLDOUT-DTI", evaluator=hold["evaluator_version"], pooled_dti=round(hold["pooled_dti"], 4),
                     ci95=[round(v, 4) for v in hold["ci95_cluster_bootstrap"]],
                     n_withheld=hold["n_withheld_positives"], n_spatial_clusters=hold["n_spatial_clusters"],
                     per_quadrant=hold["per_quadrant_dti"], current_best=HOLDOUT_BEST, beats_best=beats_holdout,
                     replay="fold-local: catalogue distance from visible faults only; visible faults masked pixel-exactly"),
        leakage_canary={k: v for k, v in canary.items() if k != "per_cell"},
        registry=dict(rasters_checked=final_two["rasters_checked"],
                      pre_placement_surface=dict(worst_rho=pre_rho,
                                                 worst_rho_submission=pre_two["literal_reading"]["worst_spearman_submission"]),
                      final_dots_literal=final_two["literal_reading"],
                      final_dots_like_for_like=final_two["like_for_like_reading"]),
        file=dict(path=str(tif.relative_to(ROOT)), sha256=sha, bytes=tif.stat().st_size, dots=int(dots.sum()),
                  zip=str(tif.with_suffix(".zip").relative_to(ROOT))),
        validator=dict(passed=validator_ok, template=tv["checks"], independent=indep),
        submission_name=name, note=note, note_chars=len(note),
        verdict=verdict, failed_gates=failed,
        ok_to_submit=False if verdict != "promote" else "selector-only (never self-selected; weekly cap applies)",
        design_history=hist[-5:],
    )
    (ROOT / "evidence" / "lbcal_run_card.json").write_text(json.dumps(card, indent=1, default=float) + "\n")
    (OUT_DIR / "holdout_detail.json").write_text(json.dumps(dict(holdout=hold, canary=canary), indent=1, default=float) + "\n")
    (OUT_DIR / "registry_scan_final.json").write_text(json.dumps(dict(two_phase=final_two, rows=final["rows"]), indent=1, default=float) + "\n")
    (OUT_DIR / "registry_scan_pre.json").write_text(json.dumps(dict(two_phase=pre_two, rows=pre["rows"]), indent=1, default=float) + "\n")
    log(f"VERDICT {verdict}; failed={failed}; file={tif.name} sha={sha[:12]} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
