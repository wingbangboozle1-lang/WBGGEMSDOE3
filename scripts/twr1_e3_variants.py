#!/usr/bin/env python3
"""TWR-1 E3: frozen variants, dual-channel selection (hide-recover + off-catalogue SGMC).

Config selection rule (frozen here before computing): among the four variants,
the FINAL candidate is the one with the higher mean of (a) pooled HOLDOUT-DTI on
the shared instrument and (b) raw DTI against SGMC off-catalogue faults (independent
external map, GEMSDOE24-pinned mirror). No variant is chosen by the holdout alone;
ties go to the lower-K (cheaper FP mass). All numbers are HOLDOUT-DTI /
SGMC-DTI, never organizer receipts.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G  # noqa: E402
from gemsw import holdout as H  # noqa: E402
from gemsw.metric import kernel  # noqa: E402

T0 = time.time()
EVID = ROOT / "evidence"
K = 37_654
BAND_IN_PX, BAND_RAMP_PX, HALO_PX, HALO_Q = 1.4, 2.4, 3, 0.75


def log(m): print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)


def rank_norm(field, active):
    out = np.zeros(field.shape, np.float32)
    v = field[active]; ok = np.isfinite(v)
    if ok.sum() < 100: return out
    edges = np.quantile(v[ok], np.linspace(0.01, 0.99, 99))
    finite = np.isfinite(field) & active
    out[finite] = (np.searchsorted(edges, field[finite], side="right").astype(np.float32) + 1) / 100.0
    return out


def place(Cf, eligible, budget=K, nms=2.0):
    Hh, Ww = Cf.shape
    flat = np.where(eligible, Cf, -np.inf).ravel()
    pool = min(1_500_000, int(eligible.sum()))
    idx = np.argpartition(flat, flat.size - pool)[flat.size - pool:]
    order = idx[np.argsort(-flat[idx], kind="stable")]
    r = int(np.ceil(nms))
    offs = [(dy, dx) for dy in range(-r, r+1) for dx in range(-r, r+1) if dy*dy+dx*dx < nms*nms+1e-9]
    blocked = np.zeros(Cf.size, bool)
    dots = np.zeros(Cf.shape, bool); n = 0
    for f in order:
        if blocked[f]: continue
        y, x = divmod(int(f), Ww)
        dots[y, x] = True; n += 1
        if n >= budget: break
        for dy, dx in offs:
            yy, xx = y+dy, x+dx
            if 0 <= yy < Hh and 0 <= xx < Ww:
                blocked[yy*Ww+xx] = True
    return dots


def window(d): return np.clip((d-BAND_IN_PX)/(BAND_RAMP_PX-BAND_IN_PX), 0.0, 1.0).astype(np.float32)


def main() -> int:
    g = G.load_grid()
    ctx = H.load_holdout_context(ROOT / "data/raw")
    C = np.load(ROOT / "data/work_twr1_C.npy")
    q75 = float(np.load(ROOT / "data/work_twr1_q75.npy")[0])
    raw = ROOT / "data/raw"
    with rasterio.open(raw / "training_features.tif") as tf:
        elev = G.clean_feature(tf.read(12))
    from gemsw.features import _fill
    log_det3 = (-9.0 * ndi.gaussian_laplace(_fill(elev, g.foot), 3.0)).astype(np.float32)
    gm_elev = ndi.gaussian_gradient_magnitude(_fill(elev, g.foot), 1.5).astype(np.float32)
    del elev
    active = g.foot & ~g.labels
    T = 0.55 * rank_norm(log_det3, active) + 0.45 * rank_norm(gm_elev, active)
    del log_det3, gm_elev
    sgmc = np.zeros(g.foot.shape, bool)
    with rasterio.open(ROOT / "data/raw/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & g.foot & ~g.labels
    yy, xx = np.mgrid[-HALO_PX:HALO_PX+1, -HALO_PX:HALO_PX+1]
    disc = yy*yy + xx*xx <= HALO_PX*HALO_PX

    variants = {
        "V1_multi_C_core":      lambda Surf, elig: (place(Surf, elig), np.zeros(g.foot.shape, bool)),
        "V2_topo_T_core":       lambda Surf, elig: (place(Surf, elig), np.zeros(g.foot.shape, bool)),
        "V3_topo_T_halo3":      None,  # handled below (core on T, halo on C>=q75)
        "V4_topo_T_nms3":       lambda Surf, elig: (place(Surf, elig, nms=3.0), np.zeros(g.foot.shape, bool)),
    }
    surfaces = {"V1_multi_C_core": C, "V2_topo_T_core": T, "V3_topo_T_halo3": T,
                "V4_topo_T_nms3": T}

    env_res, sgmc_res = {}, {}
    for cell in ctx.cells:
        vis = cell.visible_full
        w = window(ndi.distance_transform_edt(~vis))
        act_full = np.zeros(g.foot.shape, bool); act_full[cell.bbox] = cell.active_sub
        for name, Surf in surfaces.items():
            c_cell = Surf * w
            elig = act_full & ~vis & (c_cell > 0)
            if name == "V3_topo_T_halo3":
                core = place(c_cell, elig)
                halo = ndi.binary_dilation(core, structure=disc) & (C >= q75) & (w > 0) & ~core & act_full & ~vis
                dots = core | halo
            else:
                dots = variants[name](c_cell, elig)[0]
            env_res.setdefault(name, {})[cell.key] = dots
    for name in surfaces:
        ev = H.evaluate_hide_and_recover(env_res[name], ctx, name=name, n_boot=1000)
        # SGMC raw DTI on FULL catalogue surface (independent selection channel)
        d_cat = ndi.distance_transform_edt(~g.labels)
        wf = window(d_cat)
        cf = surfaces[name] * wf
        elig_f = active & (cf > 0)
        if name == "V3_topo_T_halo3":
            core_f = place(cf, elig_f)
            halo_f = ndi.binary_dilation(core_f, structure=disc) & (C >= q75) & (wf > 0) & ~core_f & active
            emit_f = core_f | halo_f
        else:
            emit_f = variants[name](cf, elig_f)[0]
        d_true = ndi.distance_transform_edt(emit_f)   # distance from every cell to nearest dot
        cred = kernel(d_true[sgmc])                    # per-truth best credit (approx via min-dist)
        tp = float(cred.sum())
        d_dots = ndi.distance_transform_edt(~sgmc)     # distance from every cell to nearest truth
        M = float(kernel(d_dots[emit_f]).sum())        # dot-side cover mass
        fp_mass = max(int(emit_f.sum()) - M, 0.0)
        del d_true, d_dots
        dti_sgmc = tp / (tp + 0.2 * fp_mass + 0.8 * float(sgmc.sum() - tp) + 1e-12)
        sgmc_res[name] = {"n_dots": int(emit_f.sum()), "sgmc_raw_dti": dti_sgmc,
                          "sgmc_coverage": tp / float(sgmc.sum())}
        log(f"{name:18s} holdout={ev['pooled_dti']:.5f} CI={[round(x,5) for x in ev['ci95_cluster_bootstrap']]} "
            f"sgmc={dti_sgmc:.5f} cov={tp/float(sgmc.sum()):.3f} dots={int(emit_f.sum())}")
        ev_out = {k: ev[k] for k in ("pooled_dti", "ci95_cluster_bootstrap", "n_withheld_positives",
                                     "evaluator_version", "score_label")}
        env_res[name] = ev_out

    score = {n: 0.5 * (env_res[n]["pooled_dti"] / 0.10) + 0.5 * (sgmc_res[n]["sgmc_raw_dti"] / 0.30)
             for n in surfaces}
    best = max(score, key=score.get)
    log(f"combined selection: { {k: round(v,3) for k,v in score.items()} }  best={best}")
    json.dump({"evidence_class": "HOLDOUT-DTI + SGMC-DTI (config selection channel)",
               "evaluator_version": "GEMSDOE32-HIDE-RECOVER-v3.0",
               "n_withheld_positives": sum(c.n_truth for c in ctx.cells),
               "variants_holdout": env_res, "variants_sgmc": sgmc_res,
               "selection": {"rule": "mean of scaled holdout DTI and scaled SGMC off-catalogue raw DTI, frozen before compute",
                             "combined": score, "selected": best},
               "elapsed_s": round(time.time()-T0, 1)},
              open(EVID / "twr1_e3_variants.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
