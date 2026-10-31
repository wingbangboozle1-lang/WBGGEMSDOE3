#!/usr/bin/env python3
"""Measure HOLDOUT-DTI for the catalogue-buffer variants of the final emission.

scan5 chose the probability floor on a ladder with a fixed 2 px catalogue
buffer.  The ledger evidence (bands / envelope / estimator) then moved the
design to a 12 px buffer at floor 0.15, a geometry scan5 never measured.  This
scan closes that gap: it re-uses the cached out-of-fold probabilities and the
shared pooled evaluator, and scores each (buffer, floor) arm on the same
quadrant instrument, with the buffer taken against each fold's VISIBLE
catalogue so nothing leaks.

Caveat that must travel with the number: the quadrant instrument's withheld
truth is a catalogue fault in the held-out quadrant, so a buffer measured
against the visible catalogue removes far less of the withheld truth than the
same buffer removes from the final raster's own support.  The number is a
valid HOLDOUT-DTI for the arm as defined, but it does NOT reproduce the
"new faults are far from every mapped fault" regime the final raster targets.

Run: .venv/bin/python -u scripts/session_2026_10_31_scan6.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(TEMPLATE / "src"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from session_2026_10_31_scan3 import capacity_support  # noqa: E402

SEED = 20261031
ARMS = ((0.0, 0.15), (2.0, 0.15), (6.0, 0.20), (12.0, 0.15), (12.0, 0.30))


def main() -> int:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    arms, per_fold, dots_total = {}, {}, {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        visible = catalogue & ~region
        d_vis = ndi.distance_transform_edt(~visible).astype(np.float32)
        for buf, fl in ARMS:
            allowed = region & (d_vis > buf) if buf > 0 else region
            m = capacity_support(np.where(allowed, prob, -np.inf).astype(np.float32),
                                 allowed, 3, 1, fl)
            vals = np.where(m, 1.0, 0.0).astype(np.float32)
            fold = dict(region=region, truth=catalogue & region,
                        visible=visible, masked_known=visible)
            res, terms = eh.evaluate(vals, fold, footprint, block_side=200,
                                     origin=(0, 0), global_shape=shape)
            tag = f"buf{buf:.0f}_f{fl:.2f}"
            arms.setdefault(tag, np.zeros_like(terms))
            arms[tag] += terms
            per_fold.setdefault(tag, {})[f"fold{f}"] = dict(dti=round(res["dti"], 5),
                                                            emitted=int(m.sum()))
            dots_total[tag] = dots_total.get(tag, 0) + int(m.sum())
        print(f"  fold {f} done", flush=True)
        del d_vis, prob, region
    names = sorted(arms, key=lambda n: -eh.from_terms(arms[n].sum(axis=0)))
    summ = eh.pooled_summary({n: arms[n] for n in names}, candidate=names[0],
                             draws=600, seed=SEED)
    print()
    for n in sorted(summ["scores"], key=lambda k: -summ["scores"][k]["dti"]):
        s = summ["scores"][n]
        print(f"  HOLDOUT {n}: DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] "
              f"dots {dots_total[n]:,}", flush=True)
    out = dict(session="2026-10-31",
               evidence_class="HOLDOUT-DTI (shared pooled evaluator, quadrant instrument)",
               evaluator="gems57-pooled-hide-v2 (template, never forked)",
               caveat=("withheld truth is a catalogue fault in the held-out quadrant; a buffer "
                       "taken against the VISIBLE catalogue therefore removes little of it, so "
                       "these arms are not a test of the off-network regime"),
               arms=list(ARMS), pooled=summ["scores"], per_fold=per_fold,
               dots_total=dots_total, paired=summ.get("paired_differences"))
    (WORK / "holdout_scan6_2026_10_31.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
