#!/usr/bin/env python3
"""Build the LBCAL calibration dataset.

1. Compute the fixed geological feature bins (src/lbcal/features.py) and cache them.
2. For every registry raster (scored or not) compute the sufficient statistics of
   the official DTI over the joint feature cells (src/lbcal/coverage.py).
3. De-duplicate identical prediction arrays (same values on the footprint).

Outputs (ignored caches): .cache/lbcal/features.npz, .cache/lbcal/dataset.npz,
and the auditable row table evidence/lbcal_dataset_rows.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import data as D, features as F, coverage as COV  # noqa: E402


def main() -> int:
    t0 = time.time()
    D.CACHE.mkdir(parents=True, exist_ok=True)
    grid = D.load_grid()
    fpath = D.CACHE / "features.npz"
    if fpath.is_file():
        feats = dict(np.load(fpath))
    else:
        feats = F.compute(grid)
        np.savez_compressed(fpath, **feats)
    print(f"[features] ready in {time.time()-t0:.1f}s; cells={F.n_cells()}", flush=True)
    cell = feats["cell"]
    ncell = F.n_cells()
    n_px = np.bincount(cell[grid.foot], minlength=ncell).astype(np.float64)

    rows = D.registry_rows()
    C, P, meta = [], [], []
    seen: dict[str, int] = {}
    for i, r in enumerate(rows):
        path = ROOT / r["local"]
        p, info = D.read_prediction(path)
        if p.shape != D.SHAPE:
            print(f"[skip] {r['submission']}: shape {p.shape}")
            continue
        pf = np.where(grid.foot, np.clip(p, 0, 1), 0).astype(np.float32)
        key = hashlib.sha256(pf.tobytes()).hexdigest()
        st = COV.stats(p, grid.foot, cell, ncell, feats["d_cat_px"])
        m = dict(r, array_sha256=key, read=info, N=st["N"], n_pos=st["n_pos"], binary=st["binary"],
                 mean_pos_value=st["mean_pos_value"], frac_footprint_positive=st["frac_footprint_positive"],
                 mass_on_catalogue=st["mass_on_catalogue"], mass_within_2px=st["mass_within_2px"],
                 median_dcat_pos=st["median_dcat_pos"],
                 out_of_range=bool(info["min"] < 0 or info["max"] > 1),
                 positive_outside_footprint=int(((p > 0) & ~grid.foot).sum()))
        m["duplicate_of"] = seen.get(key)
        if key not in seen:
            seen[key] = len(meta)
        C.append(st["C"].astype(np.float32))
        P.append(st["P"].astype(np.float32))
        meta.append(m)
        if i % 10 == 0:
            print(f"[{i+1}/{len(rows)}] {time.time()-t0:.0f}s {r['submission'][:70]} N={st['N']:.0f}", flush=True)
    np.savez_compressed(D.CACHE / "dataset.npz", C=np.stack(C), P=np.stack(P), n_px=n_px)
    (D.CACHE / "dataset_meta.json").write_text(json.dumps(meta, indent=1))
    slim = [{k: v for k, v in m.items() if k not in ("read",)} for m in meta]
    (ROOT / "evidence" / "lbcal_dataset_rows.json").write_text(json.dumps(dict(
        evidence_class="Per-raster statistics computed from hash-pinned registry bytes; scores are OWNER-REPORTED",
        n_rows=len(slim), n_unique_arrays=len(seen), rows=slim), indent=1) + "\n")
    print(f"[done] rows={len(meta)} unique_arrays={len(seen)} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
