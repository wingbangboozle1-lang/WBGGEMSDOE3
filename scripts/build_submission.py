#!/usr/bin/env python3
"""Build the W1' candidate on the REAL catalogue, audit uniqueness, write + validate the GeoTIFF pair, emit run card."""
from __future__ import annotations

# Historical LST1 path is quarantined: do not regenerate approval claims or
# place/repair dots after the literal any-registry duplicate STOP.
raise SystemExit(
    "DISABLED / DO NOT SUBMIT: LST1 used an unauthorized dense-registry "
    "exception and failed the promotion gate. See evidence/run_card.json."
)
import json, sys, time, hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import candidate as C, grid as G, ledger as L, uniq, writer as W, alloc as A

t0 = time.time()
g = G.load_grid()
active = g.foot & ~g.labels
model = C.load_model(ROOT / "data/work/lst_model.npz")
bz = np.load(ROOT / "data/work/bins.npz")
bins_foot = {k: bz[k] for k in C.MOD_FIELDS}
h = G.read_band(ROOT / "data/raw/scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif")
h_dots = np.isfinite(h) & (h > 0) & g.foot
h_dist = ndi.distance_transform_edt(~h_dots)
ON_SHARE = C.ON_SHARE_FINAL
avp = ROOT / "data/work/avoid_mask_packed.npy"
avoid = np.unpackbits(np.load(avp))[: g.foot.size].reshape(g.foot.shape).astype(bool) if avp.exists() else None
history = []
for rep in range(5):
    r = C.build(model, bins_foot, g.foot, g.labels, h_dots, h_dist, on_share=ON_SHARE, use_mod=True, iters=3, avoid=avoid,
                verbose=False)
    dots = r["dots"] & active
    aud = uniq.audit(dots, dots, ROOT, g.foot)
    history.append(dict(rep=rep, n=int(dots.sum()), n_on=r["n_on"], n_off=r["n_off"], U3_max_overlap_nonlattice=aud["U3_max_overlap_nonlattice"],
                        U2_max_abs_spearman=aud["U2_max_abs_spearman"], avoid_px=0 if avoid is None else int(avoid.sum())))
    print("repair loop", history[-1], f"t={time.time()-t0:.0f}s", flush=True)
    if aud["unique_pass"]:
        break
    new_avoid, used = uniq.avoid_zone(aud["all_rows"], ROOT, g.foot.shape, ON_SHARE - 0.02, avoid)
    changed = avoid is None or int(new_avoid.sum()) != int(avoid.sum())
    avoid = new_avoid
    print("  avoid zone now", int(avoid.sum()), "px from", len(used), "rasters; changed:", changed, flush=True)
    if not changed:
        print("  repair loop cannot improve further; reporting the audit as-is", flush=True)
        break
if avoid is not None:
    np.save(avp, np.packbits(avoid.ravel()))
print(f"built n={int(dots.sum())} on={r['n_on']} off={r['n_off']} t={time.time()-t0:.0f}s", flush=True)
dsha = uniq.dots_sha(dots)
tag = dsha[:8]
name = f"wbggems3-lst1-hybrid-20261026-{tag}"
out = ROOT / "submission"; out.mkdir(exist_ok=True)
tpl = ROOT / "data/raw/sample_submission.tif"
f_zero = W.write_submission(dots.astype(np.float32), g.foot, g.labels, tpl, out / f"{name}-zeros.tif", "zeros")
f_nan = W.write_submission(dots.astype(np.float32), g.foot, g.labels, tpl, out / f"{name}-nan.tif", "nan")
f_zip = W.write_zip(f_zero, out / f"{name}-zeros.zip")
val = {p.name: W.validate(p, tpl, g.foot, g.labels) for p in (f_zero, f_nan)}
for k, v in val.items():
    print(k, "PASSED" if v["passed"] else "FAILED", v["sha256"][:16], flush=True)
# read-back equality: the dots in the saved bytes are exactly the dots we audited
import rasterio
with rasterio.open(f_zero) as ds:
    back = ds.read(1)
assert np.array_equal(back > 0, dots), "saved bytes != audited dots"

# read-back equality: the dots in the saved bytes are exactly the dots we audited
import rasterio
with rasterio.open(f_zero) as ds:
    back = ds.read(1)
assert np.array_equal(back > 0, dots), "saved bytes != audited dots"

# ---- uniqueness (registry = nine sites + ledger + raw/scored; 4 grid-mismatch files excluded and listed) ----
aud = uniq.audit(dots, dots, ROOT, g.foot)
print("uniqueness:", {k: aud[k] for k in aud if k.startswith(("U", "unique"))}, flush=True)

# ---- LST projection BAND (stratum model, 200 bootstrap refits) with calibrators ----
d = np.load(ROOT / "data/work/design.npz", allow_pickle=True)
names = list(d["names"]); fi = names.index("NUIS_catxH")
meta = json.load(open(ROOT / "data/work/design_meta.json"))
sel = active[g.foot]
d_cat = ndi.distance_transform_edt(~g.labels)
code = (C.cat_code(d_cat[g.foot]) * 8 + C.h_code(h_dist[g.foot]))[sel].astype(np.uint8)
row = L.design_row(dots.astype(np.float32), active, {"NUIS_catxH": code}, 64)
S1 = np.bincount(code, minlength=64).astype(float)[None, :]
cols = [(0, b) for b in range(64)]
def band(A_i, B_i, N_i):
    v = [L.project(lb, cols, A_i[None, :], B_i[None, :], N_i, S1)["dti"] for lb in model["lam_boot"]]
    return dict(p10=float(np.quantile(v, .1)), p50=float(np.quantile(v, .5)), p90=float(np.quantile(v, .9)))
proj = band(row["A"][0], row["B"][0], row["N"])
cal = []
for nm in ("h33-h33-2-b2", "dotted-h19-5-d2-8", "gems70-p5", "gate_ortho", "h25-1-dotted-h19-5-d1-5"):
    for i, m in enumerate(meta):
        if nm in m["submission"]:
            cal.append(dict(submission=m["submission"], live_owner_reported=float(d["s"][i]), lst_band=band(d["A"][i][fi], d["B"][i][fi], d["N"][i])))
            break
fit = json.load(open(ROOT / "evidence/lst_fit.json"))
nested = fit["nested_family_cv"]
res = dict(name=name, dots=int(dots.sum()), n_on_network=r["n_on"], n_off_network=r["n_off"], on_share=ON_SHARE, dots_sha256=dsha,
           repair_history=history, avoid_zone_px=0 if avoid is None else int(avoid.sum()),
           model_expected_dti_internal_NOT_A_SCORE=r["expected"], lst_stratum_projection_band=proj, calibrators=cal,
           lst_error=dict(nested_leave_site_out_mae=nested["mae"], abs_err_q90=nested["abs_err_q90"], mae_top20=nested["mae_top20"]),
           files={p.name: dict(sha256=W.sha256_file(p), bytes=p.stat().st_size) for p in (f_zero, f_nan, f_zip)},
           validation=val, uniqueness=aud)
json.dump(res, open(ROOT / "evidence/build_result.json", "w"), indent=1, default=float)
np.save(ROOT / "data/work/candidate_dots_packed.npy", np.packbits(dots.ravel()))
print("PROJECTION BAND (not a score):", proj, "calibrators:", [(c["live_owner_reported"], c["lst_band"]["p50"]) for c in cal], "t=%.0fs" % (time.time() - t0))
