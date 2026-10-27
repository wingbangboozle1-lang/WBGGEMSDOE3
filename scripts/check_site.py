#!/usr/bin/env python3
"""Check generated local links and decision consistency without network access."""
from html.parser import HTMLParser
from pathlib import Path
import json
import sys
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'href', 'src'} and value:
                self.targets.append(value)

    def handle_data(self, data):
        self.text.append(data)


def main():
    errors = []
    banner = 'OK TO DOWNLOAD AND SUBMIT'
    for page in sorted(DOCS.glob('*.html')):
        p = Links()
        p.feed(page.read_text())
        if banner not in ' '.join(p.text):
            errors.append(f'{page.name}: missing positive decision banner')
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{page.name}: missing/unsafe local link {link}')
    card = json.loads((DOCS / 'data/session2_run_card.json').read_text())
    build = json.loads((DOCS / 'data/session2_build.json').read_text())
    if card.get('verdict') != 'promote' or not card.get('raster_sha256') or card.get('selector_approval'):
        errors.append('run card does not match a promoted, unselected, hashed raster')
    if card['raster_sha256'] != build['files'][card['submission_name'] + '-zeros.tif']['sha256']:
        errors.append('run card hash does not match the published TIFF')
    if not all(v['passed'] for v in build['validation'].values()):
        errors.append('published TIFF fails its own format validator')
    if not build['uniqueness']['content_aware_pass']:
        errors.append('published TIFF fails the uniqueness gate')
    dl = DOCS / 'downloads'
    for suffix in ('-zeros.tif', '-nan.tif', '-zeros.zip'):
        if not (dl / (card['submission_name'] + suffix)).is_file():
            errors.append(f'missing published download {suffix}')
    required = {'index.html', 'executive-summary.html', 'research.html', 'evidence.html'}
    present = {page.name for page in DOCS.glob('*.html')}
    if not required <= present:
        errors.append(f'missing required generated pages: {sorted(required - present)}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Site check: pages, local links, hashes, validator, uniqueness and positive status PASS.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
