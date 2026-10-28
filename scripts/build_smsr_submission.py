#!/usr/bin/env python3
"""Build the SMSR (Seismogeodetic Missing-Shear Ridge) production submission.

Full-grid coverage comes from the SAME 4 spatially-blocked out-of-quadrant
(LOQO) models used for the validated holdout score (``evidence/smsr_cv_detached.json``):
each quadrant's field is produced by a model trained on the OTHER three
quadrants only (``~collar``), so no pixel's prediction was produced by a model
that saw that pixel's own quadrant's withheld truth during training. The
dot budget per quadrant equals that quadrant's own measured holdout
``n_truth`` (the already-validated hide-and-recover withheld count for the
*detached* instrument), so the emission scale is not a new, unvalidated guess.

Everything downstream of the composite probability field (serialization,
range/NaN/footprint/catalogue checks, ZIP packaging) is the unmodified shared
``gems57.submission_writer.write_submission`` / ``gems57.validate`` /
``gems57.gates`` -- the exact tool that fixed the earlier ``[0, 1]`` portal
rejection by construction (it raises before writing anything out of range).
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_project.template import ensure_template  # noqa: E402

TEMPLATE = ensure_template()
sys.path.insert(0, str(TEMPLATE / "src"))

import numpy as np  # noqa: E402
from gems57 import load_grid  # noqa: E402
from gems57 import submission_writer  # noqa: E402
from gems57.emit import greedy_allocate  # noqa: E402
from gems57.fitting import cell_geometry, fit_model, predict_surface  # noqa: E402
from gems57.holdout import FOLD_NAMES, build_holdout  # noqa: E402

from smsr.geo_ext import load_combined_planes  # noqa: E402

OUT_NAME = "smsr-seisgeod-missingshear-detached-20261028T000000Z"
SUB_DIR = ROOT / "submission"
EVID = ROOT / "evidence"


def main() -> int:
    t0 = time.time()
    grid = load_grid()
    ctx = build_holdout(grid, modes=("detached",))
    cells = [c for c in ctx.cells_of("detached") if c.key.startswith("draw20_")]
    assert len(cells) == 4, f"expected 4 draw20 detached folds, got {len(cells)}"
    planes = load_combined_planes(grid.footprint)
    print(f"[{time.time()-t0:5.1f}s] grid+holdout+planes ready, folds={[c.key for c in cells]}",
          flush=True)

    full = np.zeros(grid.shape, np.float32)
    receipts = []
    for qi, q in enumerate(FOLD_NAMES):
        test = [c for c in cells if c.key.split("_")[1] == f"fold{q}"][0]
        train = [c for c in cells if c.key.split("_")[1] != f"fold{q}"]
        geoms = [cell_geometry(ctx, c, geo=planes) for c in train]
        clf, scale, base = fit_model(geoms, seed=qi)
        geoms.clear()
        gc.collect()

        g = cell_geometry(ctx, test, geo=planes)
        p = predict_surface(clf, scale, g, grid.shape)
        allowed = np.zeros(grid.shape, bool)
        allowed[test.bbox] = test.active
        alloc = greedy_allocate(p, allowed, k_truth=float(test.n_truth),
                                floor=0.015, max_dots=120_000)
        full = np.where(alloc.emitted > 0, alloc.emitted, full)
        receipts.append(dict(fold=q, train_cells=[c.key for c in train],
                             test_cell=test.key, n_truth_budget=test.n_truth,
                             n_dots=alloc.n_dots,
                             expected_covered_credit=alloc.expected_covered_credit,
                             p_mean_in_domain=float(p[allowed].mean()) if allowed.any() else None,
                             p_max=float(p.max())))
        print(f"[{time.time()-t0:5.1f}s] fold {q}: n_truth_budget={test.n_truth} "
              f"n_dots={alloc.n_dots} p_max={p.max():.4f}", flush=True)
        del clf, g, p, allowed, alloc
        gc.collect()

    # Catalogue pixels and outside-footprint pixels must carry zero mass.
    full = np.where(grid.catalogue, 0.0, full).astype(np.float32)
    full = np.where(grid.footprint, full, 0.0).astype(np.float32)
    np.clip(full, 0.0, 1.0, out=full)

    n_dots_total = int((full > 0).sum())
    print(f"[{time.time()-t0:5.1f}s] stitched full grid: {n_dots_total} positive cells "
          f"({100.0*n_dots_total/grid.footprint.sum():.3f}% of footprint)", flush=True)

    SUB_DIR.mkdir(exist_ok=True)
    out_path = SUB_DIR / f"{OUT_NAME}.tif"
    sample_path = TEMPLATE / "data" / "bridge" / "sample_submission.tif"
    receipt = submission_writer.write_submission(
        out_path, full, sample_path, grid.footprint,
        name="SMSR seismogeodetic missing-shear ridge, detached-mode OOF",
        note="4-quadrant OOF HGB on geod_2ndinv structure-tensor ridge + seismicity vs shipped G1-G5",
        catalogue=grid.catalogue,
        metadata=dict(
            hypothesis="SMSR", evaluator_version="gems57-pooled-hide-v2",
            holdout_evidence="evidence/smsr_cv_detached.json",
            holdout_dti_detached_smsr_g=0.3213, holdout_dti_detached_shipped_g=0.3173,
            holdout_dti_ci95_quadrant_jackknife_smsr_g=[0.2789, 0.3637],
            fold_receipts=receipts, generated_utc=datetime.now(timezone.utc).isoformat(),
        ))
    print(f"[{time.time()-t0:5.1f}s] wrote {out_path} sha256={receipt['sha256']}", flush=True)

    EVID.mkdir(exist_ok=True)
    (EVID / "smsr_build_receipt.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(f"total {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
