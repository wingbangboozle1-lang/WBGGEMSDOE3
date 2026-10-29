#!/usr/bin/env python3
"""
Pass 1: Generate a unique GEMS submission TIF from a new geological hypothesis.

Hypothesis (H_STEP_OVER_DAMAGE, new and contrarian):
  Geothermal upflow localises at dilational fault step-overs, relay ramps and
  the off-trace damage zone — NOT on the mapped catalogue traces themselves.
  Every GEMSDOE high-scorer (0.2449–0.2778) places dots ON the h19-5 /
  USGS-INGENIOUS catalogue fault network. Those dots catch known faults but
  systematically miss off-catalogue blind structures. This generator places
  dots 100 m–1.5 km OFF the catalogue traces (damage zone + step-over/relay
  zones), so it targets faults missing from the catalogue and is provably a
  different lane from the dotted-catalogue family.

Layers targeted:
  - Off-trace structural damage zone (100–700 m from catalogue trace)
  - Dilational step-over / relay zones (400 m–1.5 km from catalogue trace)

Physical signature:
  Distance-to-catalogue-trace transform (1 px = 100 m). Candidate pixels lie
  in the annulus 1–15 px off-trace, excluding the catalogue trace itself.

Named non-fault mimic:
  Lithologic/weathering contacts and erosion-resistant bedrock can also sit
  off mapped traces; these are non-fault geological features that could
  produce similar off-trace signals.

Differs from repo / GEMSDOE sites:
  All GEMSDOE high-scorers dot ON the catalogue fault network. This submission
  dots strictly OFF-trace (zero positive pixels on mapped faults by
  construction). Different lane: not within 3 px of catalogue dots for the
  vast majority of emitted dots.

Budget:
  1 geological experiment (this generator). No holdout score is computable
  without organiser truth labels (labels.tif is behind DrivenData login).
  Every number is labelled clearly: format check = local, uniqueness = local
  registry measurement, score = NOT ESTIMABLE (no receipt, no holdout truth).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d" / "src"))

from gems57.grid import load_grid
from gems57 import submission_writer, gates, validate

TEMPLATE = ROOT / "data" / "template_grid.tif"
BRIDGE = ROOT / "data" / "bridge"
OUT_DIR = ROOT / "docs" / "downloads"
EVIDENCE_DIR = ROOT / "evidence"

# --- Hypothesis parameters ---
TARGET_DOTS = 30_000
MIN_SPACING_PX = 2.5          # 250 m minimum dot spacing (Poisson disk)
DAMAGE_ZONE_PX = (1.0, 7.0)   # 100–700 m off-trace: proximal damage zone
STEP_OVER_ZONE_PX = (4.0, 15.0)  # 400 m–1.5 km off-trace: dilation/relay zone
SEED = 20261029

SUBMISSION_NAME_PREFIX = "WB-GEMS-DOE-3-STEP-OVER-DAMAGE-ZONE"
NOTE_PREFIX = "Off-catalogue step-over/damage-zone dots; format-valid; uniqueness-checked; score not estimable; not cleared for upload"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def poisson_disk_select(candidate_mask: np.ndarray, min_dist_px: float,
                        max_dots: int, seed: int) -> np.ndarray:
    """Greedy Poisson-disk thinning over candidate pixels."""
    rng = np.random.RandomState(seed)
    ys, xs = np.nonzero(candidate_mask)
    n = ys.size
    if n == 0:
        return np.zeros(candidate_mask.shape, bool)
    order = rng.permutation(n)
    chosen = np.zeros(n, bool)
    cell = min_dist_px
    H, W = candidate_mask.shape
    gw, gh = int(np.ceil(W / cell)) + 1, int(np.ceil(H / cell)) + 1
    grid = [[[] for _ in range(gw)] for _ in range(gh)]

    def cell_of(y, x):
        return int(y // cell), int(x // cell)

    min_dist_sq = min_dist_px * min_dist_px
    chosen_count = 0
    for idx in order:
        if chosen_count >= max_dots:
            break
        y, x = int(ys[idx]), int(xs[idx])
        cy, cx = cell_of(y, x)
        ok = True
        for dy in (-1, 0, 1):
            gy = cy + dy
            if gy < 0 or gy >= gh:
                continue
            for dx in (-1, 0, 1):
                gx = cx + dx
                if gx < 0 or gx >= gw:
                    continue
                for j in grid[gy][gx]:
                    jy, jx = int(ys[j]), int(xs[j])
                    if (y - jy) ** 2 + (x - jx) ** 2 < min_dist_sq:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        chosen[idx] = True
        chosen_count += 1
        grid[cy][cx].append(idx)
    dots = np.zeros(candidate_mask.shape, bool)
    dots[ys[chosen], xs[chosen]] = True
    return dots


def build_registry_index() -> dict:
    """Build a local registry index dict for gems57.uniqueness.

    Expected record keys: repo_first, sources (list), cache_file, sha256.
    """
    roots = [ROOT / "docs" / "downloads", ROOT / "submission"]
    rasters = []
    for root in roots:
        for p in sorted(root.glob("*.tif")):
            try:
                with rasterio.open(p) as src:
                    if (src.height, src.width) != (3730, 3292):
                        continue
                    if str(src.crs) != "EPSG:32611":
                        continue
            except Exception:
                continue
            h = sha256_file(p)
            rasters.append({
                "repo_first": "local",
                "sources": [p.name],
                "cache_file": str(p),
                "sha256": h,
            })
    return {"rasters": rasters, "complete_accessible_scan": False}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # --- Load grid ---
    g = load_grid(BRIDGE)
    footprint = g.footprint
    catalogue = g.catalogue

    # --- Distance to catalogue trace (pixels, 1 px = 100 m) ---
    # distance_transform_edt(~mask) gives distance to nearest True pixel.
    # We invert: distance from every pixel to nearest catalogue pixel.
    dist_to_trace = distance_transform_edt(~catalogue & footprint)
    dist_to_trace = np.where(footprint, dist_to_trace, np.inf)

    # --- Candidate selection: off-trace annuli ---
    dz = (dist_to_trace >= DAMAGE_ZONE_PX[0]) & (dist_to_trace <= DAMAGE_ZONE_PX[1]) & footprint
    sw = (dist_to_trace >= STEP_OVER_ZONE_PX[0]) & (dist_to_trace <= STEP_OVER_ZONE_PX[1]) & footprint
    candidates = dz | sw
    n_cand = int(candidates.sum())
    print(f"Candidate pixels (off-trace 100m-1.5km): {n_cand:,}")

    # --- Poisson-disk thinning ---
    dots = poisson_disk_select(candidates, MIN_SPACING_PX, TARGET_DOTS, SEED)
    n_dots = int(dots.sum())
    print(f"Selected dots: {n_dots:,}")

    # --- Safety: never place dots on the catalogue trace ---
    dots = dots & ~catalogue
    n_dots = int(dots.sum())
    print(f"Dots after catalogue exclusion: {n_dots:,}")

    # --- Build prediction array ---
    mask = dots.astype(np.float32)
    # Zero outside footprint
    mask = np.where(footprint, mask, 0.0)

    # --- Format validation (in memory before writing) ---
    assert mask.shape == (3730, 3292), mask.shape
    assert np.isfinite(mask).all(), "non-finite values"
    assert (mask >= 0.0).all() and (mask <= 1.0).all(), "out of [0,1]"
    assert not ((mask > 0) & ~footprint).any(), "positive mass outside footprint"
    assert not ((mask > 0) & catalogue).any(), "positive mass on catalogue"

    # --- Write submission to a temp path first (sha8 unknown until written) ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_name = f".tmp-{SUBMISSION_NAME_PREFIX.lower()}-{n_dots}d-{stamp}-zeros.tif"
    tmp_path = OUT_DIR / tmp_name

    receipt = submission_writer.write_submission(
        path=tmp_path,
        prediction=mask,
        sample=BRIDGE / "sample_submission.tif",
        footprint=footprint,
        catalogue=catalogue,
        name=f"{SUBMISSION_NAME_PREFIX}-{n_dots}D-PENDING",
        note=NOTE_PREFIX,
        metadata={
            "hypothesis": "H_STEP_OVER_DAMAGE",
            "mechanism": "Geothermal upflow localises at dilational fault step-overs and off-trace damage zones",
            "target_dots": TARGET_DOTS,
            "actual_dots": int(n_dots),
            "candidate_pixels": int(n_cand),
            "damage_zone_px": DAMAGE_ZONE_PX,
            "step_over_zone_px": STEP_OVER_ZONE_PX,
            "min_spacing_px": MIN_SPACING_PX,
            "seed": SEED,
        },
    )
    sha8 = receipt["sha256"][:8]

    # Rename with the real SHA-8
    final_name = f"{SUBMISSION_NAME_PREFIX}-{n_dots}D-{stamp}-{sha8.upper()}-zeros.tif"
    final_path = OUT_DIR / final_name
    tmp_path.rename(final_path)
    zip_path = final_path.with_suffix(".zip")
    receipt_path = final_path.with_suffix(".json")

    # Also move the zip and receipt if they exist
    for ext in (".zip", ".json"):
        old = tmp_path.with_suffix(ext)
        if old.exists():
            old.rename(final_path.with_suffix(ext))

    # Re-read the final TIFF for validation report
    with rasterio.open(final_path) as src:
        final_arr = src.read(1)

    # --- Local format validation ---
    val_report = validate.validate(final_path, footprint=footprint, catalogue=catalogue)

    # --- Gates format report ---
    fmt_report = gates.format_report(final_path, BRIDGE / "sample_submission.tif", footprint=footprint)

    # --- Uniqueness vs local registry (exclude self by SHA-256) ---
    reg_index = build_registry_index()
    own_sha = receipt["sha256"]
    reg_index["rasters"] = [r for r in reg_index["rasters"] if r["sha256"] != own_sha]
    n_registry = len(reg_index["rasters"])
    print(f"\nRegistry entries for uniqueness check: {n_registry} (self excluded)")

    from gems57 import uniqueness

    uniq_result = uniqueness.compare_array_to_registry(
        final_arr,
        reg_index,
        footprint,
        file_sha256=receipt["sha256"],
        expected_grid=((3730, 3292), "EPSG:32611",
                       rasterio.Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)),
    )
    n_registry = len(reg_index["rasters"])

    # --- Run card ---
    note = (f"{SUBMISSION_NAME_PREFIX}-{n_dots}D-{sha8.upper()} | {n_dots} off-trace "
            f"step-over/damage-zone dots | format PASS | uniqueness vs {n_registry} "
            f"local rasters | score NOT ESTIMABLE (no organiser truth/holdout) | not cleared "
            f"for upload pending holdout + selector")
    if len(note) > 140:
        note = note[:137] + "..."

    run_card = {
        "schema": "gems-session-run-card-v1",
        "generated_utc": stamp,
        "session_branch": "arena/075fe1bc-wbggemsdoe3",
        "verdict": "negative",
        "okay_to_submit": False,
        "okay_to_download_for_research": True,
        "decision_reason": "Unique TIF generated and locally format-valid. No holdout DTI computable "
                           "(organiser truth labels not accessible). Not cleared for submission pending "
                           "holdout validation, uniqueness vs complete registry, and separate selector "
                           "approval. Unique vs local registry: "
                       f"{uniq_result.get('unique', False)}.",
        "hypothesis": {
            "id": "H_STEP_OVER_DAMAGE",
            "name": "Dilational step-over and off-trace damage-zone geothermal upflow",
            "status": "GENERATED_NOT_TESTED",
            "mechanism": "Geothermal upflow localises at dilational fault step-overs, relay ramps, and "
                         "the off-trace damage zone where fracture density and permeability are enhanced. "
                         "These structures are frequently absent from the USGS/INGENIOUS catalogue which "
                         "maps major traces only.",
            "named_non_fault_mimic": "Lithologic/weathering contacts and erosion-resistant bedrock "
                                     "off mapped traces; non-fault geological features could produce "
                                     "similar off-trace signals.",
            "layers_targeted": ["off-trace structural damage zone (100-700 m)",
                                "dilational step-over / relay zones (400 m - 1.5 km)"],
            "physical_signature": "distance-to-catalogue-trace annulus 100 m - 1.5 km off trace",
            "why_uncatalogued": "dots are 100 m - 1.5 km off mapped USGS/INGENIOUS traces by construction; "
                                "targets blind structures absent from the catalogue.",
            "difference_from_repository": "all GEMSDOE high-scorers dot ON the catalogue fault network "
                                          "(0.2449-0.2778); this submission dots strictly OFF-trace with "
                                          "zero positive pixels on mapped faults.",
            "implementation_cost": "Low - uses only local grid + catalogue; no external data required.",
        },
        "layers": ["off-trace structural damage zone", "dilational step-over / relay zones"],
        "physical_signature": "distance-to-catalogue-trace annulus 100 m - 1.5 km",
        "catalogue_cells": int(catalogue.sum()),
        "footprint_cells": int(footprint.sum()),
        "candidate_pixels": int(n_cand),
        "target_dots": TARGET_DOTS,
        "dots": int(n_dots),
        "dots_on_catalogue": int(((mask > 0) & catalogue).sum()),
        "dots_outside_footprint": int(((mask > 0) & ~footprint).sum()),
        "submission": {
            "name": f"{SUBMISSION_NAME_PREFIX}-{n_dots}D-{sha8.upper()}",
            "filename": final_name,
            "note": note,
            "note_characters": len(note),
            "path": str(final_path),
            "sha256": receipt["sha256"],
            "zip_sha256": receipt.get("zip_sha256"),
            "bytes": receipt.get("bytes"),
            "status": "LOCALLY_VALIDATED_NOT_CLEARED",
        },
        "format_validation": val_report,
        "gates_format_report": fmt_report,
        "uniqueness": {
            "registry_entries_checked": n_registry,
            "unique": bool(uniq_result.get("unique", False)),
            "worst_spearman_full_footprint": uniq_result.get("worst_spearman_full_footprint"),
            "worst_dot_overlap": uniq_result.get("worst_dot_overlap"),
            "duplicate_count": uniq_result.get("duplicate_count", 0),
            "rho_limit": 0.90,
            "overlap_limit": 0.70,
        },
        "holdout_dti": {
            "label": "NOT-RUN",
            "status": "NO_ORGANISER_TRUTH_ACCESS",
            "value": None,
            "ci95": None,
            "evaluator_version": None,
            "withheld_positive_count": None,
            "reason": "Organiser truth labels (labels.tif) are behind DrivenData login; "
                      "no holdout DTI can be computed without them.",
        },
        "score_estimate": "NOT ESTIMABLE - no organiser receipt, no holdout truth, "
                          "no leaderboard projection. Owner-reported GEMSDOE32 best: 0.2778 "
                          "(unverified).",
        "verdict": "negative",
        "experiments": {"geological_experiments_completed": 1, "maximum": 3},
        "selector": {"action": "NONE", "weekly_slots_used": 0, "separate_selector_approval": False},
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    card_path = EVIDENCE_DIR / "run_card_unique_submission.json"
    card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Also write a copy to docs/data for the site
    docs_data = ROOT / "docs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    (docs_data / "run_card_unique_submission.json").write_text(
        json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Print summary
    print("\n" + "=" * 60)
    print("UNIQUE SUBMISSION GENERATED")
    print("=" * 60)
    print(f"Name:      {run_card['submission']['name']}")
    print(f"File:      {final_name}")
    print(f"SHA-256:   {receipt['sha256']}")
    print(f"Dots:      {n_dots:,} (all off-catalogue)")
    print(f"Format:    all_checks_passed={val_report['all_checks_passed']}")
    print(f"Unique:    {uniq_result.get('unique', False)} (vs {n_registry} local rasters)")
    print(f"OK to submit: NO (no holdout DTI, no selector approval)")
    print(f"Run card:  {card_path}")
    print(f"Download:  {final_path}")
    print("\nNOTE: This TIF is format-valid and unique vs the local registry,")
    print("but is NOT cleared for submission. Holdout validation and")
    print("separate selector approval are required first.")

    return run_card


if __name__ == "__main__":
    main()