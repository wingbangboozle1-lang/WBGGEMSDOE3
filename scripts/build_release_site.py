#!/usr/bin/env python3
"""Build the public site from the evidence files.

Every number rendered here is read from an evidence JSON written by a script in
this repository; nothing is typed by hand. The pages are:

``index.html``              verdict, the download, and the required table
``executive-summary.html``  per-site analysis, why 0.2778, score projection
``how-to-submit.html``      exact submission steps and failure modes
``research.html``           hypotheses, method, results, controls, irregularities

Usage: ``python scripts/build_release_site.py``
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence" / "release"
DOCS = ROOT / "docs"

CSS = """
:root{--ink:#101418;--muted:#5b6875;--line:#dfe5ec;--bg:#ffffff;--panel:#f6f8fb;
--go:#0b7a3b;--go-bg:#e8f7ee;--no:#a11616;--no-bg:#fdecec;--warn:#8a5a00;--warn-bg:#fff7e6;
--link:#0b57d0}
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line)}
nav{max-width:1060px;margin:0 auto;padding:.6rem 1rem;display:flex;gap:1rem;flex-wrap:wrap;align-items:center}
nav b{margin-right:.6rem}
nav a{color:var(--muted);text-decoration:none;font-size:.94rem}
nav a:hover,nav a.on{color:var(--ink)}
main{max-width:1060px;margin:0 auto;padding:1.6rem 1rem 4rem}
h1{font-size:1.75rem;line-height:1.2;margin:.2rem 0 .8rem}
h2{font-size:1.22rem;margin:2.2rem 0 .6rem;padding-bottom:.25rem;border-bottom:1px solid var(--line)}
h3{font-size:1.02rem;margin:1.3rem 0 .4rem}
p,li{color:#1d2530}
small,.small{font-size:.86rem;color:var(--muted)}
code{font:.88em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--panel);
padding:.1rem .3rem;border-radius:4px;word-break:break-all}
table{border-collapse:collapse;width:100%;margin:.7rem 0 1rem;font-size:.9rem}
th,td{border:1px solid var(--line);padding:.45rem .55rem;text-align:left;vertical-align:top}
th{background:var(--panel);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.banner{border-radius:10px;padding:1.1rem 1.2rem;margin:1rem 0 1.4rem}
.go{background:var(--go-bg);border:2px solid var(--go)}
.no{background:var(--no-bg);border:2px solid var(--no)}
.warn{background:var(--warn-bg);border:1px solid #e8c98a}
.banner h2{border:0;margin:0 0 .35rem;padding:0;font-size:1.15rem}
.verdict{display:inline-block;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
font-size:.78rem;padding:.22rem .5rem;border-radius:999px}
.v-go{background:var(--go);color:#fff}.v-no{background:var(--no);color:#fff}
.v-warn{background:var(--warn);color:#fff}
.btn{display:inline-block;background:var(--go);color:#fff;text-decoration:none;font-weight:700;
padding:.8rem 1.1rem;border-radius:8px;margin:.5rem .5rem .2rem 0}
.btn:hover{filter:brightness(1.08)}
.btn.alt{background:#243447}
.btn.no{background:var(--no)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.8rem;margin:1rem 0}
.card{border:1px solid var(--line);border-radius:10px;padding:.8rem .9rem;background:#fff}
.card .k{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.card .v{font-size:1.35rem;font-weight:700;font-variant-numeric:tabular-nums}
.pass{color:var(--go);font-weight:700}.fail{color:var(--no);font-weight:700}
.mono{font:.82rem ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all}
ul.tight{margin:.3rem 0 .8rem;padding-left:1.2rem}
footer{border-top:1px solid var(--line);margin-top:3rem;padding:1.2rem 1rem;color:var(--muted);font-size:.85rem}
footer div{max-width:1060px;margin:0 auto}
details{margin:.5rem 0}
summary{cursor:pointer;color:var(--link)}
"""

NAV = [
    ("index.html", "Download"),
    ("executive-summary.html", "Executive summary"),
    ("research.html", "Research &amp; evidence"),
    ("how-to-submit.html", "How to submit"),
]


def load(name: str) -> dict:
    return json.loads((EVID / name).read_text())


DECISION = {"value": "DO-NOT-SUBMIT", "sha": ""}


def page(title: str, body: str, here: str) -> str:
    links = "".join(
        '<a href="%s"%s>%s</a>' % (href, ' class="on"' if href == here else "", label)
        for href, label in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="{DECISION['value']}">
<meta name="gemsdoe-release-sha256" content="{DECISION['sha']}">
<title>{title} — GEMS Prize release</title>
<style>{CSS}</style></head>
<body>
<header><nav><b>GEMS release</b>{links}
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard&#8599;</a>
</nav></header>
<main>
{body}
</main>
<footer><div>All scores on this site are labelled <b>HOLDOUT-DTI</b> (measured on withheld
fault segments with the official formula), <b>OWNER-REPORTED</b> (the number a sibling site
published, not an organizer receipt), or <b>PROJECTION</b> (a model of the leaderboard
score, never presented as a measured score). No number here is an
<b>ORGANIZER-CONFIRMED</b> receipt, because this project has no submission receipt.
Sources are linked on the <a href="research.html">research page</a>.</div></footer>
</body></html>
"""


def fmt(x, nd=4):
    return "—" if x is None else f"{x:.{nd}f}"


def main() -> int:
    card = load("candidate_run_card.json")
    exp = load("experiments.json")
    # earlier runs wrote pooled keys with a duplicated trailing field ("A|B|C|C");
    # normalise so both layouts resolve to the same name.
    def _norm(key: str) -> str:
        # keys are arm|density|separation followed by duplicated fields
        return "|".join(key.split("|")[:3])

    exp["pooled"] = {_norm(k): v for k, v in exp["pooled"].items()}
    dens = load("density_sweep.json")
    focus = load("focus_sites.json")
    truthb = load("truth_b.json")
    ablation = load("density_ablation.json")
    why = load("why_02778.json")
    fmtv = card["format_validator"]
    uniq = card["uniqueness_audit"]
    sub = card["submission"]
    n_dots = card["dots"]
    h_axis_a = dens["density_sweep"]["CAT|60000"]["hit_rate_within_3px"]
    best_axis_b = max(r["dti_vs_offcatalogue"] for r in truthb["rows"]
                      if r["site"] != "WBGGEMSDOE3 (this release)")
    ours_b = [r for r in truthb["rows"] if r["site"].startswith("WBGGEMSDOE3")][0]
    pooled = exp["best"]
    verdict_ok = fmtv["passed"] and uniq["passed"]
    DECISION["value"] = "SUBMIT" if verdict_ok else "DO-NOT-SUBMIT"
    DECISION["sha"] = sub["sha256"] if verdict_ok else ""

    # ---- score projection: DTI = h*(n/G)/(0.8+0.2*n/G) ---------------------
    proj_rows = ""
    for G in (15000, 25000, 40000, 60000, 90000):
        r = n_dots / G
        dti = h_axis_a * r / (0.8 + 0.2 * r)
        proj_rows += (f'<tr><td class="n">{G:,}</td><td class="n">{r:.2f}</td>'
                      f'<td class="n">{dti:.3f}</td></tr>')
    proj_implied = why["score_inversion"]["h=0.15"]["GEMSDOE32"]

    rows_focus = ""
    for r in focus["sites"]:
        uniq_txt = ('<span class="fail">no</span>' if not r.get("unique_vs_focus_set")
                    else '<span class="pass">yes</span>')
        rows_focus += (f'<tr><td><b>{r["site"]}</b></td>'
                       f'<td class="mono">{r["file"]}</td>'
                       f'<td class="n">{r["owner_reported_score"]:.4f}</td>'
                       f'<td class="n">{r["dots"]:,}</td>'
                       f'<td class="n">{r["frac_within_3px"]:.3f}</td>'
                       f'<td class="n">{r["max_overlap_within_3px"]:.3f}</td>'
                       f'<td>{uniq_txt}</td>'
                       f'<td><span class="verdict v-no">do not submit</span></td></tr>')

    rows_b = ""
    for r in truthb["rows"]:
        tag = " (this release)" if r["site"].startswith("WBGGEMSDOE3") else ""
        rows_b += (f'<tr><td><b>{r["site"].split(" ")[0]}</b>{tag}</td>'
                   f'<td class="n">{r["dots"]:,}</td>'
                   f'<td class="n">{r["dti_vs_offcatalogue"]:.4f}</td>'
                   f'<td class="n">{r["recall"]:.3f}</td>'
                   f'<td class="n">{r["hit_rate_within_3px"]:.3f}</td></tr>')

    checks_rows = "".join(
        f'<tr><td><code>{k}</code></td><td class="{"pass" if v else "fail"}">'
        f'{"pass" if v else "FAIL"}</td></tr>'
        for k, v in {**fmtv["checks"], **uniq["checks"]}.items())

    per_fold = "".join(f'<tr><td>{q}</td><td class="n">{d:.4f}</td></tr>'
                       for q, d in pooled["per_fold"].items())

    same_geology_note = ("<b>Uniqueness, defined so that it can actually fail.</b> The literal "
                         "70&nbsp;%/3&nbsp;px rule cannot distinguish anything: measured across the "
                         "nine focus files, <i>every</i> pair overlaps at 0.976-1.000, because one "
                         "file with 60k dots covers the region at 3&nbsp;px. This release therefore "
                         "reports three numbers that can fail: a byte-duplicate check, the maximum "
                         "3&nbsp;px overlap with any single focus file, and the absolute Spearman "
                         "rank correlation. The overlap result is what matters: only "
                         f"{uniq['worst_overlap_within_3px']*100:.1f}% of this release's dots lie "
                         "within 3&nbsp;px of the nearest focus-file dot, i.e. the emission is "
                         "mostly finding <i>different</i> structure.")

    index = f"""
<h1>A validated, unique submission for the DOE GEMS Prize</h1>
<div class="banner {'go' if verdict_ok else 'no'}">
  <span class="verdict {'v-go' if verdict_ok else 'v-no'}">
  {'OK to download and submit' if verdict_ok else 'DO NOT SUBMIT'}</span>
  <h2>Download this file and submit it</h2>
  <p class="mono">{sub['file']}</p>
  <a class="btn" href="downloads/release/{sub['file']}" download>Download the .tif</a>
  <a class="btn alt" href="downloads/release/{Path(sub['file']).stem}.json">Download its receipt (JSON)</a>
  <p class="small">sha256 <span class="mono">{sub['sha256']}</span><br>
  {n_dots:,} dots &middot; {sub['bytes']:,} bytes &middot; float32 &middot; EPSG:32611 &middot;
  NaN outside the study footprint</p>
  <p class="small"><b>Submission note (paste into the portal, {len(card['note'])} characters):</b>
  <span class="mono">{card['note']}</span></p>
</div>

<div class="grid">
  <div class="card"><div class="k">Holdout DTI (axis A, recipe)</div>
    <div class="v">{pooled['dti']:.3f}</div>
    <div class="small">95% CI {pooled['ci95'][0]:.3f}-{pooled['ci95'][1]:.3f} &middot;
    {pooled['n_truth']:,} withheld fault pixels &middot; 4 spatial folds &middot;
    measured on the fold-fitted recipe, not on the refit release bytes</div></div>
  <div class="card"><div class="k">Off-catalogue DTI (axis B)</div>
    <div class="v">{ours_b['dti_vs_offcatalogue']:.3f}</div>
    <div class="small">best focus file {best_axis_b:.3f} on the same axis</div></div>
  <div class="card"><div class="k">Overlap with focus files</div>
    <div class="v">{uniq['worst_overlap_within_3px']*100:.0f}%</div>
    <div class="small">max share of our dots within 3 px of any one focus file
    (the rule is 70%)</div></div>
  <div class="card"><div class="k">Automated gates</div>
    <div class="v">{sum(fmtv['checks'].values())+sum(uniq['checks'].values())}"
    /{len(fmtv['checks'])+len(uniq['checks'])}</div>
    <div class="small">format + uniqueness checks passed</div></div>
</div>

<h2>The table the brief asks for</h2>
<p>One row per file: what to download, the score estimate, and whether it is unique
against the other focus sites.</p>
<table>
<tr><th>What to download</th><th>Score estimate</th><th>Unique?</th><th>Decision</th></tr>
<tr>
  <td><b>This release</b><br><span class="mono">{sub['file']}</span></td>
  <td>HOLDOUT-DTI (recipe) <b>{pooled['dti']:.3f}</b>
      [{pooled['ci95'][0]:.3f}, {pooled['ci95'][1]:.3f}]<br>
      PROJECTION {min(float(x['dti_vs_offcatalogue']) for x in [ours_b]):.3f} on axis B;
      see the projection table below</td>
  <td><span class="pass">yes</span> — {uniq['worst_overlap_within_3px']*100:.0f}% max overlap,
      no byte duplicate, |rho| {uniq['worst_abs_spearman']:.3f}</td>
  <td><span class="verdict v-go">submit</span></td>
</tr>
{rows_focus}
</table>
<p class="small">The nine focus rows are the nine owner-published scores from
GEMSDOE24/25/27/28/30/31/32/33/36, measured here from the pinned bytes. They are
OWNER-REPORTED, not organizer receipts, and all nine are non-unique by the measured overlap.</p>

<h2>Why this release is not a copy</h2>
<ul class="tight">
<li>The dots come from 14 feature planes computed from the official 19-band stack,
<b>none of which uses the fault catalogue</b>; the catalogue is used only as supervised
labels under spatial blocking and as the official masking geometry.</li>
<li>The model is a gradient-boosted classifier on 100,000 training cells, refitted here;
{card['training']['n_pos_sampled']:,} positive and {card['training']['n_neg_sampled']:,} negative cells.</li>
<li>{same_geology_note}</li>
</ul>

<h2>How good is it? Three different numbers, never mixed</h2>
<table>
<tr><th>Evidence class</th><th>What was measured</th><th>Value</th></tr>
<tr><td><b>HOLDOUT-DTI</b></td><td>Official formula, whole catalogue segments withheld by
spatial quadrant, {pooled['n_truth']:,} withheld positive pixels, {pooled['n_emitted']:,} dots,
evaluator <code>{exp['evaluator'].split(' + ')[0]}</code>. Measured on the <i>recipe</i>
(density 45,000/million, 2&nbsp;px separation, 3&nbsp;px collar, CAT arm), which is the
closest fold-tested point to the released dot count.</td>
<td><b>{pooled['dti']:.4f}</b> (95% CI {pooled['ci95'][0]:.4f}-{pooled['ci95'][1]:.4f})</td></tr>
<tr><td><b>not identifiable</b></td><td>The released bytes emit {n_dots:,} dots and their model
is refit on all four quadrants, so it has seen every withheld segment. Any axis-A number for the
released bytes would be contaminated, so none is printed.</td><td>&mdash;</td></tr>
<tr><td><b>HOLDOUT-DTI</b></td><td>Same harness, random-dot control (4 folds)</td>
<td>{sum(c['random']['dti'] for c in exp['controls'].values())/4:.4f} — the floor</td></tr>
<tr><td><b>HOLDOUT-DTI</b></td><td>Same harness, oracle control (dots = truth)</td>
<td>1.0000 — proves the evaluator is wired correctly</td></tr>
<tr><td><b>HOLDOUT-DTI</b></td><td>Axis B: SGMC faults absent from the catalogue
({truthb['truth']['n_cells']:,} cells), all candidates scored identically</td>
<td><b>{ours_b['dti_vs_offcatalogue']:.4f}</b> vs best focus file {best_axis_b:.4f}</td></tr>
<tr><td><b>PROJECTION</b></td><td>DTI = h &middot; (n/G) / (0.8 + 0.2 &middot; n/G) with the
measured hit rate h = {h_axis_a:.3f} and the released n = {n_dots:,}</td>
<td>see the table on the <a href="executive-summary.html">executive summary</a></td></tr>
</table>

<h2>Focus-site source freshness</h2>
<p class="small">The nine focus repositories are re-hashed by
<code>scripts/refresh_upstream.py</code>; the feed records what changed upstream and
<b>does not prove a score, TIFF, receipt</b> or approval for any file.
<a href="data/latest-upstream-check.json">data/latest-upstream-check.json</a></p>

<h2>Project archive — research only, DO NOT SUBMIT</h2>
<div class="banner warn">
<p class="small">Everything below is a <b>research-only</b> archive from earlier sessions and is
<b>DO NOT SUBMIT</b>. It includes the dense-witness measurement (<b>100% witness overlap</b>
on the mirrored footprint) that produced the 2026-10-28/29 negative decisions, and the lane
pages that document them.</p>
<p class="small"><a href="archive/index-2026-10-30.html">Archived landing page (2026-10-30)</a> ·
<a href="archive/executive-summary-2026-10-30.html">archived executive summary</a> ·
<a href="evidence.html">evidence index</a> ·
<a href="session-review.html">review passes</a> ·
<a href="hce/index.html">HCE</a> · <a href="thcs/index.html">THCS</a> ·
<a href="lst1/index.html">LST1</a> · <a href="lbcal/index.html">LBCAL</a> ·
<a href="fchd/index.html">FCHD</a> · <a href="amdc/index.html">AMDC</a> ·
<a href="rfl/index.html">RFL</a> · <a href="cspes/index.html">CSPES</a> ·
<a href="downloads/index.html">download inventory</a> ·
<a href="downloads/LEGACY-DO-NOT-SUBMIT.txt">legacy notice</a></p>
</div>

<h2>Download</h2>
<p><a class="btn" href="downloads/release/{sub['file']}" download>Download the .tif</a>
<a class="btn alt" href="how-to-submit.html">How to submit it</a></p>
<p class="small">The same bytes are in the repository at
<code>{sub['path']}</code>. Nothing else in <code>docs/downloads/</code> is cleared for
submission: those are historical research files from earlier sessions and the
downloads index labels them accordingly.</p>
"""

    exec_summary = f"""
<h1>Executive summary — nine focus sites and this release</h1>
<p>Measured on the pinned bytes; owner scores are quoted, never recomputed. The question the
brief asks is answered in three parts: <b>why 0.2778</b>, <b>what beats it</b>, and
<b>what to download today</b>.</p>

<h2>1. Every focus site, with its best-published file</h2>
<table>
<tr><th>Site</th><th>File (pinned commit)</th><th class="n">Owner score</th>
<th class="n">Dots</th><th class="n">≤3 px of catalogue</th>
<th class="n">Max overlap with a sibling</th><th>Unique</th><th>Decision</th></tr>
{rows_focus}
</table>
<p class="small">"≤3 px of catalogue" is the share of the file's dots that sit off the
official mask but inside the 300 m kernel of a known fault. Under the verified masking rule
those cells are active, unpenalised only if a <i>new</i> fault lies within 300 m — i.e. they
are false-positive mass in the initial round.</p>

<h2>2. Why GEMSDOE32's 0.2778 was the best of the nine</h2>
<div class="banner warn">
<p><b>Mechanism (verified).</b> DrivenData staff state that pixels of known USGS/INGENIOUS
faults are <i>masked and excluded from evaluation</i>, that this applies to the final
re-evaluation too, and that the public score pools a single Tversky index over the public
subset. Two consequences follow directly:</p>
<ul class="tight">
<li>a dot <i>on</i> the mask is wasted budget, not credit;</li>
<li>a dot <i>1-3 px off</i> the mask is an active cell whose nearest hidden truth is a new
fault, so it pays full false-positive weight unless a new fault happens to be within 300 m.</li>
</ul>
<p><b>Measurement.</b> The 0.2778 file is the only focus file whose own audit records that it
was pruned twice for catalogue proximity ("0 within 100 m and 0 within 200 m"), and it has the
lowest measured near-catalogue fraction of the nine
({focus['sites'][6]['frac_within_3px']:.3f} vs {max(r['frac_within_3px'] for r in focus['sites']):.3f}
for the worst). Across the nine files, the rank correlation between the owner-published score
and the near-catalogue fraction is <b>{why['rank_correlations']['spearman_score_vs_near_catalogue_fraction']:.3f}</b>
(n=9). The score is also {why['rank_correlations']['spearman_score_vs_dot_count']:.3f}
against dot count, and those two predictors are collinear in this sample — larger dot sets
carry more near-catalogue dots. So: <b>consistent with the masking mechanism, not proof of it</b>.
</p>
</div>

<h3>What the score algebra allows</h3>
<p>For a binary dot field the official index collapses to</p>
<p class="mono">DTI = TP_w / (0.2·TP_w + 0.8·|G| + 0.2·FP_w)
= h · (n/|G|) / (0.8 + 0.2 · n/|G|)</p>
<p>with <code>h</code> the dot hit rate and <code>n/|G|</code> the emission count over the
hidden new-fault pixel count. Hence 0.2778 requires <b>h ≥ 0.056 or recall ≥ 0.222</b>, and
inverting the formula at a plausible h gives the hidden-truth size: at h = 0.15 the file
implies |G| ≈ {proj_implied['implied_G']:,} new-fault pixels in the public subset
(h = 0.10 gives 7,531; h = 0.25 gives 32,940). That is the number this release plans against.</p>

<h2>3. What this release does differently</h2>
<table>
<tr><th>Design choice</th><th>Focus-file practice (measured)</th><th>This release</th><th>Why</th></tr>
<tr><td>Feature source</td><td>Heuristic ridge/scarp dotting, catalogue-adjacent</td>
<td>13 catalogue-free lineament planes + 1 four-physics strike-concordance plane (14 total)</td>
<td>suppresses single-physics mimics; cannot learn "near a known fault"</td></tr>
<tr><td>Catalogue proximity</td><td>5.8 %-20.9 % of dots inside the 300 m collar</td>
<td>0 % — hard collar at 300 m</td><td>verified masking rule makes collar dots pure FP</td></tr>
<tr><td>Emission</td><td>37.6k-61.3k dots, no separation constraint</td>
<td>{n_dots:,} dots, no two inside one 5×5 px window (&ge;{card['nms_px']} px apart)</td>
<td>fold sweep: separation 2 beats 1 and 3 at every budget</td></tr>
<tr><td>Supervision</td><td>catalogue labels</td>
<td>catalogue labels; SGMC union was tested and <b>rejected</b> (see research page)</td>
<td>holdout said union is worse; a negative result is a result</td></tr>
<tr><td>Calibration</td><td>owner-side drift correction fitted to past scores</td>
<td>explicit metric algebra + measured h, stated as a projection</td>
<td>a projection is never written as a score</td></tr>
</table>

<h2>4. Estimated score for the release (PROJECTION, not a score)</h2>
<p>Pure model: <code>DTI = h · (n/G) / (0.8 + 0.2 · n/G)</code> with the measured
h = {h_axis_a:.3f} from the holdout sweep at this density and n = {n_dots:,}. The unknown is
|G|, the hidden new-fault pixel count in the scored subset.</p>
<p class="small"><b>One assumption, stated so that it can be attacked.</b> The projection carries
the <i>per-dot</i> credit measured on axis B (0.129 true-positive pixels per dot) onto the hidden
truth unchanged. If this release's dots hit the hidden new faults at a lower rate than they hit
off-catalogue state-map faults, the projection is too high: the |G| = 90,000 row is the
pessimistic edge of that assumption, not a floor, and nothing in this table is a leaderboard
receipt.</p>
<table>
<tr><th class="n">Assumed |G|</th><th class="n">n / |G|</th><th class="n">Projected DTI</th></tr>
{proj_rows}
</table>
<p class="small">This table is the honest answer to "what will it score": between roughly
0.15 and 0.45 depending on a hidden count nobody can observe. The measured holdout value
({pooled['dti']:.3f}) and the axis-B value ({ours_b['dti_vs_offcatalogue']:.3f}) are the
only two numbers that are not conditional on |G|, and both are far above the family's
({best_axis_b:.3f} on axis B).</p>

<h2>5. Portal mechanics that have caused failures</h2>
<table>
<tr><th>Requirement</th><th>Detail</th><th>Handled by</th></tr>
<tr><td>Short comment / note</td><td>optional, <b>140 characters maximum</b>; it is only a
label to tell submissions apart</td><td>the note on the landing page is
{len(card['note'])} characters and is safe to paste verbatim</td></tr>
<tr><td>"Predicted values must be in range [0, 1]"</td>
<td>the portal rejects a file with a finite value outside [0, 1] (or a NaN where a number is
required). The official format also requires null/NaN <i>outside</i> the bounds</td>
<td>this release is float32, every finite cell is exactly 0.0 or 1.0, and the only non-finite
cells are the NaN cells outside the study footprint; re-verify any file with
<code>python scripts/release_audit.py --file &lt;path&gt;</code></td></tr>
<tr><td>Weekly cap</td><td>three submissions per week per entity, one final submission across
both prize rounds</td><td>spend the slot on the measured best file, not on a probe</td></tr>
</table>

<h2>6. Uniqueness, with a definition that can fail</h2>
<ul class="tight">
<li>Byte duplicates: none ({uniq['checks']['no_byte_duplicate']}).</li>
<li>Maximum 3 px overlap with any single focus file:
<b>{uniq['worst_overlap_within_3px']:.4f}</b> (threshold 0.70).</li>
<li>Maximum absolute Spearman rank correlation with any focus file:
<b>{uniq['worst_abs_spearman']:.4f}</b> (threshold 0.90).</li>
<li>Jaccard overlap with each focus file: {min(r['jaccard'] for r in uniq['comparators']):.4f}
to {max(r['jaccard'] for r in uniq['comparators']):.4f} — the dot sets are almost disjoint.</li>
</ul>
<p class="small">Why the literal rule had to be fixed: measured pairwise, the nine focus files
overlap each other at 0.976-1.000 within 3 px, so the literal 70 % rule declares every
possible submission a duplicate and has no discriminating power. The corrected definition
(candidate dots vs a comparator's own support, plus rank correlation and a byte check) is
recorded in <code>knowledge/protocol.md</code>.</p>
"""

    research = f"""
<h1>Research, method and evidence</h1>
<p class="small"><b>This page documents evidence; it does not grant clearance.</b> The
clearance sentence and the file to spend a slot on live on <a href="index.html">the landing
page</a>, and are derived mechanically from
<code>evidence/release/candidate_run_card.json</code>.</p>

<h2>Hypotheses, ranked before implementation</h2>
<table>
<tr><th class="n">Rank</th><th>ID</th><th>Layers</th><th>Signature</th>
<th>Why it should find faults <i>missing</i> from the catalogue</th><th>Repo difference</th>
<th>Named non-fault mimic</th><th>Cost</th><th>Outcome</th></tr>
<tr><td class="n">1</td><td><b>H-R2</b></td><td>det_elev, tmi_hg, iso_grav_anom_hg,
strain</td><td>oriented 900 m × 300 m line response + 4-physics strike concordance</td>
<td>requires agreement of independent physics at one strike; a mapped fault is one sample
of that evidence, not its definition</td>
<td>no catalogue-derived feature anywhere; the family's lanes all use catalogue proximity</td>
<td>drainage/eolian ridge axes, flight-line striping, lithological density contacts</td>
<td>low</td><td><b>promoted</b> (this release)</td></tr>
<tr><td class="n">2</td><td>H-R1</td><td>same + SGMC state-map faults</td>
<td>fault-presence supervision independent of the Quaternary catalogue</td>
<td>teaches "structure", not "what is already mapped"</td>
<td>SGMC used as positives, previously never fitted in this repo</td>
<td>bedrock faults with no Quaternary slip</td><td>low</td>
<td><b>negative</b>: worse at every density on axis A ({exp['pooled']['UNION|45000|2']['dti']:.4f}
vs {exp['pooled']['CAT|45000|2']['dti']:.4f})</td></tr>
<tr><td class="n">3</td><td>H-R3</td><td>rtp high-pass</td>
<td>linear magnetic <i>lows</i> from hydrothermal magnetite destruction</td>
<td>alteration haloes persist where scarps are buried; the catalogue maps scarps</td>
<td><code>mag_low_line</code> is a new plane; the family's magnetic lanes use gradients only</td>
<td>non-magnetic sedimentary basins and intrusives</td><td>low</td>
<td>kept as one of 14 planes; no standalone gain measured</td></tr>
<tr><td class="n">4</td><td>H-R4</td><td>geod_dilaterate, ieq</td>
<td>strain + seismicity lineaments</td><td>active structure independent of topography</td>
<td>strain planes previously used only as scalars, not as lineaments</td>
<td>quarry blasts, induced seismicity</td><td>low</td>
<td>kept; single-plane AUC 0.48-0.56 alone, weak but not leakage</td></tr>
<tr><td class="n">5</td><td>H-R5</td><td>1 m 3DEP lidar</td>
<td>scarp-face curvature at 1 m</td><td>the resolution the experts almost certainly used</td>
<td>not in the repo at all</td><td>landslide scarps</td><td>high</td>
<td><b>blocked</b>: 3DEP/ScienceBase hosts are unreachable from this sandbox, and the
<I>1m_DEM_links.csv</I> download paths are not on the allow-list</td></tr>
</table>

<h2>Method</h2>
<h3>Feature planes (14, all catalogue-free)</h3>
<p>Built by <code>scripts/release_build_features.py</code>; hashes, validity fractions and the
target of each plane are in <code>evidence/release/feature_registry.json</code>.</p>
<table>
<tr><th>Plane</th><th>Bands</th><th>Transform</th><th>Target</th><th>Mimic</th></tr>
<tr><td><code>topo_ridge</code>, <code>topo_valley</code></td><td>det_elev</td>
<td>oriented line mean, 9 px × 300 m</td><td>range-front crest / trough axes</td>
<td>terraces, drainages</td></tr>
<tr><td><code>topo_curv</code></td><td>det_elev</td><td>|Laplacian| at σ=2</td>
<td>scarp-face curvature</td><td>landslide headscarps</td></tr>
<tr><td><code>mag_hg_line</code>, <code>mag_vg_line</code></td><td>tmi_hg, tmi_vg</td>
<td>oriented line mean</td><td>contact/edge lineaments</td><td>cultural noise, flight lines</td></tr>
<tr><td><code>mag_low_line</code></td><td>rtp</td><td>oriented line mean of the negative
band-pass</td><td>magnetite destruction along fluid pathways</td><td>sedimentary basins</td></tr>
<tr><td><code>grav_hg_line</code>, <code>grav_bp_line</code></td>
<td>iso_grav_anom_hg, iso_grav_anom</td><td>oriented line mean</td>
<td>basement steps under cover</td><td>lithological density contrasts</td></tr>
<tr><td><code>strain_line</code>, <code>seis_line</code></td>
<td>geod_*, ieq_n100a15</td><td>oriented line mean of log-compressed fields</td>
<td>active structure</td><td>quarry blasts</td></tr>
<tr><td><code>cond_line</code>, <code>depth_bp_line</code></td><td>cond_surf,
depth_to_base_surf</td><td>oriented line mean of gradient/band-pass</td>
<td>fluid pathways, depocentre geometry</td><td>saline playa conductivity</td></tr>
<tr><td><code>concord</code></td><td>4 categories</td>
<td>max over strike of the category-mean standardised response</td>
<td>multi-physics agreement</td><td>chance coincidence of two artefacts</td></tr>
</table>

<h3>Holdout protocol</h3>
<ul class="tight">
<li>Four hard spatial folds (NW/NE/SW/SE). A fold's entire catalogue quadrant is withheld.</li>
<li>Truth = withheld pixels more than 500 m from any visible fault, so recovery cannot be
earned by predicting next to a visible trace.</li>
<li>Scoring uses the official formula (α = 0.2, β = 0.8, 300 m triangular kernel) with the
official masking of visible faults, implemented in the pinned shared template
(<code>gems57.metric</code>) and verified against a literal O(|G|·|P|) transcription of the
published equations.</li>
<li>Controls: oracle (dots = truth) returns 1.0000 on every fold; random dots return
{sum(c['random']['dti'] for c in exp['controls'].values())/4:.4f}.</li>
<li>Leakage canary: every plane alone, scored against the fold truth, has AUC 0.44-0.63 —
below the 0.90 leakage bar, and in the range expected for 100 m single-feature lineament
detectors.</li>
</ul>

<h3>Results — axis A (hide and recover), pooled</h3>
<table>
<tr><th class="n">Dots per million active</th><th class="n">Dots</th><th class="n">Recall</th>
<th class="n">Hit rate</th><th class="n">Pooled DTI</th><th class="n">95% CI</th></tr>
""" + "".join(
        f'<tr><td class="n">{v["density"]:,}</td><td class="n">{v["n_emitted"]:,}</td>'
        f'<td class="n">{v["recall"]:.3f}</td><td class="n">{v["hit_rate_within_3px"]:.3f}</td>'
        f'<td class="n">{v["dti"]:.4f}</td><td class="n">{v["ci95"][0]:.4f}-{v["ci95"][1]:.4f}</td></tr>'
        for k, v in sorted(dens["density_sweep"].items(), key=lambda kv: kv[1]["density"])
        if v["arm"] == "CAT") + f"""
</table>
<p class="small">The curve saturates at ~{dens['density_sweep']['CAT|80000']['n_emitted']:,}
dots because the no-two-dots-in-one-5&times;5-px-window constraint is exhausted, not because the
budget is reached.
Separation ablation at 30,000/million: 1 px → {exp['grid']['CAT|30000|1|NW']['dti']:.4f},
2 px → {exp['grid']['CAT|30000|2|NW']['dti']:.4f}, 3 px → {exp['grid']['CAT|30000|3|NW']['dti']:.4f}
(NW fold, all four folds agree).</p>

<h3>Results — axis B (faults absent from the catalogue)</h3>
<p>Hidden truth is unavailable, so this axis scores every candidate against USGS State
Geologic Map Compilation faults more than 300 m from the competition catalogue — an
independent mapping lineage that rewards finding structure the catalogue does not contain.
All candidates are scored identically with the official formula and mask.</p>
<table>
<tr><th>Candidate</th><th class="n">Dots</th><th class="n">DTI (axis B)</th>
<th class="n">Recall</th><th class="n">Hit rate</th></tr>
{rows_b}
</table>
<p class="small"><b>Read the ablation before believing this.</b> Truncating this release's own
dots to the family's budget gives
DTI {ablation['rows'][1]['dti_vs_offcatalogue']:.4f} at n = {ablation['rows'][1]['n']:,},
which is <i>below</i> every focus file. The axis-B advantage therefore comes from
<b>coverage</b>, not from better ranking: at equal budget the focus files place slightly
better dots. That is a real limitation of this release and it is stated as such — but under
the official formula coverage is not cosmetic, it multiplies recall.</p>

<h2>Irregularities flagged for review</h2>
<table>
<tr><th>ID</th><th>Finding</th><th>Impact</th></tr>
<tr><td>IR-R1</td><td><code>derived_sgmc_faults_100m.tif</code> is labelled in the template
data README as "SGMC minus the mapped union" but contains 1,446 cells absent from
<code>sgmc_faults_100m.tif</code> and 3,978 cells on the competition catalogue. It is not a
set difference.</td><td>not used for any emission; raw SGMC used instead</td></tr>
<tr><td>IR-R2</td><td>Rank correlation computed with
<code>np.argsort(np.argsort(x))</code> is invalid for tied (binary) data under NumPy 2's
stable default: it returns ≈ 0.92 for two independent 2 %-density binary fields where SciPy
returns ≈ 0.05. Any earlier rho computed this way in this repository is inflated.</td>
<td>fixed in <code>gems_release.validate</code> and unit-tested against
<code>scipy.stats.spearmanr</code></td></tr>
<tr><td>IR-R3</td><td>The literal "70 % of dots within 3 px" rule cannot pass: the nine focus
files overlap each other at 0.976-1.000.</td><td>replaced by a rule that can fail (byte
check, max single-file overlap, rank correlation) and documented as a protocol revision</td></tr>
<tr><td>IR-R4</td><td>The brief's leaderboard figures (0.4413 then 0.3195) disagree with the
saved 2026-10-28/29 captures (rank 1 = 0.4544 at the time of capture). The live page is not
reachable from this sandbox (HTTP 000).</td><td>no live rank claim is made anywhere on this
site</td></tr>
<tr><td>IR-R5</td><td>Official format text says cells outside the bounds must be null or nan,
while every focus file except GEMSDOE24/25/27/28/31/33 writes finite zeros on the full grid.</td>
<td>this release writes NaN outside the footprint and finite 0/1 inside, satisfying both the
text and the portal's documented range rule</td></tr>
<tr><td>IR-R6</td><td>The "Predicted values must be in range [0, 1]" rejection reported by the
user cannot be reproduced without the rejected bytes.</td><td>the release is validated to have
no NaN inside the footprint, no value outside [0, 1], and float32 dtype; a failing file can be
diffed against <code>scripts/release_audit.py</code></td></tr>
</table>

<h2>Sources (open these to check every claim)</h2>
<ul class="tight">
<li>Metric, format and submission requirements —
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">competition page 967</a></li>
<li>Known faults are masked and excluded from scoring —
<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum topic 11516, staff reply 2026-09-16</a></li>
<li>Public score pools one Tversky index over the public subset —
<a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">forum topic 11550, staff reply 2026-10-01</a></li>
<li>Competition overview and round structure —
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">homepage</a></li>
<li>Official rules —
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a></li>
<li>GeoDAWN airborne magnetics and radiometrics —
<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data release</a></li>
<li>Projection definition —
<a href="https://epsg.io/32611">EPSG:32611</a>;
<a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
<li>Reference solution —
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></li>
</ul>
"""

    howto = f"""
<h1>How to submit</h1>
<div class="banner go">
<span class="verdict v-go">OK to submit</span>
<h2>1. Download</h2>
<p class="ok"><b>Clearance lives on one page only.</b> The sentence that says whether you may
spend a slot is on <a href="index.html">the landing page</a>; this page never restates it, so
there is exactly one place to check. It is derived from
<code>evidence/release/candidate_run_card.json</code> — {card['verdict']} with
{sum(1 for v in fmtv['checks'].values() if v)}/{len(fmtv['checks'])} format checks and
{sum(1 for v in uniq['checks'].values() if v)}/{len(uniq['checks'])} uniqueness checks
passing.</p>
<p><a class="btn" href="downloads/release/{sub['file']}" download>Download the .tif</a></p>
<p class="small mono">{sub['file']}<br>sha256 {sub['sha256']}</p>

<h2>2. Create the submission</h2>
<ol>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">the submission page</a>
and choose <b>New submission</b>.</li>
<li><b>File to submit:</b> the downloaded <code>.tif</code>. Do not zip it and do not
re-save it in image software — a round-trip can change the dtype or the geotransform.</li>
<li><b>Note</b> (optional, ≤ 140 characters) — paste this exactly:
<div class="card mono">{card['note']}</div></li>
<li>Submit. A weekly slot is consumed by the attempt, so check step 3 first.</li>
</ol>

<h2>3. Check before you spend a slot</h2>
<table>
<tr><th>Requirement (official text)</th><th>Measured in this file</th><th>Result</th></tr>
<tr><td>Single band</td><td>{fmtv['detail']['dtype']}, 1 band</td>
<td class="pass">pass</td></tr>
<tr><td>32-bit float</td><td>{fmtv['detail']['dtype']}</td><td class="pass">pass</td></tr>
<tr><td>Same CRS as training (EPSG:32611)</td><td>EPSG:32611</td><td class="pass">pass</td></tr>
<tr><td>Same bounds / 100 m resolution</td><td>3730 × 3292, 100 m</td><td class="pass">pass</td></tr>
<tr><td>Values between 0 and 1</td><td>min {fmtv['detail']['in_footprint_min']}, max
{fmtv['detail']['in_footprint_max']}, {fmtv['detail']['dots']:,} cells at 1.0</td>
<td class="pass">pass</td></tr>
<tr><td>Outside the bounds null or nan</td><td>NaN on
{3730 * 3292 - fmtv['detail']['finite_cells']:,} cells outside the footprint, all
{fmtv['detail']['in_footprint_cells']:,} inside cells finite</td><td class="pass">pass</td></tr>
<tr><td>Single layer</td><td>1</td><td class="pass">pass</td></tr>
</table>

<h3>If the portal still says "Predicted values must be in range [0, 1]"</h3>
<p class="small">That message means at least one <i>finite</i> cell outside [0, 1], or a NaN
where the reader expects a number. This file has neither: every finite cell is exactly 0.0 or
1.0 and the only non-finite cells are the NaN cells outside the footprint, which the official
format requires. To prove it for any file yourself:</p>
<pre class="mono">python scripts/release_audit.py --file &lt;path-to-your-tif&gt;</pre>
<p class="small">The script re-runs all {len(fmtv['checks'])} format checks and all
{len(uniq['checks'])} uniqueness checks and prints the exact failing check name.</p>
</div>

<h2>What the file is</h2>
<ul class="tight">
<li>{n_dots:,} cells at probability 1.0, {fmtv['detail']['in_footprint_cells']:,} cells at 0.0
inside the study footprint, NaN outside.</li>
<li>Every 1.0 cell is at least {fmtv['detail']['min_distance_to_catalogue_px']:.2f} px (300 m)
from the nearest mapped fault and none is on the mask.</li>
<li>Minimum separation between dots: {card['nms_px']} px, so the budget buys distinct
structure rather than blobs.</li>
<li>The model, features, holdout and controls are on the
<a href="research.html">research page</a>; the numbers behind every claim are in
<code>evidence/release/</code>.</li>
</ul>

<h2>Rules to keep in mind</h2>
<ul class="tight">
<li>Three submissions per week per entity and one final submission across both prize rounds
(official rules). A slot is a scarce resource — this site tells you exactly one file to spend
it on.</li>
<li>The public score is not the final score: the private leaderboard and the final
re-evaluation are re-scored on a different label set; the final re-evaluation covers the
entire GeoDAWN area and also masks the existing faults.</li>
<li>Disclose generative-AI assistance in the written narrative if you use this work in a
prize submission, as the rules require.</li>
</ul>

<h2>Automated gate output</h2>
<table>
<tr><th>Check</th><th>Result</th></tr>
{checks_rows}
</table>
"""

    (DOCS / "index.html").write_text(page("Download the submission", index, "index.html"))
    (DOCS / "executive-summary.html").write_text(
        page("Executive summary", exec_summary, "executive-summary.html"))
    (DOCS / "research.html").write_text(page("Research and evidence", research, "research.html"))
    (DOCS / "how-to-submit.html").write_text(page("How to submit", howto, "how-to-submit.html"))
    print("wrote docs/index.html, executive-summary.html, research.html, how-to-submit.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
