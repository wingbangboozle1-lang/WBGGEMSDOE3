#!/usr/bin/env python3
"""Session 2026-10-27 (branch arena/1f0b051d) independent audit, Pass 1.

Reproduces, from restored SHA-pinned bytes only:
 A. format/range audit of every candidate + focus + calibration raster
 B. champion (GEMSDOE32 B2) anatomy + focus-9 pairwise uniqueness
 C. SGMC off-catalogue proxy profiles + the skarpline estimator refit/LOO
 D. density-matched SGMC proxy DTI (whole-segment subsampling, many seeds)
 E. static read-back HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0) for key files
Every performance number is labelled PROXY-DTI or HOLDOUT-DTI. Owner-reported
scores from the user ledger are labelled OWNER-REPORTED (no receipts exist).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe import config as C          # noqa: E402
from gemsdoe import io as gio            # noqa: E402
from gemsdoe import metric as M          # noqa: E402
from gemsdoe import validation as V      # noqa: E402

OUT = ROOT / "evidence" / "session_1f0b051d_audit.json"
report: dict = {"session": "2026-10-27", "branch": "arena/1f0b051d-wbggemsdoe3"}

OWNER = {  # user-supplied ledger values; NOT organizer receipts
    "GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449, "GEMSDOE28": 0.2710,
    "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708, "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632,
    "GEMSDOE36": 0.2750,
}
CANDIDATES = {
    "skarpline_union (this repo, prev lane)": "submission/wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif",
    "cspes_edgestab (this repo, prev lane)": "submission/wbggems3-cspes-edgestab-37654d-20261027-9e28c697-zeros.tif",
    "lst1_hybrid (this repo, prev lane)": "submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif",
    "hce1_congruence (this repo, prev lane)": "docs/hce/downloads/wbggems3-hce1-congruence-20261027T182554Z-bc1edfe6-zeros.tif",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(p) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1)


def main():
    assert gio.verify_official_data(strict=True)
    with rasterio.open(C.SAMPLE_TIF) as src:
        ref_profile = src.profile.copy()
        sample = src.read(1)
    foot = np.isfinite(sample)
    labels = gio.read_labels() & foot
    d_cat = ndi.distance_transform_edt(~labels)
    report["grid"] = {"shape": list(sample.shape), "footprint_px": int(foot.sum()),
                      "catalogue_px": int(labels.sum()),
                      "sample_ones_px": int((sample == 1).sum()),
                      "sample_ones_on_catalogue": int(((sample == 1) & labels).sum())}
    print("[grid]", report["grid"], flush=True)

    # ---------- A. format audit ----------
    files = {}
    for site in OWNER:
        files[site] = ROOT / ".cache" / "focus" / f"{site}.tif"
    for name, rel in CANDIDATES.items():
        files[name] = ROOT / rel
    for _label, _s, rel in V.REPORTED:
        files[f"calib::{Path(rel).name}"] = ROOT / rel
    fmt = {}
    arrays = {}
    for name, p in files.items():
        with rasterio.open(p) as src:
            prof = src.profile
            a = src.read(1)
        fin = np.isfinite(a)
        af = np.where(fin, a, 0.0).astype(np.float32)
        arrays[name] = af
        fmt[name] = {
            "path": str(p.relative_to(ROOT)), "sha256": sha256_file(p),
            "dtype": str(prof["dtype"]), "count": prof["count"],
            "shape_ok": a.shape == sample.shape,
            "crs_ok": str(prof["crs"]) == str(ref_profile["crs"]),
            "transform_ok": prof["transform"] == ref_profile["transform"],
            "min_finite": float(a[fin].min()) if fin.any() else None,
            "max_finite": float(a[fin].max()) if fin.any() else None,
            "nan_inside_footprint": int((~fin & foot).sum()),
            "nan_outside_footprint": int((~fin & ~foot).sum()),
            "support_px_gt0_in_foot": int(((af > 0) & foot).sum()),
            "mass_in_foot": float(af[foot].sum(dtype=np.float64)),
            "dots_on_catalogue": int(((af > 0) & labels).sum()),
            "mass_on_catalogue": float(af[labels].sum(dtype=np.float64)),
            "unique_positive_values_le20": [float(x) for x in np.unique(af[af > 0])[:20]],
        }
    report["A_format_audit"] = fmt
    for n, r in fmt.items():
        print(f"[fmt] {n:55s} support={r['support_px_gt0_in_foot']:7d} mass={r['mass_in_foot']:10.1f} "
              f"oncat={r['dots_on_catalogue']:5d} range=[{r['min_finite']},{r['max_finite']}]", flush=True)

    # ---------- B. champion anatomy + focus pairwise ----------
    def support(name):
        return (arrays[name] > 0) & foot

    champ = support("GEMSDOE32")
    anatomy = {}
    for other in OWNER:
        if other == "GEMSDOE32":
            continue
        o = support(other)
        removed = o & ~champ
        anatomy[other] = {
            "champion_subset_of_other": bool((champ & ~o).sum() == 0),
            "n_other": int(o.sum()), "n_intersection": int((champ & o).sum()),
            "n_other_minus_champion": int(removed.sum()),
            "removed_dcat_min": float(d_cat[removed].min()) if removed.any() else None,
            "removed_dcat_max": float(d_cat[removed].max()) if removed.any() else None,
            "removed_frac_dcat_le_3": float((d_cat[removed] <= 3).mean()) if removed.any() else None,
        }
    anatomy["champion_dcat_min"] = float(d_cat[champ].min())
    anatomy["champion_dcat_pcts"] = {str(q): float(np.percentile(d_cat[champ], q)) for q in (1, 5, 25, 50)}
    report["B_champion_anatomy"] = anatomy
    print("[anatomy]", json.dumps(anatomy, indent=1)[:1500], flush=True)

    sites = list(OWNER)
    dists = {s: ndi.distance_transform_edt(~support(s)) for s in sites}
    pair = {}
    for i, a_ in enumerate(sites):
        for b_ in sites[i + 1:]:
            sa, sb = support(a_), support(b_)
            pair[f"{a_}__{b_}"] = {
                "jaccard": float((sa & sb).sum() / max((sa | sb).sum(), 1)),
                "a_within3_of_b": float((dists[b_][sa] <= 3).mean()),
                "b_within3_of_a": float((dists[a_][sb] <= 3).mean()),
                "identical_support": bool((sa == sb).all()),
            }
    report["B_focus_pairwise"] = pair
    jac = [v["jaccard"] for v in pair.values()]
    w3 = [min(v["a_within3_of_b"], v["b_within3_of_a"]) for v in pair.values()]
    print(f"[pairwise] Jaccard range {min(jac):.3f}-{max(jac):.3f}; min-direction within3px range {min(w3):.3f}-{max(w3):.3f}", flush=True)

    # ---------- C. SGMC proxy profiles + estimator refit ----------
    gt = V.sgmc_only_gt(foot)
    report["C_sgmc_proxy_px"] = int(gt.sum())
    ev = M.FastDTI(gt, valid=foot)
    prof = {}
    for name, a in arrays.items():
        r = ev.evaluate(a)
        prof[name] = {"label": "PROXY-DTI (SGMC off-catalogue, gemsdoe-dti-v1.0)",
                      "dti_proxy": r["dti"], "hit_rate": r["tp"] / max(r["mass"], 1e-9),
                      "capture": r["tp"] / r["n_truth"], "mass": r["mass"], "tp_w": r["tp"]}
    report["C_proxy_profiles"] = prof
    obs = []
    for label, reported, rel in V.REPORTED:
        key = f"calib::{Path(rel).name}"
        obs.append({"label": label, "reported": reported, "path": rel,
                    "mass": prof[key]["mass"], "hit_rate": prof[key]["hit_rate"],
                    "dti_proxy": prof[key]["dti_proxy"], "capture": prof[key]["capture"]})
    fit_all = V.fit_gt_size([dict(o) for o in obs], robust=False)
    fit_trim = V.fit_gt_size([dict(o) for o in obs], robust=True)
    report["C_estimator_refit"] = {
        "note": "ESTIMATE model of previous lane, refit for audit only; see lattice/SGMC counterexamples",
        "full_fit": {k: fit_all[k] for k in ("M_trimmed", "M_all_files", "r2", "spearman", "residual_rms", "loo_rms")},
        "trimmed_fit": {k: fit_trim[k] for k in ("M_trimmed", "M_all_files", "r2", "spearman", "residual_rms", "loo_rms", "n_used")},
        "trimmed_observations": fit_trim["observations"],
    }
    for o in fit_trim["observations"]:
        print(f"[calib] {o['label']:35s} rep={o['reported']:.4f} pred={o['predicted']:.4f} h={o['hit_rate']:.4f} mass={o['mass']:.0f} used={o['used_in_fit']}", flush=True)
    m_fit = fit_trim["M_trimmed"]
    for name in CANDIDATES:
        p = prof[name]
        print(f"[est] {name:55s} h={p['hit_rate']:.4f} mass={p['mass']:.0f} -> ET={V.score_from_profile(p['hit_rate'], p['mass'], m_fit):.4f}", flush=True)

    # SGMC-copy counterexample: dotted SGMC-off-catalogue itself (spacing via greedy 3px thinning is in experiments;
    # here: every SGMC proxy pixel as pred -> h and ET are maximal by construction, yet owner-reported
    # scores for SGMC-off-catalogue submissions are 0.0512 / 0.0492 in the user ledger.)
    r_sgmc = ev.evaluate(gt.astype(np.float32))
    report["C_sgmc_self_counterexample"] = {
        "pred": "SGMC off-catalogue proxy itself (all 62,122 px, value 1)",
        "hit_rate": r_sgmc["tp"] / r_sgmc["mass"], "dti_proxy": r_sgmc["dti"],
        "ET_at_fitted_G": V.score_from_profile(r_sgmc["tp"] / r_sgmc["mass"], r_sgmc["mass"], m_fit),
        "owner_reported_sgmc_offcat_scores_in_user_ledger": {"GEMSDOE29 sgmc-off-catalogue-44k": 0.0512,
                                                              "GEMSDOE72 sgmc-offcatalogue": 0.0492},
        "conclusion": "h(proxy)->score transfer is invalid for supports that live on SGMC-like geologic-map faults; "
                      "the estimator must not be used to claim 0.428 for a broad scarp network without a density-matched check.",
    }
    print("[counterexample]", report["C_sgmc_self_counterexample"], flush=True)

    # ---------- D. density-matched proxy ----------
    comp, n_comp = ndi.label(gt, structure=np.ones((3, 3), bool))
    sizes = np.bincount(comp.ravel())
    ids = np.arange(1, n_comp + 1)
    targets = {"skarpline_union (this repo, prev lane)": arrays["skarpline_union (this repo, prev lane)"],
               "GEMSDOE32 champion": arrays["GEMSDOE32"],
               "GEMSDOE25 d2.8": arrays["GEMSDOE25"],
               "hce1": arrays["hce1_congruence (this repo, prev lane)"],
               "lst1": arrays["lst1_hybrid (this repo, prev lane)"],
               "cspes": arrays["cspes_edgestab (this repo, prev lane)"],
               "lattice_s5": arrays["calib::13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"],
               "h19_5_continuous": arrays["calib::gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif"]}
    dm = {}
    for target_px in (8430, 12691, 15672):
        rows = {k: [] for k in targets}
        for seed in range(12):
            rng = np.random.default_rng(10_000 + seed)
            order = rng.permutation(ids.size)
            keep, tot = [], 0
            for i in order:
                if tot >= target_px:
                    break
                keep.append(ids[i]); tot += int(sizes[ids[i]])
            sub = np.isin(comp, keep)
            evd = M.FastDTI(sub, valid=foot)
            for k, a in targets.items():
                rows[k].append(evd.evaluate(a)["dti"])
        dm[str(target_px)] = {k: {"mean": float(np.mean(v)), "p2.5": float(np.percentile(v, 2.5)),
                                  "p97.5": float(np.percentile(v, 97.5)), "label": "PROXY-DTI density-matched"}
                              for k, v in rows.items()}
        print(f"[density-matched |G|={target_px}] " + "  ".join(f"{k}={np.mean(v):.4f}" for k, v in rows.items()), flush=True)
    report["D_density_matched_proxy"] = dm

    # ---------- E. static hide-recover read-back ----------
    from gemsw import holdout as HO
    ctx = HO.load_holdout_context(ROOT / "data" / "raw")
    hr = {}
    for name, a in [("skarpline_union", targets["skarpline_union (this repo, prev lane)"]),
                    ("GEMSDOE32 champion", targets["GEMSDOE32 champion"]),
                    ("hce1_saved", targets["hce1"]), ("cspes_saved", targets["cspes"]),
                    ("lst1_saved", targets["lst1"]), ("GEMSDOE25 d2.8", targets["GEMSDOE25 d2.8"])]:
        r = HO.evaluate_hide_and_recover(a > 0, ctx, name=name)
        hr[name] = {"label": "HOLDOUT-DTI (static read-back, not fold-local)",
                    "evaluator_version": r["evaluator_version"],
                    "n_withheld_positives": r["n_withheld_positives"],
                    "pooled_dti": r["pooled_dti"], "ci95": r["ci95_cluster_bootstrap"],
                    "per_quadrant": r["per_quadrant_dti"]}
        print(f"[hide-recover static] {name:20s} {r['pooled_dti']:.4f} CI {r['ci95_cluster_bootstrap']}", flush=True)
    report["E_hide_recover_static"] = hr

    OUT.write_text(json.dumps(report, indent=1, default=float))
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
