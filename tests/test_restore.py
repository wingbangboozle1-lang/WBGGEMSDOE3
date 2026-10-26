import hashlib
import io

import pytest
import restore_data


def manifest(chunks):
    result = {"repo": "owner/repo", "ref": "fixed", "bytes": sum(map(len, chunks)),
              "sha256": hashlib.sha256(b"".join(chunks)).hexdigest(), "parts": []}
    for n, part in enumerate(chunks):
        digest = hashlib.sha1(f"blob {len(part)}\0".encode() + part).hexdigest()
        result["parts"].append({"path": str(n), "bytes": len(part), "git_blob_sha1": digest})
    return result


def test_multipart_restore_checks_each_blob_and_total(tmp_path, monkeypatch):
    chunks = [b"abc", b"defg"]
    monkeypatch.setattr(restore_data, "open_github", lambda repo, ref, path: io.BytesIO(chunks[int(path)]))
    dest = tmp_path / "features.tif"
    restore_data.restore_training(manifest(chunks), dest)
    assert dest.read_bytes() == b"abcdefg"
    assert not list(tmp_path.glob("*.part"))


def test_corrupt_part_never_overwrites_existing_file(tmp_path, monkeypatch):
    good = [b"abc", b"defg"]
    got = [b"abc", b"BAD!"]
    monkeypatch.setattr(restore_data, "open_github", lambda repo, ref, path: io.BytesIO(got[int(path)]))
    dest = tmp_path / "features.tif"
    dest.write_bytes(b"previous bytes")
    with pytest.raises(ValueError, match="git blob"):
        restore_data.restore_training(manifest(good), dest)
    assert dest.read_bytes() == b"previous bytes"
    assert not list(tmp_path.glob("*.part"))
