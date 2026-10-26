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
