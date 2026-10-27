#!/usr/bin/env python3
"""Rebuild the nine-focus-site table with a common LEDGER-INVERSION estimate.

Owner-reported scores are historical claims without receipts (see registry/focus_sites.json).
The estimate column applies the SAME instrumented model to every file, so the column is
comparable across sites even where the owner claim is missing or disputed.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("ec", ROOT / "scripts/emit_candidate.py")
ec = importlib.util.module_from_spec(spec); spec.loader.exec_module(ec)
from gemsw import grid as G

FOCUS = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def main() -> int:
    g = G.load_grid()
    ledger = {}
    for r in json.loads((ROOT / "data/ledger/index.json").read_text()):
        if r.get("status") != "verified":
            continue
        ledger.setdefault(r["site"], []).append(r)
    audit = json.loads((ROOT / "evidence/focus_audit.json").read_text())
    rows, all_dots = [], {}
    for site in FOCUS:
        best = max(ledger[site], key=lambda r: r["score"])
        with rasterio.open(ROOT / best["local"]) as ds:
            a = ds.read(1)
        dots = np.isfinite(a) & g.foot & (a > 0.5)
        est = ec.ledger_estimate(dots, g)
        all_dots[site] = dots
        rows.append({"site": site, "file": Path(best["path"]).name,
                     "local": best["local"], "sha256": best["sha256"],
                     "owner_reported": best["score"], "n_dots": int(dots.sum()),
                     "ledger_estimate": round(est["predicted_dti"], 4)})
    # pairwise uniqueness (max |phi| and max fraction of my dots within 3 px of the other)
    from scipy.spatial import cKDTree
    for r in rows:
        worst_phi, worst_ov, worst_site = 0.0, 0.0, None
        mine = np.column_stack(np.nonzero(all_dots[r["site"]])).astype(float)
        for other in FOCUS:
            if other == r["site"]:
                continue
            o = all_dots[other]
            phi = abs(ec._phi(all_dots[r["site"]][g.foot], o[g.foot]))
            d, _ = cKDTree(np.column_stack(np.nonzero(o)).astype(float)).query(mine, k=1)
            ov = float((d <= 3).mean())
            if ov > worst_ov:
                worst_ov, worst_site = ov, other
            worst_phi = max(worst_phi, phi)
        r.update({"max_abs_phi_vs_other_focus": round(worst_phi, 4),
                  "max_overlap_with": worst_site,
                  "max_overlap_fraction": round(worst_ov, 4),
                  "unique_vs_focus_set": bool(worst_phi <= 0.90 and worst_ov <= 0.70)})
    out = {"evidence_class": "owner-reported scores + LEDGER-INVERSION ESTIMATE (same model per row)",
           "instrument": "gemsw.inversion v2; site-grouped CV MAE 0.037, Spearman 0.946",
           "rows": rows}
    (ROOT / "evidence/nine_site_table.json").write_text(json.dumps(out, indent=1))
    for r in rows:
        print(f"{r['site']:>9} owner={r['owner_reported']:.4f} est={r['ledger_estimate']:.4f} "
              f"n={r['n_dots']:>6} uniq={r['unique_vs_focus_set']} "
              f"(max|phi|={r['max_abs_phi_vs_other_focus']:.3f}, ov={r['max_overlap_fraction']:.3f} vs {r['max_overlap_with']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
