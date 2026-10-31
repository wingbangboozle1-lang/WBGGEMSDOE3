#!/usr/bin/env python3
"""TWR-1 lane: tapered widened-recall emission around multi-sensor lineament crests.

Hypothesis (frozen before any truth-dependent choice this session)
------------------------------------------------------------------
The owner-reported 0.24-0.28 sibling family emits ~37-44k hard dots on 1-px-wide
ridge crests pruned >=1.5-2.8 px off the mapped catalogue. Under the official
metric a predicted pixel within 3 px of a truth pixel earns 0.8*k(d) credit while
its false-positive cost is only 0.2*p(x)*(1-k(d)): pixels 1-2 px off a true trace
are cheap insurance against the rasterization off-by-1 drift the organizer's own
problem page warns about. Widening the same *mechanism* (not any sibling's raster)
into a 1-3 px soft-valued halo on a fold-local multi-sensor crest energy should
recover truth pixels that 1-px dot emission structurally misses.

E1 leakage canary : each field alone, AUC on withheld truth vs sampled negatives
E2 holdout arms   : envelope vs matched core vs incumbent D2.8 replay, pooled DTI
                    on the shared GEMSDOE32-HIDE-RECOVER-v3.0 cells + paired
                    spatial-cluster bootstrap (envelope - core, envelope - champ)

Every number is labelled HOLDOUT-DTI on the shared instrument (evaluator version +
withheld-positive count). Nothing here is an ORGANIZER-CONFIRMED receipt.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G  # noqa: E402
from gemsw import holdout as H  # noqa: E402
from gemsw import features as F  # noqa: E402

T0 = time.time()
EVID = ROOT / "evidence"
WORK = ROOT / "data"
EVID.mkdir(exist_ok=True)

K_BUDGET = 37_654
CORE_NMS_PX = 2.0
BAND_IN_PX = 1.4
BAND_RAMP_PX = 2.4
HALO_PX = 3
HALO_Q = 0.75


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def rank_norm(field: np.ndarray, active: np.ndarray) -> np.ndarray:
    out = np.zeros(field.shape, np.float32)
    v = field[active]
    ok = np.isfinite(v)
    if ok.sum() < 100:
        return out
    edges = np.quantile(v[ok], np.linspace(0.01, 0.99, 99))
    finite = np.isfinite(field) & active
    r = (np.searchsorted(edges, field[finite], side="right").astype(np.float32) + 1.0) / 100.0
    out[finite] = r
    return out


def aniso_ridge(C: np.ndarray) -> np.ndarray:
    best = ndi.gaussian_filter(C, (1.2, 6.0))
    best = np.maximum(best, ndi.gaussian_filter(C, (6.0, 1.2)))
    for ang in (45.0, 135.0):
        rot = ndi.rotate(C, ang, order=1, reshape=False, mode="nearest")
        best = np.maximum(best, ndi.gaussian_filter(rot, (1.2, 6.0)))
    return best.astype(np.float32)


def band_window(d_cat: np.ndarray) -> np.ndarray:
    return np.clip((d_cat - BAND_IN_PX) / (BAND_RAMP_PX - BAND_IN_PX), 0.0, 1.0).astype(np.float32)


def place_core(C: np.ndarray, eligible: np.ndarray, budget: int = K_BUDGET,
               nms: float = CORE_NMS_PX) -> np.ndarray:
    """Greedy top-K with strict min-distance NMS; `eligible` already excludes catalogue."""
    Hh, Ww = C.shape
    flat = np.where(eligible, C, -np.inf).ravel()
    pool = min(1_500_000, int(eligible.sum()))
    idx = np.argpartition(flat, flat.size - pool)[flat.size - pool:]
    order = idx[np.argsort(-flat[idx], kind="stable")]
    r = int(np.ceil(nms))
    offs = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx < nms * nms + 1e-9]
    blocked = np.zeros(C.size, bool)
    dots = np.zeros(C.shape, bool)
    n = 0
    for f in order:
        if blocked[f]:
            continue
        y, x = divmod(int(f), Ww)
        dots[y, x] = True
        n += 1
        if n >= budget:
            break
        for dy, dx in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < Hh and 0 <= xx < Ww:
                blocked[yy * Ww + xx] = True
    return dots


def main() -> int:
    g = G.load_grid()
    log("grid loaded")
    ctx = H.load_holdout_context(ROOT / "data/raw")
    n_withheld = sum(c.n_truth for c in ctx.cells)
    log(f"holdout cells: {len(ctx.cells)}, withheld positives: {n_withheld}")

    # --- targeted band reads only (sandbox RAM cap ~3.9 GB): bands 2,4,6,12,13 ---
    import rasterio
    from gemsw.grid import clean_feature
    raw = ROOT / "data/raw/training_features.tif"
    fields = {}
    with rasterio.open(raw) as tf:
        def band(i):
            return clean_feature(tf.read(i))
        elev = band(12)
        fields["log_det_elev_s3"] = (-9.0 * ndi.gaussian_laplace(F._fill(elev, g.foot), 3.0)).astype(np.float32)
        fields["log_det_elev_s1.5"] = (-2.25 * ndi.gaussian_laplace(F._fill(elev, g.foot), 1.5)).astype(np.float32)
        fields["gradmag_det_elev_s1.5"] = ndi.gaussian_gradient_magnitude(F._fill(elev, g.foot), 1.5).astype(np.float32)
        del elev
        tc = band(6)
        fields["gradmag_tc_s2"] = ndi.gaussian_gradient_magnitude(F._fill(tc, g.foot), 2.0).astype(np.float32)
        del tc
        strain = band(4)
        fields["gradmag_geod_2ndinv_s4"] = ndi.gaussian_gradient_magnitude(F._fill(strain, g.foot), 4.0).astype(np.float32)
        del strain
        from scipy.stats import rankdata
        grav = F._fill(band(13), g.foot)
        mag = F._fill(band(2), g.foot)
        gg = ndi.gaussian_gradient_magnitude(grav, 3.0)
        gm = ndi.gaussian_gradient_magnitude(mag, 3.0)
        del grav, mag
        cg = np.sqrt(rankdata(gg[g.foot]) * rankdata(gm[g.foot])).astype(np.float32)
        cgf = np.full(g.foot.shape, np.nan, np.float32)
        cgf[g.foot] = cg
        fields["crossgrad_rank_grav_mag_s3"] = cgf
        del gg, gm, cg, cgf
    log("feature fields built (targeted)")
    active_static = g.foot & ~g.labels

    comps = {
        "crest_log3": rank_norm(fields["log_det_elev_s3"], active_static),
        "crest_log15": rank_norm(fields["log_det_elev_s1.5"], active_static),
        "gm_elev15": rank_norm(fields["gradmag_det_elev_s1.5"], active_static),
        "gm_tc": rank_norm(fields["gradmag_tc_s2"], active_static),
        "gm_strain": rank_norm(fields["gradmag_geod_2ndinv_s4"], active_static),
        "crossgrad": rank_norm(fields["crossgrad_rank_grav_mag_s3"], active_static),
    }
    Wt = {"crest_log3": 0.28, "crest_log15": 0.12, "gm_elev15": 0.22,
          "gm_tc": 0.15, "gm_strain": 0.13, "crossgrad": 0.10}
    C = np.zeros(g.foot.shape, np.float32)
    for k, w in Wt.items():
        C += w * comps[k]
    C = aniso_ridge(C)
    q75 = float(np.quantile(C[active_static], HALO_Q))
    log(f"fused anisotropic crest surface built; q75={q75:.4f}")
    for k in list(comps):
        del comps[k]

    # ------------------------------------------------------------- E1 canary
    canary_rows = {}
    for name, arr in (("gm_elev15", fields["gradmag_det_elev_s1.5"]),
                      ("gm_tc", fields["gradmag_tc_s2"]),
                      ("gm_strain", fields["gradmag_geod_2ndinv_s4"]),
                      ("crest_log3", fields["log_det_elev_s3"]),
                      ("crossgrad", fields["crossgrad_rank_grav_mag_s3"]),
                      ("fused_surface_fold_local", C)):
        s_pos, s_neg, y_pos_n = [], [], 0
        for i, cell in enumerate(ctx.cells):
            sl = cell.bbox
            ty, tx = cell.truth_coords
            s_pos.append(arr[sl][ty, tx])
            ey, ex = np.nonzero(cell.active_sub)
            rng = np.random.default_rng(1000 + i)
            pick = rng.choice(ey.size, size=min(6_000, ey.size), replace=False)
            s_neg.append(arr[sl][ey[pick], ex[pick]])
            y_pos_n += ty.size
        sp = np.concatenate(s_pos); sn = np.concatenate(s_neg)
        s_all = np.concatenate([sp, sn])
        y_true = np.concatenate([np.ones(sp.size, np.int8), np.zeros(sn.size, np.int8)])
        ok = np.isfinite(s_all)
        auc = float(roc_auc_score(y_true[ok], s_all[ok]))
        canary_rows[name] = {"auc": auc, "n_pos": int(sp.size), "n_neg": int(sn.size),
                             "alarm": bool(auc > 0.90)}
        log(f"canary {name:26s} AUC={auc:.4f}{'  LEAKAGE STOP' if auc > 0.90 else ''}")
    if any(r["alarm"] for r in canary_rows.values()):
        json.dump({"status": "STOP leakage canary", "canary": canary_rows},
                  open(EVID / "twr1_canary.json", "w"), indent=1)
        return 2
    json.dump({"status": "pass", "threshold": 0.90, "canary": canary_rows,
               "design": "single field alone; pooled over the 8 hide-and-recover cells; "
                         "6,000 sampled active-domain negatives per cell"},
              open(EVID / "twr1_canary.json", "w"), indent=1)

    del fields
    import gc; gc.collect()

    # ------------------------------------------------------------- E2 arms
    incumbent = None
    d28_path = next((ROOT / "data/ledger").glob("GEMSDOE25__*dotted-h19-5-d2-8*.tif"), None)
    if d28_path is not None:
        a = G.read_band(d28_path)
        incumbent = np.isfinite(a) & (a > 0) & g.foot
        log(f"incumbent D2.8 mirror dots: {int(incumbent.sum())}")

    arms = {"envelope": {}, "core_only": {}, "champion_d28_replay": {}}
    for cell in ctx.cells:
        vis = cell.visible_full
        d_vis = ndi.distance_transform_edt(~vis)
        w = band_window(d_vis)
        c_cell = C * w
        act_full = np.zeros(g.foot.shape, bool)
        act_full[cell.bbox] = cell.active_sub
        eligible = act_full & (c_cell > 0) & ~vis
        core = place_core(c_cell, eligible, budget=K_BUDGET, nms=CORE_NMS_PX)
        yy, xx = np.mgrid[-HALO_PX:HALO_PX + 1, -HALO_PX:HALO_PX + 1]
        disc = yy * yy + xx * xx <= HALO_PX * HALO_PX
        dil = ndi.binary_dilation(core, structure=disc)
        halo = dil & (C >= q75) & (w > 0) & ~core & act_full & ~vis
        arms["core_only"][cell.key] = core
        arms["envelope"][cell.key] = core | halo
        if incumbent is not None:
            arms["champion_d28_replay"][cell.key] = incumbent & (d_vis > 2.01) & ~vis & g.foot
        log(f"{cell.key:18s} core={int(core.sum()):6d} halo={int(halo.sum()):8d}")

    results, evs = {}, {}
    for arm, cellmap in arms.items():
        ev = H.evaluate_hide_and_recover(cellmap, ctx, name=f"twr1_{arm}", n_boot=1000)
        evs[arm] = ev
        results[arm] = {k: ev[k] for k in ("pooled_dti", "ci95_cluster_bootstrap",
                                           "n_withheld_positives", "evaluator_version", "score_label")}
        results[arm]["pooled_emitted"] = int(sum(int(v.sum()) for v in cellmap.values()))
        log(f"arm {arm:22s} pooled_dti={ev['pooled_dti']:.5f} "
            f"CI={[round(x,5) for x in ev['ci95_cluster_bootstrap']]}")

    def paired(ev_a, ev_b, n_boot=4000, seed=7):
        tpa, fpa, fna, act = ev_a
        tpb, fpb, fnb, _ = ev_b
        rng = np.random.default_rng(seed)
        f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
        d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
        ds = np.empty(n_boot)
        for i in range(n_boot):
            idx = rng.choice(act, size=act.size, replace=True)
            ds[i] = f(tpa[idx], fpa[idx], fna[idx]) - f(tpb[idx], fpb[idx], fnb[idx])
        return {"delta": float(d0),
                "ci95": [float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
                "p_delta_le_0": float(np.mean(ds <= 0.0))}

    paired_env_core = paired(evs["envelope"]["_block_totals"], evs["core_only"]["_block_totals"])
    log(f"PAIRED envelope-core delta={paired_env_core['delta']:+.5f} "
        f"CI={[round(x,5) for x in paired_env_core['ci95']]} P(<=0)={paired_env_core['p_delta_le_0']:.4f}")
    paired_env_champ = None
    if incumbent is not None:
        paired_env_champ = paired(evs["envelope"]["_block_totals"], evs["champion_d28_replay"]["_block_totals"])
        log(f"PAIRED envelope-champion delta={paired_env_champ['delta']:+.5f} "
            f"CI={[round(x,5) for x in paired_env_champ['ci95']]} P(<=0)={paired_env_champ['p_delta_le_0']:.4f}")

    out = {
        "lane": "TWR-1 tapered widened recall (multi-sensor anisotropic crest envelope)",
        "hypothesis": "soft 1-3 px crest-halo widening of a fold-local multi-sensor ridge core "
                      "beats hard-dot emission under alpha=0.2/beta=0.8",
        "score_label": "HOLDOUT-DTI",
        "evaluator_version": results["envelope"]["evaluator_version"],
        "cells": [c.key for c in ctx.cells],
        "n_withheld_positives": n_withheld,
        "frozen_params": {"K": K_BUDGET, "core_nms_px": CORE_NMS_PX, "band_in_px": BAND_IN_PX,
                          "band_ramp_px": BAND_RAMP_PX, "halo_px": HALO_PX, "halo_q": HALO_Q,
                          "q75": q75, "weights": Wt},
        "results": results,
        "paired_envelope_minus_core": paired_env_core,
        "paired_envelope_minus_champion": paired_env_champ,
        "canary_file": "evidence/twr1_canary.json",
        "elapsed_s": round(time.time() - T0, 1),
    }
    json.dump(out, open(EVID / "twr1_holdout.json", "w"), indent=1)
    fold_payload = {cell.key: np.packbits(arms["envelope"][cell.key].ravel()) for cell in ctx.cells}
    np.savez_compressed(WORK / "work_twr1_folds.npz", **fold_payload)
    np.save(WORK / "work_twr1_C.npy", C)
    np.save(WORK / "work_twr1_q75.npy", np.array([q75], np.float32))
    log("wrote evidence/twr1_holdout.json + work arrays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
