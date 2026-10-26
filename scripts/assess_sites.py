#!/usr/bin/env python3
"""Per-site executive table: best owner-reported file and best UNSCORED file (LST projection band), with automatic
format validation, dot-identity and near-duplicate (3-px overlap) audit, and download links."""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G, ledger as L, uniq, writer as W

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
t0 = time.time()
g = G.load_grid()
reg = json.load(open(ROOT / "registry/registry_index.json"))["files"]
led = json.load(open(ROOT / "data/ledger/index.json"))
led_by_sha = {e["sha256"]: e for e in led if e["status"] == "verified"}
d = dict(np.load(ROOT / "data/work/design.npz", allow_pickle=True)); names = list(d["names"]); fi = names.index("NUIS_catxH")
dr = dict(np.load(ROOT / "data/work/design_registry.npz")); drm = json.load(open(ROOT / "data/work/design_registry_meta.json"))
key_idx = {m["key"]: i for i, m in enumerate(drm)}
z = np.load(ROOT / "data/work/lst_model.npz", allow_pickle=True); boot = np.asarray(z["lam_boot"])
S = d["S"][fi][None, :]; cols = [(0, b) for b in range(64)]
def band(i):
    v = [L.project(lb, cols, dr["A"][i][fi][None, :], dr["B"][i][fi][None, :], dr["N"][i], S)["dti"] for lb in boot]
    return [float(np.quantile(v, q)) for q in (.1, .5, .9)]
# dots_sha -> scored ledger raster (dot-identical => same score for binary masks)
scored_dots = {}
for e in reg:
    if e["site"] == "ledger" and e["sha256"] in led_by_sha and e["status"] == "ok":
        scored_dots.setdefault(e["dots_sha256"], []).append(led_by_sha[e["sha256"]])
heads = {s: subprocess.check_output(["git", "-C", str(ROOT / ".cache/sites" / s), "rev-parse", "HEAD"], text=True).strip() for s in SITES}
remote = {s: subprocess.check_output(["git", "-C", str(ROOT / ".cache/sites" / s), "remote", "get-url", "origin"], text=True).strip() for s in SITES}
out = {}
picks = []
for s in SITES:
    files = [e for e in reg if e["site"] == s and e["status"] == "ok" and 1000 <= e["n_dots"] <= uniq.MAX_SUBMISSION_DOTS
             and "audit_sources" not in e["path"] and "/inputs/" not in e["path"]]
    rows = []
    for e in files:
        key = e["dots_sha256"] if e["binary"] else e["sha256"]
        if key not in key_idx:
            continue
        sc = led_by_sha.get(e["sha256"]) or None
        same = scored_dots.get(e["dots_sha256"], []) if e["binary"] else []
        live = sc["score"] if sc else (max(x["score"] for x in same) if same else None)
        rel = e["path"].split(f".cache/sites/{s}/", 1)[-1]
        b = band(key_idx[key])
        fmt_ok = e["nan_in_footprint"] == 0 and e["out_of_range_in_footprint"] == 0
        rows.append(dict(file=Path(e["path"]).name, rel=rel, n_dots=e["n_dots"], sha256=e["sha256"], dots_sha256=e["dots_sha256"],
                         owner_reported_score=live, scored_via=("exact sha" if sc else ("dot-identical to a scored raster" if same else None)),
                         lst_p10_p50_p90=b, format_flags_ok=bool(fmt_ok), on_catalogue_positive=e["on_catalogue_positive"],
                         url_blob=f"{remote[s].removesuffix('.git')}/blob/{heads[s]}/{rel}", url_raw=f"{remote[s].removesuffix('.git')}/raw/{heads[s]}/{rel}"))
    scored = sorted([r for r in rows if r["owner_reported_score"] is not None], key=lambda r: -r["owner_reported_score"])
    # unscored = no sha/dot match to the ledger; dedupe by dots_sha; best by LST median
    seen, uns = set(), []
    for r in sorted([r for r in rows if r["owner_reported_score"] is None and r["format_flags_ok"]], key=lambda r: -r["lst_p10_p50_p90"][1]):
        if r["dots_sha256"] in seen:
            continue
        seen.add(r["dots_sha256"]); uns.append(r)
    out[s] = dict(head=heads[s], remote=remote[s], n_files=len(rows), best_scored=scored[:2], best_unscored=uns[:2],
                  n_format_flagged=sum(1 for r in rows if not r["format_flags_ok"]))
    picks += [(s, "scored", r) for r in scored[:1]] + [(s, "unscored", r) for r in uns[:1]]
print("picks", len(picks), f"{time.time()-t0:.0f}s", flush=True)
# near-duplicate audit for the picks against every other registry mask (shared dilations)
pick_dots = []
for s, kind, r in picks:
    pick_dots.append(uniq.unpack(np.load(ROOT / ".cache/registry" / f"{r['dots_sha256']}.npy"), g.foot.shape))
uniq_dots = {}
for e in reg:
    if e["status"] == "ok" and 1000 <= e["n_dots"] <= uniq.MAX_SUBMISSION_DOTS and "audit_sources" not in e["path"]:
        uniq_dots.setdefault(e["dots_sha256"], e)
worst = [dict(max_overlap=0.0, vs=None, max_lattice_excess=-1.0, lattice_vs=None) for _ in picks]
foot_n = float(g.foot.sum())
for k, (dsha, e) in enumerate(uniq_dots.items()):
    ref = uniq.unpack(np.load(ROOT / ".cache/registry" / f"{dsha}.npy"), g.foot.shape)
    near = ndi.binary_dilation(ref, structure=uniq.DISC)
    for j, (s, kind, r) in enumerate(picks):
        if r["dots_sha256"] == dsha:
            continue
        ov = float((pick_dots[j] & near).sum() / max(r["n_dots"], 1))
        nul = float((near & g.foot).sum() / foot_n)          # analytic random-placement overlap
        if nul >= 0.70:                                       # lattice-like reference: judge by excess over null
            if ov - nul > worst[j]["max_lattice_excess"]:
                worst[j]["max_lattice_excess"] = ov - nul; worst[j]["lattice_vs"] = e["path"].split(".cache/sites/")[-1][:90]
        elif ov > worst[j]["max_overlap"] and int(ref.sum()) < 400_000:
            worst[j].update(max_overlap=ov, vs=e["path"].split(".cache/sites/")[-1][:90], vs_n_dots=int(ref.sum()))
    if k % 60 == 0:
        print("audit", k, f"{time.time()-t0:.0f}s", flush=True)
tpl = ROOT / "data/raw/sample_submission.tif"
for j, (s, kind, r) in enumerate(picks):
    worst[j]["unique"] = bool(worst[j]["max_overlap"] <= 0.70 and worst[j]["max_lattice_excess"] <= 0.05)
    r["max_overlap_vs_other_registry_raster"] = worst[j]
    p = ROOT / ".cache/sites" / s / r["rel"]
    v = W.validate(p, tpl, g.foot, g.labels)
    r["validator"] = dict(passed=v["passed"], failed_checks=[k for k, ok in v["checks"].items() if not ok])
json.dump(dict(generated_utc="2026-10-26", note="owner_reported_score = recorded by sibling repos; lst band = PROJECTION (not a score)",
               sites=out), open(ROOT / "evidence/site_assessment.json", "w"), indent=1, default=float)
print("done", f"{time.time()-t0:.0f}s")
