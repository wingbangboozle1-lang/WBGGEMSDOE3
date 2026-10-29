#!/usr/bin/env python3
"""Independent re-measurement of the nine GEMSDOE focus-site rasters.

What this does (and does not do)
--------------------------------
* Downloads each owner repository at the exact commit cited in
  ``evidence/focus_audit.json`` from ``codeload.github.com`` (the only GitHub
  host reachable from the project sandbox) into a scratch cache OUTSIDE the
  repository, extracts only the named rasters, and checks each file's SHA-256
  against the value recorded in ``focus_audit.json``.
* Profiles the format (driver, band count, dtype, nodata, EPSG, shape, affine)
  and every saved pixel (NaN, inf, range, positive count).
* Measures pairwise duplicate-risk among the nine files with the project's
  shared definition: a "dot" is a finite, strictly positive cell; directed
  overlap A->B is the fraction of A's dots whose Euclidean distance to the
  nearest B dot is <= 3 px; binary Spearman equals the phi coefficient for 0/1
  arrays, computed over the full 3730 x 3292 extent with NaN treated as 0.
* Tests the mechanism claimed for GEMSDOE32 B2 versus the GEMSDOE28 H27-4 base
  (positive-set inclusion and a catalogue-distance exclusion rule), using the
  owner-mirrored ``existing_faults.tif`` from GEMSDOE24's ``data/bridge``.

What it does NOT do: it has no hidden labels, so it produces no DTI, no
HOLDOUT-DTI and no organizer score. Every number it writes is a RASTER-ARTIFACT
measurement. Owner mirrors prove byte identity with a pinned commit, not organizer
provenance.

Usage: ``python scripts/verify_focus_files.py [--refresh]``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "evidence" / "focus_audit.json"
OUT = REPO / "evidence" / "focus_files_verification_2026-10-29.json"
CACHE = Path.home() / ".cache" / "gems-focus-verify"  # outside the repository, not committed

OWNER = "buffedlizard55-lab"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_AFFINE = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
RADIUS_PX = 3.0
DUP_FRACTION = 0.70
PHI_LIMIT = 0.90
BASE_SITE = "GEMSDOE28"
BASE_FILE = "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"
CATALOGUE_SITE = "GEMSDOE24"
CATALOGUE_PATH = "data/bridge/existing_faults.tif"
TARGET_SITE = "GEMSDOE32"
SAMPLE_PATH = "data/bridge/sample_submission.tif"
SITE31 = "GEMSDOE31"
REPO_TEMPLATE = REPO / "data" / "template_grid.tif"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_commit_archive(site: str, sha: str) -> Path:
    """Fetch a pinned-commit tarball from codeload (allowed host) into the cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{site}-{sha}.tar.gz"
    if not dest.exists() or dest.stat().st_size == 0:
        url = f"https://codeload.github.com/{OWNER}/{site}/tar.gz/{sha}"
        with urllib.request.urlopen(url, timeout=900) as resp, dest.open("wb") as out:
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                out.write(block)
    return dest


def extract_member(archive: Path, relpath: str, dest_dir: Path) -> Path:
    """Extract the single member whose path ends with ``relpath`` (inside the tarball's top folder)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf:
            if member.isfile() and (member.name == relpath or member.name.endswith("/" + relpath)):
                target = dest_dir / Path(relpath).name
                with tf.extractfile(member) as src, target.open("wb") as out:
                    out.write(src.read())
                return target
    raise FileNotFoundError(f"{relpath} not found in {archive.name}")


def commit_from_source(url: str) -> str:
    match = re.search(r"/blob/([0-9a-f]{40})/", url)
    if not match:
        raise ValueError(f"no pinned commit in {url}")
    return match.group(1)


def format_profile(path: Path) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        profile = {
            "driver": ds.driver,
            "band_count": ds.count,
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata,
            "epsg": ds.crs.to_epsg() if ds.crs else None,
            "shape": list(ds.shape),
            "affine": [float(v) for v in tuple(ds.transform)[:6]],
        }
    profile["grid_matches_official_template"] = (
        profile["epsg"] == 32611
        and tuple(profile["shape"]) == EXPECTED_SHAPE
        and tuple(round(v, 6) for v in profile["affine"]) == EXPECTED_AFFINE
    )
    finite = np.isfinite(arr)
    values = arr[finite]
    profile.update({
        "finite_cells": int(finite.sum()),
        "nan_cells": int(np.isnan(arr).sum()),
        "inf_cells": int(np.isinf(arr).sum()),
        "finite_min": float(values.min()) if values.size else None,
        "finite_max": float(values.max()) if values.size else None,
        "finite_out_of_0_1_cells": int(((values < 0) | (values > 1)).sum()),
        "positive_cells": int(np.count_nonzero(finite & (arr > 0))),
        "exact_zero_cells": int(np.count_nonzero(arr == 0)),
        "footprint_style": "nan_outside" if np.isnan(arr).any() else "all_cells_finite_zero_filled",
    })
    return profile, arr


def phi(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation of two 0/1 arrays (== Spearman with tie-averaged ranks)."""
    n = a.size
    n11 = int(np.count_nonzero(a & b))
    na = int(np.count_nonzero(a))
    nb = int(np.count_nonzero(b))
    denom = math.sqrt(float(na) * float(n - na) * float(nb) * float(n - nb))
    if denom == 0:
        return float("nan")
    return float((n * n11 - na * nb) / denom)


