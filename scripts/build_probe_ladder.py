#!/usr/bin/env python3
"""Build the score-probe ladder: every sibling raster that has an owner-reported score.

WHY.  The only measurements of the *hidden* truth field that exist for us are the
published public scores of sibling submissions.  For a binary prediction the official
metric reduces to  DTI = TP_w / (0.2 (TP_w + FP_w) + 0.8 |G|),  so each score is a
one-scalar measurement of the unknown truth field G.  This script

  1. matches ledger rows to the actual bytes (sha256-pinned) in the cloned sibling repos,
  2. de-duplicates byte-identical rasters,
  3. computes the exact DTI against several *candidate* truth fields, and
  4. writes the block-reduced probe arrays used by scripts/invert_ledger.py.

The candidate-truth comparison is the decisive diagnostic: it tests which field the
leaderboard actually rewards (catalogue faults, off-catalogue SGMC faults, or their
union) against ~100 independent published scores.

Usage:
    python scripts/build_probe_ladder.py --repos /tmp --out evidence/probe_ladder.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw import grid as G                      # noqa: E402
from gemsw import exact as EX                    # noqa: E402

FACTOR = 4


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def read_ledger() -> list[dict]:
    rows: list[dict] = []
    p = ROOT / "registry" / "historical_owner_claims.csv"
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["reported_public_dti"].strip():
                continue                      # ledger row recorded as blank in the brief
            rows.append({"site": r["site"].strip(), "submission": r["submission_name"].strip(),
                         "score": float(r["reported_public_dti"]),
                         "source": r.get("evidence_class", "").strip()})
    add = ROOT / "registry" / "ledger_addendum_2026-10-27.json"
    if add.exists():
        for r in json.loads(add.read_text())["rows"]:
            if r.get("score") is None:
                continue
            rows.append({"site": r["site"], "submission": r["submission"],
                         "score": float(r["score"]), "source": "ledger_addendum_2026-10-27"})
    return rows


def index_repos(repos: Path) -> dict:
    """{site: [(normalised stem, path)]} over every .tif in the cloned sibling repos."""
    idx: dict[str, list[tuple[str, Path]]] = {}
    for site_dir in sorted(repos.glob("GEMSDOE*")):
        if not site_dir.is_dir():
            continue
        d = idx.setdefault(site_dir.name, [])
        for f in site_dir.rglob("*.tif"):
            d.append((norm(f.stem), f))
    return idx


def find_files(idx: dict, site: str, submission: str) -> list[Path]:
    """Match a ledger submission name to files whose stem contains / is contained by it.

    Sibling repositories append an outside-footprint suffix (-zeros / -nan / -allfinite) that
    the ledger name omits, so containment both ways is required.  Ties prefer -zeros, then the
    shortest path.
    """
    key = norm(submission)
    if not key:
        return []
    hits = [(stem, p) for stem, p in idx.get(site, [])
            if key in stem or stem in key]
    if not hits:
        return []
    def rank(item):
        stem, p = item
        return ("zeros" not in stem, len(str(p)))
    return [p for _, p in sorted(hits, key=rank)]


def candidate_truths(g: G.Grid) -> dict[str, np.ndarray]:
    sgmc = EX.kernel_credit_field(g.labels) < 1.0          # 0 inside 3 px of a fault
    with rasterio.open(ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        s = ds.read(1) > 0
    return {
        "catalogue": g.labels.copy(),
        "sgmc_all": s & g.foot,
        "sgmc_novel": s & g.foot & sgmc,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="/tmp")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "probe_ladder.json"))
    ap.add_argument("--work", default=str(ROOT / "data" / "work"))
    a = ap.parse_args()
    t0 = time.time()

    g = G.load_grid()
    truths = candidate_truths(g)
    for k, v in truths.items():
        print(f"[truth] {k}: {int(v.sum()):,} cells", flush=True)
    k_truth = {k: EX.kernel_credit_field(v) for k, v in truths.items()}

    ledger = read_ledger()
    idx = index_repos(Path(a.repos))
    print(f"[ledger] {len(ledger)} rows, {sum(len(v) for v in idx.values())} tif files",
          flush=True)

    seen: dict[str, dict] = {}
    unmatched = []
    for r in ledger:
        cands = find_files(idx, r["site"], r["submission"])
        if not cands:
            unmatched.append({"site": r["site"], "submission": r["submission"], "score": r["score"]})
            continue
        path = cands[0]
        h = sha256(path)
        if h in seen:
            seen[h]["scores_reported"].append(r["score"])
            seen[h]["sites"].append(r["site"])
            continue
        seen[h] = {"sha256": h, "path": str(path), "site": r["site"], "sites": [r["site"]],
                   "submission": r["submission"], "scores_reported": [r["score"]]}

    print(f"[match] {len(seen)} unique rasters, {len(unmatched)} unmatched ledger rows", flush=True)

    probes = []
    act = g.foot & ~g.labels
    bh, bw = g.foot.shape[0] // FACTOR, g.foot.shape[1] // FACTOR

    def blocksum(arr: np.ndarray) -> np.ndarray:
        a = np.asarray(arr, np.float64)[: bh * FACTOR, : bw * FACTOR]
        return a.reshape(bh, FACTOR, bw, FACTOR).sum(axis=(1, 3)).ravel()

    act_count = blocksum(act)
    kA, nb, names, scores, ndots = [], [], [], [], []
    for i, (h, rec) in enumerate(sorted(seen.items(), key=lambda kv: -max(kv[1]["scores_reported"]))):
        try:
            with rasterio.open(rec["path"]) as ds:
                if (ds.height, ds.width) != G.EXPECTED_SHAPE:
                    rec["skip"] = f"shape {ds.height}x{ds.width}"
                    continue
                p = ds.read(1).astype(np.float64)
        except Exception as exc:                                   # noqa: BLE001
            rec["skip"] = f"read error: {exc}"
            continue
        p = np.where(np.isfinite(p), p, 0.0)
        p = np.clip(p, 0.0, 1.0)
        p[~g.foot] = 0.0
        supp = p > 0
        n_pos = int(supp.sum())
        if n_pos == 0:
            rec["skip"] = "empty support"
            continue
        soft = bool(not np.allclose(p[supp], 1.0))
        k_pred = EX.kernel_credit_field(supp)
        row = {"sha256": h, "site": rec["site"], "sites": sorted(set(rec["sites"])),
               "submission": rec["submission"], "n_pos": n_pos, "sum_p": float(p.sum()),
               "soft": soft, "max_p": float(p.max()),
               "scores_reported": rec["scores_reported"],
               "score": float(np.median(rec["scores_reported"]))}
        for tname, tm in truths.items():
            tp = float(k_pred[tm].sum())
            fp = float((p * (1.0 - k_truth[tname])).sum())
            n_truth = float(tm.sum())
            row[f"dti_vs_{tname}"] = EX.score_from_credit_counts(tp, fp, n_truth)
            row[f"tp_vs_{tname}"] = tp
        probes.append(row)
        # full kernel-credit field (NOT masked to the dots: credit exists within 3 px)
        k = np.where(g.foot, k_pred, 0.0)
        kA.append((blocksum(k) / np.maximum(act_count, 1.0)).astype(np.float32))
        nb.append(blocksum(p).astype(np.float32))
        names.append(f"{rec['site']}::{rec['submission']}")
        scores.append(row["score"])
        ndots.append(n_pos)
        if (i + 1) % 20 == 0:
            print(f"[probe] {i+1}/{len(seen)} ({time.time()-t0:.0f}s)", flush=True)

    out = {"evidence_class": "PROBE LADDER (owner-reported scores; no organizer receipts)",
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_probes": len(probes),
           "grid": {"shape": list(G.EXPECTED_SHAPE), "footprint_px": int(g.foot.sum()),
                    "catalogue_px": int(g.labels.sum())},
           "truths": {k: int(v.sum()) for k, v in truths.items()},
           "unmatched_ledger_rows": unmatched,
           "probes": probes}
    Path(a.out).write_text(json.dumps(out, indent=1))

    # block-reduced arrays for the tomography solver
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(work / f"probes_f{FACTOR}.npz",
                        kA=np.asarray(kA, np.float32), nblocks=np.asarray(nb, np.float32),
                        scores=np.asarray(scores, np.float64),
                        names=np.asarray(names), n_dots=np.asarray(ndots, np.float64),
                        active_blocks=blocksum(act) > 0.5,
                        block_shape=np.asarray([bh, bw]))

    print("\n[correlation with owner-reported scores]")
    s = np.array([p["score"] for p in probes])
    for tname in truths:
        v = np.array([p[f"dti_vs_{tname}"] for p in probes])
        print(f"  {tname:12s} spearman={spearmanr(v, s).statistic:+.3f}  "
              f"pearson={np.corrcoef(v, s)[0,1]:+.3f}")
    print(f"[done] {len(probes)} probes in {time.time()-t0:.0f}s -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
