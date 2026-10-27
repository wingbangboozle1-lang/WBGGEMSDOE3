"""The restoration wrapper must call the pinned template, not a missing local fork."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("restore_shared_data", ROOT / "scripts/restore_shared_data.py")
restore = module_from_spec(spec)
spec.loader.exec_module(restore)


def test_shell_wrapper_target_exists():
    wrapper = (ROOT / "scripts/restore_shared_data.sh").read_text()
    target = ROOT / "scripts/restore_shared_data.py"
    assert target.is_file()
    assert "scripts/restore_shared_data.py" in wrapper


def test_prepare_command_uses_upstream_tool(tmp_path):
    template = tmp_path / "template"
    upstream = template / "scripts" / "prepare_data.py"
    upstream.parent.mkdir(parents=True)
    upstream.write_text("# pinned upstream tool\n")

    assert restore.prepare_command("python-test", template) == [
        "python-test", str(upstream), "--fetch", "--cache-bands"
    ]


def test_prepare_command_fails_closed_if_upstream_tool_missing(tmp_path):
    try:
        restore.prepare_command(sys.executable, tmp_path)
    except FileNotFoundError as error:
        assert "pinned template data tool is missing" in str(error)
    else:
        raise AssertionError("missing upstream tool must not look like a successful restore")


def test_dry_run_does_not_fetch_or_write_data(tmp_path, monkeypatch, capsys):
    template = tmp_path / "template"
    upstream = template / "scripts" / "prepare_data.py"
    upstream.parent.mkdir(parents=True)
    upstream.write_text("# fixture\n")
    monkeypatch.setattr(restore, "ensure_template", lambda: template)
    monkeypatch.setattr(restore.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("dry run must not execute the data downloader")))

    assert restore.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Would run" in output
    assert "--fetch --cache-bands" in output


def test_template_only_does_not_fetch_data(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(restore, "ensure_template", lambda: tmp_path / "template")
    monkeypatch.setattr(restore.subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("template-only mode must not execute the data downloader")))

    assert restore.main(["--template-only"]) == 0
    assert "no data or band caches fetched" in capsys.readouterr().out
