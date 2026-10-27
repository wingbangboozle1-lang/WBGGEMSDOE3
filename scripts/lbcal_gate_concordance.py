#!/usr/bin/env python3
"""Experiment 3: does the owner's holdout gate track the public leaderboard?

For every unique scored registry array, evaluate the static prediction mask with
the same hide-and-recover evaluator used as the slot gate
(src/gemsw/holdout.evaluate_hide_and_recover, GEMSDOE32-HIDE-RECOVER-v3.0) and
correlate the HOLDOUT-DTI with the OWNER-REPORTED public score.  The LBCAL
family-CV estimate is correlated with the same scores for comparison.

Mask convention for soft rasters: cells >= 0.5 if any exist, else every positive
cell (literal).  Output: evidence/lbcal_gate_concordance.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import data as D, model as Mdl  # noqa: E402
from gemsw import holdout as H  # noqa: E402


def main() -> int:
    t0 = time.time()
    cv = json.loads((ROOT / "evidence" / "lbcal_cv.json").read_text())
    meta = json.loads((D.CACHE / "dataset_meta.json").read_text())
    key = {(m["site"], m["submission"]): m for m in meta}
    ctx = H.load_holdout_context(ROOT / "data" / "raw")
    print(f"[ctx] {time.time()-t0:.0f}s", flush=True)
    rows = []
    for j, r in enumerate(cv["observations"]):
        m = key[(r["site"], r["submission"])]
        p, _ = D.read_prediction(ROOT / m["local"])
        mask = (p >= 0.5) if (p >= 0.5).any() else (p > 0)
        ev = H.evaluate_hide_and_recover(mask & ctx.foot, ctx, name=r["submission"], n_boot=50)
        rows.append(dict(site=r["site"], submission=r["submission"], owner_reported=r["owner_reported"],
                         lbcal_family_cv=r["family_cv_estimate"], holdout_dti=round(ev["pooled_dti"], 5),
                         binary=m["binary"], n_pos=m["n_pos"]))
        if j % 20 == 0:
            print(f"[{j+1}/{len(cv['observations'])}] {time.time()-t0:.0f}s {r['submission'][:50]} "
                  f"holdout={ev['pooled_dti']:.4f} score={r['owner_reported']}", flush=True)
    s = np.array([r["owner_reported"] for r in rows])
    h = np.array([r["holdout_dti"] for r in rows])
    l = np.array([r["lbcal_family_cv"] for r in rows])
    b = np.array([r["binary"] for r in rows])
    top = np.argsort(-s)[:20]
    out = dict(
        evidence_class="REGISTRY-MEASUREMENT (holdout on hash-pinned bytes) vs OWNER-REPORTED public scores",
        evaluator=H.HIDE_RECOVER_EVALUATOR_VERSION, n=len(rows), n_binary=int(b.sum()),
        spearman_holdout_vs_score=Mdl.spearman(h, s), spearman_holdout_vs_score_binary_only=Mdl.spearman(h[b], s[b]),
        spearman_holdout_vs_score_top20=Mdl.spearman(h[top], s[top]),
        spearman_lbcal_cv_vs_score=Mdl.spearman(l, s), spearman_lbcal_cv_vs_score_top20=Mdl.spearman(l[top], s[top]),
        best_holdout_file=rows[int(np.argmax(h))], best_score_file=rows[int(np.argmax(s))],
        rows=rows,
    )
    (ROOT / "evidence" / "lbcal_gate_concordance.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
