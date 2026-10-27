#!/usr/bin/env python3
"""Fit and cross-validate the LBCAL hidden-fault density model.

Validation = leave-one-FAMILY-out, where families are connected components of
"support Jaccard >= 0.3" between registry rasters (so near-copies such as the
d2.8 dotted-ridge lineage can never sit on both sides of a split), and
additionally leave-one-site-out.  Baselines: constant mean, log-count
regression, catalogue-distance-only density.

Outputs: evidence/lbcal_cv.json, .cache/lbcal/model.npz
Every predicted number is an ESTIMATE (model output), not a score.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import VERSION, data as D, features as F, model as Mdl  # noqa: E402

LAMBDAS = [1e-4, 1e-3, 1e-2]
SUBSETS = {
    "d_cat_only": ("d_cat",),
    "d_cat+topo+crest+slope": ("d_cat", "topo", "crest", "slope"),
    "full": F.FEATURES,
}


def support_mask(path: Path, foot: np.ndarray) -> np.ndarray:
    p, _ = D.read_prediction(path)
    p = np.where(foot, p, 0)
    if (p >= 0.5).sum() > 0:
        m = p >= 0.5
    else:
        k = 60000
        thr = np.partition(p[foot], -k)[-k]
        m = p >= max(thr, 1e-12)
    return np.packbits(m[foot])


def families(masks: list[np.ndarray], thr: float = 0.3) -> np.ndarray:
    pop = np.array([int(np.unpackbits(m).sum()) for m in masks])
    n = len(masks)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    lut = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)
    for i in range(n):
        for j in range(i + 1, n):
            inter = int(lut[np.bitwise_and(masks[i], masks[j])].sum())
            union = pop[i] + pop[j] - inter
            if union and inter / union >= thr:
                parent[find(i)] = find(j)
    roots = [find(i) for i in range(n)]
    _, fam = np.unique(roots, return_inverse=True)
    return fam


def cv_predict(C, P, N, n_px, s, groups, M, names, lam, subset):
    pred = np.full(s.size, np.nan)
    for g in np.unique(groups):
        tr = groups != g
        fit = Mdl.fit(C[tr], P[tr], N[tr], n_px, s[tr], M, names, lam=lam, feature_subset=subset)
        y, _ = Mdl.predict(fit.beta, M, C[~tr], P[~tr], N[~tr], n_px)
        pred[~tr] = y
    return pred


def baseline_cv(s, N, groups):
    const = np.full(s.size, np.nan)
    logn = np.full(s.size, np.nan)
    for g in np.unique(groups):
        tr = groups != g
        const[~tr] = s[tr].mean()
        X = np.c_[np.ones(tr.sum()), np.log1p(N[tr])]
        b = np.linalg.lstsq(X, s[tr], rcond=None)[0]
        logn[~tr] = b[0] + b[1] * np.log1p(N[~tr])
    return const, logn


def summary(pred, s):
    err = pred - s
    top = np.argsort(-s)[:15]
    return dict(rmse=float(np.sqrt(np.mean(err ** 2))), mae=float(np.mean(np.abs(err))),
                spearman=Mdl.spearman(pred, s), pearson=float(np.corrcoef(pred, s)[0, 1]),
                spearman_top15=Mdl.spearman(pred[top], s[top]))


def main() -> int:
    t0 = time.time()
    ds = np.load(D.CACHE / "dataset.npz")
    meta = json.loads((D.CACHE / "dataset_meta.json").read_text())
    grid = D.load_grid()
    Call, Pall, n_px = ds["C"].astype(np.float64), ds["P"].astype(np.float64), ds["n_px"]
    Nall = np.array([m["N"] for m in meta])

    # scored, de-duplicated observations
    obs, dup_check = [], []
    first_by_key: dict[str, int] = {}
    for i, m in enumerate(meta):
        if m["score"] is None:
            continue
        k = m["array_sha256"]
        if k in first_by_key:
            j = first_by_key[k]
            dup_check.append(dict(a=meta[j]["site"] + "/" + meta[j]["submission"], score_a=meta[j]["score"],
                                  b=m["site"] + "/" + m["submission"], score_b=m["score"]))
            continue
        first_by_key[k] = i
        obs.append(i)
    obs = np.array(obs)
    s = np.array([meta[i]["score"] for i in obs], float)
    print(f"[obs] {obs.size} unique scored arrays; {len(dup_check)} identical-array duplicates", flush=True)
    disagree = [d for d in dup_check if abs(d["score_a"] - d["score_b"]) > 1e-4]

    masks = [support_mask(ROOT / meta[i]["local"], grid.foot) for i in obs]
    fam = families(masks)
    site = np.unique([meta[i]["site"] for i in obs], return_inverse=True)[1]
    print(f"[groups] families={fam.max()+1} sites={site.max()+1} ({time.time()-t0:.0f}s)", flush=True)

    C, P, N = Call[obs], Pall[obs], Nall[obs]
    results = {}
    const, logn = baseline_cv(s, N, fam)
    results["baseline_constant"] = summary(const, s)
    results["baseline_logcount"] = summary(logn, s)
    best = None
    for sname, subset in SUBSETS.items():
        M, names = Mdl.design_matrix(subset)
        for lam in LAMBDAS:
            pf = cv_predict(C, P, N, n_px, s, fam, M, names, lam, subset)
            key = f"{sname}|lam={lam:g}"
            results[key] = dict(family_cv=summary(pf, s))
            print(f"[cv] {key}: {results[key]['family_cv']} ({time.time()-t0:.0f}s)", flush=True)
            if best is None or results[key]["family_cv"]["rmse"] < results[best[0]]["family_cv"]["rmse"]:
                best = (key, subset, lam, pf)
    key, subset, lam, pf_best = best
    M, names = Mdl.design_matrix(subset)
    ps = cv_predict(C, P, N, n_px, s, site, M, names, lam, subset)
    results[key]["site_cv"] = summary(ps, s)
    final = Mdl.fit(C, P, N, n_px, s, M, names, lam=lam, feature_subset=subset)
    yfit, aux = Mdl.predict(final.beta, M, C, P, N, n_px)
    np.savez(D.CACHE / "model.npz", beta=final.beta, lam=lam, subset=np.array(subset), pi_cell=aux["pi"])

    # estimates for every registry raster (incl. unscored)
    yall, auxall = Mdl.predict(final.beta, M, Call, Pall, Nall, n_px)
    est_rows = []
    for i, m in enumerate(meta):
        est_rows.append(dict(site=m["site"], submission=m["submission"], sha256=m["sha256"], N=m["N"],
                             owner_reported=m["score"], lbcal_estimate=round(float(yall[i]), 4),
                             duplicate_of_row=m["duplicate_of"]))
    obs_rows = []
    for j, i in enumerate(obs):
        obs_rows.append(dict(site=meta[i]["site"], submission=meta[i]["submission"], family=int(fam[j]),
                             owner_reported=s[j], family_cv_estimate=round(float(pf_best[j]), 4),
                             site_cv_estimate=round(float(ps[j]), 4), in_sample_fit=round(float(yfit[j]), 4)))
    coef = {n: round(float(b), 4) for n, b in zip(names, final.beta)}
    out = dict(
        lane="LBCAL", version=VERSION, generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        evidence_class="ESTIMATE (model output fitted to OWNER-REPORTED public scores); not a score",
        n_unique_scored_arrays=int(obs.size), n_families=int(fam.max() + 1), n_sites=int(site.max() + 1),
        identical_array_pairs=len(dup_check), identical_arrays_with_different_scores=disagree,
        selected=dict(key=key, lam=lam, features=list(subset)),
        cv=results, coefficients=coef, implied_hidden_pixels_G=round(float(aux["G"]), 1),
        observations=obs_rows, estimates=est_rows,
    )
    (ROOT / "evidence" / "lbcal_cv.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(selected=out["selected"], cv=results[key], G=out["implied_hidden_pixels_G"]), indent=1))
    print(f"[done] {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
