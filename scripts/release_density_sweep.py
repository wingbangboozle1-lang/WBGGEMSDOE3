#!/usr/bin/env python3
"""Extend the density sweep and ablate the catalogue collar.

Reuses the cached per-fold score planes from ``scripts/release_experiments.py``
(no refit), so this is a selection-policy study, not a new experiment.

Caveat recorded with the results: in the *fold*, a dot placed on a visible
catalogue pixel is masked out by the official rule and therefore merely wastes
budget; in the *real* task a dot 1-3 px off the catalogue is an active cell with
no new-fault truth nearby and is pure false-positive mass. The fold ablation
therefore measures only the waste term and is a lower bound on the collar's value.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import emit, shared, truth  # noqa: E402

EVID = ROOT / "evidence" / "release"
SCORES = ROOT / "data" / "work" / "scores"
DENSITIES = (30000, 45000, 60000, 80000, 100000)
COLLARS = (0.0, 1.0, 2.0, 3.0, 5.0)


def main() -> int:
    footprint, catalogue = shared.load_masks()
    metric = shared.shared_metric()
    out = {"generated_by": "scripts/release_density_sweep.py",
           "densities": list(DENSITIES), "collars_px": list(COLLARS),
           "ablation_density": 30000, "separation_px": 2,
           "density_sweep": {}, "collar_ablation": {},
           "caveat": "fold-level collar ablation measures the waste term only; the "
                     "false-positive term that the collar removes does not exist in "
                     "the hide-and-recover fold because fold truth is defined to be "
                     ">5 px from every visible fault (verified masking rule)"}
    folds = {q: truth.fold_truth(q, catalogue) for q in truth.QUADRANTS}
    d_truth = {q: distance_transform_edt(~f["truth"]) for q, f in folds.items()}

    def run(arm, q, density, collar, sep=2):
        score = np.load(SCORES / f"{arm}_{q}.npy", mmap_mode="r")
        f = folds[q]
        allowed, _ = emit.allowed_mask(f["footprint"], f["visible"], collar_px=collar,
                                       valid=np.isfinite(np.asarray(score)))
        allowed &= f["region"]
        n_active = int((f["active"] & f["region"]).sum())
        k = int(round(density * n_active / 1_000_000))
        dots = emit.select_dots(np.asarray(score), allowed, k, nms_px=sep)
        ev = emit.evaluate(dots, f)
        ev["hit_rate_within_3px"] = float((d_truth[q][dots] <= 3.0).mean()) if dots.any() else 0.0
        ev["k_target"] = k
        ev["n_active_region"] = n_active
        ev["blocks"] = emit.block_terms(dots, f).tolist()
        return ev

    for arm in ("CAT", "UNION"):
        for density in DENSITIES:
            per = {q: run(arm, q, density, 3.0) for q in truth.QUADRANTS}
            tp = sum(v["tp"] for v in per.values()); fp = sum(v["fp"] for v in per.values())
            fn = sum(v["fn"] for v in per.values()); nt = sum(v["n_truth"] for v in per.values())
            ne = sum(v["n_emitted"] for v in per.values())
            blocks = np.concatenate([np.asarray(v["blocks"]) for v in per.values()])
            key = f"{arm}|{density}"
            out["density_sweep"][key] = dict(
                arm=arm, density=density,
                dti=float(metric.dti_from_components(tp, fp, fn)), tp=tp, fp=fp, fn=fn,
                n_truth=nt, n_emitted=ne, recall=float(tp / nt),
                n_over_g=float(ne / nt),
                hit_rate_within_3px=float(sum(v["hit_rate_within_3px"] * v["n_emitted"]
                                              for v in per.values()) / max(1, ne)),
                ci95=emit.bootstrap_ci(blocks),
                per_fold={q: per[q]["dti"] for q in per})
            print(f"[density] {key} dti={out['density_sweep'][key]['dti']:.4f} "
                  f"n={ne:,} h={out['density_sweep'][key]['hit_rate_within_3px']:.3f}", flush=True)

    for collar in COLLARS:
        per = {q: run("CAT", q, 30000, collar) for q in truth.QUADRANTS}
        tp = sum(v["tp"] for v in per.values()); fp = sum(v["fp"] for v in per.values())
        fn = sum(v["fn"] for v in per.values()); nt = sum(v["n_truth"] for v in per.values())
        ne = sum(v["n_emitted"] for v in per.values())
        out["collar_ablation"][f"{collar:g}"] = dict(
            collar_px=collar, dti=float(metric.dti_from_components(tp, fp, fn)),
            n_emitted=ne, recall=float(tp / nt),
            hit_rate_within_3px=float(sum(v["hit_rate_within_3px"] * v["n_emitted"]
                                          for v in per.values()) / max(1, ne)))
        print(f"[collar] {collar}: dti={out['collar_ablation'][f'{collar:g}']['dti']:.4f} "
              f"n={ne:,} h={out['collar_ablation'][f'{collar:g}']['hit_rate_within_3px']:.3f}",
              flush=True)

    (EVID / "density_sweep.json").write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
