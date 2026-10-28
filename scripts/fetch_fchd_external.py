#!/usr/bin/env python3
"""Fetch and SHA-256 verify the official public-domain 3DEP 10 m geomorphology, fluvial-chi,
and BLM mining-claim external rasters used by the FCHD-NCM lane.

Every byte is verified against its cryptographic SHA-256 pin; mismatches fail closed.
Provenance: owner-hosted GitHub mirrors of US Public Domain USGS 3DEP 1/3 arc-second DEM
products (17 U.S.C. § 105; https://www.usgs.gov/3d-elevation-program) and US BLM Mining Claims
(https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2).
SHA-256 pins prove mirror byte identity, not direct download from USGS/BLM inside this sandbox.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT_DIR = ROOT / "data" / "raw" / "external"
MANIFEST_PATH = ROOT / "registry" / "fchd_external_manifest.json"

FILES = [
    {
        "id": "ext_topo_10m_derived_100m_u8",
        "filename": "topo_10m_derived_100m_u8.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "commit": "02563d07fb85d2f4d35887503d380d34d4017197",
        "path": "data/external/topo_10m_derived_100m_u8.tif",
        "sha256": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
        "bytes": 32523329,
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "upstream_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/USGS_Seamless_DEM_13.vrt",
        "license": "US Public Domain (17 U.S.C. § 105)",
        "bands": [
            "slope_p90", "slope_max", "steep_frac", "slope_std", "relief_local",
            "curv_prof_absmax", "aspect_coherence", "hs_lineament", "dem_mean",
        ],
        "zero_catalogue": True,
    },
    {
        "id": "ext_dem10_chi_100m_i16",
        "filename": "dem10_chi_100m_i16.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "commit": "02563d07fb85d2f4d35887503d380d34d4017197",
        "path": "data/external/dem10_chi_100m_i16.tif",
        "sha256": "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
        "bytes": 12777098,
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "upstream_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/",
        "license": "US Public Domain (17 U.S.C. § 105)",
        "bands": [
            "step_max_x1000", "step_min_x1000", "ksn_max_m0.9",
            "log10_area_m2_x1000", "zmean_m",
        ],
        "zero_catalogue": True,
    },
    {
        "id": "ext_dem10_chi_100m_sig_i32",
        "filename": "dem10_chi_100m_sig_i32.tif",
        "repo": "buffedlizard55-lab/60GEMSDOE",
        "commit": "02563d07fb85d2f4d35887503d380d34d4017197",
        "path": "data/external/dem10_chi_100m_sig_i32.tif",
        "sha256": "0ba7816bc082b8a71ebcb26596b5e330abb63231be94abad4e447eb316ffb95c",
        "bytes": 2804587,
        "official_source": "https://www.usgs.gov/3d-elevation-program",
        "upstream_url": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current/",
        "license": "US Public Domain (17 U.S.C. § 105)",
        "bands": ["branch_signature_global_index_100m"],
        "zero_catalogue": True,
    },
    {
        "id": "ext_blm_closed_claim_distance_m",
        "filename": "blm_closed_claim_distance_m.tif",
        "repo": "buffedlizard55-lab/GEMSDOE24",
        "commit": "9da8a18381e179530c3b878d073314feaa26a20c",
        "path": "data/external/audit_sources/blm_closed_claim_distance_m.tif",
        "sha256": "a88356423c03fc8b6510a84f77cee2b1d38c4ccbd7761bc95c1ca8332a2e166a",
        "bytes": 5752587,
        "official_source": "https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2",
        "upstream_url": "https://gis.blm.gov/nlsdb/rest/services/Mining_Claims/MiningClaims/MapServer/2?f=json",
        "license": "US Public Domain (17 U.S.C. § 105 — US Bureau of Land Management)",
        "bands": ["blm_closed_claim_distance_m"],
        "zero_catalogue": True,
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    verified = []
    for item in FILES:
        dest = EXT_DIR / item["filename"]
        if not (dest.is_file() and sha256_file(dest) == item["sha256"]):
            tmp = dest.with_suffix(".tif.part")
            with tmp.open("wb") as fh:
                r = subprocess.run(
                    [
                        "gh", "api",
                        f"repos/{item['repo']}/contents/{item['path']}?ref={item['commit']}",
                        "-H", "Accept: application/vnd.github.raw",
                    ],
                    stdout=fh,
                )
            if r.returncode != 0:
                tmp.unlink(missing_ok=True)
                print(f"[FAIL] download failed for {item['id']}", file=sys.stderr)
                return 1
            tmp.replace(dest)
        got_sha = sha256_file(dest)
        got_bytes = dest.stat().st_size
        if got_sha != item["sha256"] or got_bytes != item["bytes"]:
            dest.unlink(missing_ok=True)
            print(
                f"[FAIL] hash/size mismatch for {item['id']}: got {got_sha} ({got_bytes} B)",
                file=sys.stderr,
            )
            return 1
        print(f"[PASS] {item['id']:32s} {got_bytes:>11,d} B  sha256={got_sha[:16]}...")
        verified.append(item)

    manifest = {
        "schema": "fchd-external-manifest-v1",
        "generated_utc": "2026-10-27",
        "provenance_note": (
            "Cryptographic SHA-256 pins verify exact byte identity of owner-hosted GitHub mirrors "
            "attributed to official US Public Domain USGS 3DEP 1/3 arc-sec DEM and US BLM Mining "
            "Claims products. Mirrors are integrity-pinned, not fetched directly from USGS/BLM inside this sandbox."
        ),
        "files": verified,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
