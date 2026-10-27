#!/usr/bin/env python3
"""Finalise the WBGGEMSDOE3 discovery submission end to end.

Steps (all automatic, no human inspection):
  1. verify the official rasters against their pinned SHA-256
  2. build the two independent lineament scores and their union support
  3. measure the external-catalogue proxy profile + bootstrap CI
  4. estimate the leaderboard score with the calibrated metric model
  5. uniqueness audit against every archived and focus-site raster on disk
  6. write the GeoTIFF + zip, and re-validate the *saved bytes*
  7. write evidence JSONs consumed by the site

Every number written here is labelled HOLDOUT/PROXY/ESTIMATE or ORGANIZER-REPORTED.
No proxy value is ever reported as a competition score.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsdoe import config as C          # noqa: E402
from src.gemsdoe import emit as E            # noqa: E402
from src.gemsdoe import io as gio            # noqa: E402
from src.gemsdoe import metric as M          # noqa: E402
from src.gemsdoe import pipeline as P        # noqa: E402
from src.gemsdoe import uniqueness as U      # noqa: E402
from src.gemsdoe import validation as V      # noqa: E402

SUB_DIR = ROOT / "submission"
EV_DIR = ROOT / "evidence"
DOC_DATA = ROOT / "docs" / "data"
FOCUS = ROOT / ".cache" / "focus"


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gt_bootstrap(pred, gt, valid, mass, m_fit, n_boot=300, seed=5) -> dict:
    """Bootstrap over connected GT components -> CI on proxy DTI and on the estimate."""
    lab, n = __import__("scipy.ndimage", fromlist=["label"]).label(gt, structure=np.ones((3, 3), bool))
    ev = M.FastDTI(gt, valid=valid)
    cred = ev.credit_vector(pred)
    rows, cols = np.nonzero(gt)
    comp_of_px = lab[rows, cols]
    fp = float(np.sum(np.where(valid, pred, 0.0) * ev.far, dtype=np.float64))
    ids = np.arange(1, n + 1)
    order = np.argsort(comp_of_px, kind="stable")
    starts = np.searchsorted(comp_of_px[order], ids)
    ends = np.searchsorted(comp_of_px[order], ids, side="right")
    sizes = ends - starts
    rng = np.random.default_rng(seed)
    nonempty = np.nonzero(sizes > 0)[0]
    outc_dti, out_est = [], []
    for _ in range(n_boot):
        pick = rng.choice(nonempty, size=nonempty.size, replace=True)
        tp = float(sum(cred[order[starts[i]:ends[i]]].sum() for i in pick))
        ntn = float(sum(sizes[i] for i in pick))
        dti = tp / (C.ALPHA * (tp + fp) + C.BETA * ntn + C.EPS)
        h = tp / max(mass, 1e-9)
        outc_dti.append(dti)
        out_est.append(V.score_from_profile(h, mass, m_fit))
    f = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {"dti_proxy_ci95": f(outc_dti), "estimate_ci95": f(out_est),
            "n_gt_components": int((sizes > 0).sum())}


def main() -> int:
    EV_DIR.mkdir(exist_ok=True)
    DOC_DATA.mkdir(parents=True, exist_ok=True)
    SUB_DIR.mkdir(exist_ok=True)

    print("== 1. official data integrity")
    hashes = gio.verify_official_data(strict=True)
    for k, v in hashes.items():
        print(f"   {k:24s} sha256 {v['sha256'][:16]}... pin_match={v['matches_pin']}")

    print("== 2. build scores + support")
    B = P.build_all()

    print("== 3. proxy profile + calibration")
    valid = gio.read_footprint()
    gt = V.sgmc_only_gt(valid)
    obs = V.build_reported_observations(valid, gt)
    fit = V.fit_gt_size(obs, robust=True)
    m_fit = fit["M_trimmed"]
    print(f"   |G| fitted = {m_fit:.0f} px  (robust, {fit['n_used']}/{fit['n_total']} files, "
          f"LOO rms {fit['loo_rms']:.4f})")

    support = B["support"]
    pred = E.emit(np.zeros((C.HEIGHT, C.WIDTH), np.float32), support, level=1.0)
    pr = V.profile(pred, gt, valid)
    est = V.score_from_profile(pr["hit_rate"], pr["mass"], m_fit)
    boot = gt_bootstrap(pred, gt, valid, pr["mass"], m_fit)
    print(f"   proxy: mass={pr['mass']:.0f} h={pr['hit_rate']:.4f} capture={pr['capture']:.3f} "
          f"DTI_proxy={pr['dti_proxy']:.4f}")
    print(f"   ESTIMATE {est:.4f}  95%CI {boot['estimate_ci95']}")

    sens = {str(int(m)): round(V.score_from_profile(pr["hit_rate"], pr["mass"], m), 4)
            for m in (8430, m_fit, 22938, 30000)}

    print("== 4. per-site estimates (organizer-reported vs calibrated estimate)")
    site_rows = []
    focus_reg = json.loads((ROOT / "registry" / "focus_sites.json").read_text())
    for s in focus_reg["sites"]:
        site = s["site"]
        p = FOCUS / (site + "__" + Path(s["path"]).name)
        if not p.exists():
            site_rows.append({"site": site, "file": Path(s["path"]).name,
                              "organizer_reported": s["owner_reported"], "status": "file_not_fetched"})
            continue
        a = U.load_mask(p)
        prof = V.profile(a, gt, valid)
        est_site = V.score_from_profile(prof["hit_rate"], prof["mass"], m_fit)
        site_rows.append({
            "site": site, "file": Path(s["path"]).name,
            "download_sha256": sha256_file(p),
            "organizer_reported": s["owner_reported"],
            "estimated": round(est_site, 4),
            "estimate_minus_reported": round(est_site - float(s["owner_reported"]), 4),
            "mass_px": int(prof["mass"]), "proxy_hit_rate": round(prof["hit_rate"], 6),
            "proxy_dti": round(prof["dti_proxy"], 6),
            "status": "ok",
        })
        print(f"   {site:10s} reported {s['owner_reported']:>6}  estimated {est_site:.4f}  "
              f"mass {int(prof['mass']):>7d}  h {prof['hit_rate']:.4f}")

    print("== 5. uniqueness audit")
    comparators = []
    for s in focus_reg["sites"]:
        p = FOCUS / (s["site"] + "__" + Path(s["path"]).name)
        if p.exists():
            comparators.append((f"{s['site']} top file", p))
    for label, rep, rel in V.REPORTED:
        p = ROOT / rel
        if p.exists() and not any(str(p).endswith(Path(c[1]).name) for c in comparators):
            comparators.append((label, p))
    uniq = []
    for label, p in comparators:
        r = U.compare(pred, U.load_mask(p), valid)
        r["comparator"] = label
        r["file"] = Path(p).name
        uniq.append(r)
        flag = "BLOCK" if r["blocked"] else "ok"
        print(f"   {flag:5s} {label[:36]:36s} jacc={r['jaccard']:.3f} "
              f"within3={r['within_3px_of_candidate']:.3f} rho_dens={r['rho_density']:+.3f}"
              + (f"  [3px rule vacuous: comparator covers {r['comparator_3px_coverage']:.0%} "
                 "of the map within 3px]" if r["space_filling_comparator"] else ""))
    blocked = [u["comparator"] for u in uniq if u["blocked"]]
    max_j = max(u["jaccard"] for u in uniq) if uniq else 0.0
    max_w = max(u["within_3px_of_candidate"] for u in uniq) if uniq else 0.0
    max_rho = max(abs(u["rho_density"]) for u in uniq) if uniq else 0.0
    unique_ok = len(blocked) == 0

    print("== 6. write + validate submission")
    name = "wbggemsdoe3-skarpline-union"
    tmp = SUB_DIR / f"{name}.tif"
    prof_out = {
        "driver": "GTiff", "height": C.HEIGHT, "width": C.WIDTH, "count": 1,
        "dtype": "float32", "crs": C.CRS,
        "transform": Affine(C.PIXEL_M, 0, C.ORIGIN_X, 0, -C.PIXEL_M, C.ORIGIN_Y),
        "compress": "deflate", "predictor": 2, "tiled": False, "nodata": None,
    }
    with rasterio.open(tmp, "w", **prof_out) as dst:
        dst.write(pred.astype(np.float32), 1)
    digest = sha256_file(tmp)
    final_name = f"{name}-20261027-{digest[:8]}-zeros.tif"
    final = SUB_DIR / final_name
    tmp.replace(final)
    digest = sha256_file(final)
    print(f"   wrote {final.name} sha256 {digest}")

    # strict validation of the saved bytes
    tmpl = gio.read_footprint()
    with rasterio.open(final) as src:
        arr = src.read(1)
        meta = {"band_count": src.count, "dtype": src.dtypes[0], "shape": [src.height, src.width],
                "crs": str(src.crs), "transform": list(src.transform)[:6], "nodata": src.nodata}
    checks = {
        "single_band": meta["band_count"] == 1,
        "float32": meta["dtype"] == "float32",
        "shape_matches_template": meta["shape"] == [C.HEIGHT, C.WIDTH],
        "crs_matches_template": meta["crs"] == C.CRS,
        "transform_matches_template": np.allclose(meta["transform"],
                                                  [C.PIXEL_M, 0, C.ORIGIN_X, 0, -C.PIXEL_M, C.ORIGIN_Y]),
        "all_finite": bool(np.isfinite(arr).all()),
        "values_in_0_1": bool((arr >= 0).all() and (arr <= 1).all()),
        "footprint_cells_finite": bool(np.isfinite(arr[tmpl]).all()),
        "n_positive": int((arr > 0).sum()),
        "n_nonzero_outside_footprint": int(((arr != 0) & ~tmpl).sum()),
    }
    checks["zero_mass_outside_footprint"] = checks["n_nonzero_outside_footprint"] == 0
    checks["pass"] = all(checks[k] for k in
                         ["single_band", "float32", "shape_matches_template", "crs_matches_template",
                          "transform_matches_template", "all_finite", "values_in_0_1",
                          "footprint_cells_finite", "zero_mass_outside_footprint"])
    for k in ("single_band", "float32", "shape_matches_template", "crs_matches_template",
              "transform_matches_template", "all_finite", "values_in_0_1",
              "footprint_cells_finite", "zero_mass_outside_footprint"):
        print(f"   {'PASS' if checks[k] else 'FAIL'} {k}")
    print(f"   info n_positive={checks['n_positive']} "
          f"n_nonzero_outside_footprint={checks['n_nonzero_outside_footprint']}")

    # zip twin
    import zipfile
    zpath = SUB_DIR / final.name.replace(".tif", ".zip")
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo(final.name, date_time=(2026, 10, 27, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, final.read_bytes())
    print(f"   zip {zpath.name} {zpath.stat().st_size} bytes sha256 {sha256_file(zpath)[:16]}")

    # provenance: verify portability by re-reading and recomputing the profile
    check = V.profile(U.load_mask(final), gt, valid)

    residuals = [r["estimate_minus_reported"] for r in site_rows if r.get("status") == "ok"]
    bias = float(np.mean(residuals)) if residuals else 0.0
    est_bias_corrected = est - bias
    gaps = json.loads(json.dumps(boot))
    estimate = {
        "evidence_class": "ESTIMATE (calibrated metric model; NOT an organizer score)",
        "primary_estimate": round(est, 4),
        "bias_corrected_estimate": round(est_bias_corrected, 4),
        "observed_bias_on_focus_sites": round(bias, 4),
        "bias_convention": "mean(estimate - reported) over the nine focus-site top files; "
                           "subtracted to give the bias-corrected point forecast",
        "bootstrap_ci95": gaps["estimate_ci95"],
        "sensitivity_over_gt_size": sens,
        "gt_size_fitted_px": round(m_fit, 1),
        "gt_size_convention": "fitted to 10 organizer-reported archived submissions (robust trimmed fit)",
        "calibration_observations": [
            {"label": o["label"], "mass": round(o["mass"], 1), "hit_rate": round(o["hit_rate"], 6),
             "reported": o["reported"], "predicted": round(o["predicted"], 4),
             "residual": round(o["residual"], 4), "used_in_fit": bool(o["used_in_fit"])}
            for o in fit["observations"]],
        "calibration": {"r2": round(fit["r2"], 4), "spearman": round(fit["spearman"], 4),
                        "loo_rms": round(fit["loo_rms"], 4), "residual_median_abs": round(fit["residual_median_abs"], 4),
                        "n_used": fit["n_used"], "n_total": fit["n_total"]},
        "proxy": {"source": V.SGMC_SOURCE, "gt_px": int(gt.sum()),
                  "hit_rate": round(check["hit_rate"], 6), "capture": round(check["capture"], 6),
                  "dti_proxy": round(check["dti_proxy"], 6), "mass_px": int(check["mass"])},
        "confidence_statement": (
            f"Estimated leaderboard DTI {est:.3f} (95% GT-bootstrap CI "
            f"{gaps['estimate_ci95'][0]:.3f}-{gaps['estimate_ci95'][1]:.3f}; "
            f"{sens['8430']:.3f}-{sens['30000']:.3f} across the plausible ground-truth size range). "
            "This is a model-based estimate from a validated proxy, not an organizer receipt."
        ),
    }

    run_card = {
        "submission": final.name,
        "sha256": digest,
        "created_utc": "2026-10-27",
        "hypothesis": ("Faults the Quaternary catalogue missed are best recovered from "
                       "multi-scale scarp morphology of the detrended-elevation surface plus "
                       "2 m LiDAR free-face/step descriptors, emitted as a thin, binary, "
                       "catalogue-free lineament network sized for the official Tversky penalty."),
        "mechanism": ("Ridge non-maximum suppression of plan/profile curvature and paired-scarp "
                      "response (100 m) unioned with NMS of 2 m LiDAR slope-excess/antislope channels, "
                      "rank-averaged; binary level 1.0 on the union support."),
        "non_fault_mimic": ("Roads, railroad grades, alluvial-fan edges, shorelines/terraces, "
                            "landslides, mines and drainage channels also produce scarps; "
                            "the TIGER road-distance and acquisition-block audit layers are used to "
                            "quantify, not to mask, this confound (see docs/executive-summary.html)."),
        "evaluator": {
            "official_metric": "DTI = TP_w/(TP_w + 0.2 FP_w + 0.8 FN_w), R=300 m triangular kernel",
            "implementation": "src/gemsdoe/metric.py (verified vs brute force and vs a third-party "
                              "measured value on the official 512x512 fixture)",
            "proxy": "USGS SGMC faults >300 m from every catalogue fault (external catalogue proxy)",
        },
        "holdout_result": {"dti_proxy": check["dti_proxy"], "ci95": boot["dti_proxy_ci95"],
                           "n_withheld_positives": int(gt.sum()), "evaluator_version": "gemsdoe-dti-v1.0",
                           "label": "PROXY-DTI (not a competition score)"},
        "estimate": estimate,
        "uniqueness": {
            "policy": "exact-duplicate / Jaccard>0.5 / >70% within 3px / |rho|>0.9 vs submission-like comparators",
            "comparators": len(uniq), "blocked": blocked,
            "max_jaccard": round(max_j, 6), "max_within_3px": round(max_w, 6),
            "max_abs_rho_density": round(max_rho, 6), "unique": bool(unique_ok),
            "rho_statistic": "Spearman of 2 km density fields inside the footprint "
                             "(binary-mask correlation is degenerate for disjoint supports)",
            "rows": uniq,
        },
        "validator": checks,
        "download": {
            "tif": f"submission/{final.name}",
            "zip": f"submission/{zpath.name}",
            "note": ("GEMS-DOE-3 skarpline union 60k+40k, dti-optimised binary, cat-suppressed r=0"),
        },
        "verdict": "promote" if (checks["pass"] and unique_ok) else "negative",
        "evidence_class": "LOCAL-EVIDENCE (format + uniqueness + proxy); no organizer receipt",
    }

    (EV_DIR / "gemsdoe_run_card.json").write_text(json.dumps(run_card, indent=1))
    (DOC_DATA / "estimate.json").write_text(json.dumps(estimate, indent=1))
    (DOC_DATA / "focus_estimates.json").write_text(json.dumps(
        {"note": ("ESTIMATE = calibrated metric model applied to each site's top archived file. "
                  "Organizer-reported values are owner logs, not upload receipts."),
         "gt_size_fitted_px": round(m_fit, 1), "rows": site_rows}, indent=1))
    (DOC_DATA / "uniqueness.json").write_text(json.dumps(
        {"policy": run_card["uniqueness"]["policy"], "rows": uniq}, indent=1))
    print(f"== verdict: {run_card['verdict']}  (validator {checks['pass']}, unique {unique_ok})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
