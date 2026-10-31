#!/usr/bin/env python3
"""Refinement scan: emission surface x NMS geometry x probability floor.

Session 2026-10-31.  Re-uses the cached leave-one-quadrant-out probability
surfaces (`scripts/session_2026_10_31_holdout.py --fit`) and the pinned shared
evaluator.  Evidence class: HOLDOUT-DTI.
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
from session_2026_10_31_holdout import greedy_support, QUAD_NAMES  # noqa: E402

SEED = 20261031


def surfaces(prob: np.ndarray, region: np.ndarray) -> dict[str, np.ndarray]:
    p = np.where(region, prob, 0.0).astype(np.float32)
    out = {"raw": p}
    out["mean3"] = ndi.uniform_filter(p, size=3, mode="nearest").astype(np.float32)
    out["mean5"] = ndi.uniform_filter(p, size=5, mode="nearest").astype(np.float32)
    out["max5"] = ndi.maximum_filter(p, size=5, mode="nearest").astype(np.float32)
    return out


def main() -> int:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    rng = np.random.default_rng(SEED + 1)
    uniform = rng.random(shape).astype(np.float32)

    grid = [("raw", sp, None) for sp in (1, 2, 3)]
    grid += [("mean3", sp, None) for sp in (1, 2, 3)]
    grid += [("mean5", 2, None), ("max5", 2, None)]
    grid += [("raw", 2, 0.05), ("raw", 2, 0.10), ("raw", 2, 0.20), ("raw", 2, 0.35)]

    arms: dict[str, np.ndarray] = {}
    per_fold: dict[str, dict] = {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        truth = catalogue & region
        fold = dict(region=region, truth=truth, visible=catalogue & ~region,
                    masked_known=catalogue & ~region)
        surf = surfaces(prob, region)
        cand: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for sname, sp, floor in grid:
            s = np.where(region, surf[sname], -np.inf).astype(np.float32)
            m = greedy_support(s, region, None, floor, sp)
            tag = f"{sname}_nms{sp}" + ("" if floor is None else f"_f{floor:.2f}")
            cand[tag] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
        for tag in list(cand):
            m = cand[tag][0]
            u = greedy_support(np.where(region, uniform, -np.inf), region,
                               int(m.sum()), None, 0)
            cand[tag + "__randmatch"] = (u, np.where(u, 1.0, 0.0).astype(np.float32))
        for tag, (m, vals) in cand.items():
            res, terms = eh.evaluate(vals, fold, footprint, block_side=200,
                                     origin=(0, 0), global_shape=shape)
            arms.setdefault(tag, np.zeros_like(terms))
            arms[tag] += terms
            per_fold.setdefault(tag, {})[QUAD_NAMES[f]] = dict(
                dti=round(res["dti"], 5), emitted=int(m.sum()))
        print(f"fold {f} done: {len(cand)} arms", flush=True)

    names = sorted(arms, key=lambda n: -eh.from_terms(arms[n].sum(axis=0)))
    ref = names[0]
    summary = eh.pooled_summary({n: arms[n] for n in names}, candidate=ref,
                                draws=600, seed=SEED)
    out = dict(session="2026-10-31", evidence_class="HOLDOUT-DTI",
               evaluator_version=eh.VERSION, per_fold=per_fold,
               pooled=summary["scores"],
               paired_differences_vs_best=summary.get("paired_differences"),
               bootstrap=summary["bootstrap"],
               implementation_sha256=summary["implementation_sha256"])
    (WORK / "holdout_scan2_2026_10_31.json").write_text(json.dumps(out, indent=1))
    print(f"\n=== pooled (best = {ref}) ===")
    for n, s in sorted(summary["scores"].items(), key=lambda kv: -kv[1]["dti"]):
        tot = sum(v["emitted"] for v in per_fold[n].values())
        print(f"  {n:26s} DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] "
              f"tp {s['tpw']:7.0f} fp {s['fpw']:8.0f} dots {tot:>7,}")
    print("\n--- paired differences vs best (selected) ---")
    for n, v in sorted(summary["paired_differences"].items(), key=lambda kv: -kv[1]["delta"]):
        if n.endswith("__randmatch") or "nms2" in n:
            print(f"  {n:26s} delta {v['delta']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
