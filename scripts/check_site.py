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


def _check_links(pages, errors, expected_banner):
    for page in sorted(pages):
        parser = Links()
        parser.feed(page.read_text(encoding='utf-8'))
        text = ' '.join(parser.text)
        if expected_banner and expected_banner not in text:
            errors.append(f'{page.relative_to(DOCS)}: missing negative banner')
        for link in parser.targets:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS.resolve()) or not target.exists():
                errors.append(f'{page.relative_to(DOCS)}: missing/unsafe local link {link}')


def main():
    errors = []
    root_pages = list(DOCS.glob('*.html'))
    _check_links(root_pages, errors, 'No competition file is cleared')

    lst1 = DOCS / 'lst1'
    lst1_pages = list(lst1.glob('*.html'))
    required_lst1 = {
        'index.html', 'summary.html', 'how-to-submit.html', 'why.html',
        'hypotheses.html', 'evidence.html', 'limitations.html',
    }
    present_lst1 = {page.name for page in lst1_pages}
    if not required_lst1 <= present_lst1:
        errors.append(f'missing required LST1 pages: {sorted(required_lst1 - present_lst1)}')
    _check_links((lst1 / name for name in required_lst1 if (lst1 / name).exists()), errors, None)
    for name in ('index.html', 'summary.html', 'how-to-submit.html'):
        page = lst1 / name
        if page.exists() and 'DO NOT SUBMIT' not in page.read_text(encoding='utf-8'):
            errors.append(f'lst1/{name}: missing explicit DO NOT SUBMIT status')

    card = json.loads((DOCS / 'data/run_card.json').read_text())
    if card.get('verdict') != 'negative' or card.get('raster_sha256') is not None or card.get('selector_approval'):
        errors.append('main run card does not match a negative, no-raster decision')
    legacy_card_path = lst1 / 'lst1_run_card.json'
    if legacy_card_path.exists():
        legacy = json.loads(legacy_card_path.read_text())
        if (legacy.get('ready_to_submit') is not False
                or legacy.get('selector_approval') is not False
                or legacy.get('registry_audit', {}).get('literal_rule_pass') is not False
                or legacy.get('gate_status', {}).get('G1_literal_overlap_le_0.70_for_every_registry_raster') != 'FAIL'
                or legacy.get('gate_status', {}).get('G3_current_shared_evaluator_result_available') != 'NOT RUN'
                or 'lst_projection_band' in legacy or 'lst_calibrators' in legacy):
            errors.append('LST1 card still contains approval or current-facing projection data')
    if (lst1 / 'build_result.json').exists():
        errors.append('raw historical projection diagnostics must not be served from docs/lst1')

    required = {'index.html', 'executive-summary.html', 'research.html', 'evidence.html'}
    present = {page.name for page in root_pages}
    if not required <= present:
        errors.append(f'missing required generated pages: {sorted(required - present)}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Site check: root and LST1 pages, local links, fail-closed statuses and projection quarantine PASS.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
