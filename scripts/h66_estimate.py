#!/usr/bin/env python3
"""LEDGER-INVERSION ESTIMATE for the H66-SPRP candidate and the nine focus files.

This is the repository's existing estimator (``gemsw.inversion`` v2): the public
score ledger (owner-reported scalars, no organizer receipts) is inverted into a
coarse hidden-truth density field, and any candidate raster is then scored
against that field.

WHAT IT IS NOT: not ground truth, not a HOLDOUT-DTI, not an ORGANIZER-CONFIRMED
score.  The instrument's own leave-one-site-out error is quoted next to every
estimate.  A projection is never written as a score.

Usage:
    python scripts/h66_estimate.py --candidate submission/<file>.tif
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G              # noqa: E402
from gemsw import inversion as INV       # noqa: E402

WORK = ROOT / "data" / "work"
FACTOR = 4
ALPHA, BETA = 0.2, 0.8
OUT = ROOT / "evidence" / "h66_sprp"
FOCUS = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")


def kernel_credit_from_density(rho: np.ndarray, act_count: np.ndarray) -> np.ndarray:
    f_cell = rho / np.maximum(act_count, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        d_nn = np.where(f_cell > 1e-6, 0.5 / np.maximum(f_cell, 1e-6), 1e6)
    return np.clip(1.0 - d_nn / INV.RADIUS_PX, 0.0, 1.0)


def estimate_for(dots: np.ndarray, rho: np.ndarray, act_count: np.ndarray,
                 foot: np.ndarray) -> dict:
    """Project one dot mask onto the recovered truth-density field."""
    dist = ndi.distance_transform_edt(~dots)
    k = INV.kernel_from_distance(dist)
    k[~foot] = 0.0
    kA = (INV.block_sum(k, FACTOR).ravel() / np.maximum(act_count, 1.0)).astype(np.float32)
    nb = INV.block_sum(dots.astype(np.float64), FACTOR).ravel().astype(np.float32)
    mass = float(rho.sum())
    T = float(kA @ rho.astype(np.float32))
    q = kernel_credit_from_density(rho, act_count)
    FP = float((nb * (1.0 - q)).sum())
    dti = T / (T + ALPHA * FP + BETA * max(mass - T, 0.0) + 1e-12)
    return dict(estimate=float(dti), T=T, FP=FP, truth_mass=mass,
                n_dots=int(dots.sum()))


def dots_of(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
    a = np.where(np.isfinite(a), a, 0.0)
    return (a > 0) & foot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default=str(OUT / "estimate.json"))
    args = ap.parse_args()

    t0 = time.time()
    g = G.load_grid()
    rho_path = WORK / "rho_blocks.npy"
    if not rho_path.exists():
        raise SystemExit("run scripts/invert_ledger.py first (it writes rho_blocks.npy)")
    rho = np.load(rho_path).ravel().astype(np.float32)
    act_count = INV.block_sum((g.foot & ~g.labels).astype(np.float64), FACTOR).ravel().astype(np.float32)
    active_blocks = INV.block_mean((g.foot & ~g.labels).astype(np.float64), FACTOR).ravel() > 0.5
    print(f"[estimate] truth mass {rho.sum():.0f} cells, {int(active_blocks.sum())} active blocks")

    ledger = json.loads((ROOT / "data/ledger/index.json").read_text())
    rows = []
    for r in ledger:
        if r.get("status") != "verified":
            continue
        p = ROOT / r["local"]
        if not p.exists():
            continue
        rows.append((r["site"], r["submission"], p, float(r["score"])))
    focus_rows = [r for r in rows if r[0] in FOCUS]
    print(f"[estimate] {len(rows)} ledger rasters, {len(focus_rows)} focus-site rasters")

    out_rows = []
    for site, submission, path, score in focus_rows:
        d = dots_of(path, g.foot)
        est = estimate_for(d, rho, act_count, g.foot)
        out_rows.append(dict(kind="focus_site", site=site, submission=submission,
                              owner_reported=score, estimate=est["estimate"],
                              n_dots=est["n_dots"], local=str(path.relative_to(ROOT))))
        print(f"  {site:11s} {submission[:52]:52s} owner {score:.4f} est {est['estimate']:.4f}")

    cand = Path(args.candidate)
    if not cand.is_absolute():
        cand = ROOT / cand
    d = dots_of(cand, g.foot)
    est = estimate_for(d, rho, act_count, g.foot)
    out_rows.append(dict(kind="candidate", site="WBGGEMSDOE3", submission=cand.stem,
                          owner_reported=None, estimate=est["estimate"],
                          n_dots=est["n_dots"], local=str(cand.relative_to(ROOT))))

    card = json.loads((ROOT / "evidence/ledger_inversion.json").read_text())
    out = dict(
        evidence_class="LEDGER-INVERSION ESTIMATE (owner-reported scores, no organizer receipts)",
        instrument="gemsw.inversion v2 (linear score tomography, 400 m blocks, exact EDT kernel)",
        instrument_cv=card.get("site_grouped_cv"),
        instrument_note=("Cross-validated error of the instrument itself; an estimate is not a "
                         "score and is not ORGANIZER-CONFIRMED."),
        truth_mass_cells=float(rho.sum()),
        rows=out_rows,
        elapsed_s=round(time.time() - t0, 1),
    )
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"[estimate] candidate {cand.name}: ESTIMATE {est['estimate']:.4f} "
          f"({est['n_dots']} dots) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
