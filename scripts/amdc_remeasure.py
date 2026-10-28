#!/usr/bin/env python3
"""Remeasure AMDC uniqueness with coverage-aware control classification (no new experiment).

Correction disclosed in the run card: the first measurement classified registry rows by
DOT COUNT (<20% of footprint = sparse). The spacing-5 lattice calibration raster has
~4% dot support but 99.87% 3px-halo coverage, so the literal 70% overlap test is vacuous
for it (any candidate overlaps ~100%). Same for the 100%-support E-proba control.

Content-aware rule (preregistered 2026-10-27; same precedent as the SGCE lane's
lattice-excess pass and the RFL lane's +0.05 null-excess rule):
  * control rows: registry rasters whose 3px halo covers >90% of the footprint
    -> gate on EXCESS = overlap - coverage <= 0.05 (reported, flagged IR-01)
  * all other rows: literal gates (|rho|<=0.90, overlap<=0.70, no exact duplicates)

Reads evidence/amdc/final_{surface,dots}.npy + registry_index.json (same bytes as the
finalize measurement). Writes evidence/amdc/uniqueness_remeasured.json.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import uniqueness as U  # noqa: E402

OUT = ROOT / "evidence" / "amdc"


def halo_coverage(p: Path, foot: np.ndarray) -> tuple[int, float]:
    with rasterio.open(p) as ds:
        a = ds.read(1)
    sup = (np.isfinite(a) & (a > 0)) & foot
    cov = float(U._near(sup)[foot].mean())
    return int(sup.sum()), cov


def main() -> int:
    t0 = time.time()
    idx = json.loads((OUT / "registry_index.json").read_text())["files"]
    surface = np.load(OUT / "final_surface.npy")
    dots = np.load(OUT / "final_dots.npy")
    with rasterio.open(ROOT / ".cache/57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
                       / "data/official/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        expected = (ds.shape, ds.crs, ds.transform)

    rep_dots = json.loads((OUT / "uniqueness_dots.json").read_text())
    rep_surf = json.loads((OUT / "uniqueness_surface.json").read_text())

    rows = []
    for r in rep_dots["rows"]:
        if "error" in r:
            rows.append({**r, "coverage": None, "is_control": False})
            continue
        ndots, cov = halo_coverage(Path(r["file"]), foot)
        assert ndots == r["their_dots"], (r["file"], ndots, r["their_dots"])
        is_control = cov > 0.90
        ov = r["my_dots_within_3px_of_theirs"]
        rows.append({**r, "coverage": cov, "is_control": is_control,
                     "excess": (ov - cov) if is_control else None})
    controls = [r for r in rows if r.get("is_control")]
    gated = [r for r in rows if not r.get("is_control") and "error" not in r]
    errs = [r for r in rows if "error" in r]
    rhos = [(abs(r["spearman_full_footprint"]), r["submission"]) for r in rows
            if r.get("spearman_full_footprint") is not None]
    ovs = [(r["my_dots_within_3px_of_theirs"], r["submission"]) for r in gated]
    exact = [r["submission"] for r in rows
             if r.get("identical_bytes") or r.get("identical_decoded_predictions")]
    max_exc = max([c["excess"] for c in controls]) if controls else None
    max_rho = max(rhos) if rhos else (None, None)
    max_ov = max(ovs) if ovs else (None, None)
    s_rows = [r for r in rep_surf["rows"] if "error" not in r]
    s_rhos = [(abs(r["spearman_full_footprint"]), r["submission"]) for r in s_rows
              if r["spearman_full_footprint"] is not None]
    s_max_rho = max(s_rhos) if s_rhos else (None, None)
    s_exact = [r["submission"] for r in s_rows
               if r.get("identical_bytes") or r.get("identical_decoded_predictions")]

    p3 = bool(max_rho[0] is not None and max_rho[0] <= 0.90
              and (max_ov[0] is None or max_ov[0] <= 0.70)
              and (max_exc is None or max_exc <= 0.05)
              and not exact and s_max_rho[0] is not None and s_max_rho[0] <= 0.90
              and not s_exact)
    out = {
        "rule": "coverage-aware content-aware (preregistered; controls = halo coverage >0.90, "
                "excess<=0.05; others literal 0.90/0.70; no exact duplicates)",
        "n_registry": len(rows), "n_controls": len(controls), "n_gated": len(gated),
        "n_errors": len(errs), "errors": errs,
        "controls": [{"submission": c["submission"], "their_dots": c["their_dots"],
                      "coverage": round(c["coverage"], 4),
                      "overlap": round(c["my_dots_within_3px_of_theirs"], 4),
                      "excess": round(c["excess"], 4)} for c in controls],
        "dots_max_abs_rho": max_rho[0], "dots_max_abs_rho_with": max_rho[1],
        "dots_max_gated_overlap": max_ov[0], "dots_max_gated_overlap_with": max_ov[1],
        "dots_max_control_excess": max_exc,
        "surface_max_abs_rho": s_max_rho[0], "surface_max_abs_rho_with": s_max_rho[1],
        "exact_duplicates": exact, "surface_exact_duplicates": s_exact,
        "top10_gated_overlaps": sorted(
            [{"submission": r["submission"],
              "overlap": round(r["my_dots_within_3px_of_theirs"], 4),
              "rho": (round(r["spearman_full_footprint"], 4)
                      if r["spearman_full_footprint"] is not None else None)}
             for r in gated], key=lambda r: -r["overlap"])[:10],
        "pass": p3,
        "literal_reading": {"dots_unique": rep_dots["unique"],
                            "dots_duplicate_count": rep_dots["duplicate_count"],
                            "surface_unique": rep_surf["unique"]},
        "wall_s": round(time.time() - t0, 1),
    }
    (OUT / "uniqueness_remeasured.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in (
        "n_registry", "n_controls", "n_gated", "controls", "dots_max_abs_rho",
        "dots_max_abs_rho_with", "dots_max_gated_overlap", "dots_max_gated_overlap_with",
        "dots_max_control_excess", "surface_max_abs_rho", "surface_max_abs_rho_with",
        "exact_duplicates", "pass", "literal_reading")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
