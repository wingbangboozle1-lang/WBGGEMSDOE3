#!/usr/bin/env python3
"""Refresh nine GitHub HEAD identities; never silently refresh scores or approve files.

Each repository is checked independently. Failed checks retain their last known
observation but become UNKNOWN/FAILED, rather than appearing fresh. Changes are
measured against the recorded October 26 audit HEADs, not against unrelated
historical file commits. This is an identity monitor, not a content re-audit.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'registry/upstream_baseline_2026-10-26.json'
MANIFEST = ROOT / 'registry/focus_sites.json'
OUTPUT = ROOT / 'evidence/latest-upstream-check.json'
HEX_SHA = re.compile(r'^[0-9a-f]{40}$')


def _read_json(path: Path, fallback: dict | None = None) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        if fallback is None:
            raise
        return fallback


def _fetch_head(repo: str) -> tuple[str, str]:
    url = f'https://api.github.com/repos/{repo}/commits/main'
    headers = {'User-Agent': 'GEMS-evidence-audit/1.0', 'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.geturl() != url:
            raise ValueError('GitHub commit API redirected')
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('GitHub commit response too large')
    commit = json.loads(raw)
    sha, tree = commit['sha'], commit['commit']['tree']['sha']
    if not HEX_SHA.fullmatch(sha) or not HEX_SHA.fullmatch(tree):
        raise ValueError('malformed GitHub commit or tree identity')
    return sha, tree


def refresh(output: str | Path = OUTPUT, baseline_path: str | Path = BASELINE,
            manifest_path: str | Path = MANIFEST) -> int:
    output = Path(output)
    baseline = _read_json(Path(baseline_path))
    manifest = _read_json(Path(manifest_path))
    previous = _read_json(output, {'repositories': []})
    old = {r['repo']: r for r in previous.get('repositories', [])}
    pins = {f"buffedlizard55-lab/{r['site']}": r['ref'] for r in manifest['sites']}
    base = {r['repo']: r for r in baseline['repositories']}
    if (len(pins) != len(manifest['sites']) or len(base) != len(baseline['repositories'])
            or set(base) != set(pins) or any(not HEX_SHA.fullmatch(p) for p in pins.values())):
        raise ValueError('baseline must contain exactly the focus-site repositories')
    for repo, row in base.items():
        if row.get('status') != 'FETCHED' or not HEX_SHA.fullmatch(row.get('commit', '')):
            raise ValueError(f'invalid historical baseline: {repo}')
    now = datetime.now(timezone.utc).isoformat()

    def check(repo):
        prior = old.get(repo, {})
        result = {
            'site': repo.rsplit('/', 1)[-1], 'repo': repo,
            'baseline_audit_head': base[repo]['commit'], 'pinned_file_ref': pins[repo],
            'last_attempt_utc': now,
            'observed_head': prior.get('observed_head') or prior.get('commit'),
            'observed_tree': prior.get('observed_tree') or prior.get('tree'),
            'last_success_utc': (prior.get('last_success_utc') or previous.get('checked_at'))
                                if prior.get('observed_head') or prior.get('commit') else None,
            'fetch_status': 'FAILED', 'comparison_to_baseline': 'UNKNOWN',
            'last_attempt_error': None,
        }
        try:
            sha, tree = _fetch_head(repo)
            result.update(observed_head=sha, observed_tree=tree, last_success_utc=now,
                          fetch_status='FETCHED',
                          comparison_to_baseline=('UNCHANGED' if sha == base[repo]['commit'] else 'CHANGED'))
        except Exception as error:
            result['last_attempt_error'] = type(error).__name__ + ': ' + str(error)[:160]
        return result

    # Mapping preserves the focus-manifest order and isolates each failure.
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, pins))
    report = {
        'checked_at': now, 'baseline_checked_at': baseline['checked_at'],
        'scope': ('GitHub main HEAD identities only; CHANGED means a new commit since the '
                  'historical audit, not proof that a particular score or TIFF changed. '
                  'No receipt, full content review, registry completeness, or approval is implied.'),
        'approved_for_submission': False, 'repositories': rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + '.tmp')
    tmp.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    tmp.replace(output)
    print(f"GitHub HEAD monitor: {sum(r['fetch_status']=='FETCHED' for r in rows)}/{len(rows)} fetched; "
          f"{sum(r['comparison_to_baseline']=='CHANGED' for r in rows)} changed; "
          f"{sum(r['fetch_status']=='FAILED' for r in rows)} failed/unknown.")
    return 0 if all(r['fetch_status'] == 'FETCHED' for r in rows) else 1


def mark_monitor_failure(output: str | Path, error: Exception) -> bool:
    """Mark all last-known rows UNKNOWN if setup fails before per-repo checks.

    If no readable prior snapshot exists, return False so the caller/build
    fails rather than manufacturing observations. Preserve the previous values
    and their individual successful timestamps.
    """
    output = Path(output)
    try:
        report = json.loads(output.read_text())
        rows = report['repositories']
        if not rows:
            return False
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            row.update(last_attempt_utc=now, fetch_status='FAILED',
                       comparison_to_baseline='UNKNOWN',
                       last_attempt_error='Monitor setup failed: ' + type(error).__name__)
        report.update(checked_at=now, approved_for_submission=False)
        tmp = output.with_suffix(output.suffix + '.tmp')
        tmp.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        tmp.replace(output)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=OUTPUT, type=Path)
    args = parser.parse_args()
    try:
        result = refresh(args.output)
    except Exception as error:
        retained = mark_monitor_failure(args.output, error)
        print(f'GitHub HEAD monitor failed: {type(error).__name__}; '
              f'{"marked prior rows UNKNOWN" if retained else "no valid prior snapshot"}.')
        result = 1
    raise SystemExit(result)
