"""Download immutable public GitHub content, verifying it before use.

The GitHub token, when supplied by the environment, is sent only as an HTTP
header and is never written to a receipt. This module does not download from
redirects to arbitrary user-provided URLs.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(newurl)
        if target.scheme != "https" or target.netloc != "api.github.com":
            raise ValueError("refusing to forward credentials to a redirected host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(_SafeRedirect())


CHUNK = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def api_url(repo: str, ref: str, path: str) -> str:
    if not repo or not ref or not path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("invalid pinned GitHub path")
    return f"https://api.github.com/repos/{quote(repo, safe='/')}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}"


def open_github(repo: str, ref: str, path: str):
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "WBGGEMSDOE3-evidence-audit",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    return OPENER.open(Request(api_url(repo, ref, path), headers=headers), timeout=90)


def fetch_pinned(repo: str, ref: str, path: str, dest: Path, expected: str, size: int | None = None) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (size is None or dest.stat().st_size == size) and sha256(dest) == expected:
        return dest
    fd, temp_name = tempfile.mkstemp(prefix=".download-", suffix=".part", dir=dest.parent)
    temp = Path(temp_name)
    try:
        digest = hashlib.sha256()
        count = 0
        with os.fdopen(fd, "wb") as out, open_github(repo, ref, path) as response:
            while block := response.read(CHUNK):
                count += len(block)
                if size is not None and count > size:
                    raise ValueError(f"unexpected size while downloading {path}")
                digest.update(block)
                out.write(block)
        if digest.hexdigest() != expected or (size is not None and count != size):
            raise ValueError(f"hash or size mismatch for {repo}@{ref}:{path}")
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest
