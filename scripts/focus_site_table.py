#!/usr/bin/env python3
"""Nine-site table, measured from the bytes (dot counts) + arithmetic (implied coverage)."""
from __future__ import annotations
import glob, json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT/"evidence"/"pair_identification.json").read_text())["identification"]["hidden_truth_cells_M"]
focus = json.loads((ROOT/"registry"/"focus_sites.json").read_text())["sites"]
rows = []
for f in focus:
    base = Path(f["path"]).name
    hits = sorted(glob.glob(f"/tmp/{f['site']}/**/{base}", recursive=True))
    if not hits:
        continue
    with rasterio.open(hits[0]) as ds:
        a = ds.read(1).astype(np.float64)
    a = np.where(np.isfinite(a), np.clip(a, 0, 1), 0.0)
    n = int((a > 0).sum()); s = float(f["owner_reported"])
    T = s * (0.2*n + 0.8*M)
    rows.append({"site": f["site"], "file": base, "path": f["path"], "ref": f["ref"],
                 "owner_reported": s, "n_dots": n, "implied_T": T, "yield_per_dot": T/n,
                 "github_url": f"https://github.com/buffedlizard55-lab/{f['site']}/blob/{f['ref']}/{f['path']}"})
ns = np.array([r["n_dots"] for r in rows]); ss = np.array([r["owner_reported"] for r in rows])
out = {"evidence_class": "MEASURED dot counts + OWNER-REPORTED scores + model-implied coverage",
       "M": M, "rows": rows,
       "spearman_nDots_vs_score": float(spearmanr(ns, ss).statistic),
       "note": "implied_T = score*(0.2*n_dots + 0.8*M); a constant implied_T across files is the model's self-consistency check"}
(ROOT/"evidence"/"focus_site_table.json").write_text(json.dumps(out, indent=1))
print(f"spearman(dots, score) = {out['spearman_nDots_vs_score']:+.3f}")
for r in rows: print(f"  {r['site']:10s} {r['n_dots']:6d} {r['owner_reported']:.4f} T={r['implied_T']:6.0f} y={r['yield_per_dot']:.3f}")
