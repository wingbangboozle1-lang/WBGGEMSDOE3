#!/usr/bin/env python3
"""Physically-bounded LBCAL variants (pre-registered after the unbounded fit saturated).

The unbounded log-link fit (lbcal_fit.py, lam=1e-4) predicts held-out families
well but drives pi to the clip value 1.0 on ~5k pixels -- a physically
implausible density that a dot optimiser would exploit.  This script re-runs the
same leave-one-family-out CV for bounded links pi = pi_max * sigmoid(eta) and
selects, among variants with pi_max <= 0.2, the lowest family-CV RMSE.  The
selection rule was fixed before the variants were run (see
knowledge/preregistration-2026-10-27-lbcal.md).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import data as D, features as F, model as Mdl  # noqa: E402

VARIANTS = [(None, 1e-4), (0.2, 1e-4), (0.1, 1e-4), (0.05, 1e-4), (0.1, 1e-3)]
N_FOLDS = 10  # families are randomly grouped into 10 folds (seed 20261027) to bound run time


def main() -> int:
    t0 = time.time()
    cv = json.loads((ROOT / "evidence" / "lbcal_cv.json").read_text())
    ds = np.load(D.CACHE / "dataset.npz")
    meta = json.loads((D.CACHE / "dataset_meta.json").read_text())
    key = {(m["site"], m["submission"]): i for i, m in enumerate(meta)}
    obs = np.array([key[(r["site"], r["submission"])] for r in cv["observations"]])
    fam = np.array([r["family"] for r in cv["observations"]])
    s = np.array([r["owner_reported"] for r in cv["observations"]], float)
    C, P, n_px = ds["C"][obs].astype(float), ds["P"][obs].astype(float), ds["n_px"]
    N = np.array([meta[i]["N"] for i in obs])
    M, names = Mdl.design_matrix()
    keep = (n_px > 0) | (C.sum(0) > 0) | (P.sum(0) > 0)   # drop empty joint cells (exact)
    M, C, P, n_px = M[keep], C[:, keep], P[:, keep], n_px[keep]
    rng = np.random.default_rng(20261027)
    fam_ids = np.unique(fam)
    fold_of_fam = dict(zip(fam_ids, rng.permutation(len(fam_ids)) % N_FOLDS))
    fold = np.array([fold_of_fam[f] for f in fam])
    out = {}
    for pi_max, lam in VARIANTS:
        full = Mdl.fit(C, P, N, n_px, s, M, names, lam=lam, pi_max=pi_max)
        pred = np.full(s.size, np.nan)
        for g in range(N_FOLDS):
            tr = fold != g
            f = Mdl.fit(C[tr], P[tr], N[tr], n_px, s[tr], M, names, lam=lam, pi_max=pi_max)
            pred[~tr] = Mdl.predict(f.beta, M, C[~tr], P[~tr], N[~tr], n_px, pi_max=pi_max)[0]
        y, aux = Mdl.predict(full.beta, M, C, P, N, n_px, pi_max=pi_max)
        pic = aux["pi"]
        err = pred - s
        top = np.argsort(-s)[:15]
        k = f"pi_max={pi_max}|lam={lam:g}"
        out[k] = dict(pi_max=pi_max, lam=lam, cv_scheme=f"{N_FOLDS}-fold grouped by support-Jaccard family",
                      fit_converged=bool(full.success),
                      family_cv=dict(rmse=float(np.sqrt(np.mean(err ** 2))), mae=float(np.mean(np.abs(err))),
                                     spearman=Mdl.spearman(pred, s), pearson=float(np.corrcoef(pred, s)[0, 1]),
                                     spearman_top15=Mdl.spearman(pred[top], s[top])),
                      G=float(aux["G"]), pixels_pi_ge_half_max=int(n_px[pic >= 0.5 * (pi_max or 1.0)].sum()),
                      beta=[float(b) for b in full.beta], cv_pred=[float(v) for v in pred])
        print(f"[{time.time()-t0:.0f}s] {k}: {out[k]['family_cv']} G={aux['G']:.0f} "
              f"px>=pimax/2={out[k]['pixels_pi_ge_half_max']}", flush=True)
    eligible = {k: v for k, v in out.items() if v["pi_max"] is not None and v["pi_max"] <= 0.2}
    best = min(eligible, key=lambda k: eligible[k]["family_cv"]["rmse"])
    res = dict(evidence_class="ESTIMATE model-selection record (OWNER-REPORTED scores as targets)",
               keep_cells_note=f"{int(keep.sum())} non-empty joint cells (n_px>0) used; list omitted",
               unbounded_reference=cv["cv"][cv["selected"]["key"]]["family_cv"],
               selection_rule="lowest leave-one-family-out RMSE among pi_max <= 0.2",
               selected=best, variants=out, names=names)
    (ROOT / "evidence" / "lbcal_variants.json").write_text(json.dumps(res, indent=1) + "\n")
    print("[selected]", best, out[best]["family_cv"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
