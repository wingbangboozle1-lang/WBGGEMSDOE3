#!/usr/bin/env python3
"""H66-SPRP uniqueness audit against the indexed public owner-repository registry.

TWO READINGS ARE REPORTED, BOTH FROM THE SHARED TEMPLATE TOOL:

1. LITERAL reading (the inherited definition: every positive finite pixel of a
   registry raster is a "dot").  A registered continuous probability surface
   that is positive on the whole footprint makes this test fire for ANY
   non-empty candidate; it is reported, not hidden.
2. LIKE-FOR-LIKE reading (the same thresholds applied to registry rasters that
   are discrete dot fields, i.e. rasters whose positive support covers at most
   ``DENSE_SUPPORT_FRACTION`` of the footprint).  A dot-overlap test only
   carries information against a comparator that is itself a dot field.

A third reading, PR-01 informative-probe (knowledge/pr-01-uniqueness-protocol.md),
keeps only comparators whose 3-px dilated support covers <= 60 % of the
footprint, because a comparator that is positive everywhere carries no
positional information about where a fault is.

The rank-correlation test is applied to EVERY registry raster in every reading.

Every number here is a REGISTRY MEASUREMENT, never a score.  Nothing in this
file decides whether a file may be uploaded: the selector step is separate.

Usage:
    python scripts/h66_uniqueness.py --candidate submission/<file>.tif --shard 0 --nshards 2 \
        --out evidence/h66_sprp/uniqueness_shard0.json
    python scripts/h66_uniqueness.py --candidate submission/<file>.tif \
        --merge evidence/h66_sprp/uniqueness_shard*.json \
        --out evidence/h66_sprp/uniqueness.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_COMMIT = "822a0ce5546c7b6749cdd82eb145b6b3e616603d"
TPL = ROOT / ".cache" / f"57GEMSDOE-{TEMPLATE_COMMIT}"
sys.path.insert(0, str(TPL / "src"))
from gems57 import grid as G                    # noqa: E402
from gems57 import uniqueness as U              # noqa: E402

OUT = ROOT / "evidence" / "h66_sprp"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".cache" / "registry"
LEDGER = ROOT / "data" / "ledger"
SCORED = ROOT / "data" / "raw" / "scored"
REPO_SUBS = ROOT / "submission"
PR01_COVERAGE_CAP = 0.60      # knowledge/pr-01-uniqueness-protocol.md
SKIP_NAMES = ("labels.tif", "existing_faults.tif", "sample_submission.tif")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_registry(exclude_sha: set[str] | None = None) -> list[dict]:
    """Every sibling raster we can hash-verify locally, deduplicated by sha256.

    The candidate's own bytes are never part of the comparison set.
    """
    exclude_sha = set(exclude_sha or ())
    found: dict[str, dict] = {}
    groups = [(CACHE, "registry-cache"), (LEDGER, "ledger"), (SCORED, "scored-mirror"),
              (REPO_SUBS, "this-repo")]
    for base, label in groups:
        if not base.exists():
            continue
        for p in sorted(base.glob("*.tif")):
            if p.name in SKIP_NAMES:
                continue
            try:
                digest = sha256_file(p)
            except OSError:
                continue
            if digest in exclude_sha:
                print(f"[registry] excluded (candidate bytes): {p}", flush=True)
                continue
            if digest in found:
                found[digest]["sources"].append(f"{label}:{p.name}")
                continue
            found[digest] = dict(repo_first=label, sources=[f"{label}:{p.name}"],
                                 cache_file=str(p), sha256=digest)
    return list(found.values())


def candidate_meta(cand: np.ndarray, fp: np.ndarray, cand_path: Path) -> dict:
    values = cand[fp]
    ranks = np.argsort(np.argsort(values)).astype(np.float64)
    norm = float(np.linalg.norm(ranks - ranks.mean()))
    return dict(my_file=str(cand_path.relative_to(ROOT)),
                my_dots=int((np.isfinite(cand) & (cand > 0) & fp).sum()),
                candidate_decoded_sha256=hashlib.sha256(
                    np.ascontiguousarray(cand.astype(np.float32)).tobytes()).hexdigest(),
                candidate_file_sha256=sha256_file(cand_path),
                candidate_rank_variation=bool(norm > 0))


def run_shard(cand: np.ndarray, cand_path: Path, records: list[dict], out: Path) -> None:
    g = G.load_grid(TPL / "data" / "bridge")
    index = dict(rasters=records, complete_accessible_scan=True, errors=[],
                 note=("Hash-verified public owner-repository rasters reachable from this "
                       "checkout. NOT a complete organizer registry: external, private, "
                       "unlinked or later-written files may be absent."))
    result = U.compare_array_to_registry(
        cand, index, g.footprint,
        file_sha256=sha256_file(cand_path),
        include_reverse=True,
        expected_grid=None,
        progress=lambda i, n, row: print(f"  [{i}/{n}] {row.get('submission')}", flush=True)
        if i % 25 == 0 else None)
    rows = result["rows"]
    # PR-01 coverage of each comparator: how much of the footprint its 3-px
    # dilated support covers.  A comparator that covers everything cannot
    # discriminate position.
    for row in rows:
        if "error" in row:
            row["their_support_coverage_3px"] = None
            row["informative_probe"] = False
            continue
        p = Path(row["file"])
        with rasterio.open(p) as src:
            theirs = src.read(1).astype(np.float32)
        theirs = np.where(np.isfinite(theirs), theirs, 0.0)
        support = (theirs > 0) & g.footprint
        if support.any():
            cov = float(U._near(support)[g.footprint].sum() / g.footprint.sum())
        else:
            cov = 0.0
        row["their_support_coverage_3px"] = cov
        row["informative_probe"] = bool(cov <= PR01_COVERAGE_CAP)
    out.write_text(json.dumps(dict(shard_rows=rows, n=len(rows)), indent=1,
                               allow_nan=False) + "\n")
    print(f"[shard] {len(rows)} rows -> {out}")


def merge(shard_files: list[str], cand_path: Path, out: Path) -> None:
    g = G.load_grid(TPL / "data" / "bridge")
    with rasterio.open(cand_path) as src:
        cand = src.read(1).astype(np.float32)
    merged: dict[str, dict] = {}
    for f in shard_files:
        for path in sorted(glob.glob(f)):
            blob = json.loads(Path(path).read_text())
            for row in blob["shard_rows"]:
                key = row.get("sha256") or row.get("file")
                if key in merged:
                    continue
                merged[key] = row
    rows = list(merged.values())
    expected = len(rows)
    summary = U.summarize_registry_rows(
        rows, registry_rasters_expected=expected, complete_accessible_scan=True,
        source_errors=[], candidate_meta=candidate_meta(cand, g.footprint, cand_path),
        scope=("All hash-verified accessible entries in the indexed public owner-repository "
               "inventory; not a complete organizer registry. External/private/unlinked/"
               "inaccessible files may be absent. Reverse overlap is diagnostic only."))
    two = U.two_phase_summary(rows, int(g.footprint.sum()), expected_rasters=expected)

    informative = [r for r in rows if r.get("informative_probe")]
    excluded = [dict(submission=r.get("submission"), repo=r.get("repo"),
                     coverage_3px=r.get("their_support_coverage_3px"),
                     their_dots=r.get("their_dots"),
                     forward_overlap=r.get("my_dots_within_3px_of_theirs"))
                for r in rows if r.get("informative_probe") is False]
    worst_info = max((r.get("my_dots_within_3px_of_theirs") or 0.0) for r in informative) \
        if informative else 0.0
    worst_info_name = None
    for r in informative:
        if (r.get("my_dots_within_3px_of_theirs") or 0.0) == worst_info:
            worst_info_name = r.get("submission")
    pr01_pass = bool(informative) and worst_info <= U.OVERLAP_LIMIT
    rank_rows = [r for r in rows if r.get("spearman_full_footprint") is not None]
    max_abs_rho = max((abs(r["spearman_full_footprint"]) for r in rank_rows), default=0.0)
    worst_rho_name = None
    for r in rank_rows:
        if abs(r["spearman_full_footprint"]) == max_abs_rho:
            worst_rho_name = r.get("submission")

    result = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        candidate=str(cand_path.relative_to(ROOT)),
        candidate_sha256=sha256_file(cand_path),
        my_dots=int((np.isfinite(cand) & (cand > 0) & g.footprint).sum()),
        registry_rasters_checked=expected,
        registry_rasters_expected=expected,
        literal_reading=dict(
            summary=two,
            worst_spearman=two["literal_reading"].get("worst_spearman_full_footprint"),
            worst_spearman_submission=two["literal_reading"].get("worst_spearman_submission"),
            worst_forward_overlap=two["literal_reading"].get("worst_forward_overlap"),
            worst_overlap_submission=two["literal_reading"].get("worst_overlap_submission"),
            forward_overlap_firings=two["literal_reading"].get("forward_overlap_firings"),
            rho_firings=two["literal_reading"].get("rho_firings"),
            duplicate=two["literal_reading"].get("duplicate"),
            note=("Literal inherited definition (every positive finite pixel is a dot). A "
                  "registered continuous surface that is positive over the whole footprint "
                  "fires this test for every non-empty candidate; the firing is reported "
                  "here and is not a statement about copying."),
            firings=two.get("literal_firings", [])),
        like_for_like_reading=dict(
            dot_field_rasters=two["like_for_like_reading"].get("dot_field_rasters"),
            continuous_surface_rasters=two["like_for_like_reading"].get("continuous_surface_rasters"),
            worst_forward_overlap=two["like_for_like_reading"].get("worst_forward_overlap_dot_fields"),
            worst_forward_overlap_submission=two["like_for_like_reading"].get(
                "worst_forward_overlap_dot_field_submission"),
            worst_reverse_overlap=two["like_for_like_reading"].get("worst_reverse_overlap"),
            forward_overlap_firings=two["like_for_like_reading"].get("forward_overlap_firings"),
            duplicate=two["like_for_like_reading"].get("duplicate")),
        pr01_informative_probe_reading=dict(
            rule=("comparators whose 3-px dilated support covers <= 60 % of the footprint "
                  "(knowledge/pr-01-uniqueness-protocol.md); all other comparators are "
                  "listed, never silently dropped"),
            coverage_cap=PR01_COVERAGE_CAP,
            n_informative=len(informative), n_excluded=len(excluded),
            worst_forward_overlap=worst_info, worst_forward_overlap_submission=worst_info_name,
            excluded=excluded, passed=pr01_pass),
        max_abs_spearman_all_registries=max_abs_rho,
        worst_abs_spearman_submission=worst_rho_name,
        spearman_limit=U.RHO_LIMIT, spearman_passed=bool(max_abs_rho <= U.RHO_LIMIT),
        identical_bytes=summary.get("byte_unique_among_checked"),
        identical_pixels=summary.get("pixel_unique_among_checked"),
        shared_tool_summary={k: v for k, v in summary.items() if k != "rows"},
        scope=summary.get("scope"),
        rows=rows,
    )
    out.write_text(json.dumps(result, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in (
        "my_dots", "registry_rasters_checked", "max_abs_spearman_all_registries",
        "spearman_passed", "identical_bytes", "identical_pixels")}, indent=1))
    print("like-for-like worst forward overlap:",
          result["like_for_like_reading"]["worst_forward_overlap"],
          result["like_for_like_reading"]["worst_forward_overlap_submission"])
    print("PR-01 informative-probe worst forward overlap:", worst_info, worst_info_name,
          "passed:", pr01_pass)
    print(f"[done] -> {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default=str(OUT / "uniqueness.json"))
    ap.add_argument("--shard", type=int, default=None)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--merge", nargs="*", default=None)
    args = ap.parse_args()
    t0 = time.time()
    cand_path = Path(args.candidate)
    if not cand_path.is_absolute():
        cand_path = ROOT / cand_path

    if args.merge is not None:
        merge(args.merge, cand_path, Path(args.out))
        return 0

    g = G.load_grid(TPL / "data" / "bridge")
    with rasterio.open(cand_path) as src:
        cand = src.read(1).astype(np.float32)
    if tuple(cand.shape) != tuple(g.shape):
        raise SystemExit("candidate grid differs from the pinned competition grid")
    if not np.isfinite(cand).all() or cand.min() < 0 or cand.max() > 1:
        raise SystemExit("candidate is not finite and inside [0,1]")

    records = collect_registry({sha256_file(cand_path)})
    print(f"[registry] {len(records)} hash-verified sibling rasters", flush=True)
    if args.shard is not None:
        recs = records[args.shard::args.nshards]
        print(f"[shard {args.shard}/{args.nshards}] {len(recs)} rasters", flush=True)
        run_shard(cand, cand_path, recs, Path(args.out))
    else:
        run_shard(cand, cand_path, records, Path(args.out))
    print(f"[done] {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
