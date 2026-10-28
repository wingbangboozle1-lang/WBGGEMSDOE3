#!/usr/bin/env python3
"""Recheck a pinned registry blocker and an existing research TIFF, not a model run.

Examples:
  python scripts/recheck_registry_witness.py --fetch
  python scripts/recheck_registry_witness.py --sample path/sample.tif --witness path/witness.tif

Inputs are hash-checked against the public mirror pins; the script never writes
or changes a prediction, uploads a file, or asserts organizer data provenance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.audit import SAMPLE_SHA, WITNESS, universal_witness  # noqa: E402
from gems_project.format_preflight import raster_report  # noqa: E402
from gems_project.sources import download_github_file, sha256_file  # noqa: E402

SAMPLE_REPO = "buffedlizard55-lab/57GEMSDOE"
SAMPLE_REF = "822a0ce5546c7b6749cdd82eb145b6b3e616603d"
SAMPLE_SOURCE = "data/bridge/sample_submission.tif"
SAMPLE_BLOB = "7d865a9921a40ed2ea4c742a6a25b1fa2f357c5a"
CANDIDATE = ROOT / "submission/wbggems3-sgce-20261027-f52d35d8-zeros.tif"
PUBLISHED = ROOT / "docs/downloads/wbggems3-sgce-20261027-f52d35d8-zeros.tif"
CANDIDATE_SHA = "0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09"
DEFAULT_SAMPLE = ROOT / ".cache/verification/owner-sample-submission.tif"
DEFAULT_WITNESS = ROOT / ".cache/verification/17gemsdoe-witness.tif"
INDEX = ROOT / "registry/registry_session2.json"
OUT = ROOT / "evidence/registry_witness_recheck_2026-10-27.json"


def observations(sample: Path, witness: Path, candidate: Path) -> dict:
    """Measure aligned saved pixels. Does not decide eligibility or verify origins."""
    with rasterio.open(sample) as s, rasterio.open(witness) as w, rasterio.open(candidate) as c:
        if s.count != 1 or s.crs is None:
            raise ValueError("sample must be a single-band georeferenced raster")
        for name, ds in (("witness", w), ("candidate", c)):
            if ds.count != 1 or ds.shape != s.shape or ds.crs != s.crs or ds.transform != s.transform:
                raise ValueError(f"{name} grid differs from sample")
        a, b, p = s.read(1), w.read(1), c.read(1)
        foot = np.isfinite(a) & (s.read_masks(1) > 0)
        ref = np.isfinite(b) & (b > 0) & (w.read_masks(1) > 0)
        dots = np.isfinite(p) & (p > 0) & (c.read_masks(1) > 0)
        proof = universal_witness(foot, ref)
        count, outside = int(dots.sum()), int(np.count_nonzero(dots & ~foot))
        if not count:
            raise ValueError("empty research prediction cannot establish directed overlap")
        # A coincident positive is already within 3 px. For general fixtures,
        # compute the actual Euclidean 3-pixel overlap; EDT has a special case
        # for an empty reference, so handle that explicitly.
        coincident = int(np.count_nonzero(dots & ref))
        if coincident == count:
            near_count = count
        elif not ref.any():
            near_count = 0
        else:
            near_count = int(np.count_nonzero(dots & (distance_transform_edt(~ref) <= 3.0)))
        return {
            "grid": {"shape": list(s.shape), "crs": str(s.crs), "transform": list(s.transform)[:6]},
            "witness": proof,
            "candidate": {
                "positive_pixels_all": count,
                "positive_pixels_inside": count - outside,
                "positive_pixels_outside": outside,
                "positive_pixels_coincident_with_witness": coincident,
                "positive_pixels_within_3px_of_witness": near_count,
                "directed_overlap_within_3px_all_positive": near_count / count,
                "surface_rank_correlation": None,
                "surface_check": "NOT REPLAYED; this is a saved-raster audit only",
            },
        }


def build_report(sample: Path, witness: Path, candidate: Path, published: Path, registry: Path) -> dict:
    """Require immutable pins before treating pixel measurements as this audit."""
    expected = ((sample, SAMPLE_SHA), (witness, WITNESS["sha256"]),
                (candidate, CANDIDATE_SHA), (published, CANDIDATE_SHA))
    for path, pin in expected:
        if not path.is_file() or sha256_file(path) != pin:
            raise ValueError(f"missing file or SHA-256 mismatch: {path}")
    index = json.loads(registry.read_text())
    rows = [r for r in index.get("files", []) if r.get("sha256") == WITNESS["sha256"]]
    if not rows or not any(r.get("status") == "ok" for r in rows):
        raise ValueError("pinned witness is not an OK entry in the committed registry")
    result = observations(sample, witness, candidate)
    result["witness"].update({
        "sha256": WITNESS["sha256"], "registered": True,
        "registry": str(registry.relative_to(ROOT)),
        "registry_sha256": sha256_file(registry),
        "source": f"https://github.com/{WITNESS['repo']}/blob/{WITNESS['ref']}/{WITNESS['path']}",
        "definition": "finite, GDAL-valid value > 0; directed Euclidean overlap <= 3 pixels",
    })
    result["candidate"].update({
        "file": str(candidate.relative_to(ROOT)), "published_file": str(published.relative_to(ROOT)),
        "sha256": CANDIDATE_SHA, "published_bytes_match": True,
        "literal_duplicate": result["candidate"]["directed_overlap_within_3px_all_positive"] > 0.70,
    })
    result.update({
        "schema": "registry-witness-recheck-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "RASTER-ARTIFACT MEASUREMENT; not HOLDOUT-DTI and not a competition score",
        "sample": {"sha256": SAMPLE_SHA,
                   "source": f"https://github.com/{SAMPLE_REPO}/blob/{SAMPLE_REF}/{SAMPLE_SOURCE}",
                   "provenance": "public owner mirror, not authenticated as an organizer download"},
        "local_format_diagnostic": raster_report(candidate, sample),
        "scope": "One registered witness and one previously generated research file; not a full registry audit or new candidate.",
        "verdict": "negative",
        "approved_for_submission": False,
        "experiments_run": 0,
        "slots_used": 0,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--witness", type=Path, default=DEFAULT_WITNESS)
    parser.add_argument("--fetch", action="store_true", help="restore pinned public GitHub bytes into the cache")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    if args.fetch:
        download_github_file(SAMPLE_REPO, SAMPLE_REF, SAMPLE_SOURCE, args.sample, SAMPLE_SHA, SAMPLE_BLOB)
        download_github_file(WITNESS["repo"], WITNESS["ref"], WITNESS["path"], args.witness,
                             WITNESS["sha256"], WITNESS["blob_sha1"])
    report = build_report(args.sample, args.witness, CANDIDATE, PUBLISHED, INDEX)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temp.replace(args.output)
    print(f"Wrote {args.output}: universal blocker={report['witness']['universal_blocker']}; "
          f"existing research file overlap={report['candidate']['directed_overlap_within_3px_all_positive']:.1%}. "
          "No submission is authorized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
