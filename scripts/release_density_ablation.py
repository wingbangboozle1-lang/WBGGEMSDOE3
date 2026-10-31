#!/usr/bin/env python3
"""Is the axis-B advantage density or quality? Ablate our own candidate's budget."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import shared, truth  # noqa: E402

EVID = ROOT / "evidence" / "release"


def main() -> int:
    import rasterio
    from scipy.ndimage import distance_transform_edt

    footprint, catalogue = shared.load_masks()
    metric = shared.shared_metric()
    truth_b = truth.sgmc_offcatalogue(catalogue)["mask"] & footprint
    d_truth = distance_transform_edt(~truth_b)
    card = json.loads((EVID / "candidate_run_card.json").read_text())
    with rasterio.open(ROOT / card["submission"]["path"]) as src:
        arr = src.read(1)
    ok = footprint & np.isfinite(arr) & (arr > 0) & ~catalogue
    flat = np.where(ok, arr, -np.inf).ravel()
    order = np.argsort(-flat)
    rows = []
    for k in (20000, 40000, 60000, 80000, 100000, 120000, 140000):
        dots = np.zeros(arr.size, bool)
        dots[order[:k]] = True
        dots = dots.reshape(arr.shape)
        ev = metric.dti_binary(dots, truth_b, valid=footprint, known=catalogue)
        n = int(dots.sum())
        rows.append(dict(n=n, dti_vs_offcatalogue=ev["dti"],
                         recall=float(ev["tp"] / max(1, ev["n_truth"])),
                         hit_rate_within_3px=float((d_truth[dots] <= 3.0).mean())))
        print(f"n={n:7,d} DTI_B={ev['dti']:.4f} recall={rows[-1]['recall']:.3f} "
              f"h={rows[-1]['hit_rate_within_3px']:.3f}", flush=True)
    (EVID / "density_ablation.json").write_text(json.dumps({
        "generated_by": "scripts/release_density_ablation.py",
        "question": "does the axis-B advantage come from emitting more dots or from "
                    "better-placed dots?",
        "answer_rule": "if DTI_B at 40k is close to the siblings' 0.093-0.102, the "
                       "advantage is density; if it is clearly higher, it is quality",
        "truth_b_cells": int(truth_b.sum()), "rows": rows}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
