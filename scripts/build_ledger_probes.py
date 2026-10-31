#!/usr/bin/env python3
"""Stage 1 of the ledger inversion: turn the 118 public sibling rasters into probe matrices.

This builder was missing from the repository: `docs/data/ledger_inversion.json` (published by
PR #66) is produced by `scripts/invert_ledger.py`, which reads `data/work/probes_f4.npz`, and
nothing in the repo wrote that file.  Reproducing the published inversion - and scoring a NEW
candidate with the same instrument - therefore required restoring this stage.

For every pinned sibling raster with an owner-reported score we reduce its dot mask to
  * ``kA[i, block]``  mean official-triangular-kernel credit that a dot in that block earns, and
  * ``nb[i, block]``  dot count per 400 m block,
which is exactly the linear forward model ``DTI_i = f(kA_i, nb_i; rho)`` inverted downstream.

Evidence class: measurement on public files; the scores are OWNER-REPORTED, not receipts.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import inversion as INV      # noqa: E402
from gemsdoe import io as gio           # noqa: E402
from gemsdoe import uniqueness as U     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "data" / "work" / "probes_f4.npz"))
    a = ap.parse_args()
    t0 = time.time()
    (ROOT / "data" / "work").mkdir(parents=True, exist_ok=True)

    footprint = gio.read_footprint()
    catalogue = gio.read_labels() & footprint
    rows = json.loads((ROOT / "registry" / "upstream_live_ledger_rasters.json").read_text())["rows"]
    dots_list, scores, names, n_dots = [], [], [], []
    for r in rows:
        if r.get("status") != "ok":
            continue
        p = ROOT / "data" / "ledger" / f"{r['site']}__{Path(r['path']).name}"
        if not p.exists():
            print(f"  skip (not mirrored): {p.name}", flush=True)
            continue
        d = (U.load_mask(p) > 0) & footprint
        dots_list.append(d)
        scores.append(float(r["score"]))
        names.append(f"{r['site']}::{r['submission']}")
        n_dots.append(int(d.sum()))
        print(f"  [{time.time()-t0:5.1f}s] {len(names):3d} {names[-1][:66]:66s} dots={n_dots[-1]:>8,}", flush=True)

    ps = INV.build_probe_set(dots_list, scores, names, footprint, catalogue, factor=a.factor)
    np.savez_compressed(
        a.out, kA=np.ascontiguousarray(ps.kA), nblocks=np.ascontiguousarray(ps.nblocks),
        active_blocks=ps.active_blocks, block_shape=np.array(ps.block_shape),
        scores=ps.scores, names=np.array(ps.names), n_dots=ps.n_dots,
        factor=np.array(ps.factor), active_fraction=ps.active_fraction)
    out = dict(path=str(Path(a.out).relative_to(ROOT)), n_probes=len(names),
               n_blocks=int(ps.kA.shape[1]), factor=a.factor,
               block_shape=list(map(int, ps.block_shape)),
               recovered_dots_min=int(min(n_dots)), recovered_dots_max=int(max(n_dots)),
               score_range=[min(scores), max(scores)],
               sha_of_members=[r["sha256"] for r in rows if r.get("status") == "ok"][:1],
               elapsed_s=round(time.time() - t0, 1),
               note="stage-1 probe matrices for scripts/invert_ledger.py; owner-reported scores only")
    print(json.dumps(out, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
