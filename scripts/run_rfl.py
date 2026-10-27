#!/usr/bin/env python3
"""RFL lane driver (session arena/bd44f94b): E1 canary -> surface uniqueness ->
E2 holdout battery -> E3 conditional budget sweep -> final-dots uniqueness.

Preregistration: knowledge/preregistration-2026-10-27-rfl.md (frozen before results).
Shared tools reused unchanged: gemsw.holdout evaluator, gemsw.cspes.place_dots,
gemsw.grid.  Packaging happens in scripts/build_rfl_submission.py (vendor writer).

Outputs: evidence/rfl_canary.json, evidence/rfl_holdout.json,
         evidence/rfl_uniqueness.json, .cache/rfl/final_dots.npy (+ surface).
Stop rules (protocol): canary AUC>0.90 -> stop; surface/final |rho|>0.90 or
>70% dots within 3px of a sparse registry mask -> log duplicate, stop.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import cspes as C, grid as G, holdout as H, rfl as R  # noqa: E402

T0 = time.time()
RNG = np.random.default_rng(20261027)
EVID = ROOT / "evidence"
CACHE = ROOT / ".cache" / "rfl"
CACHE.mkdir(parents=True, exist_ok=True)
DISC3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


def paired_delta(ev_a, ev_b, n_boot=4000, seed=7):
    """Paired spatial-cluster bootstrap of pooled DTI(a)-DTI(b) (CSPES lane pattern)."""
    tpa, fpa, fna, act = ev_a["_block_totals"]
    tpb, fpb, fnb, _ = ev_b["_block_totals"]
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.choice(act, size=act.size, replace=True)
        ds[i] = f(tpa[idx], fpa[idx], fna[idx]) - f(tpb[idx], fpb[idx], fnb[idx])
    return {"delta": float(d0), "ci95": [float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
            "p_delta_le_0": float(np.mean(ds <= 0.0))}


def registry_masks():
    """(dots_sha, path_hint, dense, n_dots) for every unique mask in the rebuilt registry."""
    idx = json.loads((ROOT / "registry/cspes_registry_index.json").read_text())
    seen = {}
    for f in idx["files"]:
        seen.setdefault(f["dots_sha256"], f)
    return idx, seen


def unpack(dsha, shape):
    pk = np.load(ROOT / ".cache/registry" / f"{dsha}.npy")
    return np.unpackbits(pk)[: shape[0] * shape[1]].reshape(shape).astype(bool)


def uniqueness(cand_dots, cand_surface, foot, label):
    """No-exemption audit: every rebuilt registry mask gets overlap + null + rho.
    Verdicts are split: sparse-submission gate (operative stop rule) vs literal any-raster."""
    idx, seen = registry_masks()
    n = int(cand_dots.sum())
    fi = np.flatnonzero(foot.ravel())
    rng = np.random.default_rng(11)
    null = np.zeros(foot.size, bool)
    null[rng.choice(fi, n, replace=False)] = True
    null = null.reshape(foot.shape)
    sidx = rng.choice(fi, min(600_000, fi.size), replace=False)
    rs = rankdata(ndi.gaussian_filter(cand_surface.astype(np.float32), 1.5).ravel()[sidx])
    rows = []
    for dsha, f in seen.items():
        ref = unpack(dsha, foot.shape)
        near = ndi.binary_dilation(ref, structure=DISC3)
        obs = float((cand_dots & near).sum() / max(n, 1))
        nul = float((null & near).sum() / max(n, 1))
        rv = ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[sidx].astype(float)
        rho = float(np.corrcoef(rs, rankdata(rv))[0, 1]) if rv.std() > 0 else 0.0
        rows.append({"dots_sha256": dsha, "example_path": f.get("path"), "dense": bool(f.get("dense")),
                     "n_ref_dots": int(f.get("n_dots", int(ref.sum()))), "overlap_within3px": obs,
                     "null_overlap_same_count": nul, "excess_over_null": obs - nul,
                     "spearman_smoothed": rho})
    rows.sort(key=lambda r: -r["overlap_within3px"])
    sparse = [r for r in rows if not r["dense"]]
    dense = [r for r in rows if r["dense"]]
    lattice = [r for r in sparse if r["null_overlap_same_count"] >= 0.70]
    nonlat = [r for r in sparse if r["null_overlap_same_count"] < 0.70]
    out = {
        "label": label, "n_candidate_dots": n,
        "registry": {"n_files_indexed": idx["n_files_indexed"], "n_unique_masks": len(seen),
                     "n_sparse": len(sparse), "n_dense": len(dense),
                     "n_lattice_like_null_ge_0.70": len(lattice), "n_nonlattice": len(nonlat),
                     "coverage_note": idx.get("coverage_note")},
        "sparse_gate": {
            "definition": ("U2 |Spearman|<=0.90 all masks; U3 raw overlap<=0.70 vs non-lattice sparse; "
                           "U3 lattice-like (null>=0.70) excess<=0.05. Preregistration Amendment 1."),
            "max_overlap_within3px_sparse_raw": max((r["overlap_within3px"] for r in sparse), default=0.0),
            "max_overlap_within3px_nonlattice": max((r["overlap_within3px"] for r in nonlat), default=0.0),
            "max_excess_lattice_like": max((r["excess_over_null"] for r in lattice), default=0.0),
            "max_abs_spearman": max((abs(r["spearman_smoothed"]) for r in rows), default=0.0),
            "overlap_pass_le_0.70": all(r["overlap_within3px"] <= 0.70 for r in nonlat)
                                    and all(r["excess_over_null"] <= 0.05 for r in lattice),
            "rho_pass_le_0.90": all(abs(r["spearman_smoothed"]) <= 0.90 for r in rows),
            "worst_sparse": sparse[0] if sparse else None,
            "worst_nonlattice": max(nonlat, key=lambda r: r["overlap_within3px"]) if nonlat else None,
            "lattice_like_rows": lattice},
        "literal_any_raster": {
            "max_overlap_within3px": max((r["overlap_within3px"] for r in rows), default=0.0),
            "pass_le_0.70": all(r["overlap_within3px"] <= 0.70 for r in rows),
            "dense_witness_rows": dense,
            "note": "Vacuous: witness is positive on all footprint cells; champion B2 itself = 1.0 (E0 audit)."},
        "top10_by_overlap": rows[:10],
        "all_rows": [{k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()} for r in rows],
    }
    out["sparse_gate"]["pass"] = bool(out["sparse_gate"]["overlap_pass_le_0.70"] and out["sparse_gate"]["rho_pass_le_0.90"])
    return out


def main() -> int:
    g = G.load_grid(ROOT / "data/raw")
    log(f"grid ok footprint={int(g.foot.sum()):,} catalogue={int(g.labels.sum()):,}")
    with rasterio.open(ROOT / "data/raw/training_features.tif") as ds:
        assert ds.descriptions[11].split(" - ")[0] == "det_elev", ds.descriptions[11]
        elev_raw = G.clean_feature(ds.read(R.BAND_DET_ELEV))
    log("band 12 verified det_elev; building RFL surface ...")
    fields = R.build_surface(elev_raw, g.foot)
    np.save(CACHE / "surface.npy", fields.surface)
    ctx = H.load_holdout_context(ROOT / "data/raw")
    log("holdout context loaded")

    # ---------------- E1: leakage canary (protocol rule 4) ----------------
    def canary_samples(per_cell_neg=4_000):
        out = []
        for cell in ctx.cells:
            ys, xs = np.nonzero(cell.active_sub)
            pick = RNG.choice(ys.size, size=min(per_cell_neg, ys.size), replace=False)
            out.append((cell.bbox, cell.truth_coords[0], cell.truth_coords[1], ys[pick], xs[pick]))
        return out

    cells_idx = canary_samples()
    canary = {}
    for name in ("raw_det_elev", "relief_r2_500m", "relief_r5_1100m", "grad_relief_g2",
                 "grad_relief_g5", "rank_r5", "rfl_full"):
        arr = fields.components[name]
        y, s = [], []
        for sl, ty, tx, ny, nx in cells_idx:
            sub = arr[sl]
            y += [np.ones(ty.size, np.int8), np.zeros(ny.size, np.int8)]
            s += [sub[ty, tx], sub[ny, nx]]
        y, s = np.concatenate(y), np.concatenate(s)
        fin = np.isfinite(s)
        auc = float(roc_auc_score(y[fin], s[fin]))
        canary[name] = {"auc": auc, "n_pos": int(y.sum()), "n_neg": int((y == 0).sum()),
                        "leakage_alarm_gt_0.90": bool(auc > 0.90)}
        log(f"E1 canary {name:16s} AUC={auc:.4f}")
    json.dump({"experiment": "E1", "status": "STOP" if any(v["leakage_alarm_gt_0.90"] for v in canary.values()) else "pass",
               "canary": canary}, open(EVID / "rfl_canary.json", "w"), indent=1)
    if any(v["leakage_alarm_gt_0.90"] for v in canary.values()):
        log("STOP: leakage canary")
        return 2

    # ---------------- Surface uniqueness (before placement, protocol rule 1) ----
    # Probe dots = top-K surface cells without NMS (surface-level support check).
    K = R.DEFAULT_BUDGET
    elig = g.foot & ~g.labels & (fields.surface > 0)
    flat = np.flatnonzero(elig)
    topk = flat[np.argpartition(fields.surface.ravel()[flat], flat.size - K)[-K:]]
    probe = np.zeros(g.foot.shape, bool)
    probe.ravel()[topk] = True
    log("surface uniqueness vs rebuilt registry ...")
    u_surf = uniqueness(probe, fields.surface, g.foot, "surface_topK_probe_before_placement")
    # Amendment 1: surface-stage stop = rank-correlation gate; 70% dot gate on final dots.
    log(f"surface rho-pass={u_surf['sparse_gate']['rho_pass_le_0.90']} maxRho={u_surf['sparse_gate']['max_abs_spearman']:.3f} "
        f"probe maxOverlapNonLat={u_surf['sparse_gate']['max_overlap_within3px_nonlattice']:.3f} "
        f"literalMax={u_surf['literal_any_raster']['max_overlap_within3px']:.3f}")
    if not u_surf["sparse_gate"]["rho_pass_le_0.90"]:
        json.dump({"status": "STOP_DUPLICATE_SURFACE_RHO", "surface": u_surf}, open(EVID / "rfl_uniqueness.json", "w"), indent=1)
        log("STOP: surface rank-correlation >0.90 vs a registry raster (log duplicate)")
        return 3

    # ---------------- E2: holdout battery ----------------
    def evaluate(mask, name):
        ev = H.evaluate_hide_and_recover(mask, ctx, name=name, n_boot=1000)
        log(f"E2 {name:34s} HOLDOUT-DTI={ev['pooled_dti']:.4f} CI={[round(x, 4) for x in ev['ci95_cluster_bootstrap']]}")
        return ev

    results, dots_by, evs = {}, {}, {}
    for name in ("rfl_full", "abl_g500_only", "abl_g1100_only", "abl_piedmont_gate", "abl_slope_reference"):
        dots = C.place_dots(fields.components[name], g.foot, g.labels, budget=K)
        dots_by[name] = dots
        evs[name] = evaluate(dots, name)
    null_dots = np.zeros(g.foot.shape, bool)
    elig_flat = np.flatnonzero((g.foot & ~g.labels).ravel())
    null_dots.ravel()[RNG.choice(elig_flat, K, replace=False)] = True
    evs["random_null_k37654"] = evaluate(null_dots, "random_null_k37654")

    d28_path = ROOT / "data/raw/scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
    d28 = G.read_band(d28_path)
    d28_dots = np.isfinite(d28) & (d28 > 0) & g.foot
    champ_cells = {}
    for cell in ctx.cells:
        d_vis = ndi.distance_transform_edt(~cell.visible_full)
        champ_cells[cell.key] = d28_dots & (d_vis > 2.01) & ~cell.visible_full
    champ = H.evaluate_hide_and_recover(champ_cells, ctx, name="champion_proxy_d28_b2", n_boot=1000)
    evs["champion_proxy_d28_b2"] = champ
    log(f"E2 {'champion_proxy_d28_b2':34s} HOLDOUT-DTI={champ['pooled_dti']:.4f} CI={[round(x, 4) for x in champ['ci95_cluster_bootstrap']]}")

    # Existing saved files, static read-back (labelled, not fold-local).
    static = {}
    for name, p in [("skarpline_union_saved", ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
                    ("hce1_saved", ROOT / "docs/hce/downloads/wbggems3-hce1-latest.tif"),
                    ("cspes_saved", ROOT / "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif")]:
        a = G.read_band(p)
        m = np.isfinite(a) & (a > 0) & g.foot
        static[name] = evaluate(m, name)
    for name, ev in list(evs.items()) + list(static.items()):
        results[name] = {k: v for k, v in ev.items() if not k.startswith("_") and k != "folds"}
    paired_champ = paired_delta(evs["rfl_full"], champ)
    paired_null = paired_delta(evs["rfl_full"], evs["random_null_k37654"])
    log(f"E2 paired RFL-champion delta={paired_champ['delta']:+.4f} CI={[round(x, 4) for x in paired_champ['ci95']]}")
    log(f"E2 paired RFL-null     delta={paired_null['delta']:+.4f} CI={[round(x, 4) for x in paired_null['ci95']]}")

    # SGMC proxy for the primary surface + saved files (second, independent proxy population).
    sgmc = {}
    for name, m in [("rfl_full_k37654", dots_by["rfl_full"])] + \
                   [(k, np.isfinite(G.read_band(p)) & (G.read_band(p) > 0) & g.foot) for k, p in
                    [("skarpline_union_saved", ROOT / "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif"),
                     ("hce1_saved", ROOT / "docs/hce/downloads/wbggems3-hce1-latest.tif")]]:
        sg = H.evaluate_sgmc_with_ci(m, ctx, n_boot=1000, name=name)
        sgmc[name] = {k: v for k, v in sg.items() if not str(k).startswith("_")}
        log(f"E2 SGMC-proxy {name:26s} raw={sg.get('sgmc_raw_pooled_dti', sg.get('pooled_dti'))}")

    # ---------------- E3: conditional budget sweep ----------------
    final_name, final_dots, e3 = "rfl_full_k37654", dots_by["rfl_full"], {"run": False,
        "reason": "E2 paired CI vs champion does not reach >0" if paired_champ["ci95"][1] <= 0 else "run"}
    if paired_champ["ci95"][1] > 0:
        e3 = {"run": True, "budgets": {}}
        best = (evs["rfl_full"]["pooled_dti"], K, dots_by["rfl_full"])
        for k2 in (60_000, 97_608):
            d2 = C.place_dots(fields.surface, g.foot, g.labels, budget=k2)
            ev2 = evaluate(d2, f"rfl_full_k{k2}")
            e3["budgets"][str(k2)] = {kk: vv for kk, vv in ev2.items() if not kk.startswith("_") and kk != "folds"}
            if ev2["pooled_dti"] > best[0]:
                best = (ev2["pooled_dti"], k2, d2)
        final_name, final_dots = f"rfl_full_k{best[1]}", best[2]
        e3["selected_budget"] = best[1]
        log(f"E3 selected budget {best[1]} (DTI {best[0]:.4f})")
    np.save(CACHE / "final_dots.npy", np.packbits(final_dots.ravel()))
    (CACHE / "final_name.txt").write_text(final_name)

    json.dump({"experiment": "E2/E3", "lane": "RFL range-front relief-discontinuity",
               "evaluator_version": evs["rfl_full"]["evaluator_version"],
               "n_withheld_positives": evs["rfl_full"]["n_withheld_positives"],
               "budget_K_primary": K, "results": results,
               "paired_rfl_minus_champion": paired_champ, "paired_rfl_minus_null": paired_null,
               "sgmc_proxy": sgmc, "e3_budget_sweep": e3, "final_dots_name": final_name,
               "final_n_dots": int(final_dots.sum()), "elapsed_s": round(time.time() - T0, 1)},
              open(EVID / "rfl_holdout.json", "w"), indent=1)

    # ---------------- Final-dots uniqueness ----------------
    log("final-dots uniqueness vs rebuilt registry ...")
    u_final = uniqueness(final_dots, fields.surface, g.foot, f"final_dots_{final_name}")
    json.dump({"surface_before_placement": u_surf, "final_dots": u_final},
              open(EVID / "rfl_uniqueness.json", "w"), indent=1)
    log(f"final sparse-gate pass={u_final['sparse_gate']['pass']} "
        f"maxOverlapNonLat={u_final['sparse_gate']['max_overlap_within3px_nonlattice']:.3f} "
        f"maxExcessLattice={u_final['sparse_gate']['max_excess_lattice_like']:+.3f} maxRho={u_final['sparse_gate']['max_abs_spearman']:.3f}")
    if not u_final["sparse_gate"]["pass"]:
        log("STOP: final dots duplicate a sparse registry raster (log duplicate)")
        return 4
    log("RFL experiments complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
