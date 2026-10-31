#!/usr/bin/env python3
"""Calibrate a score estimator for a dot-map submission from public information only.

Inputs (all hash-pinned, nothing private):
  * 117-118 sibling submission rasters + their OWNER-REPORTED public scores
    (`registry/upstream_live_ledger_rasters.json`, bytes in `data/ledger/`);
  * the USGS SGMC external fault catalogue restricted to cells >300 m from every
    public-catalogue cell -- the population the organiser's experts annotated
    ("faults the catalogue missed");
  * the official DTI algebra (alpha=0.2, beta=0.8, R=300 m, kernel max over dots).

Model. For a submitted field with dot mass m and proxy credit rate h_p = TP_w^proxy/m,
assume the hidden-set rate is h_g = a*h_p and that the false-positive mass is a fraction
kappa of m, so

    T = a*h_p*m,   FP = kappa*m,   DTI = T / (0.2*(T + FP) + 0.8*K)

with three scalars (a, kappa, K) fitted to the sibling reports. K is the effective hidden
truth count in the scored chunks; a and kappa absorb the density and geometry mismatch
between the proxy and the private labels.

Honesty contract: the fit is validated by GROUPED cross-validation over sites (no two
rows from the same site share train and test). The estimator is an ESTIMATE, its CV MAE is
printed next to every number it produces, and it is never labelled a score.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import minimize
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe import config as C          # noqa: E402
from gemsdoe import io as gio             # noqa: E402
from gemsdoe import uniqueness as U       # noqa: E402
import importlib                          # noqa: E402

V = importlib.import_module("gemsdoe.validation")
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


def main() -> int:
    footprint = gio.read_footprint()
    catalogue = gio.read_labels() & footprint
    gt = V.sgmc_only_gt(footprint)
    k_map = np.clip(1.0 - ndi.distance_transform_edt(~gt) / C.RADIUS_PX, 0.0, 1.0).astype(np.float32)
    log(f"proxy positives {int(gt.sum()):,}")

    rows = [r for r in json.loads((ROOT / "registry" / "upstream_live_ledger_rasters.json").read_text())["rows"]
            if r.get("status") == "ok"]
    P = []
    for r in rows:
        p = ROOT / "data" / "ledger" / f"{r['site']}__{Path(r['path']).name}"
        if not p.exists():
            continue
        a = U.load_mask(p)
        sup = (a > 0) & footprint
        m = int(sup.sum())
        if m == 0:
            continue
        tp = float(k_map[sup].sum())
        P.append(dict(site=r["site"], name=r["submission"], reported=float(r["score"]),
                      mass=float(m), h=tp / m, on_cat=int((sup & catalogue).sum()) / m,
                      sha=r["sha256"]))
    log(f"probes {len(P)}")

    h = np.array([p["h"] for p in P]); m = np.array([p["mass"] for p in P])
    obs = np.array([p["reported"] for p in P]); occ = np.array([p["on_cat"] for p in P])
    mass_frac = m / float(footprint.sum())

    def predict(theta, hh, mm, oc):
        a, kap, logK, b = theta
        K = np.exp(logK)
        T = np.clip(a * hh + b * oc, 0.0, 1.0) * mm
        return T / (C.ALPHA * (T + kap * mm) + C.BETA * K + C.EPS)

    def loss(theta, i):
        return float(np.abs(predict(theta, h[i], m[i], occ[i]) - obs[i]).mean())

    best = None
    for a0 in (0.3, 0.6, 1.0):
        for kap0 in (0.5, 0.9, 1.3):
            for lk in (8.5, 9.5, 10.5, 11.5):
                th = np.array([a0, kap0, lk, 0.0])
                r = minimize(loss, th, args=(np.arange(len(P)),), method="Nelder-Mead",
                             options=dict(maxiter=4000, xatol=1e-3, fatol=1e-6))
                if best is None or r.fun < best.fun:
                    best = r
    th = best.x
    fitted = predict(th, h, m, occ)
    full = dict(mae=round(float(np.abs(fitted - obs).mean()), 5),
                rmse=round(float(np.sqrt(((fitted - obs) ** 2).mean())), 5),
                spearman=round(float(spearmanr(fitted, obs).statistic), 4),
                r2=round(float(1 - ((fitted - obs) ** 2).sum() / ((obs - obs.mean()) ** 2).sum()), 4),
                bias=round(float((fitted - obs).mean()), 5),
                max_abs=round(float(np.abs(fitted - obs).max()), 4))
    sites = sorted({p["site"] for p in P})
    errs, preds, obsd = [], [], []
    for s in sites:
        te = np.array([i for i, p in enumerate(P) if p["site"] == s])
        tr = np.array([i for i, p in enumerate(P) if p["site"] != s])
        r = minimize(loss, th, args=(tr,), method="Nelder-Mead", options=dict(maxiter=2500))
        pr = predict(r.x, h[te], m[te], occ[te])
        errs.append(np.abs(pr - obs[te])); preds.append(pr); obsd.append(obs[te])
    e = np.concatenate(errs)
    cv = dict(mae=round(float(e.mean()), 5), rmse=round(float(np.sqrt((e ** 2).mean())), 5),
              p90_abs=round(float(np.percentile(e, 90)), 4), max_abs=round(float(e.max()), 4),
              n=len(P), n_groups=len(sites),
              spearman=round(float(spearmanr(np.concatenate(preds), np.concatenate(obsd)).statistic), 4),
              note="leave-one-site-out; rows from the same site never share train and test")
    out = dict(model="DTI = T/(0.2*(T+kappa*m)+0.8*K), T = (a*h_proxy + b*frac_on_catalogue)*m",
               params=dict(a=round(float(th[0]), 5), kappa=round(float(th[1]), 5),
                           K_px=round(float(np.exp(th[2])), 1), b=round(float(th[3]), 5)),
               n_probes=len(P), in_sample=full, site_grouped_cv=cv,
               observed=dict(min=float(obs.min()), max=float(obs.max()), median=float(np.median(obs))),
               estimator_version="gems-3param-ledger-calib-v1",
               evidence_class="LEDGER CALIBRATION on owner-reported scores (no organizer receipts)",
               utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def estimate(hit_rate: float, n_dots: int, on_cat_frac: float = 0.0) -> dict:
        mm = np.array([float(n_dots)])
        oc = np.array([float(on_cat_frac)])
        v = float(predict(th, np.array([hit_rate]), mm, oc)[0])
        lo = float(predict(th, np.array([hit_rate * 0.8]), mm, oc)[0])
        hi = float(predict(th, np.array([min(1.0, hit_rate * 1.25)]), mm, oc)[0])
        return dict(estimate=round(v, 4),
                    cv_band=[round(max(0.0, v - cv["mae"]), 4), round(v + cv["mae"], 4)],
                    h_sensitivity_band=[round(min(lo, hi), 4), round(max(lo, hi), 4)],
                    inputs=dict(hit_rate=round(hit_rate, 5), n_dots=int(n_dots),
                                on_catalogue_frac=round(float(on_cat_frac), 5)),
                    label="LEDGER-CALIBRATED ESTIMATE", not_a_score=True)

    (ROOT / "evidence" / "score_estimator.json").write_text(json.dumps(out, indent=1) + "\n")
    log(f"fit a={th[0]:.3f} kappa={th[1]:.3f} K={np.exp(th[2]):,.0f} b={th[3]:.3f}")
    log(f"in-sample {json.dumps(full)}")
    log(f"site-grouped CV {json.dumps(cv)}")

    # reference estimates for the nine focus sites so the table is comparable
    ref = {}
    for p in P:
        ref.setdefault(p["site"], []).append(dict(name=p["name"], reported=p["reported"],
                                                  n_dots=int(p["mass"]), h=round(p["h"], 5),
                                                  **estimate(p["h"], int(p["mass"]), p["on_cat"])))
    (ROOT / "evidence" / "ledger_probe_estimates.json").write_text(
        json.dumps(dict(estimator=out, per_site=ref), indent=1) + "\n")
    log("wrote evidence/score_estimator.json + evidence/ledger_probe_estimates.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
