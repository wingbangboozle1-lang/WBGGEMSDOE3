#!/usr/bin/env python3
"""Restore SHA-pinned mirrors into the .cache layout expected by src/gemsdoe.

Reuses registry/data_manifest.json + research/input_manifest.json pins.
Fails closed on any digest mismatch. Mirrors are owner-supplied GitHub blobs,
NOT organizer-authenticated bytes (see registry/data_manifest.json note).
"""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
X24_REF = "07345ea0604953d7efb858d9cfbc21e20c7aca0b"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gh_raw(repo: str, ref: str, path: str) -> bytes:
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
         "-H", "Accept: application/vnd.github.raw"],
        check=True, capture_output=True)
    return r.stdout


def fetch(job):
    repo, ref, path, dest, want_sha, want_bytes = job
    dest = Path(dest)
    if dest.exists():
        b = dest.read_bytes()
        if (not want_sha or sha256(b) == want_sha) and (not want_bytes or len(b) == want_bytes):
            return f"CACHED {dest.relative_to(ROOT)}"
    b = gh_raw(repo, ref, path)
    if want_sha and sha256(b) != want_sha:
        raise ValueError(f"SHA MISMATCH {path}: {sha256(b)} != {want_sha}")
    if want_bytes and len(b) != want_bytes:
        raise ValueError(f"SIZE MISMATCH {path}: {len(b)} != {want_bytes}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b)
    return f"PASS {dest.relative_to(ROOT)} sha={sha256(b)[:16]} bytes={len(b)}"


def main():
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]
    by_id = {f["id"]: f for f in manifest}
    jobs = []

    # core rasters -> .cache/data/
    tf = by_id["training_features"]
    parts = []
    for i, p in enumerate(tf["parts"]):
        d = CACHE / "data" / f"_tf_part-{i:03d}"
        parts.append(d)
        jobs.append((tf["repo"], tf["ref"], p, d, None, None))
    for fid in ("labels", "sample_submission"):
        f = by_id[fid]
        jobs.append((f["repo"], f["ref"], f["path"], CACHE / "data" / f["dest"], f["sha256"], f["bytes"]))

    # external layers -> .cache/upstream/x24/data/external/
    for fid in ("ext_lidar_scarp_features_u8", "ext_geodawn_rad_u8", "ext_geodawn_extensions_u8",
                "ext_derived_sgmc_faults_100m_u8", "ext_tiger_road_distance_m",
                "ext_gdr_wellspring_in_footprint", "ext_gdr_volcanic_vents_in_footprint",
                "ext_gdr_qfaults_traces"):
        f = by_id[fid]
        jobs.append((f["repo"], f["ref"], f["path"],
                     CACHE / "upstream" / "x24" / "data" / "external" / Path(f["dest"]).name,
                     f["sha256"], f["bytes"]))
    # lidar band semantics JSON (no manifest pin; sha recorded in output)
    jobs.append(("buffedlizard55-lab/GEMSDOE24", X24_REF, "data/external/lidar_scarp_features.json",
                 CACHE / "upstream" / "x24" / "data" / "external" / "lidar_scarp_features.json", None, None))

    # exact REPORTED calibration rasters expected by src/gemsdoe/validation.py
    sys.path.insert(0, str(ROOT / "src"))
    from gemsdoe.validation import REPORTED  # noqa: E402
    for _label, _score, rel in REPORTED:
        relp = Path(rel)
        parts_rel = relp.parts  # .cache/upstream/xNN/...
        repo_dir = parts_rel[2]
        inner = str(Path(*parts_rel[3:]))
        if repo_dir == "x24":
            repo, ref = "buffedlizard55-lab/GEMSDOE24", X24_REF
        elif repo_dir == "x32":
            repo, ref = "buffedlizard55-lab/GEMSDOE32", "5fc7792c5887735ecd3aa9a612787da588a7bf2c"
        else:
            raise ValueError(repo_dir)
        jobs.append((repo, ref, inner, ROOT / rel, None, None))

    # nine focus-site top files (pinned in research/input_manifest.json)
    for item in json.loads((ROOT / "research/input_manifest.json").read_text()):
        if item["id"].startswith("GEMSDOE"):
            jobs.append((item["repo"], item["ref"], item["path"],
                         CACHE / "focus" / item["dest"], item["sha256"], None))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for msg in pool.map(fetch, jobs):
            print(msg, flush=True)

    # assemble + verify training_features
    out = CACHE / "data" / "training_features.tif"
    if not (out.exists() and sha256(out.read_bytes()) == tf["sha256"]):
        with out.open("wb") as fh:
            for d in parts:
                fh.write(d.read_bytes())
    got = sha256(out.read_bytes())
    assert got == tf["sha256"], f"training_features sha {got}"
    for d in parts:
        d.unlink(missing_ok=True)
    print(f"PASS training_features.tif sha={got[:16]} bytes={out.stat().st_size}", flush=True)
    print("ALL RESTORED", flush=True)


if __name__ == "__main__":
    main()
