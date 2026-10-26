#!/usr/bin/env python3
"""EXP1+EXP2: screen every independent field against the live ledger, select a sparse set with NESTED grouped CV,
quote honest projection error, and save the fitted hidden-truth density model.

HOLDOUT label for this experiment = LEDGER-CV (leave-one-site-family-out over OWNER-REPORTED live scores).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import ledger as L, features as F

W = ROOT / "data/work"
d = np.load(W / "design.npz", allow_pickle=True)
A, B, N, S, s, names = d["A"], d["B"], d["N"], d["S"], d["s"], list(d["names"])
meta = json.load(open(W / "design_meta.json"))
nb = A.shape[2]
nuis = [i for i, n in enumerate(names) if n == "NUIS_catxH"]   # product stratum = LLI-S0-style nuisance baseline
feat = [i for i, n in enumerate(names) if not n.startswith("NUIS_")]


def cols_for(fields):
    return [(f, b) for f in fields for b in range(nb) if S[f, b] > 0]


def mae_sp(pred, idx=None):
    idx = np.arange(len(s)) if idx is None else idx
    return float(np.mean(np.abs(pred[idx] - s[idx]))), float(spearmanr(pred[idx], s[idx])[0])


# groups: leave-SITE-out (site = submitting repo/lineage label) so that folds are not dominated by one family
site = np.array([m["site"] for m in meta])
fam = np.unique(site, return_inverse=True)[1]
sizes_ = np.bincount(fam)
# greedy balanced assignment of sites to 8 outer folds (largest first)
fold_load = np.zeros(8); fold_of = {}
for g_ in np.argsort(-sizes_):
    k_ = int(np.argmin(fold_load)); fold_of[g_] = k_; fold_load[k_] += sizes_[g_]
outer = np.array([fold_of[g_] for g_ in fam])
print("rasters", len(s), "sites", len(sizes_), "outer fold sizes", np.bincount(outer))


def cv_pred(fields, ridge, groups):
    return L.loo(A, B, N, S, s, cols_for(fields), ridge, groups=groups)


t0 = time.time()
res = {"n_rasters": int(len(s)), "families": int(len(np.unique(fam))), "evaluator": "LST-v1 ledger-CV (owner-reported scores)"}
# ---- baseline nuisance-only model, ridge by leave-one-out ----
best = None
for r in (1e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0):
    p = cv_pred(nuis, r, None)
    m, sp = mae_sp(p)
    print(f"stratum-only ridge={r:g} LOO MAE={m:.4f} spearman={sp:.3f}")
    if best is None or m < best[0]:
        best = (m, sp, r)
RIDGE = best[2]
p0_loo = cv_pred(nuis, RIDGE, None); p0_fam = cv_pred(nuis, RIDGE, fam)
res["baseline_nuisance_only"] = dict(ridge=RIDGE, loo_mae=mae_sp(p0_loo)[0], loo_spearman=mae_sp(p0_loo)[1],
                                      family_cv_mae=mae_sp(p0_fam)[0], family_cv_spearman=mae_sp(p0_fam)[1])
top = np.argsort(-s)[:20]
res["baseline_nuisance_only"]["family_cv_mae_top20"] = mae_sp(p0_fam, top)[0]

# ---- per-field screening: nuisance + one field ----
scr = []
for f in feat:
    p = cv_pred(nuis + [f], RIDGE, fam)
    m, sp = mae_sp(p)
    lam = L.fit(A, B, N, S, s, cols_for(nuis + [f]), RIDGE)
    cols = cols_for(nuis + [f])
    # top-bin enrichment: lambda in the two highest bins relative to the field's mean density
    lf = {c: lam[i] for i, c in enumerate(cols) if c[0] == f}
    sz = {b: S[f, b] for b in range(nb)}
    mean_l = sum(lf.get((f, b), 0) * sz[b] for b in range(nb)) / max(sum(sz.values()), 1)
    hi = [b for b in (8, 9) if sz[b] > 0]
    enr_hi = (sum(lf.get((f, b), 0) * sz[b] for b in hi) / max(sum(sz[b] for b in hi), 1)) / max(mean_l, 1e-12)
    lo = [b for b in (1, 2) if sz[b] > 0]
    enr_lo = (sum(lf.get((f, b), 0) * sz[b] for b in lo) / max(sum(sz[b] for b in lo), 1)) / max(mean_l, 1e-12)
    scr.append(dict(field=names[f], idx=int(f), fam_cv_mae=m, fam_cv_spearman=sp,
                    d_mae_vs_nuisance=m - res["baseline_nuisance_only"]["family_cv_mae"],
                    enrich_top4pct=float(enr_hi), enrich_bottom5pct=float(enr_lo)))
scr.sort(key=lambda r: r["d_mae_vs_nuisance"])
res["screening"] = scr
for r in scr[:12]:
    print(f"{r['field']:34s} dMAE={r['d_mae_vs_nuisance']:+.4f} sp={r['fam_cv_spearman']:.3f} enr_top={r['enrich_top4pct']:.2f} enr_bot={r['enrich_bottom5pct']:.2f}")
print(f"screening done {time.time()-t0:.0f}s")


# ---- forward selection (greedy by family-CV MAE), max K fields ----
def forward(train_mask, kmax=6, ridge=RIDGE, inner_groups=None):
    chosen = []
    cur = None
    for _ in range(kmax):
        bestf = None
        for f in feat:
            if f in chosen:
                continue
            idx = np.flatnonzero(train_mask)
            sub = dict(A=A[idx], B=B[idx], N=N[idx], s=s[idx])
            p = L.loo(sub["A"], sub["B"], sub["N"], S, sub["s"], cols_for(nuis + chosen + [f]), ridge, groups=inner_groups[idx])
            m = float(np.mean(np.abs(p - sub["s"])))
            if bestf is None or m < bestf[0]:
                bestf = (m, f)
        if cur is not None and bestf[0] > cur - 1e-5:
            break
        chosen.append(bestf[1]); cur = bestf[0]
    return chosen


# honest nested estimate: outer folds by family; selection uses ONLY the outer-training rasters
nested = np.zeros(len(s)); sel_sets = []
for k in range(8):
    te = outer == k
    ch = forward(~te, kmax=4, inner_groups=fam)
    sel_sets.append([names[i] for i in ch])
    lam = L.fit(A[~te], B[~te], N[~te], S, s[~te], cols_for(nuis + ch), RIDGE)
    cols = cols_for(nuis + ch)
    for i in np.flatnonzero(te):
        nested[i] = L.project(lam, cols, A[i], B[i], N[i], S)["dti"]
    print(f"outer fold {k}: selected {[names[i] for i in ch]}  t={time.time()-t0:.0f}s", flush=True)
m, sp = mae_sp(nested)
res["nested_family_cv"] = dict(mae=m, spearman=sp, mae_top20=mae_sp(nested, top)[0],
                               abs_err_q90=float(np.quantile(np.abs(nested - s), 0.9)), selections=sel_sets,
                               baseline_mae=res["baseline_nuisance_only"]["family_cv_mae"])
print("NESTED family-CV: MAE=%.4f spearman=%.3f (baseline nuisance-only %.4f)" % (m, sp, res["baseline_nuisance_only"]["family_cv_mae"]))

# ---- final model on all rasters ----
final = forward(np.ones(len(s), bool), kmax=5, inner_groups=fam)
# parsimony rule fixed in advance: keep fields ONLY if nested leave-site-out MAE beats the stratum-only baseline by >= 0.001
fields_help = (res["nested_family_cv"]["baseline_mae"] - res["nested_family_cv"]["mae"]) >= 0.001
res["fields_identified_by_ledger"] = bool(fields_help)
if not fields_help:
    print("VERDICT (ledger-field supervision): NEGATIVE - fields do not beat the stratum-only baseline; final model = stratum only")
    final = []
cols = cols_for(nuis + final)
lam = L.fit(A, B, N, S, s, cols, RIDGE)
insample = np.array([L.project(lam, cols, A[i], B[i], N[i], S)["dti"] for i in range(len(s))])
res["final"] = dict(fields=[names[i] for i in final], ridge=RIDGE, in_sample_mae=mae_sp(insample)[0],
                    in_sample_spearman=mae_sp(insample)[1],
                    g_hat=float(sum(lam[i] * S[c] for i, c in enumerate(cols))))
res["per_raster"] = [dict(submission=m_["submission"], site=m_["site"], live=float(s[i]), fit=float(insample[i]),
                          nested_cv=float(nested[i])) for i, m_ in enumerate(meta)]
# bootstrap of the (stratum-only) fit: lower-confidence-bound lambdas stop the allocator exploiting noisy maxima
boot = []
rngb = np.random.default_rng(123)
cs = cols_for(nuis)
for _ in range(200):
    ib = rngb.integers(0, len(s), len(s))
    lb = L.fit(A[ib], B[ib], N[ib], S, s[ib], cs, RIDGE)
    tab = np.zeros(nb)
    for (f_, b_), v_ in zip(cs, lb):
        tab[b_] = v_
    boot.append(tab)
boot = np.array(boot)
res["bootstrap"] = dict(n=200, lam_q25_total_mass=float((np.quantile(boot, 0.25, axis=0) * S[nuis[0]]).sum()),
                        lam_q50_total_mass=float((np.quantile(boot, 0.5, axis=0) * S[nuis[0]]).sum()),
                        lam_q75_total_mass=float((np.quantile(boot, 0.75, axis=0) * S[nuis[0]]).sum()))
np.savez(W / "lst_model.npz", lam_boot=boot, lam=lam, cols=np.array(cols), fields=np.array([names[i] for i in nuis + final]),
         field_idx=np.array(nuis + final), ridge=RIDGE, resid_q=np.quantile(np.abs(nested - s), [0.5, 0.8, 0.9, 0.95]))
json.dump(res, open(ROOT / "evidence/lst_fit.json", "w"), indent=1)
print("FINAL fields:", res["final"]["fields"], "in-sample MAE %.4f" % res["final"]["in_sample_mae"], f"t={time.time()-t0:.0f}s")
