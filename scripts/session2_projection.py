#!/usr/bin/env python3
"""Calibrated PROJECTION (never a score) from hash-verified public dot masks + owner-reported claims.

Fits a small regression of structural dot-mask descriptors on the 118 hash-verified ledger
rasters whose live scores are OWNER-REPORTED (no organizer receipts).  Leave-one-site-out CV is
reported; predictions are labelled PROJECTION with an empirical residual interval.  Scores in the
executive table are NEVER presented as organizer-confirmed.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G, sgce  # noqa: E402
from gemsw.uniq2 import unpack, DISC  # noqa: E402

OUT = ROOT / "evidence" / "session2_projection.json"
CACHE = ROOT / ".cache" / "registry2"


def load_dots(dsha, shape):
    return unpack(np.load(CACHE / f"{dsha}.npy"), shape)


def descriptors(dots, g, near_ch, near_d28, d_cat, bins, block_n=32):
    n = int(dots.sum())
    if n == 0:
        return None
    H, W = dots.shape
    f = np.zeros(9, np.float64)
    f[0] = np.log10(n)
    f[1] = float((dots & near_ch).sum() / n)
    f[2] = float((dots & near_d28).sum() / n)
    f[3] = float((dots & (d_cat <= 3)).sum() / n)
    f[4] = float(np.minimum(d_cat[dots], 30).mean())
    by = (np.arange(H)[:, None] // block_n)
    bx = (np.arange(W)[None, :] // block_n)
    bid = by * int(np.ceil(W / block_n)) + bx
    f[5] = float(np.unique(bid[dots]).size / np.unique(bid[g.foot]).size)
    for j, name in enumerate(("geod_2ndinv", "tc", "det_elev_slope")):
        b = np.asarray(bins[sgce.FIELDS.index(name)])
        f[6 + j] = float(b[dots].mean())
    return f


def main() -> None:
    g = G.load_grid()
    bins = sgce.load_bins(g)
    reg = json.loads((ROOT / "registry" / "registry_session2.json").read_text())
    by_sha = {e["sha256"]: e["dots_sha256"] for e in reg["files"] if e["status"] == "ok"}
    ledger = json.loads((ROOT / "data" / "ledger" / "index.json").read_text())

    ch_path = next((ROOT / "data" / "ledger").glob("*h33-h33-2-b2*.tif"))
    d28_path = next((ROOT / "data" / "ledger").glob("*dotted-h19-5-d2-8-20261002*.tif"))
    import rasterio
    with rasterio.open(ch_path) as ds:
        a = ds.read(1)
    ch = np.isfinite(a) & (a > 0) & g.foot
    with rasterio.open(d28_path) as ds:
        a = ds.read(1)
    d28 = np.isfinite(a) & (a > 0) & g.foot
    near_ch = ndi.binary_dilation(ch, structure=DISC)
    near_d28 = ndi.binary_dilation(d28, structure=DISC)
    d_cat = ndi.distance_transform_edt(~g.labels).astype(np.float32)

    X, y, names, groups = [], [], [], []
    for r in ledger:
        s = r.get("score")
        dsha = by_sha.get(r["sha256"])
        if not (isinstance(s, (int, float)) and s > 0 and dsha and (CACHE / f"{dsha}.npy").exists()):
            continue
        f = descriptors(load_dots(dsha, g.foot.shape), g, near_ch, near_d28, d_cat, bins)
        if f is None:
            continue
        X.append(f); y.append(float(s)); names.append(r["submission"]); groups.append(r["site"])
    X, y = np.asarray(X), np.asarray(y)
    print(f"training rows {len(y)} sites {len(set(groups))}", flush=True)

    def loso(model_fn):
        pred = np.zeros_like(y)
        for site in sorted(set(groups)):
            tr = np.array([i for i, s in enumerate(groups) if s != site])
            te = np.array([i for i, s in enumerate(groups) if s == site])
            sc = StandardScaler().fit(X[tr])
            m = model_fn().fit(sc.transform(X[tr]), y[tr])
            pred[te] = m.predict(sc.transform(X[te]))
        mae = float(np.mean(np.abs(pred - y)))
        ss = float(np.sum((y - y.mean()) ** 2))
        r2 = float(1 - np.sum((pred - y) ** 2) / ss)
        return mae, r2, pred

    cand = {"ridge": loso(lambda: Ridge(alpha=3.0)),
            "forest": loso(lambda: RandomForestRegressor(n_estimators=200, min_samples_leaf=2,
                                                         random_state=7, n_jobs=2))}
    for k, v in cand.items():
        print(k, "LOSO MAE", round(v[0], 4), "R2", round(v[1], 3), flush=True)
    best = min(cand, key=lambda k: cand[k][0])
    mae, r2, pred = cand[best]
    resid = np.sort(np.abs(pred - y))
    q80 = float(resid[int(0.8 * len(resid)) - 1])
    sc = StandardScaler().fit(X)
    model = (Ridge(alpha=3.0) if best == "ridge" else
             RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=7, n_jobs=2)).fit(
                 sc.transform(X), y)

    def project(dots, label):
        f = descriptors(dots, g, near_ch, near_d28, d_cat, bins)
        if f is None:
            return None
        p = float(model.predict(sc.transform(f[None, :]))[0])
        return dict(label="PROJECTION", point=round(p, 4),
                    empirical_80pct_interval=[round(max(0.0, p - q80), 4), round(min(1.0, p + q80), 4)],
                    descriptors=dict(zip(
                        ["log10_dots", "overlap_champion_3px", "overlap_d28_3px", "frac_within_3px_catalogue",
                         "mean_catalogue_distance_cap30", "block_coverage_32px", "mean_bin_geod_2ndinv",
                         "mean_bin_tc", "mean_bin_det_elev_slope"],
                        [round(float(v), 5) for v in f])),
                    name=label)

    # Nine focus-site best files (pinned owner claims, independently re-read here).
    focus = json.loads((ROOT / "registry" / "focus_sites.json").read_text())["sites"]
    out_focus = {}
    for s in focus:
        dsha = by_sha.get(s["sha256"])
        if not dsha or not (CACHE / f"{dsha}.npy").exists():
            out_focus[s["site"]] = dict(error="pinned bytes not in local registry")
            continue
        dots = load_dots(dsha, g.foot.shape)
        out_focus[s["site"]] = dict(filename=s["path"].split("/")[-1], sha256=s["sha256"],
                                    owner_reported_unverified=float(s["owner_reported"]),
                                    n_dots=int(dots.sum()), projection=project(dots, s["path"].split("/")[-1]))
    # Other comparators
    extra = {}
    p = ROOT / "submission" / "wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif"
    if p.exists():
        import hashlib
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        dsha = by_sha.get(h)
        if dsha:
            extra["lst1_research_only"] = project(load_dots(dsha, g.foot.shape), p.name)
    # Released session-2 candidate (read the exact packed dot mask that was validated).
    cand_packed = ROOT / "data" / "work" / "session2_dots_packed.npy"
    cand_proj = None
    if cand_packed.exists():
        cand_dots = unpack(np.load(cand_packed), g.foot.shape)
        cand_proj = project(cand_dots, "released SGCE candidate")
    res = dict(evidence_class="PROJECTION — calibrated on OWNER-REPORTED claims; NOT a score or receipt",
               n_training=len(y), n_sites=len(set(groups)), model=best,
               leave_one_site_out=dict(mae=mae, r2=r2, residual_abs_q80=q80),
               owner_claim_max=float(y.max()),
               focus_sites=out_focus, extra=extra,
               candidate=dict(projection=cand_proj, n_dots=int(cand_dots.sum()) if cand_packed.exists() else None,
                              note="Same dot bytes as the released TIFF; projection is not a score."),
               caveats=["Training targets are owner-reported, not organizer-confirmed receipts.",
                        "The public leaderboard leader was 0.4544 on 2026-10-27; these claims top out at 0.2778, so the ledger is NOT representative of the current top of the board.",
                        "A projection is not a score, and no projection can validate a new method on hidden labels."])
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print("wrote", OUT, "model", best, "MAE", mae, flush=True)


if __name__ == "__main__":
    main()
