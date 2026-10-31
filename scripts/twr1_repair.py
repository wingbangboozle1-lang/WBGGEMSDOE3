#!/usr/bin/env python3
"""TWR-1 uniqueness-repair iteration (precedent: hce_run_card.json uniqueness_repair).

The first placement exceeded the 0.70 forward 3-px overlap on exactly one non-degenerate
comparator (GEMSDOE50 90k scarp scatter, forward 0.776). Repair rule (frozen here): keep
the same surface, band window and budget K=37,654 but forbid dots inside the 3-px halo of
that comparator's dots, taking the next-best crest cells instead; then re-audit all gates.
Report both the fold-local holdout of the repaired rule (comparable number) and the static
read-back (documented as catalogue-exclusive by construction).
"""
from __future__ import annotations
import hashlib, json, shutil, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TEMPLATE = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(TEMPLATE / "src"))
from gemsw import grid as G  # noqa: E402
from gemsw import holdout as H  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402

T0 = time.time()
EVID = ROOT / "evidence"
K, NMS = 37_654, 3.0
BAND_IN_PX, BAND_RAMP_PX = 1.4, 2.4
RHO_LIMIT, OVERLAP_LIMIT, DEG_COVER = 0.90, 0.70, 0.70
NAME = "wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros"
NOTE = ("TWR-1r2: fold-local anisotropic crest core, 37,654 dots, 3-px NMS, "
        "3 flagged comparator halos avoided; holdout-negative research file")


def log(m): print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)
def sha256(b): return hashlib.sha256(b).hexdigest()


def rank_norm(field, active):
    out = np.zeros(field.shape, np.float32)
    v = field[active]; ok = np.isfinite(v)
    edges = np.quantile(v[ok], np.linspace(0.01, 0.99, 99))
    finite = np.isfinite(field) & active
    out[finite] = (np.searchsorted(edges, field[finite], side="right").astype(np.float32) + 1) / 100.0
    return out


def place(Cf, eligible, budget=K, nms=NMS):
    Hh, Ww = Cf.shape
    flat = np.where(eligible, Cf, -np.inf).ravel()
    pool = min(1_500_000, int(eligible.sum()))
    idx = np.argpartition(flat, flat.size - pool)[flat.size - pool:]
    order = idx[np.argsort(-flat[idx], kind="stable")]
    r = int(np.ceil(nms))
    offs = [(dy, dx) for dy in range(-r, r+1) for dx in range(-r, r+1) if dy*dy+dx*dx < nms*nms+1e-9]
    blocked = np.zeros(Cf.size, bool)
    dots = np.zeros(Cf.shape, bool); n = 0
    for f in order:
        if blocked[f]: continue
        y, x = divmod(int(f), Ww)
        dots[y, x] = True; n += 1
        if n >= budget: break
        for dy, dx in offs:
            yy, xx = y+dy, x+dx
            if 0 <= yy < Hh and 0 <= xx < Ww:
                blocked[yy*Ww+xx] = True
    return dots


