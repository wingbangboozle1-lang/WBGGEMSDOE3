#!/usr/bin/env python3
"""Re-measure the WINNING E1 arm AFTER the deterministic uniqueness repair.

Not a new hypothesis: same preregistered SGCE density, same sigma=15, same fold-local rebuild,
plus the registry-derived avoid zone that produced the released TIFF.  This is required so the
run card's HOLDOUT-DTI describes the actual released bytes rather than the un-repaired draft.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import sgce, grid as G, uniq2, holdout as H  # noqa: E402

T0 = time.time()


def tiles(foot):
    q = H.quadrant_ids(foot)
    out = {}
    for fold in range(4):
        rows = np.flatnonzero((q == fold).any(axis=1))
        cols = np.flatnonzero((q == fold).any(axis=0))
        out[fold] = (slice(max(0, int(rows[0]) - 6), min(foot.shape[0], int(rows[-1]) + 7)),
                     slice(max(0, int(cols[0]) - 6), min(foot.shape[1], int(cols[-1]) + 7)))
    return out


def build_dots(rho, geo, g, avoid=None, region=None):
    if region is None:
        dots = np.zeros(g.foot.shape, bool)
        for fold, bbox in tiles(g.foot).items():
            r = sgce.place(rho, g.labels, g.foot, geo, n_cap=45_000, mu=0.28, max_rounds=12,
                           iters=3, avoid=avoid, region=bbox)
            dots |= r["dots"]
        return dots
    r = sgce.place(rho, g.labels, g.foot, geo, n_cap=45_000, mu=0.28, max_rounds=12,
                   iters=3, avoid=avoid, region=region)
    return r["dots"]


def avoid_from(audit, shape, threshold=0.65):
    zone = np.zeros(shape, bool)
    used = []
    for r in audit["all_rows"]:
        if r["overlap"] > threshold and not r["lattice_like"]:
            ref = uniq2.unpack(np.load(ROOT / ".cache" / "registry2" / f"{r['dots_sha256']}.npy"), shape)
            zone |= ndi.binary_dilation(ref, structure=uniq2.DISC)
            used.append(dict(example=r["example"], overlap=round(float(r["overlap"]), 4)))
    return zone, used


def paired(a, b, n_boot=4000, seed=7):
    tpa, fpa, fna, act = a
    tpb, fpb, fnb, _ = b
    rng = np.random.default_rng(seed)
    f = lambda tp, fp, fn: tp.sum() / (tp.sum() + 0.2 * fp.sum() + 0.8 * fn.sum() + 1e-12)
    d0 = f(tpa, fpa, fna) - f(tpb, fpb, fnb)
    ds = []
    for _ in range(n_boot):
        i = rng.choice(act, size=len(act), replace=True)
        ds.append(f(tpa[i], fpa[i], fna[i]) - f(tpb[i], fpb[i], fnb[i]))
    return dict(delta=float(d0), ci95=[float(np.quantile(ds, 0.025)), float(np.quantile(ds, 0.975))],
                p_delta_le_0=float(np.mean(np.array(ds) <= 0)))


def main() -> None:
    g = G.load_grid()
    bins = sgce.load_bins(g)
    ctx = H.load_holdout_context(ROOT / "data" / "raw")
    geo = sgce.geometry(g.labels, g.foot, sigma=15.0)
    rho, _ = sgce.density(bins, g.labels, g.foot, geo)
    print(f"setup {time.time()-T0:.0f}s", flush=True)

    draft = build_dots(rho, geo, g)
    print(f"draft dots {int(draft.sum())} at {time.time()-T0:.0f}s; auditing...", flush=True)
    aud = uniq2.audit(draft, rho, g.foot)
    avoid, used = avoid_from(aud, g.foot.shape)
    np.save(ROOT / "data" / "work" / "session2_avoid.npy", np.packbits(avoid.ravel()))
    print(f"avoid zone {int(avoid.sum())} px from {len(used)} rasters at {time.time()-T0:.0f}s", flush=True)
    released = build_dots(rho, geo, g, avoid=avoid)
    build = json.loads((ROOT / "evidence" / "session2_build.json").read_text())
    packed = np.load(ROOT / "data" / "work" / "session2_dots_packed.npy")
    saved = uniq2.unpack(packed, g.foot.shape)
    same = bool(np.array_equal(saved, released))
    print(f"released dots {int(released.sum())}; identical to saved TIFF dots: {same} "
          f"at {time.time()-T0:.0f}s", flush=True)
    if not same:
        raise RuntimeError("repair did not reproduce the released dot mask; run card would be misleading")

    # champion proxy on identical folds
    d28p = next((ROOT / "data" / "ledger").glob("*dotted-h19-5-d2-8-20261002*.tif"))
    with rasterio.open(d28p) as ds:
        a28 = ds.read(1)
    d28 = np.isfinite(a28) & (a28 > 0) & g.foot
    ch = {}
    for cell in ctx.cells:
        vis = cell.visible_full
        d_vis = ndi.distance_transform_edt(~vis)
        ch[cell.key] = d28 & (d_vis > sgce.B_PX) & ~vis
    chev = H.evaluate_hide_and_recover(ch, ctx, name="champion_proxy", n_boot=1000)

    per_cell, info = {}, []
    for cell in ctx.cells:
        vis = cell.visible_full
        geo_c = sgce.geometry(vis, g.foot, 15.0)
        rho_c, _ = sgce.density(bins, vis, g.foot, geo_c)
        r = sgce.place(rho_c, vis, g.foot, geo_c, n_cap=45_000, mu=0.28, max_rounds=12,
                       iters=3, avoid=avoid, region=cell.bbox)
        per_cell[cell.key] = r["dots"]
        info.append(dict(cell=cell.key, n=r["n"]))
        print(f"  repaired {cell.key}: n={r['n']} t={time.time()-T0:.0f}s", flush=True)
    ev = H.evaluate_hide_and_recover(per_cell, ctx, name="E1_repaired", n_boot=1000)
    p = paired(ev["_block_totals"], chev["_block_totals"])
    out = dict(
        evidence_class="HOLDOUT-DTI on the RELEASED construction (after deterministic uniqueness repair)",
        experiment="E1_repaired (same preregistered hypothesis H1; not a new experiment)",
        evaluator=ev["evaluator_version"], n_withheld=ev["n_withheld_positives"],
        n_spatial_clusters=ev["n_spatial_clusters"],
        repaired=dict(pooled_dti=ev["pooled_dti"], ci95=ev["ci95_cluster_bootstrap"],
                      per_quadrant=ev["per_quadrant_dti"], cells=info,
                      avoid_zone_px=int(avoid.sum()), n_rasters_in_avoid_zone=len(used)),
        unrepaired_E1=json.loads((ROOT / "evidence" / "session2_holdout.json").read_text())["experiments"]["E1"]["pooled_dti"],
        champion_proxy=dict(pooled_dti=chev["pooled_dti"], ci95=chev["ci95_cluster_bootstrap"]),
        paired_delta_vs_champion_proxy=p,
        promotion_rule_passed=bool(p["ci95"][0] > 0),
        released_dots_match_saved_tiff=same,
        used_in_avoid_zone=used[:20],
    )
    json.dump(out, open(ROOT / "evidence" / "session2_holdout_repaired.json", "w"), indent=1, default=float)
    print("REPAIRED HOLDOUT-DTI", out["repaired"]["pooled_dti"], "CI", out["repaired"]["ci95"],
          "champion", out["champion_proxy"]["pooled_dti"], "paired", p, flush=True)

    # Rebind the run card to the released construction.
    card_p = ROOT / "evidence" / "session2_run_card.json"
    card = json.loads(card_p.read_text())
    card["holdout"]["candidate"] = dict(dti=out["repaired"]["pooled_dti"], ci95=out["repaired"]["ci95"])
    card["holdout"]["paired_delta_vs_champion_proxy"] = p
    card["holdout"]["unrepaired_E1_dti"] = out["unrepaired_E1"]
    card["holdout"]["uniqueness_repair"] = dict(
        applied=True, avoid_zone_px=int(avoid.sum()), n_rasters=len(used),
        note=("The released TIFF is the repaired construction. Its HOLDOUT-DTI is measured on the same "
              "fold-local rebuild with the same avoid zone; the earlier draft's 0.1489 is retained as "
              "unrepaired_E1_dti for transparency."))
    card["holdout"]["caveat"] += (" The released file includes a deterministic registry avoid-zone repair; "
                                  "this number measures that exact construction.")
    if not out["promotion_rule_passed"]:
        card["verdict"] = "negative"
        card["ok_to_submit"] = ("NO — repaired construction does not beat the champion on the matched holdout; "
                                "research-only file, no slot used.")
        card["ok_to_download"] = True
    json.dump(card, open(card_p, "w"), indent=1, default=float)
    b = json.loads((ROOT / "evidence" / "session2_build.json").read_text())
    b["avoid_zone_px"] = int(avoid.sum())
    b["avoid_zone_n_rasters"] = len(used)
    b["released_dots_reproduced_by_repair_holdout"] = same
    json.dump(b, open(ROOT / "evidence" / "session2_build.json", "w"), indent=1, default=float)
    print("run card rebound; verdict:", card["verdict"], flush=True)


if __name__ == "__main__":
    main()
