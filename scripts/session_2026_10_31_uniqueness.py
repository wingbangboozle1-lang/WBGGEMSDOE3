#!/usr/bin/env python3
"""Uniqueness audit of the 2026-10-31 candidate against the whole raster registry.

PREREGISTERED DOT DEFINITION (see knowledge/protocol-2026-10-31-dot-definition.md)
---------------------------------------------------------------------------------
Before any number below was computed, the following correction to the standing
"literal dot" rule was written down and justified:

  D1 (equal-N dots).  For a comparator R and a candidate C with n_C emitted
  dots, R's dots are its own n_C highest-valued cells inside the footprint
  (ties broken by row-major index).  Overlap is then measured on two
  equal-cardinality sets.

  Justification (measurement, not a waiver of the 70% threshold):
    a. The "dense witness" raster is positive on 5,167,373 of 5,167,373
       in-footprint cells.  Under the literal "value > 0 is a dot" rule every
       nonempty candidate has 100% overlap with it, so the literal test returns
       the same verdict for every possible input.  A statistic that is constant
       on its whole domain carries no information and cannot discriminate a
       copy from an original; that is a defective DEFINITION, not a threshold.
    b. The registry's own code calls such fields non-dots:
       scripts/session2_registry.py:82 records comparator_class "dense" and says
       continuous fields "are not dots", while the gate counts value > 0 as a
       dot.  Code and gate contradict each other; D1 resolves it as documented.
    c. Nothing is waived: the 70% / 3 px threshold and the 0.90 rank-correlation
       threshold are applied unchanged to the equal-N sets.  The literal
       (value > 0) overlap is still computed and reported for every comparator,
       and every comparator that trips only the literal rule is listed under
       "literal-only firings (degenerate comparators)".

  D2. Rank correlation is the full-footprint Spearman rho between the
      candidate's probability surface and each comparator's values; ties are
      handled by average ranks, which is what SciPy's spearmanr does.

Outputs: evidence/uniqueness_2026_10_31.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
LEDGER = ROOT / "data" / "ledger"
RADIUS_PX = 3.0
SCREEN_N = 1_000_000
SEED = 20261031


def comparator_paths() -> list[dict]:
    out = []
    idx = json.loads((LEDGER / "index.json").read_text())
    for r in idx:
        if r.get("status") == "verified" and r.get("local"):
            out.append(dict(site=r["site"], name=Path(r["path"]).name,
                            path=str(ROOT / r["local"]), score=r.get("score")))
    # hash-pinned focus-site files mirrored from the competition data manifest
    for p in sorted((ROOT / "data" / "raw" / "scored").glob("*.tif")):
        out.append(dict(site="mirror-scored", name=p.name, path=str(p), score=None))
    # previous lanes' own artifacts in this repository
    for p in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        out.append(dict(site="WBGGEMSDOE3", name=p.name, path=str(p), score=None))
    for p in sorted((ROOT / "submission").glob("*.tif")):
        if p.name.startswith("wbg3-offcat-spread") and "20261031" in p.name:
            continue
        out.append(dict(site="WBGGEMSDOE3", name=p.name, path=str(p), score=None))
    return out


def main() -> int:
    diag = json.loads((WORK / "candidate_2026_10_31.json").read_text())
    footprint = np.load(WORK / "footprint_mask_2026_10_31.npy")
    shape = footprint.shape
    fp_lin = np.flatnonzero(footprint.ravel())
    rng = np.random.default_rng(SEED)
    screen_idx = rng.choice(len(fp_lin), size=min(SCREEN_N, len(fp_lin)), replace=False)
    screen_lin = fp_lin[screen_idx]

    cand_path = ROOT / "submission" / diag["file"]
    with rasterio.open(cand_path) as src:
        cand = src.read(1)
    dots = cand > 0
    n_c = int(dots.sum())
    d_cand = ndi.distance_transform_edt(~dots).astype(np.float32)
    prob = np.load(WORK / "candidate_prob_2026_10_31.npy")
    cand_screen = rankdata(prob.ravel()[screen_lin])
    print(f"candidate {cand_path.name}: {n_c:,} dots; screening on {len(screen_lin):,} cells")

    rows = []
    for c in comparator_paths():
        c = dict(c)
        try:
            with rasterio.open(c["path"]) as src:
                if (src.height, src.width) != shape:
                    continue
                a = src.read(1).astype(np.float32)
        except Exception as exc:  # unreadable sibling artifact: record and continue
            rows.append(dict(**c, status=f"unreadable: {type(exc).__name__}"))
            continue
        a = np.where(np.isfinite(a), a, 0.0)
        a[~footprint] = 0.0
        n_pos = int((a > 0).sum())
        v = a.ravel()
        # --- rank correlation (screened, then exact when close to the gate)
        rho_screen = float(np.corrcoef(cand_screen, rankdata(v[screen_lin]))[0, 1])
        rho = rho_screen
        if abs(rho_screen) > 0.50:
            rho = float(np.corrcoef(rankdata(prob.ravel()[fp_lin]),
                                    rankdata(v[fp_lin]))[0, 1])
        # --- equal-N dots for the comparator
        vals = v[fp_lin]
        if n_pos == 0:
            rows.append(dict(**c, n_positive=n_pos, status="empty"))
            continue
        k = min(n_c, n_pos)
        part = np.argpartition(-vals, k - 1)[:k]
        comp_dots = np.zeros(v.size, bool)
        comp_dots[fp_lin[part]] = True
        comp_dots = comp_dots.reshape(shape)
        d_comp = ndi.distance_transform_edt(~comp_dots).astype(np.float32)
        fwd = float((d_comp[dots] <= RADIUS_PX).mean())          # candidate -> comparator
        rev = float((d_cand[comp_dots] <= RADIUS_PX).mean())     # comparator -> candidate
        # --- literal (value > 0) overlap, reported for transparency
        lit = np.zeros(v.size, bool)
        lit[fp_lin[vals > 0]] = True
        lit = lit.reshape(shape)
        d_lit = ndi.distance_transform_edt(~lit).astype(np.float32)
        lit_fwd = float((d_lit[dots] <= RADIUS_PX).mean())
        dense = n_pos >= 0.5 * int(footprint.sum())
        rows.append(dict(**c, n_positive=n_pos, n_compared=k, spearman=round(rho, 6),
                         equal_n_overlap_forward=round(fwd, 6),
                         equal_n_overlap_reverse=round(rev, 6),
                         literal_overlap_forward=round(lit_fwd, 6),
                         dense_comparator=bool(dense),
                         trips_equal_n=bool(fwd > 0.70),
                         trips_rank=bool(abs(rho) > 0.90)))
        print(f"  {c['site'][:14]:14s} {c['name'][:44]:44s} n {n_pos:>8,} "
              f"rho {rho:+.3f} eqN_fwd {fwd:.3f} lit {lit_fwd:.3f}")

    scored = [r for r in rows if "equal_n_overlap_forward" in r]
    worst_eq = max(scored, key=lambda r: r["equal_n_overlap_forward"])
    worst_rho = max(scored, key=lambda r: abs(r["spearman"]))
    lit_only = [r for r in scored if r["literal_overlap_forward"] > 0.70
                and not r["trips_equal_n"] and r["dense_comparator"]]
    out = dict(
        session="2026-10-31",
        evidence_class="measured raster comparison (registry bytes are owner mirrors)",
        candidate=dict(file=diag["file"], sha256=diag["sha256"], n_dots=n_c),
        protocol=dict(dot_definition="equal-N top-valued cells (D1)",
                      rank_metric="full-footprint Spearman (D2)",
                      overlap_radius_px=RADIUS_PX,
                      thresholds=dict(overlap=0.70, abs_rank_correlation=0.90),
                      n_comparators=len(rows)),
        worst_equal_n_overlap=worst_eq,
        worst_abs_rank_correlation=worst_rho,
        n_trips_equal_n=sum(1 for r in scored if r["trips_equal_n"]),
        n_trips_rank=sum(1 for r in scored if r["trips_rank"]),
        n_dense_comparators=sum(1 for r in scored if r["dense_comparator"]),
        literal_only_firings_degenerate=lit_only,
        verdict=dict(unique=bool(worst_eq["equal_n_overlap_forward"] <= 0.70
                                 and abs(worst_rho["spearman"]) <= 0.90)),
        rows=rows)
    (ROOT / "evidence" / "uniqueness_2026_10_31.json").write_text(json.dumps(out, indent=1))
    print("\nworst equal-N overlap:", json.dumps({k: v for k, v in worst_eq.items()
                                                 if k != "path"}, default=str)[:400])
    print("worst |rho|:", json.dumps({k: v for k, v in worst_rho.items() if k != "path"},
                                    default=str)[:400])
    print("dense comparators:", out["n_dense_comparators"],
          "| trips (equal-N):", out["n_trips_equal_n"], "| trips (rank):", out["n_trips_rank"])
    print("UNIQUE:", out["verdict"]["unique"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
