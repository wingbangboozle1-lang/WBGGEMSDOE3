#!/usr/bin/env python3
"""Replace the historical LST1 microsite with a research-only archive notice.

No TIFF is generated, repackaged, copied to Pages, or approved by this script.
Historical evidence and the original research bytes remain under evidence/ and
submission/ in the repository; the old readiness claims are superseded.
"""
from __future__ import annotations

import html
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/lst1'
GITHUB = 'https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/'
PAGES = ('index.html', 'summary.html', 'how-to-submit.html', 'why.html',
         'hypotheses.html', 'evidence.html', 'limitations.html')


def build() -> None:
    report = json.loads((ROOT / 'evidence/archive_audit.json').read_text())
    rows = report.get('tiffs', [])
    if (len(rows) != 2 or report.get('approved_for_submission') is not False or
            any(r.get('forward_overlap_witness_within_3px_all_positive') != 1.0 or
                r.get('positive_inside') != 32810 or r.get('positive_outside') != 0 or
                r.get('dtype') != 'float32' or not r.get('inside_finite_range_0_1') or
                r.get('inside_nan') != 0 or r.get('inside_infinity') != 0 for r in rows)):
        raise ValueError('Archive report does not support a negative LST1 notice; review before publishing')
    for row in rows:
        name = row['filename']
        if Path(name).name != name or hashlib.sha256((ROOT / 'submission' / name).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Archive report no longer matches the saved TIFF bytes')
    archive_name = report['zip']['filename']
    if (Path(archive_name).name != archive_name or not report['zip']['crc_test_passed'] or
            not report['zip']['matches_tiff'] or
            hashlib.sha256((ROOT / 'submission' / archive_name).read_bytes()).hexdigest() != report['zip']['sha256']):
        raise ValueError('Archive report no longer matches the saved ZIP bytes')
    entries = ''.join(
        '<li><a href="' + GITHUB + 'submission/' + html.escape(r['filename'], quote=True) + '">'
        + html.escape(r['filename']) + '</a> · SHA-256 <code>' + html.escape(r['sha256'])
        + '</code> · 100% witness overlap · research only</li>' for r in rows)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Archived LST1 research · DO NOT SUBMIT</title><link rel="stylesheet" href="../assets/styles.css"></head>
<body><header class="topbar"><div class="wrap navrow"><a class="brand" href="../index.html">GEMS FIELD NOTES</a>
<nav class="navigation"><a href="../index.html">Current dashboard</a><a href="../executive-summary.html">Submission guide</a><a href="../evidence.html">Evidence</a></nav></div></header>
<main class="wrap content"><div class="eyebrow">Superseded archive / LST1</div><h1>Research only.<br>Do not submit.</h1>
<div class="decision"><div class="decision-inner"><div><div class="decision-label">Negative verdict</div><h2>No competition file is cleared.</h2>
<p>Both historical LST1 TIFFs have 100% directed overlap with a registered witness; they violate the literal &gt;70% stop. The earlier uniqueness exemptions were unauthorized. A local format diagnostic does not establish portal acceptance.</p></div></div></div>
<section class="section"><div class="grid2"><article class="card panel"><h2>What the bytes show</h2>
<p>The two saved files have one float32 band, match the pinned mirrored grid, have no NaNs inside its footprint and have in-footprint range [0, 1]. They differ outside the footprint: one uses zeros, one NaNs. The correct portal interpretation is unresolved.</p>
<ul>{entries}</ul><p><a href="../data/archive_audit.json">Read the complete archive audit →</a></p></article>
<article class="card panel"><h2>What the historical experiment does not prove</h2><p>The old holdout used fixed H19-5-derived and D2.8 rasters and catalogue-wide binning/canaries. Fold-local compliance and hidden-label performance have not been established. Earlier positive readiness and uniqueness claims are superseded, and the historical projection is not a score.</p>
<p>No candidate was created and no slot was used in the current audit. For future work, resolve the registry rule and outside-footprint format upstream, then rerun a leakage-safe holdout.</p></article></div></section>
<p><a href="../index.html">← Return to the current evidence dashboard</a></p></main></body></html>'''
    DOCS.mkdir(parents=True, exist_ok=True)
    for filename in PAGES:
        (DOCS / filename).write_text(page, encoding='utf-8')
    # Eliminate stale, approval-bearing public duplicates. Provenance remains in
    # evidence/ and submission/; nothing under those directories is modified.
    for filename in ('build_result.json', 'field_canary.json', 'holdout_results.json',
                     'lst1_run_card.json', 'lst_fit.json'):
        (DOCS / filename).unlink(missing_ok=True)
    downloads = DOCS / 'downloads'
    for row in rows:
        (downloads / row['filename']).unlink(missing_ok=True)
    (downloads / report['zip']['filename']).unlink(missing_ok=True)
    if downloads.exists() and not any(downloads.iterdir()):
        downloads.rmdir()
    (DOCS / '.nojekyll').touch()


if __name__ == '__main__':
    build()
    print('Built research-only LST1 archive notices; no TIFF copied or approved.')
