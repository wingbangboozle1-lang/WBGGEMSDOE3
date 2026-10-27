#!/usr/bin/env python3
"""Check the generated site: decision consistency, local links, artefact integrity.

The decision is read from docs/data/run_card.json. Every published page must carry
the same <meta name="gemsdoe-decision"> value, and if the verdict is `promote` the
downloaded artefact must exist inside docs/downloads with the recorded SHA-256.
"""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import sys
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
PAGES = ('index.html', 'executive-summary.html', 'research.html', 'evidence.html')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.meta = {}
        self.text = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'meta' and d.get('name') == 'gemsdoe-decision':
            self.meta['decision'] = d.get('content')
        for key, value in attrs:
            if key in {'href', 'src'} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors = []
    card = json.loads((DOCS / 'data' / 'run_card.json').read_text())
    verdict = card.get('verdict')
    if verdict not in {'promote', 'negative'}:
        errors.append(f'run card verdict invalid: {verdict!r}')
    expected = 'SUBMIT' if verdict == 'promote' else 'DO-NOT-SUBMIT'

    for name in PAGES:
        page = DOCS / name
        if not page.exists():
            errors.append(f'missing page {name}')
            continue
        p = Links()
        p.feed(page.read_text())
        if p.meta.get('decision') != expected:
            errors.append(f'{name}: decision meta {p.meta.get("decision")!r} != {expected!r}')
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{name}: missing/unsafe local link {link}')
        body = ' '.join(p.text)
        if verdict == 'promote':
            if 'OK TO DOWNLOAD AND SUBMIT' not in body and 'Download .tif' not in body:
                errors.append(f'{name}: promote verdict but no submit action shown')

    tif = Path(card['download']['tif']).name
    served = DOCS / 'downloads' / tif
    if verdict == 'promote':
        if not served.exists():
            errors.append(f'artefact not published for download: downloads/{tif}')
        elif sha256(served) != card['sha256']:
            errors.append('published artefact SHA-256 does not match the run card')
    if not (DOCS / 'assets' / 'submission-map.png').exists():
        errors.append('missing quick-look map asset')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Site check PASS: {len(PAGES)} pages, decision {expected}, links resolve, artefact verified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