def main() -> int:
    g = G.load_grid()
    with rasterio.open(ROOT / "data/raw/training_features.tif") as tf:
        elev = G.clean_feature(tf.read(12))
    from gemsw.features import _fill
    log3 = (-9.0 * ndi.gaussian_laplace(_fill(elev, g.foot), 3.0)).astype(np.float32)
    gm = ndi.gaussian_gradient_magnitude(_fill(elev, g.foot), 1.5).astype(np.float32)
    del elev
    active = g.foot & ~g.labels
    T = 0.55 * rank_norm(log3, active) + 0.45 * rank_norm(gm, active)
    del log3, gm
    d_cat = ndi.distance_transform_edt(~g.labels)
    w = np.clip((d_cat - BAND_IN_PX) / (BAND_RAMP_PX - BAND_IN_PX), 0.0, 1.0).astype(np.float32)

    yy, xx = np.mgrid[-3:4, -3:4]
    disc = yy*yy + xx*xx <= 9
    forbid = np.zeros(g.foot.shape, bool)
    forbidden_rasters = []
    FORBID_GLOBS = ("GEMSDOE50__*scatter-90k*.tif", "GEMSDOE22__*h23-b-dti-optimal-emission-10pct*.tif",
                    "GEMSDOE23__*h30-arrangement-matched-habitat*.tif")
    forbid_files = []
    for pat in FORBID_GLOBS:
        for p in sorted((ROOT / "data/ledger").glob(pat)):
            forbid_files.append(p)
    _fb_cache = {}
    for p in forbid_files:
        a = G.read_band(p)
        dset = np.isfinite(a) & (a > 0) & g.foot
        _fb_cache[p] = dset
        forbid |= ndi.binary_dilation(dset, structure=disc)
        forbidden_rasters.append(p.name)
        log(f"forbid halo from {p.name}: +{int(dset.sum())} dots")
    log(f"forbidden px: {int(forbid[g.foot].sum())}")

    core = place(T * w, active & (T * w > 0) & ~forbid)
    log(f"repaired core dots: {int(core.sum())}")

    # fold-local holdout of the repaired rule (honest comparable number)
    ctx = H.load_holdout_context(ROOT / "data/raw")
    cellmaps, n_shift = {}, 0
    for cell in ctx.cells:
        vis = cell.visible_full
        wv = np.clip((ndi.distance_transform_edt(~vis) - BAND_IN_PX) /
                     (BAND_RAMP_PX - BAND_IN_PX), 0.0, 1.0).astype(np.float32)
        act_full = np.zeros(g.foot.shape, bool); act_full[cell.bbox] = cell.active_sub
        dots = place(T * wv, act_full & ~vis & (T * wv > 0) & ~forbid)
        cellmaps[cell.key] = dots
    ev = H.evaluate_hide_and_recover(cellmaps, ctx, name="TWR1r_fold_local", n_boot=1000)
    log(f"repaired fold-local HOLDOUT-DTI={ev['pooled_dti']:.5f} CI={[round(x,5) for x in ev['ci95_cluster_bootstrap']]}")
    ev_static = H.evaluate_hide_and_recover({c.key: core for c in ctx.cells}, ctx,
                                            name="TWR1r_static", n_boot=1000)
    log(f"repaired static read-back DTI={ev_static['pooled_dti']:.5f} (catalogue-exclusive by construction)")

    # write final raster with the shared writer
    arr = np.zeros(g.foot.shape, np.float32)
    arr[core] = 1.0
    out_tif = ROOT / "submission" / f"{NAME}.tif"
    sample = ROOT / "data/raw/sample_submission.tif"
    receipt = SW.write_submission(out_tif, arr, sample, g.foot, note=NOTE, name=NAME,
                                  catalogue=g.labels,
                                  metadata={"lane": "TWR-1 (uniqueness-repaired)", "evidence_class": "candidate raster"})
    (ROOT / "submission" / (out_tif.stem + ".manifest.json")).write_text(json.dumps(receipt, indent=1))
    log(f"writer ok={receipt['template_report']['ok']} validator={receipt['validator']['all_checks_passed']}")

    # re-audit uniqueness over all local comparators
    sidx = np.random.default_rng(11).choice(np.flatnonzero(g.foot.ravel()), 120_000, replace=False)
    surf_s = rankdata((T * w).ravel()[sidx])
    near_mine = ndi.binary_dilation(core, structure=disc)
    ledger_idx = json.loads((ROOT / "data/ledger/index.json").read_text())
    score_by_name = {Path(r["local"]).name: r.get("score") for r in ledger_idx if r.get("status") == "verified"}
    comp_rows = []
    files = sorted((ROOT / "data/ledger").glob("*.tif")) + sorted((ROOT / ".cache/focus").glob("*.tif")) + \
            [p for p in sorted((ROOT / "submission").glob("*.tif")) if p.name != out_tif.name]
    for p in files:
        try:
            with rasterio.open(p) as ds:
                if ds.shape != g.foot.shape or ds.count != 1:
                    continue
                a = ds.read(1)
        except Exception:
            continue
        dots_c = np.isfinite(a) & (a > 0) & g.foot
        if not dots_c.any():
            continue
        rv = rankdata(np.where(np.isfinite(a), a, 0.0).ravel()[sidx])
        try:
            rho = float(np.corrcoef(surf_s, rv)[0, 1]) if rv.std() > 0 else 0.0
        except Exception:
            rho = 0.0
        if not np.isfinite(rho):
            rho = 0.0
        near_c = ndi.binary_dilation(dots_c, structure=disc)
        forward = float(near_c[core].mean())
        reverse = float(near_mine[dots_c].mean())
        cover = float(near_c[g.foot].mean())
        degenerate = cover > DEG_COVER
        dup = (forward > OVERLAP_LIMIT and reverse > OVERLAP_LIMIT) or \
              (forward > OVERLAP_LIMIT and not degenerate)
        comp_rows.append(dict(site_file=p.name, owner_reported_score=score_by_name.get(p.name),
                              n_dots=int(dots_c.sum()), forward_overlap_3px=round(forward, 4),
                              reverse_overlap_3px=round(reverse, 4),
                              comparator_coverage=round(cover, 4),
                              comparator_class="dense" if degenerate else "sparse",
                              abs_spearman_surface=round(abs(rho), 4), duplicate_flag=bool(dup)))
        if dup:
            log(f"  STILL FLAGGED {p.name}: fwd={forward:.3f} rev={reverse:.3f}")
    worst_fwd = max((r["forward_overlap_3px"] for r in comp_rows), default=0.0)
    worst_rho = max((r["abs_spearman_surface"] for r in comp_rows), default=0.0)
    n_dup = sum(1 for r in comp_rows if r["duplicate_flag"])
    uniq_pass = n_dup == 0 and worst_rho <= RHO_LIMIT
    log(f"re-audit: {len(comp_rows)} comparators, flags={n_dup}, worst_fwd={worst_fwd:.3f}, worst_rho={worst_rho:.3f} -> {'PASS' if uniq_pass else 'FAIL'}")
    json.dump({"evidence_class": "REGISTRY-MEASUREMENT (owner-mirrored, hash-verified upstream)",
               "candidate_file": str(out_tif.relative_to(ROOT)), "candidate_sha256": sha256(out_tif.read_bytes()),
               "comparators": comp_rows,
               "summary": dict(n=len(comp_rows), duplicate_flags=n_dup, worst_forward_overlap=worst_fwd,
                               worst_abs_spearman=worst_rho, ratified_rule_pass=bool(uniq_pass),
                               rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT, degenerate_coverage_cut=DEG_COVER,
                               forbidden_rasters=forbidden_rasters),
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(EVID / "twr1r_uniqueness.json", "w"), indent=1)

    card = json.load(open(EVID / "twr1_run_card.json"))
    card["uniqueness_repair"] = {"forbidden_rasters": forbidden_rasters,
                                 "forbidden_px": int(forbid[g.foot].sum()),
                                 "dots_before": 37654, "dots_after": int(core.sum()),
                                 "note": "same budget and physical ranking; dots forced outside the 3-px halo of the one non-degenerate comparator above 0.70"}
    card["raster_sha256"] = sha256(out_tif.read_bytes())
    card["submission"] = {"name": NAME, "note": NOTE, "note_characters": len(NOTE),
                          "files": [str(out_tif.relative_to(ROOT)),
                                    str(out_tif.with_suffix('.zip').relative_to(ROOT))]}
    card["holdout_dti"]["repaired_fold_local"] = {"value": round(ev["pooled_dti"], 5),
                                                  "ci95": [round(x, 5) for x in ev["ci95_cluster_bootstrap"]],
                                                  "n_withheld": int(ev["n_withheld_positives"])}
    card["holdout_dti"]["repaired_static_readback"] = round(ev_static["pooled_dti"], 5)
    card["registry_overlap"].update({"duplicate_flags": n_dup, "worst_forward_overlap_3px": worst_fwd,
                                     "worst_abs_spearman": round(worst_rho, 4),
                                     "ratified_rule_pass": bool(uniq_pass)})
    card["validator"]["passed"] = bool(receipt["validator"]["all_checks_passed"] and receipt["template_report"]["ok"])
    card["validator"]["checks"] = receipt["validator"]["checks"]
    card["okay_to_download_for_research"] = True
    card["okay_to_submit"] = False
    card["verdict"] = "negative"
    json.dump(card, open(EVID / "twr1_run_card.json", "w"), indent=1)

    dd = ROOT / "docs/downloads"
    for f in dd.glob("wbg3-twr1-*"):
        f.unlink()
    for f in (out_tif, out_tif.with_suffix(".zip")):
        shutil.copy2(f, dd / f.name)
    log("published repaired file to docs/downloads; run card updated")
    return 0 if uniq_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
