"""Bootstrap, but never fork, the pinned shared 57GEMSDOE template."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

from .sources import sha256_file

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "822a0ce5546c7b6749cdd82eb145b6b3e616603d"
ARCHIVE_SHA256 = "1dafa3152617706e3932c260548746c9030b24454f3ad5dea19c99c1c715c780"
CRITICAL = {
    "scripts/prepare_data.py": "73c743e8ab7238b44ce82b9a8d4f9c7a17312fc023ee894ebd0e3788a456d7d6",
    "src/gems57/evaluate_holdout.py": "ad86640b46f3c5fc6b1aceec4c4bfc82d03e35008b37ab2a8ad6076e6810ff3a",
    "src/gems57/submission_writer.py": "41220185ac2823fe5358603d38f2a915ea3e5f1ab1f94f0b237295b38b4a2565",
    "src/gems57/uniqueness.py": "1c5094b814277ae801ccea6a47cf744429cffcdc10f9cc79f229d5fc44a8df95",
    "src/gems57/holdout.py": "7a0a84176986190b527aa9c6a84216c2dab4b599f25b1143db5f420e85020ab1",
    "src/gems57/metric.py": "4afe10cbaa229948520c75194b1ebc32676e72544f05582f0725092b097b4d7f",
    "src/gems57/grid.py": "b96df7ec0f33658a61b0baa5db85fcd19be2cd8b1873f99699bd26bddae8cd8d",
    "src/gems57/gates.py": "7c57f70dbba58bb1112df4193a3de56516af0f981970d4b943b394f99b573dae",
    "src/gems57/validate.py": "e7849554b47f6a2b66aeb2f7cfd5db06267412f049f52a73f1c41f934a2c34dd",
    "evidence/uniqueness_session6_full_registry_696.json": "d1c721a65e0ec4e32a51aeb80620ded0f3498b0b356046787c7abecf5038a80f",
}


def verify_template(root: Path) -> Path:
    root = Path(root)
    for relative, digest in CRITICAL.items():
        p = root / relative
        if not p.is_file() or sha256_file(p) != digest:
            raise ValueError(f"shared template is missing/modified: {p}; refusing a private fork")
    return root


def _safe_members(archive: tarfile.TarFile):
    """Reject paths, symlinks, and special files that could escape extraction."""
    members = archive.getmembers()
    for member in members:
        path = Path(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            raise ValueError(f"unsafe archive member: {member.name}")
    return members


def ensure_template(root: Path | None = None) -> Path:
    """Use a hash-checked local template or restore its pinned archive to cache."""
    override = root or (Path(os.environ["GEMS_TEMPLATE_DIR"]) if os.getenv("GEMS_TEMPLATE_DIR") else None)
    if override:
        return verify_template(Path(override).resolve())
    cache = ROOT / ".cache"
    target = cache / f"57GEMSDOE-{COMMIT}"
    if target.exists():
        return verify_template(target)
    cache.mkdir(parents=True, exist_ok=True)
    archive_path = cache / "template57-pinned.tar.gz"
    if not archive_path.is_file() or sha256_file(archive_path) != ARCHIVE_SHA256:
        fd, temporary = tempfile.mkstemp(prefix=".template-", dir=cache)
        os.close(fd)
        try:
            request = urllib.request.Request(
                f"https://codeload.github.com/buffedlizard55-lab/57GEMSDOE/tar.gz/{COMMIT}",
                headers={"User-Agent": "GEMS-research-audit/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response, open(temporary, "wb") as out:
                shutil.copyfileobj(response, out, length=1 << 20)
            if sha256_file(Path(temporary)) != ARCHIVE_SHA256:
                raise ValueError("shared template archive SHA-256 mismatch")
            os.replace(temporary, archive_path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix=".template-extract-", dir=cache) as temp_dir:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = _safe_members(archive)
            # _safe_members rejects links, special files, absolute paths, and '..'.
            # Avoid the Python 3.12-only filter argument so 3.11 also works.
            archive.extractall(temp_dir, members=members)
        extracted = Path(temp_dir) / f"57GEMSDOE-{COMMIT}"
        verify_template(extracted)
        os.replace(extracted, target)
    return verify_template(target)
