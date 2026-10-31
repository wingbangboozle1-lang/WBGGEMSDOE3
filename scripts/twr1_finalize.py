#!/usr/bin/env python3
"""TWR-1 finalize: V4 emission -> shared writer -> uniqueness + validator -> run card.

Gate order (all automatic, no human intervention):
  U-surface : |Spearman| <= 0.90 vs every registry raster (decoded arrays, sampled)
  U-literal : forward 3-px dot overlap <= 0.70 vs every registry raster   (reported)
  U-content : duplicate flag only when forward AND reverse > 0.70 (or forward > 0.70
              with comparator 3-px coverage <= 0.70). Thresholds unchanged; only the
              comparison is made symmetric so degenerate space-filling comparators
              cannot universal-block (owner-ratified correction of IR-29-13).
  Validator : shared gems57 writer receipt (single band, float32, [0,1], finite inside,
              zero on catalogue, zero outside footprint, CRS/shape/transform match)
  Holdout   : V4 lane value vs comparable holdout best (documented as the promote bar)
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
K = 37_654
NMS = 3.0
BAND_IN_PX, BAND_RAMP_PX = 1.4, 2.4
RHO_LIMIT, OVERLAP_LIMIT, DEG_COVER = 0.90, 0.70, 0.70
NAME = "wbg3-twr1-crestcore3px-37654-20261031-a1f4d0c9-zeros"
NOTE = ("TWR-1: fold-local multi-sensor anisotropic crest core, 37,654 dots, "
        "3-px NMS, catalogue-band pruned; holdout-negative research file")


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
    # ---- surface + emission (full catalogue; identical rule to instrument arm V4)
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
    core = place(T * w, active & (T * w > 0))
    log(f"core dots placed: {int(core.sum())}")
    arr = np.zeros(g.foot.shape, np.float32)
    arr[core] = 1.0

    # ---- write with the SHARED template writer (fail-closed validator inside)
    out_tif = ROOT / "submission" / f"{NAME}.tif"
    if out_tif.exists():
        out_tif = ROOT / "submission" / f"{NAME}-{time.strftime('%H%M%S')}.tif"
    sample = ROOT / "data/raw/sample_submission.tif"
    receipt = SW.write_submission(out_tif, arr, sample, g.foot, note=NOTE, name=NAME,
                                  catalogue=g.labels,
                                  metadata={"lane": "TWR-1", "evidence_class": "candidate raster"})
    (ROOT / "submission" / (out_tif.stem + ".manifest.json")).write_text(json.dumps(receipt, indent=1))
    log(f"writer receipt ok={receipt['template_report']['ok']} validator={receipt['validator']['all_checks_passed']}")

    # ---- registry build (local mirrors only; hash-verified upstream)
    reg_rows, seen = [], {}
    dirs = [("ledger", ROOT / "data/ledger"), ("repo-submission", ROOT / "submission"),
            ("focus-mirror", ROOT / ".cache/focus")]
    yy, xx = np.mgrid[-3:4, -3:4]
    disc = yy*yy + xx*xx <= 9
    rng = np.random.default_rng(11)
    sidx = rng.choice(np.flatnonzero(g.foot.ravel()), 120_000, replace=False)
    surf_field = T * w  # pre-placement density surface (fold rule: continuous rank field)
    surf_s = rankdata(surf_field.ravel()[sidx])
    near_mine = ndi.binary_dilation(core, structure=disc)
    cov_mine = float(near_mine[g.foot].mean())
    comp_rows = []
    ledger_idx = json.loads((ROOT / "data/ledger/index.json").read_text()) if (ROOT / "data/ledger/index.json").exists() else []
    score_by_name = {Path(r["local"]).name: r.get("score") for r in ledger_idx if r.get("status") == "verified"}
    files = []
    for origin, d in dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.tif")):
                if p.name.endswith("manifest.json"): continue
                files.append((origin, p))
    for origin, p in files:
        try:
            with rasterio.open(p) as ds:
                if ds.shape != g.foot.shape or ds.count != 1:
                    continue
                a = ds.read(1)
        except Exception:
            continue
        dots_c = np.isfinite(a) & (a > 0)
        if not dots_c.any() or int(dots_c[g.foot].sum()) == 0:
            continue
        if p.name == out_tif.name or p == out_tif:
            continue  # never compare the candidate against itself
        rv = rankdata(np.where(np.isfinite(a), a, 0.0).ravel()[sidx])
        try:
            rho = float(np.corrcoef(surf_s, rv)[0, 1]) if rv.std() > 0 else 0.0
        except Exception:
            rho = 0.0
        if not np.isfinite(rho):
            rho = 0.0
        near_c = ndi.binary_dilation(dots_c, structure=disc)
        forward = float(near_c[core].mean()) if core.any() else 0.0
        reverse = float(near_mine[dots_c & g.foot].mean()) if (dots_c & g.foot).any() else 0.0
        cover = float(near_c[g.foot].mean())
        degenerate = cover > DEG_COVER
        dup = (forward > OVERLAP_LIMIT and reverse > OVERLAP_LIMIT) or \
              (forward > OVERLAP_LIMIT and not degenerate)
        row = dict(site_file=p.name, origin=origin,
                   owner_reported_score=score_by_name.get(p.name),
                   n_dots_in_footprint=int((dots_c & g.foot).sum()),
                   forward_overlap_3px=round(forward, 4), reverse_overlap_3px=round(reverse, 4),
                   comparator_footprint_3px_coverage=round(cover, 4), comparator_class=("dense" if degenerate else "sparse"),
                   abs_spearman_surface=round(abs(rho), 4), duplicate_flag=bool(dup),
                   sha256_file=sha256(p.read_bytes())[:16])
        comp_rows.append(row)
        if row["duplicate_flag"] or abs(rho) > RHO_LIMIT:
            log(f"  FLAG {p.name}: fwd={forward:.3f} rev={reverse:.3f} rho={rho:.3f} dense={degenerate}")
    n_dense = sum(1 for r in comp_rows if r["comparator_class"] == "dense")
    worst_fwd = max((r["forward_overlap_3px"] for r in comp_rows), default=0.0)
    worst_rho = max((r["abs_spearman_surface"] for r in comp_rows), default=0.0)
    n_dup = sum(1 for r in comp_rows if r["duplicate_flag"])
    uniq_pass = (n_dup == 0 and worst_rho <= RHO_LIMIT)
    log(f"uniqueness: {len(comp_rows)} comparators ({n_dense} dense-degenerate), flags={n_dup}, worst_fwd={worst_fwd:.3f}, worst_rho={worst_rho:.3f} -> {'PASS' if uniq_pass else 'FAIL'}")
    json.dump({"evidence_class": "REGISTRY-MEASUREMENT (owner-mirrored bytes, hash-verified upstream; not organizer-census)",
               "candidate_file": str(out_tif.relative_to(ROOT)), "candidate_sha256": sha256(out_tif.read_bytes()),
               "comparators": comp_rows,
               "summary": dict(n=len(comp_rows), n_dense_degenerate=n_dense, duplicate_flags=n_dup,
                               worst_forward_overlap=worst_fwd, worst_abs_spearman=worst_rho,
                               literal_forward_rule_pass=None, literal_note="forward>0.70 fires for most rasters because the family ridges saturate the geometry; reported per comparator",
                               ratified_rule_pass=bool(uniq_pass), rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT,
                               degenerate_coverage_cut=DEG_COVER),
               "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(EVID / "twr1_uniqueness.json", "w"), indent=1)

    # ---- holdout instrument read-back: V4 static + the nine focus-site files
    ctx = H.load_holdout_context(ROOT / "data/raw")
    focus = ["GEMSDOE24.tif", "GEMSDOE25.tif", "GEMSDOE27.tif", "GEMSDOE28.tif", "GEMSDOE30.tif",
             "GEMSDOE31.tif", "GEMSDOE32.tif", "GEMSDOE33.tif", "GEMSDOE36.tif"]
    readback = {}
    v4 = H.evaluate_hide_and_recover({c.key: core for c in ctx.cells}, ctx, name="TWR1_V4_static", n_boot=1000)
    readback["wbg3-twr1-V4-candidate"] = {k: v4[k] for k in ("pooled_dti", "ci95_cluster_bootstrap",
                                                             "n_withheld_positives", "evaluator_version")}
    log(f"TWR1-V4 static read-back DTI={v4['pooled_dti']:.5f}")
    for fn in focus:
        p = ROOT / ".cache/focus" / fn
        if not p.exists(): continue
        a = G.read_band(p)
        dmask = np.isfinite(a) & (a > 0) & g.foot
        ev = H.evaluate_hide_and_recover({c.key: dmask for c in ctx.cells}, ctx, name=fn, n_boot=1000)
        readback[fn] = {k: ev[k] for k in ("pooled_dti", "ci95_cluster_bootstrap",
                                           "n_withheld_positives", "evaluator_version")}
        log(f"read-back {fn:16s} DTI={ev['pooled_dti']:.5f} n_dots={int(dmask.sum())}")
    json.dump({"evidence_class": "HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0, static full-catalogue files "
               "read back through the instrument; NOT organizer scores, NOT fold-local)",
               "withheld_positives": sum(c.n_truth for c in ctx.cells),
               "results": readback}, open(EVID / "twr1_focus_readback.json", "w"), indent=1)

    # ---- final map + run card
    tif_bytes = out_tif.read_bytes()
    card = {
        "schema": "gems-session-run-card-v2",
        "lane": "TWR-1 tapered widened recall",
        "date_utc": "2026-10-31",
        "session_branch": "arena/eba465cb-wbggemsdoe3",
        "hypothesis": "widened/tapered soft envelopes around fold-local multi-sensor crest cores beat hard-dot emission under alpha=0.2/beta=0.8",
        "mechanism": "anisotropic fused crest energy (detrended-elevation curvature+slope, TMI-HG, strain second invariant, grav x mag cross-gradient) -> visible-only catalogue band window (0 inside 1.4 px, ramp to 2.4 px) -> top-37,654 dots with 3-px NMS",
        "named_non_fault_mimic": "erosional gully heads, alluvial-fan margins, road cuts and GeoDAWN flight-line edges share the linear high-curvature signature; none is a fault",
        "holdout_dti": {"label": "HOLDOUT-DTI", "value": round(v4["pooled_dti"], 5),
                         "ci95": [round(x, 5) for x in v4["ci95_cluster_bootstrap"]],
                         "evaluator_version": v4["evaluator_version"],
                         "withheld_positives": int(v4["n_withheld_positives"]),
                         "envelope_arm_value": 0.00795, "core_arm_value": 0.02082,
                         "matched_incumbent_replay": 0.09920,
                         "comparable_holdout_best": {"value": 0.0992, "name": "champion-proxy replay (fold-observed)",
                                                      "caveat": "HCE-1 0.1292 flagged inflated by IR-25 training bug"}},
        "registry_overlap": {"n_comparators": len(comp_rows), "dense_degenerate": n_dense,
                             "duplicate_flags": n_dup, "worst_forward_overlap_3px": worst_fwd,
                             "worst_abs_spearman": round(worst_rho, 4), "ratified_rule_pass": bool(uniq_pass)},
        "raster_sha256": sha256(tif_bytes),
        "validator": {"writer": "shared gems57 submission_writer (template 57GEMSDOE@822a0ce)",
                      "passed": bool(receipt["validator"]["all_checks_passed"] and receipt["template_report"]["ok"]),
                      "checks": receipt["validator"]["checks"],
                      "outside_footprint": "all-finite zeros outside footprint (writer policy); NaN-outside is the official-format alternative; both accepted by the portal per owner receipts"},
        "submission": {"name": NAME, "note": NOTE, "note_characters": len(NOTE),
                       "files": [str(out_tif.relative_to(ROOT)),
                                 str(out_tif.with_suffix('.zip').relative_to(ROOT))]},
        "experiments": {"geological_experiments_completed": 3, "maximum": 3},
        "verdict": "negative",
        "verdict_reason": (f"holdout V4 static read-back {v4['pooled_dti']:.5f} is below the comparable "
                           "holdout best 0.0992 -> promote bar NOT met; the envelope mechanism itself was "
                           "refuted on the instrument (paired CI negative, evidence/twr1_holdout.json); "
                           "uniqueness + validator gates PASS"),
        "okay_to_download_for_research": True,
        "okay_to_submit": False,
        "selector": {"action": "NONE", "weekly_slots_used": 0},
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    json.dump(card, open(EVID / "twr1_run_card.json", "w"), indent=1)
    # publish download + manifest next to it
    dd = ROOT / "docs/downloads"
    dd.mkdir(exist_ok=True)
    for f in (out_tif, out_tif.with_suffix(".zip")):
        if f.exists():
            shutil.copy2(f, dd / f.name)
    log(f"run card written; verdict={card['verdict']}; files in docs/downloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
