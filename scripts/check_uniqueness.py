#!/usr/bin/env python3
"""Uniqueness gate: directed 3-px overlap and rank correlation vs the sibling registry.

Rule (user's parallel-run protocol): a design is a duplicate if >70% of its dots fall
within 3 px of one registry raster's dots, or if |Spearman| > 0.90 against one registry
raster.  This compares the candidate against (a) the nine focus-site champions that the
brief names, (b) every scored probe raster (98), and (c) this repository's own
docs/downloads GeoTIFFs.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G, exact as EX

INPUT_MARKERS = ("/data/external/", "audit_sources", "/data/bridge/", "distance_m", "acquisition_block",
                 "_u8", "lidar_scarp_features", "geodawn", "derived_sgmc", "tiger_road", "blm_closed",
                 "temperature", "paleo_geothermal", "wellspring", "volcanic_vents", "existing_faults",
                 "labels.tif", "sample_submission", "training_features", "template_grid")


def kind_of(path: str) -> str:
    """'input_feature' for covariates / labels / sample grids; 'submission' for everything else.

    Inputs are reported but excluded from the duplicate rule, which is about prior SUBMISSIONS.
    The rule is listed here so a reviewer can audit each classification.
    """
    low = path.lower()
    return "input_feature" if any(m.lower() in low for m in INPUT_MARKERS) else "submission"


def main() -> int:
    """Directed-overlap and Spearman gate against every sha256-verified registry raster.

    Discovery (fixed 2026-10-28): the previous version globbed a /tmp mirror that no longer
    exists, so it silently compared only 58 rasters.  Now the comparator set is exactly the
    sha256-verified files written by scripts/fetch_registry_rasters.py (evidence/
    registry_fetch_2026-10-28.json) plus the owner focus TIFFs and this repo's own docs/downloads.
    Files with a different grid are counted, not silently dropped.
    """
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evidence" / "uniqueness_gate.json"
    cand = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        ROOT / "docs" / "downloads" / "wbggems3-invdesign-anchor-20k-zeros.tif"
    if not cand.is_absolute():
        cand = ROOT / cand
    with rasterio.open(cand) as ds:
        c = np.where(np.isfinite(ds.read(1)), ds.read(1), 0.0)
    ours = c > 0
    ka = EX.kernel_credit_field(ours)

    fetch = json.loads((ROOT / "evidence" / "registry_fetch_2026-10-28.json").read_text())
    files = [ROOT / p for p in fetch["matched_files"].values()]
    files += sorted((ROOT / "docs" / "downloads").glob("*.tif"))
    files += sorted((ROOT / ".cache" / "focus").glob("*.tif"))
    files = [f for f in files if f.resolve() != cand.resolve()]
    # Drop the candidate's own bytes wherever they appear (docs/downloads copies of it).
    cand_sha = hashlib.sha256(cand.read_bytes()).hexdigest()
    files = [f for f in files if hashlib.sha256(f.read_bytes()).hexdigest() != cand_sha]

    seen_sha, results, grid_mismatch, unreadable = set(), [], 0, 0
    for f in files:
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if digest in seen_sha:
            continue
        seen_sha.add(digest)
        try:
            with rasterio.open(f) as ds:
                if (ds.height, ds.width) != ours.shape:
                    grid_mismatch += 1
                    continue
                b = ds.read(1).astype(np.float64)
        except Exception:
            unreadable += 1
            continue
        b = np.where(np.isfinite(b), np.clip(b, 0, 1), 0.0)
        s = b > 0
        if s.sum() == 0:
            continue
        ov = float((EX.kernel_credit_field(s)[ours] > 0).mean())
        rev = float((ka[s] > 0).mean())
        rho_s = spearmanr(b[::6, ::6].ravel(), c[::6, ::6].ravel()).statistic
        name = (f.relative_to(ROOT).as_posix() if f.is_relative_to(ROOT) else f.name)
        results.append({"file": name, "kind": kind_of(name), "sha256": digest, "n_dots": int(s.sum()), "our_dots_within3px": ov,
                        "their_dots_within3px": rev,
                        "spearman": float(rho_s) if np.isfinite(rho_s) else None})
    results.sort(key=lambda r: -r["our_dots_within3px"])
    subs = [r for r in results if r["kind"] == "submission"]
    worst_ov = subs[0]["our_dots_within3px"] if subs else 0.0
    worst_rev = max((r["their_dots_within3px"] for r in subs), default=0.0)
    worst_sp = max((abs(r["spearman"]) for r in subs if r["spearman"] is not None), default=0.0)
    out = {"schema": "gems-uniqueness-gate-v2", "candidate": str(cand.relative_to(ROOT)),
           "candidate_sha256": hashlib.sha256(cand.read_bytes()).hexdigest(),
           "n_registry_compared": len(subs), "n_input_features_reported": len(results) - len(subs),
           "n_distinct_bytes_seen": len(seen_sha),
           "n_grid_mismatch_skipped": grid_mismatch, "n_unreadable_skipped": unreadable,
           "limit_overlap": 0.70, "limit_abs_spearman": 0.90,
           "max_directed_overlap": worst_ov, "max_reverse_overlap": worst_rev,
           "max_abs_spearman": worst_sp,
           "unique": bool(worst_ov <= 0.70 and worst_sp <= 0.90),
           "n_over_0_60": sum(1 for r in subs if r["our_dots_within3px"] > 0.60),
           "n_over_0_70": sum(1 for r in subs if r["our_dots_within3px"] > 0.70),
           "submissions_over_0_70": [r["file"] for r in subs if r["our_dots_within3px"] > 0.70],
           "top10_submissions_by_overlap": subs[:10],
           "top10_input_features_for_reference": [r for r in results if r["kind"] == "input_feature"][:10],
           "rows": results}
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n_registry_compared", "n_grid_mismatch_skipped", "max_directed_overlap",
                                          "max_reverse_overlap", "max_abs_spearman", "unique", "n_over_0_60")}, indent=1))
    for r in subs[:8]:
        print(f"  SUB {r['file'][-70:]:70s} ov={r['our_dots_within3px']:.4f} rev={r['their_dots_within3px']:.4f} n={r['n_dots']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
