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
    for page in sorted(DOCS.glob('*.html')):
        p = Links()
        p.feed(page.read_text())
        if 'No competition file is cleared' not in ' '.join(p.text):
            errors.append(f'{page.name}: missing negative banner')
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{page.name}: missing/unsafe local link {link}')
    card = json.loads((DOCS / 'data/run_card.json').read_text())
    if card.get('verdict') != 'negative' or card.get('raster_sha256') is not None or card.get('selector_approval'):
        errors.append('run card does not match a negative, no-raster decision')
    required = {'index.html', 'executive-summary.html', 'research.html', 'evidence.html'}
    present = {page.name for page in DOCS.glob('*.html')}
    if not required <= present:
        errors.append(f'missing required generated pages: {sorted(required - present)}')

    # CSPES lane subtree: its own pages, local links, negative banner and run-card consistency.
    lane = DOCS / 'cspes'
    required_lane = {'index.html', 'how-to-submit.html'}
    lane_pages = set(p.name for p in lane.glob('*.html')) if lane.is_dir() else set()
    if not required_lane <= lane_pages:
        errors.append(f'missing CSPES lane pages: {sorted(required_lane - lane_pages)}')
    for page in sorted(lane.glob('*.html')) if lane.is_dir() else []:
        p = Links()
        p.feed(page.read_text())
        text = ' '.join(p.text)
        if 'Not cleared for upload' not in text and 'NOT OK TO SUBMIT' not in text:
            errors.append(f'{page.relative_to(DOCS)}: missing negative lane banner')
        for link in p.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{page.relative_to(DOCS)}: missing/unsafe local link {link}')
    lane_card_path = lane / 'data/cspes_run_card.json'
    if lane_card_path.is_file():
        lc = json.loads(lane_card_path.read_text())
        if lc.get('verdict') != 'negative' or lc.get('selector_approval') or lc.get('slots_spent') != 0:
            errors.append('CSPES run card must be negative, unapproved and spend zero slots')
        if not lc.get('validator_output', {}).get('independent_gemsw_validate', {}).get('passed'):
            errors.append('CSPES run card lost its independent validator PASS')
        tif = DOCS / lc['files']['tif'].removeprefix('docs/')
        if not tif.is_file():
            errors.append(f'CSPES downloadable TIF missing: {tif}')
    else:
        errors.append('missing CSPES run card in site data')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Site check: required pages, local links and negative status PASS.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
