#!/usr/bin/env python3
"""Emit the release submission: train on every quadrant, score, select dots, write.

The written file is our own work: catalogue-free feature planes computed from the
official 19-band stack, a model fitted on official labels under spatial blocking,
and a dot-selection policy taken from the verified masking + metric structure.
Nothing is copied from any sibling submission (the sibling rasters are used only
as *comparators* in the uniqueness audit).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_release import emit, model, shared, truth, validate  # noqa: E402

EVID = ROOT / "evidence" / "release"
DOWNLOAD = ROOT / "docs" / "downloads" / "release"
NOTE_SUFFIX = "multi-physics structural detector, catalogue-independent supervision, 300 m collar"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--density", type=int, default=20000, help="dots per million active cells")
    ap.add_argument("--arm", default="UNION", choices=["CAT", "UNION"])
    ap.add_argument("--kind", default="hgb", choices=["hgb", "logit"])
    ap.add_argument("--nms", type=int, default=2)
    ap.add_argument("--max-dots", type=int, default=165000,
                    help="hard cap at the fold-tested saturation point")
    ap.add_argument("--collar", type=float, default=3.0)
    ap.add_argument("--n-pos", type=int, default=40000)
    ap.add_argument("--n-neg", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=20261031)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    EVID.mkdir(parents=True, exist_ok=True)
    DOWNLOAD.mkdir(parents=True, exist_ok=True)
    utc = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    footprint, catalogue = shared.load_masks()
    names, planes = model.open_planes()
    sg = truth.sgmc_offcatalogue(catalogue)
    sgmc_off = sg["mask"]
    active = footprint & ~catalogue

    # Train on the whole study area: no quadrant is held out for the final fit.
    rng = np.random.default_rng(args.seed)
    pos = catalogue if args.arm == "CAT" else (catalogue | sgmc_off)
    negatives = truth.background_mask(catalogue, footprint, model.NEG_MIN_PX)
    pr, pc = model._sample_index(pos, args.n_pos, rng)
    nr, nc = model._sample_index(negatives, args.n_neg, rng)
    train = dict(pos_rows=pr, pos_cols=pc, neg_rows=nr, neg_cols=nc,
                 n_pos_sampled=int(pr.size), n_neg_sampled=int(nr.size),
                 n_pos_available=int(pos.sum()), n_neg_available=int(negatives.sum()))
    fitted, meta = model.fit(planes, names, train, kind=args.kind, seed=args.seed)
    print(f"[fit] arm={args.arm} pos={meta['n_pos']} total={meta['n_samples']}", flush=True)

    score = model.score_region(fitted, planes, footprint)
    np.save(ROOT / "data" / "work" / "scores" / f"final_{args.arm}.npy", score,
            allow_pickle=False)
    allowed, d_cat = emit.allowed_mask(footprint, catalogue, collar_px=args.collar,
                                       valid=np.isfinite(score))
    k = min(int(round(args.density * int(active.sum()) / 1_000_000)), args.max_dots)
    dots = emit.select_dots(score, allowed, k, nms_px=args.nms,
                            candidate_cap=1_200_000)
    n_dots = int(dots.sum())
    print(f"[emit] density={args.density}/M k_target={k:,} dots={n_dots:,}", flush=True)

    # Write to a staging path, hash it, then rename so the filename carries the sha.
    staging = DOWNLOAD / f".candidate{args.tag}.tif"
    first = emit.write_submission(staging, dots, footprint)
    final = DOWNLOAD / (f"WBGGEMSDOE3-CIFS-multiphysics-{args.arm.lower()}-{n_dots}d-"
                        f"{utc}-{first['sha256'][:8]}{args.tag}.tif")
    staging.replace(final)
    written = dict(first, path=str(final))
    if written["sha256"] != shared.sha256_file(final):  # rename must not change bytes
        raise RuntimeError("sha256 changed across rename")

    fmt = validate.validate_format(final, footprint, catalogue, collar_px=args.collar)
    comparators = []
    if (EVID / "comparators.json").is_file():
        comparators = json.loads((EVID / "comparators.json").read_text())["comparators"]
    uniq = validate.uniqueness_audit(final, footprint, catalogue, comparators)

    card = {
        "generated_by": "scripts/release_emit.py",
        "generated_utc": utc,
        "submission": {"file": final.name, "path": str(final.relative_to(ROOT)),
                       "sha256": written["sha256"], "bytes": written["bytes"]},
        "hypothesis": "Faults missing from the Quaternary catalogue are detectable from "
                      "structural lineaments that agree across independent physics "
                      "(topography, magnetics, gravity, strain/seismicity), and the "
                      "official metric rewards covering them while the catalogue mask "
                      "makes near-catalogue dots pure false-positive mass.",
        "mechanism": "Oriented 900 m x 300 m line filters on 13 catalogue-free feature "
                     "planes plus a 4-physics strike-concordance plane; supervised ranking "
                     f"({args.kind}, arm {args.arm}); binary 1.0 dots at "
                     f"{args.density}/million active cells, 3 px collar, {args.nms} px "
                     "minimum separation, zeros inside the footprint, NaN outside.",
        "non_fault_mimic": "Drainage and eolian ridge axes in the DEM, cultural/flight-line "
                           "striping in magnetics, and lithological density contrasts in "
                           "gravity all produce linear gradients; the concordance plane and "
                           "the cross-validated weighting are what suppress them.",
        "arm": args.arm, "kind": args.kind, "density_per_million": args.density,
        "collar_px": args.collar, "nms_px": args.nms, "max_dots_cap": args.max_dots,
        "dots": n_dots, "active_cells": int(active.sum()),
        "training": {k2: int(v) for k2, v in train.items() if k2.startswith("n_")},
        "format_validator": fmt,
        "uniqueness_audit": uniq,
        "note": (f"WB-GEMS-DOE-3 CIFS {args.arm} | {n_dots} dots, catalogue-free "
                 f"multi-physics concordance, >{int(args.collar*100)} m collar | {NOTE_SUFFIX}")[:140],
        "verdict": "promote" if (fmt["passed"] and uniq["passed"]) else "negative",
    }
    (EVID / "candidate_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    (DOWNLOAD / (final.stem + ".json")).write_text(json.dumps({
        "file": final.name, "sha256": written["sha256"], "dots": n_dots,
        "note": card["note"], "format_passed": fmt["passed"],
        "uniqueness_passed": uniq["passed"],
        "format_checks": fmt["checks"], "uniqueness_checks": uniq["checks"],
        "rules": shared.SOURCES,
    }, indent=2) + "\n")
    print(json.dumps({"file": final.name, "sha256": written["sha256"],
                      "format_passed": fmt["passed"], "uniqueness_passed": uniq["passed"],
                      "failed_checks": [k2 for k2, v in fmt["checks"].items() if not v]
                      + [k2 for k2, v in uniq["checks"].items() if not v]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
