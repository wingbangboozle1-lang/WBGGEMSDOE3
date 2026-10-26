#!/usr/bin/env python3
"""Restore integrity-pinned owner mirrors into ignored local data/raw/.

Public mirrors are not proof of official origin. This does not reconstruct the
missing shared feature cache or pretend to download the login-walled data page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from github_bytes import CHUNK, fetch_pinned, open_github, sha256

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/data-sources.json"
RAW = ROOT / "data/raw"


def restore_training(meta: dict, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size == meta["bytes"] and sha256(dest) == meta["sha256"]:
        print(f"verified cached {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".training-", suffix=".part", dir=dest.parent)
    temp = Path(temp_name)
    total = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as out:
            for part in meta["parts"]:
                print(f"restoring {part['path'].rsplit('/', 1)[-1]}", flush=True)
                git = hashlib.sha1(f"blob {part['bytes']}\0".encode())
                n = 0
                with open_github(meta["repo"], meta["ref"], part["path"]) as response:
                    while block := response.read(CHUNK):
                        n += len(block)
                        if n > part["bytes"]:
                            raise ValueError("training part exceeds expected size")
                        git.update(block)
                        total.update(block)
                        out.write(block)
                if n != part["bytes"] or git.hexdigest() != part["git_blob_sha1"]:
                    raise ValueError(f"training part failed git blob check: {part['path']}")
        if temp.stat().st_size != meta["bytes"] or total.hexdigest() != meta["sha256"]:
            raise ValueError("assembled training raster failed SHA-256 / size check")
        os.replace(temp, dest)
        print(f"verified {dest.name}: {meta['sha256']}")
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small-only", action="store_true", help="skip the large multi-part feature raster")
    args = parser.parse_args()
    meta = json.loads(MANIFEST.read_text())
    print(meta["notice"])
    for item in meta["files"]:
        dest = RAW / item["dest"]
        fetch_pinned(meta["repo"], meta["ref"], item["path"], dest, item["sha256"], item["bytes"])
        print(f"verified {dest.name}: {item['sha256']}")
    if not args.small_only:
        restore_training(meta["training_features"], RAW / meta["training_features"]["dest"])
    print("Still missing or unverified:")
    for item in meta["missing"]:
        print(" -", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
