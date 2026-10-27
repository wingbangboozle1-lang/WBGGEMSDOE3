from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_generated_sites_fail_closed_and_have_resolved_local_links():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_site.py")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "fail-closed statuses and projection quarantine PASS" in result.stdout
