"""Pinned public-source retrieval. Digests verify bytes, not organizer provenance."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def github_blob_sha1(path: Path) -> str:
    path = Path(path)
    h = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download_github_file(repo: str, ref: str, source: str, dest: Path,
                         sha256: str, blob_sha1: str | None = None) -> Path:
    """Read an immutable GitHub file into cache and require its pinned digest.

    The GitHub CLI uses the environment's existing connection; it never writes
    credentials into this project. An unauthenticated HTTPS fallback is used only
    if `gh` is not installed. Corrupt downloads are never promoted into cache.
    """
    dest = Path(dest)
    if dest.is_file() and sha256_file(dest) == sha256:
        if blob_sha1 and github_blob_sha1(dest) != blob_sha1:
            raise ValueError(f"cached Git blob mismatch for {source}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".download-", dir=dest.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    endpoint = f"repos/{repo}/contents/{source}?ref={ref}"
    try:
        if shutil.which("gh"):
            with tmp.open("wb") as out:
                result = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw+json", endpoint],
                                        stdout=out, stderr=subprocess.PIPE, timeout=180, check=False)
            if result.returncode:
                raise RuntimeError(f"GitHub fetch failed for {repo}/{source}: {result.stderr.decode(errors='replace')[:300]}")
        else:
            req = urllib.request.Request(f"https://api.github.com/{endpoint}", headers={
                "Accept": "application/vnd.github.raw+json", "User-Agent": "GEMS-research-audit/1.0"})
            with urllib.request.urlopen(req, timeout=180) as stream, tmp.open("wb") as out:
                shutil.copyfileobj(stream, out, length=1 << 20)
        if sha256_file(tmp) != sha256:
            raise ValueError(f"SHA-256 mismatch for {repo}/{source}; cached pin not replaced")
        if blob_sha1 and github_blob_sha1(tmp) != blob_sha1:
            raise ValueError(f"Git blob mismatch for {repo}/{source}")
        os.replace(tmp, dest)
        return dest
    finally:
        tmp.unlink(missing_ok=True)
