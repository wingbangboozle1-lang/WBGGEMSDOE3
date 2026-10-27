"""Legacy API for the project's conservative read-only GeoTIFF preflight.

A format PASS is never a submission approval or organizer acceptance. A real
reference grid is mandatory; synthetic/owner-mirrored samples do not prove
organizer provenance. See ``gems_project.format_preflight`` for the checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from .gems_project.format_preflight import raster_report
    from .gems_project.sources import sha256_file
except ImportError:  # direct ``python src/validate.py`` execution
    from gems_project.format_preflight import raster_report
    from gems_project.sources import sha256_file


@dataclass
class ValidationResult:
    ok: bool
    passed: list[str]
    failed: list[str]
    metrics: dict
    sha256: str | None

    @property
    def summary(self) -> str:
        status = 'PASS' if self.ok else 'BLOCK'
        lines = [f'[{status}] local format diagnostic — NOT submission approval',
                 f'sha256: {self.sha256}']
        lines.extend(f'  PASS: {item}' for item in self.passed)
        lines.extend(f'  FAIL: {item}' for item in self.failed)
        return '\n'.join(lines)


def validate_submission(submission_path: str, reference_path: str | None = None, *,
                        require_single_band: bool = True,
                        value_range: tuple[float, float] = (0.0, 1.0)) -> ValidationResult:
    path = Path(submission_path)
    digest = sha256_file(path) if path.is_file() else None
    if not reference_path:
        return ValidationResult(False, [], ['a real reference grid is required'], {}, digest)
    if not require_single_band or value_range != (0.0, 1.0):
        return ValidationResult(False, [], ['competition format checks cannot be relaxed'], {}, digest)
    try:
        report = raster_report(path, reference_path)
    except Exception as exc:
        return ValidationResult(False, [], [f'could not inspect raster or reference: {exc}'], {}, digest)
    checks = report['checks']
    metrics = dict(report)
    metrics.update(value_min=report['inside_min'], value_max=report['inside_max'])
    return ValidationResult(report['format_ok'], [k for k, v in checks.items() if v],
                            [k for k, v in checks.items() if not v], metrics, report['sha256'])


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print('usage: python -m src.validate <candidate.tif> <reference.tif>')
        raise SystemExit(2)
    result = validate_submission(sys.argv[1], sys.argv[2])
    print(result.summary)
    raise SystemExit(0 if result.ok else 1)
