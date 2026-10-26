"""Restore pinned comparison-only rasters. Never publish these as new submissions."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def restore(item):
    dest = ROOT / 'data' / item['dest']
    if (ROOT / 'data').resolve() not in dest.resolve().parents:
        raise ValueError('Unsafe destination')
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == item['sha256']:
        return item['id']
    result = subprocess.run(['gh', 'api',
        f"repos/{item['repo']}/contents/{item['path']}?ref={item['ref']}",
        '-H', 'Accept: application/vnd.github.raw'], check=True, capture_output=True)
    if hashlib.sha256(result.stdout).hexdigest() != item['sha256']:
        raise ValueError(f"Checksum mismatch: {item['id']}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(result.stdout)
    return item['id']


if __name__ == '__main__':
    items = json.loads((ROOT / 'research/input_manifest.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(restore, items):
            print('SHA-256 verified:', name)
