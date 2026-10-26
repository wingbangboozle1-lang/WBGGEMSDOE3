#!/usr/bin/env python3
"""Design rows (A, B, N) for every unique registry raster so each can be PROJECTED with the LST model.
Binary files are reconstructed from the packed dot-mask cache; non-binary files are read from the TIF."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw.grid import load_grid, read_band
from gemsw import ledger as L, features as F, uniq

g = load_grid()
active = g.foot & ~g.labels
bz = np.load(ROOT / "data/work/bins.npz")
sel = active[g.foot]              # bins.npz is footprint-ordered
bins = {k: bz[k][sel] for k in bz.files}
reg = json.load(open(ROOT / "registry/registry_index.json"))["files"]
seen, rows, meta = set(), [], []
t0 = time.time()
for e in reg:
    if e["status"] != "ok" or e["n_dots"] == 0:
        continue
    key = e["dots_sha256"] if e["binary"] else e["sha256"]
    if key in seen:
        continue
    seen.add(key)
    if e["binary"]:
        p = uniq.unpack(np.load(ROOT / ".cache/registry" / f"{e['dots_sha256']}.npy"), g.foot.shape).astype(np.float32)
    else:
        p = read_band(ROOT / e["path"]).astype(np.float32)
        p = np.clip(np.where(np.isfinite(p), p, 0.0), 0.0, 1.0)
    p[~active] = 0.0
    row = L.design_row(p, active, bins, 64)
    rows.append(row); meta.append(dict(key=key, path=e["path"], site=e["site"], binary=e["binary"], n_dots=row["dots"], N=row["N"]))
    if len(rows) % 20 == 0:
        print(len(rows), f"{time.time()-t0:.0f}s", flush=True)
np.savez_compressed(ROOT / "data/work/design_registry.npz", A=np.stack([r["A"] for r in rows]), B=np.stack([r["B"] for r in rows]),
                    N=np.array([r["N"] for r in rows]))
json.dump(meta, open(ROOT / "data/work/design_registry_meta.json", "w"))
print("done", len(rows), f"{time.time()-t0:.0f}s")