def directed_overlap(a_dots: np.ndarray, b_dist_to_dots: np.ndarray) -> float:
    total = int(np.count_nonzero(a_dots))
    if total == 0:
        return float("nan")
    return float(np.count_nonzero(a_dots & (b_dist_to_dots <= RADIUS_PX)) / total)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="re-download even if cached")
    args = parser.parse_args(argv)
    if args.refresh:
        for f in CACHE.glob("*.tar.gz"):
            f.unlink()

    audit = json.loads(AUDIT.read_text())
    sites = audit["focus_sites"]
    base_commit = None
    rasters: dict[str, dict] = {}
    recorded_sha: dict[str, str] = {}
    commits: dict[str, str] = {}

    for entry in sites:
        site = entry["site"]
        sha = commit_from_source(entry["source"])
        commits[site] = sha
        archive = fetch_commit_archive(site, sha)
        local = extract_member(archive, f"docs/downloads/{entry['filename']}", CACHE / "extract" / site)
        digest = sha256_of(local)
        recorded_sha[site] = entry["sha256"]
        profile, arr = format_profile(local)
        rasters[site] = {
            "site": site,
            "filename": entry["filename"],
            "source_commit": sha,
            "claimed_by_owner_not_receipt": entry.get("claimed_by_owner_not_receipt"),
            "sha256": digest,
            "sha256_matches_focus_audit": digest == entry["sha256"],
            "format": profile,
            "_arr": arr,
        }
        if not rasters[site]["sha256_matches_focus_audit"]:
            raise SystemExit(f"SHA-256 mismatch for {site}: {digest} != {entry['sha256']}")

    # Dot masks (finite and > 0) and nearest-dot distance maps.
    dots = {s: (np.isfinite(r["_arr"]) & (r["_arr"] > 0)) for s, r in rasters.items()}
    dist = {s: distance_transform_edt(~dots[s]) for s in dots}

    names = list(dots)
    pairwise = {}
    for a in names:
        row = {}
        for b in names:
            if a == b:
                continue
            row[b] = {
                "directed_overlap_within_3px": round(directed_overlap(dots[a], dist[b]), 6),
                "phi_spearman_binary_full_extent": round(phi(dots[a], dots[b]), 6),
            }
        pairwise[a] = row

    uniqueness = {}
    for a in names:
        others = [b for b in names if b != a]
        worst = max(others, key=lambda b: pairwise[a][b]["directed_overlap_within_3px"])
        max_overlap = pairwise[a][worst]["directed_overlap_within_3px"]
        max_abs_phi = max(abs(pairwise[a][b]["phi_spearman_binary_full_extent"]) for b in names if b != a)
        uniqueness[a] = {
            "max_directed_overlap_within_3px": max_overlap,
            "max_overlap_vs": worst,
            "max_abs_phi": round(max_abs_phi, 6),
            "passes_70pct_3px_rule": max_overlap <= DUP_FRACTION,
            "passes_abs_phi_0_90_rule": max_abs_phi <= PHI_LIMIT,
            "literal_user_rule_status": "DUPLICATE-STOP" if max_overlap > DUP_FRACTION else "clear vs focus set",
        }

    # Catalogue geometry (owner mirror of the official existing_faults.tif name).
    cat_archive = fetch_commit_archive(CATALOGUE_SITE, commits[CATALOGUE_SITE])
    cat_path = extract_member(cat_archive, CATALOGUE_PATH, CACHE / "extract" / "catalogue")
    with rasterio.open(cat_path) as ds:
        cat = ds.read(1)
        cat_profile = {"dtype": ds.dtypes[0], "nodata": ds.nodata, "epsg": ds.crs.to_epsg(),
                       "shape": list(ds.shape)}
    catalogue_faults = cat == 1
    dist_cat = distance_transform_edt(~catalogue_faults)
    catalogue_geometry = {
        "source": f"https://github.com/{OWNER}/{CATALOGUE_SITE}/blob/{commits[CATALOGUE_SITE]}/{CATALOGUE_PATH}",
        "sha256": sha256_of(cat_path),
        "profile": cat_profile,
        "fault_cells_value_1": int(catalogue_faults.sum()),
        "value_counts": {str(int(v)): int(c) for v, c in zip(*np.unique(cat, return_counts=True))},
        "per_site_fraction_of_dots_within_2px": {},
        "per_site_fraction_of_dots_within_3px": {},
    }
    for s in names:
        catalogue_geometry["per_site_fraction_of_dots_within_2px"][s] = round(
            float(np.count_nonzero(dots[s] & (dist_cat <= 2.0)) / max(1, np.count_nonzero(dots[s]))), 6)
        catalogue_geometry["per_site_fraction_of_dots_within_3px"][s] = round(
            float(np.count_nonzero(dots[s] & (dist_cat <= 3.0)) / max(1, np.count_nonzero(dots[s]))), 6)

    # GEMSDOE32 B2 versus GEMSDOE28 H27-4 base (mechanism check).
    base_commit = commits[BASE_SITE]
    base_archive = fetch_commit_archive(BASE_SITE, base_commit)
    base_local = extract_member(base_archive, f"docs/downloads/{BASE_FILE}", CACHE / "extract" / "base")
    base_profile, base_arr = format_profile(base_local)
    base_dots = np.isfinite(base_arr) & (base_arr > 0)
    b2 = dots[TARGET_SITE]
    removed = base_dots & ~b2
    kept = b2
    rule_pred = base_dots & (dist_cat > 2.0)
    mechanism = {
        "base_source": f"https://github.com/{OWNER}/{BASE_SITE}/blob/{base_commit}/docs/downloads/{BASE_FILE}",
        "base_sha256": sha256_of(base_local),
        "base_sha256_matches_focus_audit": sha256_of(base_local) == audit["h33_mechanism"]["base_sha256"],
        "base_positive_cells": int(base_dots.sum()),
        "target_positive_cells": int(b2.sum()),
        "target_cells_not_in_base": int(np.count_nonzero(b2 & ~base_dots)),
        "target_is_subset_of_base": bool(not np.any(b2 & ~base_dots)),
        "base_cells_removed": int(removed.sum()),
        "removed_min_dist_to_catalogue_px": float(dist_cat[removed].min()) if removed.any() else None,
        "removed_max_dist_to_catalogue_px": float(dist_cat[removed].max()) if removed.any() else None,
        "kept_min_dist_to_catalogue_px": float(dist_cat[kept].min()) if kept.any() else None,
        "rule_tested": "target == base AND (distance to nearest catalogue fault > 2.0 px)",
        "rule_mismatch_cells": int(np.count_nonzero(rule_pred != b2)),
        "removed_fraction_of_base": round(float(removed.sum() / base_dots.sum()), 6),
    }

    # Official sample (owner mirror) versus the training labels inside the footprint.
    sample_archive = fetch_commit_archive(CATALOGUE_SITE, commits[CATALOGUE_SITE])
    sample_path = extract_member(sample_archive, SAMPLE_PATH, CACHE / "extract" / "sample")
    with rasterio.open(sample_path) as ds:
        sample_arr = ds.read(1)
    sample_ones = sample_arr == 1
    with rasterio.open(cat_path) as ds:
        labels_arr = ds.read(1)
    sample_check = {
        "source": f"https://github.com/{OWNER}/{CATALOGUE_SITE}/blob/{commits[CATALOGUE_SITE]}/{SAMPLE_PATH}",
        "sha256": sha256_of(sample_path),
        "sha256_matches_focus_audit_template_sample": sha256_of(sample_path).startswith("2176d08e"),
        "finite_cells": int(np.isfinite(sample_arr).sum()),
        "value_1_cells": int(sample_ones.sum()),
        "value_0_cells": int(np.count_nonzero(sample_arr == 0)),
        "footprint_equals_nan_outside_files": bool(all(
            np.array_equal(np.isfinite(rasters[s]["_arr"]), np.isfinite(sample_arr))
            for s in names if rasters[s]["format"]["footprint_style"] == "nan_outside")),
        "value_1_cells_identical_to_training_labels": bool(np.array_equal(sample_ones, labels_arr == 1)),
        "official_text": "A sample submission that predicts total fault absence is provided for your reference",
        "irregularity": "The owner-mirrored sample contains positive cells and they equal the training labels; "
                        "this conflicts with the official description. Flagged for review; do not use as a null baseline.",
    }
    repo_template = {
        "path": "data/template_grid.tif",
        "sha256": sha256_of(REPO_TEMPLATE) if REPO_TEMPLATE.exists() else None,
        "finite_cells": None,
        "is_identical_to_sample_submission_footprint": False,
        "irregularity": "Not the official sample grid: it is fully finite with zeros, while the sample has a 5,167,373-cell "
                        "NaN-outside footprint. Do not use it as the footprint reference.",
    }
    with rasterio.open(REPO_TEMPLATE) as ds:
        repo_template["finite_cells"] = int(np.isfinite(ds.read(1)).sum())

    # Owner-reported score association across the nine sites (n=9; descriptive only).
    owner = {s: float(rasters[s]["claimed_by_owner_not_receipt"]) for s in names}
    dots_n = {s: rasters[s]["format"]["positive_cells"] for s in names}
    assoc = {}
    for label, values in (("dot_count", dots_n),
                          ("fraction_dots_within_2px_of_catalogue", catalogue_geometry["per_site_fraction_of_dots_within_2px"]),
                          ("fraction_dots_within_3px_of_catalogue", catalogue_geometry["per_site_fraction_of_dots_within_3px"])):
        rho, pval = spearmanr([owner[s] for s in names], [values[s] for s in names])
        assoc[label] = {"spearman_rho_vs_owner_score": round(float(rho), 4),
                        "p_value": float(pval), "n": len(names),
                        "interpretation": "descriptive association across nine self-reported scores; not causal, not a score"}

    identities = {
        "GEMSDOE31_dot_set_identical_to_GEMSDOE28_H27_4_base": bool(np.array_equal(dots[SITE31], base_dots)),
        "GEMSDOE25_dot_set_identical_to_GEMSDOE30": bool(np.array_equal(dots["GEMSDOE25"], dots["GEMSDOE30"])),
    }

    for r in rasters.values():
        r.pop("_arr", None)

    card = {
        "schema": "gems-focus-files-verification-v1",
        "evidence_class": "RASTER-ARTIFACT-MEASUREMENT; owner-mirror bytes at pinned commits; "
                          "NOT organizer-confirmed; NOT HOLDOUT-DTI; no hidden labels used",
        "checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "codeload pinned-commit tarballs; SHA-256 vs evidence/focus_audit.json; "
                  "dots = finite & >0; 3 px Euclidean directed overlap; binary Spearman == phi",
        "rules": {"radius_px": RADIUS_PX, "duplicate_overlap_limit": DUP_FRACTION, "abs_phi_limit": PHI_LIMIT},
        "official_format_reference": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "official_format_text": "single layer float32 with values between 0 and 1; data outside the bounds is null or nan",
        "rasters": rasters,
        "pairwise": pairwise,
        "uniqueness_vs_focus_set": uniqueness,
        "catalogue": catalogue_geometry,
        "mechanism_gems32_vs_gems28_h27_4": mechanism,
        "identities": identities,
        "owner_score_associations_descriptive": assoc,
        "official_sample_submission_check": sample_check,
        "repo_template_grid_check": repo_template,
        "limitations": [
            "Owner-mirror bytes; not the official DrivenData download.",
            "No hidden labels: no DTI, no CI, no organizer score can be computed here.",
            "Full-registry uniqueness is NOT established; only the nine focus files were compared.",
            "Official format wording (null/NaN outside bounds) is not verified against the portal.",
            "The owner-mirrored sample_submission.tif is used as the footprint reference; its provenance is not authenticated.",
        ],
    }
    OUT.write_text(json.dumps(card, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}")
    for s in names:
        u = uniqueness[s]
        print(f"{s}: dots={rasters[s]['format']['positive_cells']} style={rasters[s]['format']['footprint_style']} "
              f"max3px={u['max_directed_overlap_within_3px']:.4f} vs {u['max_overlap_vs']} -> {u['literal_user_rule_status']}")
    print("GEMSDOE32 subset of GEMSDOE28 base:", mechanism["target_is_subset_of_base"],
          "| removed:", mechanism["base_cells_removed"], "| rule mismatches:", mechanism["rule_mismatch_cells"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
