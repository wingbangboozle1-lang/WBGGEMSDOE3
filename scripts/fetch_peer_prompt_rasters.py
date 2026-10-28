#!/usr/bin/env python3
"""Fetch, SHA-256 pin, and audit all newly listed 2026-10-27 prompt peer repositories and GeoTIFFs.

Covers GEMSDOE92, GEMSDOEkarage1/2/3, ApartGEMSDOE1/2/3, GEMSDOESASS1/2/3, GINNYGEMSDOE1/2/3,
and EUGGEMSDOE1/2/3 so no submission raster named in the user prompt is omitted from uniqueness
checks or the auditable site ledger. No peer file is copied into any submission.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "peer_extra"
MANIFEST_OUT = ROOT / "registry" / "peer_prompt_2026-10-27.json"

PEER_RASTERS = [
    ("GEMSDOE92", "gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros", None,
     "buffedlizard55-lab/GEMSDOE92", "0fd35bc0ef0654bf511b40d15eb19c53fc229a08",
     "docs/downloads/gemsdoe92-lbmc1-35801dots-20261027-89a660f6-zeros.tif"),
    ("GEMSDOE92", "gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros", 0.0255,
     "buffedlizard55-lab/GEMSDOE92", "0fd35bc0ef0654bf511b40d15eb19c53fc229a08",
     "docs/downloads/gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros.tif"),
    ("GEMSDOEkarage1", "karage1-hmas-sinter-dualcover-sep29-20261027T220000Z-zeros", None,
     "karagemop466-tech/GEMSDOEkarage1", "65c07db29591",
     "docs/downloads/karage1-hmas-sinter-dualcover-sep29-20261027T220000Z-zeros.tif"),
    ("GEMSDOEkarage1", "gemsk1-gpcz-polarity-damagezone-36000dots-20261027T213002Z-636ed4c9-zeros", None,
     "karagemop466-tech/GEMSDOEkarage1", "65c07db29591",
     "docs/downloads/gemsk1-gpcz-polarity-damagezone-36000dots-20261027T213002Z-636ed4c9-zeros.tif"),
    ("GEMSDOEkarage2", "gemsdoe-karage2-hkarage1-irregular-submodular-15000d-6a3f542a-zeros", None,
     "karagemop466-tech/GEMSDOEkarage2", "690d7dd51ae4",
     "docs/downloads/gemsdoe-karage2-hkarage1-irregular-submodular-15000d-6a3f542a-zeros.tif"),
    ("GEMSDOEkarage3", "gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros", None,
     "karagemop466-tech/GEMSDOEkarage3", "ad17f0a45859",
     "docs/downloads/gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif"),
    ("GEMSDOEkarage3", "karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-zeros", None,
     "karagemop466-tech/GEMSDOEkarage3", "ad17f0a45859",
     "docs/downloads/karage3-k3-fuse-greedy-b2-20261027T212847Z-80117cd2-zeros.tif"),
    ("ApartGEMSDOE1", "apartgems1-udth-submod-e3-20261027-50e7b334-zeros", None,
     "apartanish22-droid/ApartGEMSDOE1", "43e6cb59ef82",
     "docs/downloads/apartgems1-udth-submod-e3-20261027-50e7b334-zeros.tif"),
    ("ApartGEMSDOE2", "apartgemsdoe2-udsr-exp3-strat2reg-26173-20261027T223500Z-017adbb0-zeros", None,
     "apartanish22-droid/ApartGEMSDOE2", "e72ec0626ac7",
     "docs/downloads/apartgemsdoe2-udsr-exp3-strat2reg-26173-20261027T223500Z-017adbb0-zeros.tif"),
    ("ApartGEMSDOE2", "apartgemsdoe2-ap2-oofctrl-44090dots-20261027T220804Z-5e265df9-zeros", None,
     "apartanish22-droid/ApartGEMSDOE2", "e72ec0626ac7",
     "docs/downloads/apartgemsdoe2-ap2-oofctrl-44090dots-20261027T220804Z-5e265df9-zeros.tif"),
    ("ApartGEMSDOE2", "apartgemsdoe2-ap1-dilatcond-37654-20261027-1f26aa05-zeros", None,
     "apartanish22-droid/ApartGEMSDOE2", "e72ec0626ac7",
     "docs/downloads/apartgemsdoe2-ap1-dilatcond-37654-20261027-1f26aa05-zeros.tif"),
    ("ApartGEMSDOE3", "apartgemsdoe3-h-apart3-1-cfkc-dhc-37654-20261027T215000Z-9dedadfc-zeros", None,
     "apartanish22-droid/ApartGEMSDOE3", "c47c806d1bac",
     "docs/downloads/apartgemsdoe3-h-apart3-1-cfkc-dhc-37654-20261027T215000Z-9dedadfc-zeros.tif"),
    ("GEMSDOESASS1", "gemsass1-swgb-hrv2-44090dots-20261027T122104Z-f9b3f764-zeros", None,
     "sassnarep3-star/GEMSDOESASS1", "7f87fc64dded",
     "swgb/downloads/gemsass1-swgb-hrv2-44090dots-20261027T122104Z-f9b3f764-zeros.tif"),
    ("GEMSDOESASS2", "gemsass2-ass2-altedge-hgb-44090-20261027-cc854482215e-zeros", None,
     "sassnarep3-star/GEMSDOESASS2", "3b21e4e9bf70",
     "docs/downloads/gemsass2-ass2-altedge-hgb-44090-20261027-cc854482215e-zeros.tif"),
    ("GEMSDOESASS2", "gemsdoesass2-hvfd-exp3-hydrocollinear-37654-20261027T120000Z-fc98343e-zeros", None,
     "sassnarep3-star/GEMSDOESASS2", "3b21e4e9bf70",
     "docs/downloads/gemsdoesass2-hvfd-exp3-hydrocollinear-37654-20261027T120000Z-fc98343e-zeros.tif"),
    ("GEMSDOESASS3", "gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros", None,
     "sassnarep3-star/GEMSDOESASS3", "86874b723021",
     "docs/downloads/gemsdoesass3-lwst-geoconduit-dual37654-20261027T120000Z-a9ad3386-zeros.tif"),
    ("GEMSDOESASS3", "gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros", None,
     "sassnarep3-star/GEMSDOESASS3", "86874b723021",
     "docs/downloads/gemsdoesass3-gsdhua3-sar-deconf-37654-20261027-74f544e862fd-zeros.tif"),
]

EMPTY_REPOS_VERIFIED = [
    {"site": "GINNYGEMSDOE1", "repo": "ginnymcfiner23-ux/GINNYGEMSDOE1", "tree_sha12": "761158ab9f7a", "tif_count": 0},
    {"site": "GINNYGEMSDOE2", "repo": "ginnymcfiner23-ux/GINNYGEMSDOE2", "tree_sha12": "91d564fcda6c", "tif_count": 0},
    {"site": "GINNYGEMSDOE3", "repo": "ginnymcfiner23-ux/GINNYGEMSDOE3", "tree_sha12": "4e00b89ed122", "tif_count": 0},
    {"site": "EUGGEMSDOE1", "repo": "eugboogieman123-ops/EUGGEMSDOE1", "tree_sha12": "81ac8521ea03", "tif_count": 0},
    {"site": "EUGGEMSDOE2", "repo": "eugboogieman123-ops/EUGGEMSDOE2", "tree_sha12": "3ae1fc951e54", "tif_count": 0},
    {"site": "EUGGEMSDOE3", "repo": "eugboogieman123-ops/EUGGEMSDOE3", "tree_sha12": "8fbb61b58ea0", "tif_count": 0},
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_commit(repo: str, ref: str) -> str:
    if len(ref) == 40:
        return ref
    r = subprocess.run(["gh", "api", f"repos/{repo}/commits/{ref}", "--jq", ".sha"], capture_output=True, text=True)
    if r.returncode != 0 or len(r.stdout.strip()) != 40:
        raise RuntimeError(f"Cannot resolve commit {repo}@{ref}: {r.stderr}")
    return r.stdout.strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prior = {}
    if MANIFEST_OUT.is_file():
        prior = {r["local"]: r for r in json.loads(MANIFEST_OUT.read_text()).get("rasters", [])}

    rows = []
    for site, sub, score, repo, ref, path in PEER_RASTERS:
        local = OUT_DIR / f"{site}__{Path(path).name}"
        rel = str(local.relative_to(ROOT))
        commit = prior.get(rel, {}).get("commit") or resolve_commit(repo, ref)
        if not local.is_file():
            tmp = local.with_suffix(".tif.part")
            with tmp.open("wb") as fh:
                r = subprocess.run(
                    ["gh", "api", f"repos/{repo}/contents/{path}?ref={commit}", "-H", "Accept: application/vnd.github.raw"],
                    stdout=fh,
                )
            if r.returncode != 0:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"Download failed: {repo}:{path}@{commit}")
            tmp.replace(local)
        digest = sha256_file(local)
        if rel in prior and prior[rel]["sha256"] != digest:
            raise RuntimeError(f"SHA mismatch against pinned peer raster {rel}")
        with rasterio.open(local) as ds:
            arr = ds.read(1)
            n_pos = int((np.isfinite(arr) & (arr > 0)).sum())
            shape = list(ds.shape)
        rows.append({
            "site": site,
            "submission": sub,
            "score": score,
            "score_class": "OWNER-REPORTED (unverified)" if score is not None else "UNSCORED (listed without score)",
            "repo": repo,
            "commit": commit,
            "path": path,
            "url": f"https://github.com/{repo}/blob/{commit}/{path}",
            "local": rel,
            "sha256": digest,
            "bytes": local.stat().st_size,
            "positive_pixels": n_pos,
            "shape": shape,
        })
        print(f"[peer] {digest[:12]}  dots={n_pos:7d}  {site:15s}  {sub}")

    doc = {
        "schema": "peer-prompt-2026-10-27-v1",
        "generated_utc": "2026-10-27",
        "note": "Read-only SHA-256-pinned comparator inventory of peer GeoTIFFs newly listed in the 2026-10-27 prompt. Used exclusively for uniqueness gates and research comparison; never copied into a submission.",
        "rasters": rows,
        "empty_repos_verified_zero_tif": EMPTY_REPOS_VERIFIED,
    }
    MANIFEST_OUT.write_text(json.dumps(doc, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
