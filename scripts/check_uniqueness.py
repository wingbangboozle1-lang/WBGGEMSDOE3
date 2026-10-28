#!/usr/bin/env python3
"""Uniqueness gate: directed 3-px overlap and rank correlation vs the sibling registry.

Rule (user's parallel-run protocol): a design is a duplicate if >70% of its dots fall
within 3 px of one registry raster's dots, or if |Spearman| > 0.90 against one registry
raster.  This compares the candidate against (a) the nine focus-site champions that the
brief names, (b) every scored probe raster (98), and (c) this repository's own
docs/downloads GeoTIFFs.
"""
from __future__ import annotations
import json, sys, glob
from pathlib import Path
import numpy as np, rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G, exact as EX

def main() -> int:
    cand = ROOT / "docs" / "downloads" / "wbggems3-invdesign-anchor-20k-zeros.tif"
    with rasterio.open(cand) as ds:
        c = np.where(np.isfinite(ds.read(1)), ds.read(1), 0.0)
    ours = c > 0
    focus = json.loads((ROOT / "registry" / "focus_sites.json").read_text())
    files = []
    for f in focus["sites"]:
        hits = sorted(glob.glob(f"/tmp/{f['ref'] and ''}{f['site']}/docs/downloads/*.tif"))
        for h in hits:
            if f["path"].split("/")[-1][:38] in Path(h).name:
                files.append(h)
                break
    ladder = json.loads((ROOT / "evidence" / "probe_ladder.json").read_text())
    for p in ladder["probes"]:
        hits = sorted(glob.glob(f"/tmp/{p['site']}/**/{p['submission']}*.tif", recursive=True))
        if hits:
            files.append(hits[0])
    files += [str(x) for x in (ROOT / "docs" / "downloads").glob("*.tif") if x.name != cand.name]
    seen, results = set(), []
    for f in files:
        if f in seen:
            continue
        seen.add(f)
        try:
            with rasterio.open(f) as ds:
                if (ds.height, ds.width) != ours.shape:
                    continue
                b = ds.read(1).astype(np.float64)
        except Exception:
            continue
        b = np.where(np.isfinite(b), np.clip(b, 0, 1), 0.0)
        s = b > 0
        if s.sum() == 0:
            continue
        k = EX.kernel_credit_field(s)
        ov = float((k[ours] > 0).mean())
        ka = EX.kernel_credit_field(ours)
        rev = float((ka[s] > 0).mean())
        rho_s = spearmanr(b[::6, ::6].ravel(), c[::6, ::6].ravel()).statistic
        results.append({"file": str(Path(f).relative_to("/tmp")) if f.startswith("/tmp") else str(Path(f).name),
                        "n_dots": int(s.sum()), "our_dots_within3px": ov,
                        "their_dots_within3px": rev,
                        "spearman": float(rho_s) if np.isfinite(rho_s) else None})
    results.sort(key=lambda r: -r["our_dots_within3px"])
    worst_ov = results[0]["our_dots_within3px"] if results else 0.0
    worst_sp = max((abs(r["spearman"]) for r in results if r["spearman"] is not None), default=0.0)
    out = {"candidate": str(cand.relative_to(ROOT)), "n_registry_compared": len(results),
           "limit_overlap": 0.70, "limit_abs_spearman": 0.90,
           "max_directed_overlap": worst_ov, "max_abs_spearman": worst_sp,
           "unique": bool(worst_ov <= 0.70 and worst_sp <= 0.90),
           "top10_by_overlap": results[:10],
           "top_overlap_vs_focus_champions": [r for r in results if r["file"].startswith("GEMSDOE")][:4]}
    (ROOT / "evidence" / "uniqueness_gate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_registry_compared","max_directed_overlap","max_abs_spearman","unique")}, indent=1))
    for r in results[:6]:
        print(f"  {r['file'][:70]:70s} ov={r['our_dots_within3px']:.3f} rev={r['their_dots_within3px']:.3f} rho={r['spearman']:+.3f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
