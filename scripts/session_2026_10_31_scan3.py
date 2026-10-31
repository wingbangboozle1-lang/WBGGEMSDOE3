#!/usr/bin/env python3
"""Emission-density scan: how many dots per neighbourhood, and where.

Session 2026-10-31.  Re-uses the cached leave-one-quadrant-out probability
surfaces and the pinned shared evaluator (gems57.evaluate_holdout).

The previous scan showed the winning geometry is "one dot per neighbourhood,
spread out" (NMS spacing 1 beats spacing 2 and 3, and beats un-thinned top-N).
This scan asks the next question: given that neighbourhood rule, what CAPACITY
per neighbourhood maximises the official DTI?  Capacity is enforced by counting
already-accepted dots inside a b x b window (kings-block RSA with capacity c).

Evidence class: HOLDOUT-DTI.
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
from session_2026_10_31_holdout import QUAD_NAMES  # noqa: E402

SEED = 20261031


def capacity_support(score: np.ndarray, region: np.ndarray, block: int, cap: int,
                     floor: float | None = None) -> np.ndarray:
    """Greedy highest-score cells with at most `cap` accepted dots per b x b window.

    `count[cy, cx]` = number of accepted dots inside the b x b window centred on
    (cy, cx).  A candidate (y, x) is accepted only when every window that would
    contain it (centres within r = b//2 of it) is still below capacity, and
    accepting it increments exactly those windows.
    """
    s = np.where(region, score, -np.inf)
    idx = np.flatnonzero(region & np.isfinite(score))
    if idx.size == 0:
        return np.zeros(score.shape, bool)
    order = idx[np.argsort(-s.ravel()[idx], kind="stable")]
    if floor is not None:
        order = order[: int(np.searchsorted(-s.ravel()[order], -float(floor), side="right"))]
    h, w = score.shape
    r = int(block // 2)
    accepted = np.zeros(score.size, bool)
    count = np.zeros(score.shape, np.int16)
    for lin in order:
        y, x = divmod(int(lin), w)
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        if count[y0:y1, x0:x1].max() >= cap:
            continue
        accepted[lin] = True
        count[y0:y1, x0:x1] += 1
    return accepted.reshape(score.shape)


def main() -> int:
    z = np.load(WORK / "fold_probs_2026_10_31.npz")
    footprint, catalogue = z["footprint"], z["catalogue"]
    shape = footprint.shape
    rng = np.random.default_rng(SEED + 1)
    uniform = rng.random(shape).astype(np.float32)

    grid = [(3, 1, None), (3, 2, None), (3, 3, None), (3, 4, None),
            (5, 3, None), (5, 5, None), (5, 8, None),
            (3, 2, 0.10), (3, 3, 0.10), (3, 4, 0.10), (5, 5, 0.10)]

    arms: dict[str, np.ndarray] = {}
    per_fold: dict[str, dict] = {}
    for f in range(4):
        prob, region = z[f"prob{f}"], z[f"region{f}"]
        truth = catalogue & region
        fold = dict(region=region, truth=truth, visible=catalogue & ~region,
                    masked_known=catalogue & ~region)
        cand: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for b, c, floor in grid:
            m = capacity_support(prob, region, b, c, floor)
            tag = f"cap{b}x{b}_c{c}" + ("" if floor is None else f"_f{floor:.2f}")
            cand[tag] = (m, np.where(m, 1.0, 0.0).astype(np.float32))
        from session_2026_10_31_holdout import greedy_support
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
        print(f"fold {f}: {len(cand)} arms", flush=True)

    names = sorted(arms, key=lambda n: -eh.from_terms(arms[n].sum(axis=0)))
    ref = names[0]
    summary = eh.pooled_summary({n: arms[n] for n in names}, candidate=ref,
                                draws=600, seed=SEED)
    out = dict(session="2026-10-31", evidence_class="HOLDOUT-DTI",
               evaluator_version=eh.VERSION, per_fold=per_fold,
               pooled=summary["scores"],
               paired_differences_vs_best=summary.get("paired_differences"),
               bootstrap=summary["bootstrap"])
    (WORK / "holdout_scan3_2026_10_31.json").write_text(json.dumps(out, indent=1))
    print(f"\n=== pooled (best = {ref}) ===")
    for n, s in sorted(summary["scores"].items(), key=lambda kv: -kv[1]["dti"]):
        tot = sum(v["emitted"] for v in per_fold[n].values())
        dens = tot / 4_885_941
        print(f"  {n:24s} DTI {s['dti']:.4f} [{s['ci95'][0]:.4f}, {s['ci95'][1]:.4f}] "
              f"tp {s['tpw']:7.0f} fp {s['fpw']:8.0f} dots {tot:>7,} ({dens*100:.1f}%)")
    print("\n--- paired differences vs best ---")
    for n, v in sorted(summary["paired_differences"].items(), key=lambda kv: -kv[1]["delta"]):
        print(f"  {n:24s} delta {v['delta']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
