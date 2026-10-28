#!/usr/bin/env python3
"""Session 2026-10-27 finalize: uniqueness repair of E3, shared-writer TIF,
saved-byte validation, final evaluation, analog-frontier estimate, run card.

Uses the pinned shared template writer (vendor/template24, unmodified) and the
pinned sample_submission.tif as template. No weekly slot is selected.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "template24" / "src"))
from gems.submission import write_submission, check_variants, zip_single  # noqa: E402
from session_experiments import (  # noqa: E402
    SESS, RAW, SQRT5, grid, load_fields, load_float, greedy_dots, lst_project,
    density_matched, comparator_subset)
from gemsdoe import validation as V  # noqa: E402
from gemsw import holdout as HO      # noqa: E402

TEMPLATE = ROOT / ".cache" / "data" / "sample_submission.tif"
LANE_DIR = ROOT / "docs" / "session-1f0b051d"
TARGET_W3 = 0.67
SPACING = 2.83
K = 40_000


def log(*a):
    print(*a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def within3_frac(dots_pts, other_pts):
    if len(other_pts) == 0 or len(dots_pts) == 0:
        return 0.0
    d, _ = cKDTree(other_pts).query(dots_pts, workers=2)
    return float((d <= 3.0).mean()), d


def main():
    raise RuntimeError("BLOCKED: superseded renderer or generator bypasses the literal registry gate; use scripts/build_site.py and see evidence/session_9b794637_run_card.json")
    t0 = time.time()
    foot, labels = grid()
    stack, names = load_fields()
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]])
    d_h = np.asarray(stack[ix["d_h19"]])
    S = np.load(SESS / "E2_surface.npy")
    dots = np.load(SESS / "E3_hybrid_dots.npy")
    dots_a = np.load(SESS / "E3_hybrid_dotsA.npy")
    champ = (load_float(ROOT / ".cache/focus/GEMSDOE32.tif") > 0) & foot
    skarp = (load_float(ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif") > 0) & foot
    d_ch = ndi.distance_transform_edt(~champ)
    d_sk = ndi.distance_transform_edt(~skarp)

    e3 = json.loads((SESS / "E3_hybrid_result.json").read_text())
    cov = {r["comparator"]: r for r in json.loads((SESS / "comparator_coverage.json").read_text())}
    comps = comparator_subset(full=True)
    comp_path = dict(comps)

    # ---- identify offenders (sparse class + within3 > TARGET) and refill avoid-union (>0.60)
    rows = {r["comparator"]: r for r in e3["uniqueness"]["rows"]}
    offenders, avoid_names = [], []
    for name, r in rows.items():
        if r["cand_within3"] is None:
            continue
        if cov[name]["coverage3px_footprint"] >= 0.90:
            continue
        if r["cand_within3"] > TARGET_W3:
            offenders.append(name)
        if r["cand_within3"] > 0.60:
            avoid_names.append(name)
    log(f"[repair] offenders(>{TARGET_W3}): {offenders}")
    log(f"[repair] refill avoid-union from: {avoid_names}")

    offender_pts = {}
    avoid_mask = np.zeros(foot.shape, bool)
    for name in set(offenders) | set(avoid_names):
        sup = (load_float(comp_path[name]) > 0) & foot
        oy, ox = np.nonzero(sup)
        offender_pts[name] = np.c_[oy, ox].astype(np.float64)
        avoid_mask |= ndi.distance_transform_edt(~sup) <= 3.0
    log(f"[repair] avoid-union covers {float(avoid_mask[foot].mean()):.3f} of footprint")

    pool_a_mask = dots_a.copy()  # provenance of surviving dots
    # --- joint repair v2: per-offender halo masks; drop lowest-score dots jointly;
    # refill with per-offender cap tracking (final fraction <= TARGET_W3 for every offender).
    halo_masks = {}
    for name in offenders:
        sup = (load_float(comp_path[name]) > 0) & foot
        halo_masks[name] = ndi.distance_transform_edt(~sup) <= 3.0
    history = []
    ys, xs = np.nonzero(dots)
    in_halo = {n: halo_masks[n][ys, xs] for n in offenders}
    frac0 = {n: float(in_halo[n].mean()) for n in offenders}
    history.append({"iteration": 0, "within3": frac0, "n_dots": int(dots.sum())})
    log(f"[repair v2] initial within3: {frac0}")
    scores = S[ys, xs]
    n_off = np.sum([in_halo[n] for n in offenders], axis=0)
    # candidate drops: dots in >=1 halo, ordered by (n_off desc, score asc) via lexsort on (score, -n_off)
    cand_idx = np.flatnonzero(n_off > 0)
    order = cand_idx[np.lexsort((scores[cand_idx], -n_off[cand_idx]))]
    keep = np.ones(len(ys), bool)
    counts = {n: int(in_halo[n].sum()) for n in offenders}
    cap = int(TARGET_W3 * K)
    for i in order:
        if all(counts[n] <= cap for n in offenders):
            break
        if any(in_halo[n][i] and counts[n] > cap for n in offenders):
            keep[i] = False
            for n in offenders:
                if in_halo[n][i]:
                    counts[n] -= 1
    dropped = ~keep
    n_drop_a = int(pool_a_mask[ys[dropped], xs[dropped]].sum())
    n_drop = int(dropped.sum())
    dots[ys[dropped], xs[dropped]] = False
    pool_a_mask[ys[dropped], xs[dropped]] = False
    history.append({"iteration": 1, "dropped": n_drop, "dropped_poolA": n_drop_a,
                    "counts_after_drop": counts, "cap_per_offender": cap})
    log(f"[repair v2] dropped {n_drop} (poolA {n_drop_a}); counts in halo now {counts} cap {cap}")

    def refill(pool_mask, k, counts):
        """Streaming score-ordered placement: spacing (vs existing + own) and per-offender caps."""
        if k <= 0:
            return np.zeros_like(dots), counts
        s_local = np.where(pool_mask, S, 0.0).astype(np.float32)
        mx = ndi.maximum_filter(s_local, size=3, mode="constant")
        cand = pool_mask & (s_local > 0) & (s_local >= mx) & ~dots
        cy, cx = np.nonzero(cand)
        order_c = np.argsort(-s_local[cy, cx], kind="stable")
        cy, cx = cy[order_c], cx[order_c]
        cell = SPACING
        gh = int(dots.shape[0] // cell) + 2; gw = int(dots.shape[1] // cell) + 2
        g = [[[] for _ in range(gw)] for _ in range(gh)]
        ey, ex = np.nonzero(dots)
        for y, x in zip(ey.tolist(), ex.tolist()):
            g[int(y // cell)][int(x // cell)].append((y, x))
        sp2 = SPACING * SPACING
        placed = np.zeros_like(dots)
        n_placed = 0
        for y, x in zip(cy.tolist(), cx.tolist()):
            if n_placed >= k:
                break
            if any(halo_masks[n][y, x] and counts[n] + 1 > cap for n in offenders):
                continue
            gy, gx = int(y // cell), int(x // cell)
            ok = True
            for jy in (gy - 1, gy, gy + 1):
                if jy < 0 or jy >= gh:
                    continue
                row = g[jy]
                for jx in (gx - 1, gx, gx + 1):
                    if jx < 0 or jx >= gw:
                        continue
                    for (py, px) in row[jx]:
                        if (y - py) ** 2 + (x - px) ** 2 < sp2:
                            ok = False; break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                continue
            placed[y, x] = True
            g[gy][gx].append((y, x))
            n_placed += 1
            for n in offenders:
                if halo_masks[n][y, x]:
                    counts[n] += 1
        log(f"[repair v2] refill placed {n_placed}/{k} (candidates {len(cy):,})")
        return placed, counts

    base_allowed = foot & ~labels & (d_cat >= SQRT5) & (S > 0)
    ra, counts = refill(base_allowed & (d_h <= 2.0), n_drop_a, counts)
    dots |= ra; pool_a_mask |= ra
    need = K - int(dots.sum())
    rb, counts = refill(base_allowed & (d_h > 2.0) & (d_ch > 3.0) & (d_sk > 3.0), need, counts)
    dots |= rb
    if int(dots.sum()) < K:  # relax pool boundary only (caps still enforced)
        rx, counts = refill(base_allowed, K - int(dots.sum()), counts)
        pool_a_mask |= rx & (d_h <= 2.0)
        dots |= rx
        log(f"[repair v2] relaxed refill brought total to {int(dots.sum())}")
    # drop-only enforcement so fractions hold on the FINAL N (cap was computed at K)
    for _round in range(3):
        ys2, xs2 = np.nonzero(dots)
        fr = {n: float(halo_masks[n][ys2, xs2].mean()) for n in offenders}
        bad = [n for n, f in fr.items() if f > TARGET_W3]
        if not bad:
            break
        sc = S[ys2, xs2]
        inb = {n: halo_masks[n][ys2, xs2] for n in bad}
        nbad = np.sum([inb[n] for n in bad], axis=0)
        cand_i = np.flatnonzero(nbad > 0)
        order_i = cand_i[np.lexsort((sc[cand_i], -nbad[cand_i]))]
        keep2 = np.ones(len(ys2), bool)
        cnt = {n: int(halo_masks[n][ys2, xs2].sum()) for n in offenders}
        N_now = len(ys2)
        for i in order_i:
            if all(cnt[n] <= TARGET_W3 * N_now for n in offenders):
                break
            if any(halo_masks[n][ys2[i], xs2[i]] and cnt[n] > TARGET_W3 * N_now for n in offenders):
                keep2[i] = False; N_now -= 1
                for n in offenders:
                    if halo_masks[n][ys2[i], xs2[i]]:
                        cnt[n] -= 1
        dots[ys2[~keep2], xs2[~keep2]] = False
        pool_a_mask[ys2[~keep2], xs2[~keep2]] = False
        log(f"[repair v2] drop-only round removed {int((~keep2).sum())}; N={int(dots.sum())}")
    ys2, xs2 = np.nonzero(dots)
    frac_final = {n: float(halo_masks[n][ys2, xs2].mean()) for n in offenders}
    history.append({"iteration": 2, "within3_after_refill": frac_final, "n_dots": int(dots.sum()),
                    "poolA_dots": int((pool_a_mask & dots).sum())})
    log(f"[repair v2] final within3 vs offenders: {frac_final}; dots={int(dots.sum())} poolA={int((pool_a_mask & dots).sum())}")

    np.save(SESS / "final_dots.npy", dots)
    np.save(SESS / "final_dots_poolA.npy", pool_a_mask & dots)

    # ---- write with the pinned shared writer (zeros outside), hash, name by hash
    assert np.isfinite(dots.astype(np.float32)[foot]).all()
    tmp = SESS / "candidate_tmp.tif"
    write_submission(dots.astype(np.float32), TEMPLATE, tmp, outside="zero")
    sha = sha256_file(tmp)
    name = f"wbg3-dipolehybrid-{int(dots.sum())}d-20261027-{sha[:8]}-zeros.tif"
    sub_path = ROOT / "submission" / name
    shutil.copyfile(tmp, sub_path)
    assert sha256_file(sub_path) == sha
    (LANE_DIR / "downloads").mkdir(parents=True, exist_ok=True)
    (LANE_DIR / "data").mkdir(parents=True, exist_ok=True)
    dl_path = LANE_DIR / "downloads" / name
    shutil.copyfile(sub_path, dl_path)
    zip_path = zip_single(dl_path)
    log(f"[write] {name} sha256={sha}")

    # ---- saved-byte validation: vendor checks + strict independent audit
    vendor = check_variants(sub_path, TEMPLATE)
    with rasterio.open(TEMPLATE) as t:
        t_prof, t_crs, t_tr, t_shape = t.profile, t.crs, t.transform, t.shape
    with rasterio.open(sub_path) as ds:
        a = ds.read(1)
        strict = {
            "single_band": ds.count == 1,
            "dtype_float32": ds.dtypes[0] == "float32",
            "shape_matches": ds.shape == t_shape,
            "crs_matches": str(ds.crs) == str(t_crs),
            "crs_epsg32611": ds.crs is not None and ds.crs.to_epsg() == 32611,
            "transform_matches": ds.transform == t_tr,
            "whole_array_finite": bool(np.isfinite(a).all()),
            "whole_array_in_0_1": bool(((a >= 0) & (a <= 1)).all()),
            "no_nan_inside_footprint": int(np.isnan(a[foot]).sum()) == 0,
            "outside_footprint_all_zero": bool((a[~foot] == 0).all()),
            "binary_values_only": sorted(float(x) for x in np.unique(a)) == [0.0, 1.0],
            "support_equals_intended_dots": bool((((a > 0) & foot) == dots).all()),
            "zero_on_catalogue": int((a[labels] > 0).sum()) == 0,
            "min_dcat_ge_sqrt5": float(d_cat[dots].min()) >= SQRT5 - 1e-9,
        }
        nodata = ds.nodata
    strict["nodata_is_none"] = nodata is None
    validator = {"vendor_check_variants": vendor, "strict_saved_byte_audit": strict,
                 "all_strict_pass": bool(all(strict.values())),
                 "vendor_format_valid": bool(vendor.get("format_valid"))}
    log(f"[validate] vendor format_valid={validator['vendor_format_valid']} strict_all_pass={validator['all_strict_pass']}")
    if not (validator["vendor_format_valid"] and validator["all_strict_pass"]):
        raise SystemExit(f"VALIDATION FAILED: {validator}")

    # ---- final evaluation on saved bytes
    saved = load_float(sub_path)
    from session_experiments import uniqueness as uniq_fn
    uniq = uniq_fn(saved > 0, comps)
    for r in uniq["rows"]:
        r["coverage3px_footprint"] = cov[r["comparator"]]["coverage3px_footprint"]
        r["class"] = "space-filling (R1 excluded, listed)" if r["coverage3px_footprint"] >= 0.90 else "sparse"
    sparse_rows = [r for r in uniq["rows"] if r["class"] == "sparse" and r["cand_within3"] is not None]
    uniq_summary = {
        "n_comparators": len(uniq["rows"]), "n_sparse": len(sparse_rows),
        "max_cand_within3_sparse": max(r["cand_within3"] for r in sparse_rows),
        "worst_sparse": max(sparse_rows, key=lambda r: r["cand_within3"])["comparator"],
        "max_jaccard_sparse": max(r["jaccard"] for r in sparse_rows),
        "max_abs_density_spearman": uniq["max_abs_density_spearman"],
        "space_filling_excluded": [r["comparator"] for r in uniq["rows"] if r["class"] != "sparse"],
        "rows": sorted(uniq["rows"], key=lambda r: -(r["cand_within3"] or 0)),
    }
    ctx = HO.load_holdout_context(RAW)
    hr = HO.evaluate_hide_and_recover(saved > 0, ctx, b_visible_px=SQRT5, name="final_saved")
    gt = V.sgmc_only_gt(foot)
    dm = density_matched({"final": saved, "champion_GEMSDOE32": load_float(ROOT / ".cache/focus/GEMSDOE32.tif"),
                          "GEMSDOE70_frontier": load_float(comp_path["GEMSDOE70::gems70-p5-dual-submod300-oof38k-20261020"])},
                         foot, gt)
    lst = lst_project(saved)

    # ---- archive-analog frontier estimate
    idx = json.load(open(ROOT / "data/ledger/index.json"))
    analogs = []
    for rec in idx:
        if rec["status"] != "verified":
            continue
        p = ROOT / rec["local"]
        key = f"{rec['site']}::{rec['submission']}"
        m = (load_float(p) > 0) & foot
        n = int(m.sum())
        if n < 1000:
            continue
        analogs.append({"site": rec["site"], "submission": rec["submission"],
                        "owner_reported": rec["score"], "dots": n,
                        "frac_gt3px_from_champion": float((d_ch[m] > 3).mean()),
                        "frac_dh_gt2": float((d_h[m] > 2).mean())})
    cand_frac_unique = float((d_ch[dots] > 3).mean())
    cand_frac_dh = float((d_h[dots] > 2).mean())
    near = [r for r in analogs if 30_000 <= r["dots"] <= 55_000
            and 0.35 <= r["frac_gt3px_from_champion"] <= 0.75
            and 0.30 <= r["frac_dh_gt2"] <= 0.70]
    near_scores = sorted(r["owner_reported"] for r in near)
    estimate = {
        "method": "archive-analog frontier: owner-reported scores of restored ledger files with similar "
                  "(mass, fraction >3px from champion, fraction off-network). NOT an organizer score.",
        "candidate_features": {"dots": int(dots.sum()), "frac_gt3px_from_champion": cand_frac_unique,
                               "frac_dh_gt2": cand_frac_dh},
        "analog_set_n": len(near),
        "analog_scores_owner_reported": near_scores,
        "analog_median": float(np.median(near_scores)) if near else None,
        "analog_mean": float(np.mean(near_scores)) if near else None,
        "analog_range": [near_scores[0], near_scores[-1]] if near else None,
        "analogs": sorted(near, key=lambda r: -r["owner_reported"]),
        "all_ledger_features": analogs,
    }
    log(f"[analog] n={len(near)} median={estimate['analog_median']} range={estimate['analog_range']}")

    canary = json.loads((SESS / "canary.json").read_text())
    lst_fit = json.loads((SESS / "lst_fit_session.json").read_text())
    note = ("WBG3 dipole-hybrid: lidar scarp-dipole x segment coherence, piedmont-gated; "
            "50% corridor + 50% novel; d2.83 dotted, B2 trim")
    assert len(note) <= 140, len(note)
    gates = {
        "G1_canary_le_0.90": bool(canary["all_pass"]),
        "G2_uniqueness_sparse_le_0.70": bool(uniq_summary["max_cand_within3_sparse"] <= 0.70),
        "G2b_density_spearman_le_0.90": bool((uniq_summary["max_abs_density_spearman"] or 0) <= 0.90),
        "G3_revised_frontier_allocation": bool(30_000 <= int(dots.sum()) <= 55_000
                                               and 0.35 <= cand_frac_unique <= 0.75),
        "G4_density_matched_proxy_ge_champion@12691": bool(
            dm["by_target"]["12691"]["final"]["mean"] >= dm["by_target"]["12691"]["champion_GEMSDOE32"]["mean"]),
        "G5_holdout_beats_strata_control": bool(e3["strata_control"]["paired_delta_ci95"][0] > 0),
        "G6_saved_byte_validator": bool(validator["vendor_format_valid"] and validator["all_strict_pass"]),
    }
    card = {
        "schema": "parallel-run card v1 (session 2026-10-27, branch arena/1f0b051d-wbggemsdoe3)",
        "lane": "H1 lidar scarp-dipole polarity + segment coherence, piedmont-gated, frontier-hybrid emission",
        "hypothesis": "Young normal-fault scarps missing from the Quaternary catalogue are signed lidar dipoles "
                      "(crest convexity lapneg + base concavity lappos + dominant face polarity) that are "
                      "strike-coherent over >500 m in low-relief piedmont settings; emitting them as "
                      "2.83 px-spaced dots half inside the corroborated H19-5 corridor and half on novel "
                      "off-network strands recovers faults the catalogue and the champion family missed.",
        "mechanism": "Dequantised USGS-3DEP 2 m lidar aggregate channels -> percentile-rank geomean dipole "
                     "(lapneg, lappos, max(upface,downface), step) x coh100 x (1-0.5 cross-dominance) -> "
                     "segment coherence (max directional mean, 4 orientations, +-4 px) -> piedmont setting "
                     "factor (relief/slope rank penalty) x TIGER road-distance factor x contour factor -> "
                     "greedy dotted placement (2.83 px inhibition), d_cat>=sqrt(5) px B2 trim, 40,000 dots "
                     "(pool A d_H19-5<=2 px; pool B off-network and >3 px from champion+skarpline); "
                     "uniqueness repair vs full registry; binary 1.0 emission, zeros outside footprint.",
        "named_non_fault_mimic": "Lahontan shoreline/terrace risers and road cut-and-fill benches "
                                 "(mitigated, not eliminated, by cross-dominance, road-distance and "
                                 "along-strike elevation-change factors).",
        "experiments_run": 3,
        "experiment_summaries": {
            "E1_dipole": {"holdout_dti": 0.0039, "lst_projection": 0.0592, "within3_vs_skarpline": 0.742,
                          "verdict": "failed G2/G3 (bedrock-dipole population; duplicate of skarpline lane)"},
            "E2_dipole_suppressed": {"holdout_dti": 0.0036, "lst_projection": 0.0367,
                                     "verdict": "unique vs subset but strata-empty; motivated frontier diagnostic"},
            "E3_hybrid": {"holdout_dti_pre_repair": e3["holdout"]["pooled_dti"], "lst_projection": e3["lst"]["projection"]},
        },
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": hr["evaluator_version"],
            "n_withheld_positives": hr["n_withheld_positives"],
            "final_saved_file_static_readback": {"pooled_dti": hr["pooled_dti"], "ci95": hr["ci95_cluster_bootstrap"],
                                                 "per_quadrant": hr["per_quadrant_dti"]},
            "fold_legal_E3_pre_repair": {"pooled_dti": e3["holdout"]["pooled_dti"], "ci95": e3["holdout"]["ci95"]},
            "strata_shuffled_control": e3["strata_control"],
            "reference_statics_from_audit": {"champion_GEMSDOE32": 0.0045, "skarpline_union": 0.0305,
                                             "d2.8_GEMSDOE25": 0.0967, "hce1_saved": 0.0931},
            "interpretation": "Hide-and-recover withholds catalogue segments; off-catalogue strategies are "
                              "anti-correlated with it (champion static 0.0045). Used here only with its "
                              "strata-shuffled control: micro-placement beats chance (paired delta CI > 0).",
        },
        "canary": {"label": canary["label"], "threshold": 0.90, "all_pass": canary["all_pass"],
                   "worst_non_catalogue_field": canary["worst_non_catalogue_field"],
                   "n_withheld_positives": canary["n_withheld_positives"]},
        "correlation_overlap_vs_registry": uniq_summary,
        "repair_history": history,
        "density_matched_proxy": dm,
        "ledger_projection": {**lst, "model": {k: lst_fit[k] for k in
                                               ("n_unique_rasters", "loo_mae", "loo_spearman", "family_cv_mae", "g_hat")},
                              "identification_caveat": "Refit lambda is ~0 off the H19-5 network, yet archived "
                                                       "files with ~50% off-network dots scored 0.219-0.2478; "
                                                       "lambda off-network is unidentified, so this projection "
                                                       "is a lower-bound-shaped diagnostic, not an estimate."},
        "analog_frontier_estimate": estimate,
        "gates": gates,
        "raster_sha256": sha,
        "validator_output": validator,
        "submission_name": name,
        "submission_note": note,
        "submission_note_chars": len(note),
        "download": {"tif": f"submission/{name}", "site_tif": f"docs/session-1f0b051d/downloads/{name}",
                     "site_zip": f"docs/session-1f0b051d/downloads/{Path(zip_path).name}"},
        "dots": int(dots.sum()), "poolA_corridor_dots": int((pool_a_mask & dots).sum()),
        "poolB_novel_dots": int((dots & ~pool_a_mask).sum()),
        "verdict": "negative",
        "verdict_reason": "The file is unique, format-valid and geology-driven, and sits inside the archive's "
                          ">=0.219 analog frontier (median analog 0.23), but no available instrument "
                          "demonstrates beating the champion's owner-reported 0.2778: ledger lambda is "
                          "unidentified off-network, the SGMC density-matched proxy ranks it below the "
                          "champion, and hide-and-recover is an anti-proxy for off-catalogue placement. "
                          "Beat-0.2778 hypothesis: NOT supported. Slot selection is a separate selector "
                          "step; if a slot is spent on a unique entry, this is the lane's candidate, "
                          "with final-round expert-review discovery value as the upside.",
        "organizer_confirmed_score": None,
        "slots_used": 0,
        "elapsed_s_this_phase": round(time.time() - t0, 1),
    }
    (ROOT / "evidence" / "session_1f0b051d_run_card.json").write_text(json.dumps(card, indent=1, default=float))
    (LANE_DIR / "data" / "run_card.json").write_text(json.dumps(card, indent=1, default=float))
    log(f"[card] verdict={card['verdict']} gates={gates}")
    log(f"[done] {sub_path} sha={sha}")


if __name__ == "__main__":
    main()
