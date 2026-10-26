"""Report live GitHub source drift; never silently refresh scientific evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for source in json.loads((ROOT / 'docs/sources.json').read_text()):
        result = subprocess.run(['gh', 'api', f"repos/{source['repo']}/commits/HEAD", '--jq', '.sha'], capture_output=True, text=True)
        current = result.stdout.strip() if result.returncode == 0 else None
        rows.append({'repo': source['repo'], 'pinned': source['commit'], 'observed': current,
                     'state': 'UNKNOWN' if current is None else ('UNCHANGED' if current == source['commit'] else 'CHANGED'),
                     'error': result.stderr.strip() if result.returncode else None})
    output = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'GitHub source HEAD only; not a live leaderboard or complete raster registry',
              'rows': rows, 'submission_authorized': False}
    (ROOT / 'docs/freshness.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
