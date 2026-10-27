"""ARCHIVED / DISABLED: the historical description below is not an approval or verified protocol result.

WB-GEMS-DOE-3 unique submission generator.

Contrarian, geologically-grounded hypothesis (not previously implemented in this
repo or the GEMSDOE sites):

    H_STEP-OVER: geothermal upflow localises at dilational step-overs and relay
    ramps between en-echelon fault segments and in the off-trace fault damage
    zone -- NOT on the mapped catalogue fault traces themselves. Every
    GEMSDOE high-scorer (0.2449-0.2778) places dots ON the h19-5 / catalogue
    fault network. Those dots catch known faults but miss off-catalogue blind
    structures. This generator places dots 100 m - 1.5 km OFF the catalogue
    traces (damage zone + step-over/relay zones), so it targets faults missing
    from the USGS/INGENIOUS catalogue and is provably a different lane from the
    dotted-catalogue family.

Method (reproducible from public grid + catalogue-fault geometry used only for
learning; the emitted dots are new locations):
  1. Load catalogue-fault trace from a registry raster (champion dots).
  2. Distance-to-trace transform (pixels, 1 px = 100 m).
  3. Damage-zone candidates: 1-7 px off trace.
  4. Step-over/relay candidates: 4-15 px off trace (wide damage / dilation zones).
  5. Poisson-disk thin to target dot count (min spacing 2.5 px).
  6. Rasterize binary mask; clip to footprint; write -zeros / -nan via
     submission_writer; run strict format audit + lane-uniqueness audit.

Output: docs/downloads/<name>-zeros.tif  (the downloadable submission)
        evidence/run_card.json          (HOLDOUT-DTI label, uniqueness, sha256,
                                         verdict, submission note <=140 chars)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from submission_writer import write_submission, audit_saved_file, EXPECTED_HEIGHT, EXPECTED_WIDTH
from uniqueness_audit import audit_uniqueness

TEMPLATE = ROOT / "data" / "template_grid.tif"
REGISTRY_DIR = ROOT / "data" / "downloads" / "gemsdoe32_repo" / "GEMSDOE32-main" / "docs" / "downloads"
OUT_DIR = ROOT / "docs" / "downloads"
EVIDENCE_DIR = ROOT / "evidence"

TARGET_DOTS = 35_000
MIN_SPACING_PX = 2.5
DAMAGE_ZONE_PX = (1.0, 7.0)      # 100-700 m off-trace
STEP_OVER_ZONE_PX = (4.0, 15.0)  # 400 m - 1.5 km off-trace (dilation / relay)
SEED = 20261026


def load_template():
    with rasterio.open(TEMPLATE) as src:
        profile = src.profile.copy()
        arr = src.read(1)
    # Footprint = finite cells of the template grid (scored domain).
    footprint = np.isfinite(arr)
    transform = src.transform
    crs = src.crs
    return profile, footprint, transform, crs


def load_catalogue_trace():
    """Catalogue-fault dots from the GEMSDOE32 champion registry raster
    (used for learning the trace geometry; emitted dots are off-trace)."""
    best = None
    for cand in [
        "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
    ]:
        p = REGISTRY_DIR / cand
        if p.exists():
            best = p
            break
    if best is None:
        # Fall back to any local registry raster with the right grid.
        tifs = sorted(REGISTRY_DIR.glob("*.tif"))
        for p in tifs:
            try:
                with rasterio.open(p) as src:
                    if (src.height, src.width) == (EXPECTED_HEIGHT, EXPECTED_WIDTH):
                        best = p
                        break
            except Exception:
                continue
    if best is None:
        raise FileNotFoundError("No registry raster with the competition grid found")
    with rasterio.open(best) as src:
        trace = (np.isfinite(src.read(1)) & (src.read(1) > 0.5))
    return best, trace


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


def main():
    # Historical implementation retained for reproducibility only. Its grid
    # marks the whole rectangle valid, and the literal registry witness makes
    # every nonempty in-footprint candidate fail before placement. Never emit a
    # candidate or overwrite another run's evidence from this unsafe entrypoint.
    raise RuntimeError(
        "DISABLED / DO NOT SUBMIT: the literal registry witness blocks candidate "
        "generation and the mirrored footprint differs from the all-valid grid. "
        "See evidence/concurrent_audit.json and README.md."
    )
    profile, footprint, transform, crs = load_template()
    trace_src, trace = load_catalogue_trace()

    # Distance to nearest catalogue-trace pixel, in pixels.
    dist = distance_transform_edt(~trace & footprint)
    dist = np.where(footprint, dist, np.inf)

    dz = (dist >= DAMAGE_ZONE_PX[0]) & (dist <= DAMAGE_ZONE_PX[1]) & footprint
    sw = (dist >= STEP_OVER_ZONE_PX[0]) & (dist <= STEP_OVER_ZONE_PX[1]) & footprint
    candidates = dz | sw
    n_cand = int(candidates.sum())

    dots = poisson_disk_select(candidates, MIN_SPACING_PX, TARGET_DOTS, SEED)
    n_dots = int(dots.sum())

    # Safety: never place dots on the catalogue trace (keeps us off-catalogue).
    dots = dots & ~trace

    mask = dots.astype(np.float32)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"wb-gems-doe-3-stepover-damagezone-{n_dots}d-{stamp}"
    zeros_name = f"{slug}-zeros.tif"
    nan_name = f"{slug}-nan.tif"
    zeros_path = OUT_DIR / zeros_name
    nan_path = OUT_DIR / nan_name

    arr_z = write_submission(mask, footprint, TEMPLATE, zeros_path, mode="zeros")
    arr_n = write_submission(mask, footprint, TEMPLATE, nan_path, mode="nan")

    # Strict format audit on saved bytes.
    audit_z = audit_saved_file(zeros_path, TEMPLATE, strict_whole_array=True)
    audit_n = audit_saved_file(nan_path, TEMPLATE, strict_whole_array=True)

    # Lane-uniqueness audit vs all local registry rasters with the competition grid.
    registry_tifs = []
    for p in sorted(REGISTRY_DIR.glob("*.tif")):
        try:
            with rasterio.open(p) as src:
                if (src.height, src.width) == (EXPECTED_HEIGHT, EXPECTED_WIDTH):
                    registry_tifs.append(p)
        except Exception:
            continue
    uniq = audit_uniqueness(zeros_path, registry_tifs)

    sha8 = audit_z["sha256"][:8]
    unique_name = f"WB-GEMS-DOE-3-STEPOVER-DAMAGEZONE-{n_dots}D-{sha8.upper()}"
    note = (f"{unique_name} | {n_dots} off-trace step-over/damage-zone dots | "
            f"format PASS | unique PASS | score unverified projection | research/audit")
    if len(note) > 140:
        note = note[:137] + "..."

    run_card = {
        "submission_name": unique_name,
        "filename": zeros_name,
        "nan_twin": nan_name,
        "sha256": audit_z["sha256"],
        "sha8": sha8,
        "note": note,
        "note_chars": len(note),
        "generated_utc": stamp,
        "hypothesis": "H_STEP-OVER: geothermal upflow localises at off-trace "
                      "dilational step-overs and the fault damage zone, catching "
                      "off-catalogue blind faults missed by dotted-catalogue entries.",
        "layers_targeted": ["off-trace structural damage zone", "dilational step-over / relay zones"],
        "physical_signature": "distance-to-catalogue-trace in 100 m - 1.5 km (damage zone / dilation)",
        "why_missing_from_catalogue": "dots are 100 m - 1.5 km off mapped USGS/INGENIOUS traces, so it "
                                      "targets blind structures absent from the catalogue.",
        "differs_from_repo": "all GEMSDOE high-scorers dot ON the catalogue fault network; this "
                             "submission dots strictly OFF-trace (a different lane).",
        "dots": int(n_dots),
        "candidate_pixels": int(n_cand),
        "format_audit": audit_z,
        "nan_twin_audit": audit_n,
        "uniqueness": uniq.to_dict(),
        "holdout_dti": None,  # populated by evaluate_holdout when labels are present
        "score_estimate": "UNVERIFIED PROJECTION (no organizer receipt, no label access). "
                          "Catalogue proximity proxy: 0.0% of dots on catalogue traces "
                          "(by construction); off-catalogue blind-fault recall cannot be "
                          "measured without the private test labels. Do not treat as a score.",
        "verdict": "FORMAT_PASS / UNIQUE_PASS / SCORE_UNVERIFIED "
                   "- OK to download for research/audit. NOT organizer-cleared for live "
                   "submission until a holdout win + organizer receipt confirms the score.",
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    card_path = EVIDENCE_DIR / "run_card.json"
    card_path.write_text(json.dumps(run_card, indent=2), encoding="utf-8")

    # Also write the latest symlink-friendly copies for the one-click download.
    latest = OUT_DIR / "wb-gems-doe-3-latest-submission-zeros.tif"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    try:
        latest.symlink_to(zeros_name)
    except OSError:
        latest.write_bytes(zeros_path.read_bytes())

    print(json.dumps({
        "submission_name": unique_name,
        "filename": zeros_name,
        "sha256": audit_z["sha256"],
        "dots": int(n_dots),
        "format_passed": bool(audit_z["all_checks_passed"]),
        "unique": bool(uniq.unique),
        "max_overlap_within_3px": uniq.max_overlap_within_3px,
        "max_abs_rho_surface": uniq.max_abs_rho_surface,
        "note": note,
        "run_card": str(card_path),
        "download": str(zeros_path),
    }, indent=2))


if __name__ == "__main__":
    main()
