from io import BytesIO
from pathlib import Path
import hashlib
import tarfile
import pytest

from gems_project.sources import sha256_file, github_blob_sha1, download_github_file
from gems_project.template import _safe_members


def test_digest_and_cached_pins_are_required(tmp_path):
    p = tmp_path / "reference.tif"
    p.write_bytes(b"known content")
    digest = hashlib.sha256(b"known content").hexdigest()
    blob = hashlib.sha1(b"blob 13\0known content").hexdigest()
    assert sha256_file(p) == digest
    assert github_blob_sha1(p) == blob
    assert download_github_file("x/y", "abc", "file.tif", p, digest, blob) == p
    with pytest.raises(ValueError, match="cached Git blob mismatch"):
        download_github_file("x/y", "abc", "file.tif", p, digest, "0" * 40)


def tar_with(name, member_type=tarfile.REGTYPE):
    stream = BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as t:
        item = tarfile.TarInfo(name)
        item.type = member_type
        if member_type == tarfile.SYMTYPE:
            item.linkname = "../../elsewhere"
        t.addfile(item)
    stream.seek(0)
    return stream


@pytest.mark.parametrize("name,kind", [("../escape", tarfile.REGTYPE),
                                       ("/absolute", tarfile.REGTYPE),
                                       ("folder/link", tarfile.SYMTYPE)])
def test_archive_path_escape_and_links_rejected(name, kind):
    with tarfile.open(fileobj=tar_with(name, kind), mode="r") as archive:
        with pytest.raises(ValueError, match="unsafe archive"):
            _safe_members(archive)


def test_archive_allows_normal_files():
    with tarfile.open(fileobj=tar_with("template/file.py"), mode="r") as archive:
        assert len(_safe_members(archive)) == 1


def test_public_fetch_falls_back_when_gh_cannot_fetch(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch
    payload = b'verified public bytes'
    expected = hashlib.sha256(payload).hexdigest()

    def failed_gh(*args, **kwargs):
        kwargs['stdout'].write(b'partial error body')
        return SimpleNamespace(returncode=1, stderr=b'not authenticated')

    with patch('gems_project.sources.shutil.which', return_value='/usr/bin/gh'), \
         patch('gems_project.sources.subprocess.run', side_effect=failed_gh), \
         patch('gems_project.sources.urllib.request.urlopen', return_value=BytesIO(payload)):
        result = download_github_file('owner/repo', 'immutable-ref', 'x.tif', tmp_path / 'x.tif', expected)
    assert result.read_bytes() == payload
