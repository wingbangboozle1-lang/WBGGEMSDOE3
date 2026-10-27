#!/usr/bin/env python3
"""Audit a finished submission GeoTIFF against every verified sibling raster (PR-01).

Independent of the emission code path: it reads the SAVED FILE, decodes its positive support and
runs the two-sided correlation test plus the 3-px forward-overlap test.  Use it as the last gate
before a portal upload.

Usage: python scripts/audit_uniqueness.py submission/<file>.tif [--out evidence/uniqueness.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("ec", ROOT / "scripts/emit_candidate.py")
ec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec)
from gemsw import grid as G  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--out", default=str(ROOT / "evidence/uniqueness.json"))
    a = ap.parse_args()
    g = G.load_grid()
    with rasterio.open(a.tif) as ds:
        arr = ds.read(1)
        meta = {"crs": str(ds.crs), "shape": [ds.height, ds.width], "count": ds.count,
                "dtype": ds.dtypes[0], "transform_matches_template":
                    bool(ds.transform == g.profile["transform"])}
    dots = np.isfinite(arr) & g.foot & (arr > 0.5)
    rows = [r for r in json.loads((ROOT / "data/ledger/index.json").read_text())
            if r.get("status") == "verified"]
    res = ec.registry_overlap(dots, g, rows)
    out = {"file": str(Path(a.tif).name), "sha256": ec.sha256(Path(a.tif)),
           "n_dots": int(dots.sum()), "raster_meta": meta,
           "all_finite": bool(np.isfinite(arr).all()),
           "in_range": bool(arr.min() >= 0 and arr.max() <= 1),
           "uniqueness": res}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"dots={out['n_dots']} max|phi|={res['max_abs_spearman']:.4f} "
          f"informative={res['n_informative_probes']}/{res['n_probes']} "
          f"worst_overlap={res['max_my_dots_within_3px_informative']:.4f} "
          f"PASS={res['passes']}")
    print(f"excluded (coverage > {ec.COVERAGE_CAP}): "
          + ", ".join(f"{e['site']}@{e['coverage']:.3f}" for e in res["excluded_blanket_probes"]))
    return 0 if res["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
