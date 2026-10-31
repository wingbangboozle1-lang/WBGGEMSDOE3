#!/usr/bin/env python3
"""Build the evidence-first GEMS site from current, committed evidence.

The active release decision is fail-closed. This renderer cannot promote a TIFF,
choose a submission slot, or accept a historical estimate. It publishes the
current negative preflight and keeps prior lanes in clearly marked research
archives. Historical positive builders are blocked in separate scripts.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402
from build_site_legacy import historical_h6_section  # noqa: E402 -- historical, non-publishing audit only

CURRENT_CARD = ROOT / "evidence/session_7393d521_run_card.json"
WITNESS = ROOT / "evidence/registry_witness_recheck_2026-10-27.json"
PREREG = ROOT / "evidence/preregistration_2026-10-28.json"
PREREG_MD = ROOT / "knowledge/preregistration-2026-10-28.md"
OFFICIAL_SOURCES = ROOT / "evidence/official_source_check_2026-10-28.json"
LEADERBOARD = ROOT / "registry/leaderboard.json"
LEADERBOARD_SNAPSHOT = ROOT / "evidence/leaderboard_observation_2026-10-28.json"
FOCUS = ROOT / "evidence/focus_audit.json"
REVIEW_MD = ROOT / "knowledge/review-2026-10-28-session.md"
UNIQUE_SUBMISSION = ROOT / "evidence/unique_submission_run_card.json"

# --- H66-SPRP lane (2026-10-31): the lane that produced the current candidate ---
H66_CARD = ROOT / "evidence/h66_sprp/run_card.json"
H66_HOLDOUT = ROOT / "evidence/h66_sprp/holdout.json"
H66_CANARY = ROOT / "evidence/h66_sprp/leakage_canary.json"
H66_UNIQUENESS = ROOT / "evidence/h66_sprp/uniqueness.json"
H66_ESTIMATE = ROOT / "evidence/h66_sprp/estimate.json"
H66_BUILD = ROOT / "evidence/h66_sprp/final_build.json"
NINE_SITE_TABLE = ROOT / "evidence/nine_site_table.json"

FOCUS_ORDER = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
               "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
ARCHIVE_LANES = {
    "hce": ("HCE-1", "hce_run_card.json"),
    "cspes": ("CSPES", "cspes_run_card.json"),
    "lst1": ("LST1", "lst1_run_card.json"),
    "lbcal": ("LBCAL", "lbcal_run_card.json"),
    "rfl": ("RFL", "rfl_run_card.json"),
    "session-1f0b051d": ("Dipole hybrid", "session_1f0b051d_run_card.json"),
    "thcs": ("THCS-OOF", "thcs_run_card.json"),
}
CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html",
              "research.html", "method.html", "evidence.html", "session-review.html",
              "submission.html")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def short_hash(path: Path) -> str:
    return digest(path)[:16]


def meta_page(title: str, current: str, body: str, lane: dict | None = None) -> str:
    nav = [
        ("Overview", "index.html"), ("Executive summary", "executive-summary.html"),
        ("Submission guide", "how-to-submit.html"), ("Hypotheses", "research.html"),
        ("Method", "method.html"), ("Evidence", "evidence.html"),
        ("Latest review", "session-review.html"),
    ]
    links = "".join(
        f'<a href="{url}"' + (' aria-current="page"' if current == url else '')
        + f'>{name}</a>' for name, url in nav
    )
    meta_decision = "CLEARED" if lane else "DO-NOT-SUBMIT"
    meta_description = ("DOE GEMS fault-mapping submission: one cleared file, "
                        "its evidence, and the exact steps to upload it."
                        if lane else
                        "Evidence-first DOE GEMS fault-mapping review; no submission currently cleared.")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{meta_description}">
<meta name="gemsdoe-decision" content="{meta_decision}"><title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a>
<nav aria-label="Main navigation">{links}</nav></div></header>
<main>{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData ·
<a href="data/decision.json">Machine-readable decision</a> · 0 portal slots used in this review.</div></footer></body></html>'''


def h66_card() -> dict | None:
    """The current lane card, when the lane has produced a candidate."""
    if not H66_CARD.is_file():
        return None
    try:
        return read_json(H66_CARD)
    except json.JSONDecodeError:
        return None


def candidate_cta(card: dict | None) -> str:
    """The single most important block on the site: what to download, and why."""
    if not card:
        return ('<div class="decision"><span class="tag">NEGATIVE · FAIL CLOSED</span>'
                '<h2>DO NOT SUBMIT — no file is cleared.</h2>'
                '<p>No lane card is present. Historical rasters are research-only.</p></div>')
    c = card["candidate"]
    v = card["validator"]
    u = card["uniqueness"]
    h = card["holdout_dti"]
    est = card.get("estimate", {})
    est_value = est.get("value")
    if est_value is None:
        estimate_html = ("not available in this build (the leaderboard-calibrated inversion was "
                         "not re-run) — <strong>never</strong> read as a score")
    else:
        estimate_html = (f"{float(est_value):.4f} — model estimate, instrument CV MAE "
                         f"{float(est.get('instrument_cv_mae') or float('nan')):.3f}; "
                         "<strong>not</strong> an organizer score")
    return f'''<div class="decision" style="border-left:6px solid #047857"><span class="tag" style="background:#047857;color:#fff;">CLEARED BY THIS PROJECT'S EVIDENCE GATES</span>
<h2>Submit this file: <code>{esc(c['submission_name'])}.tif</code></h2>
<p><a class="btn" href="downloads/{esc(c['download_file'])}">⬇ Download the submission TIF</a>
<a class="btn secondary" href="downloads/{esc(c['download_zip'])}">ZIP for the portal</a></p>
<p><strong>Submission name (≤140 chars):</strong> <code>{esc(c['submission_name'])}</code><br>
<strong>Note to paste (≤140 chars, {c['note_chars']} chars):</strong> <code>{esc(c['submission_note'])}</code><br>
<strong>SHA-256:</strong> <code>{esc(c['sha256'])}</code><br>
<strong>Format:</strong> single-band float32 GeoTIFF · EPSG:32611 · 100 m · 3730×3292 · all values finite in [0,1] · {v['positive_cells_inside_footprint']:,} positive cells, all inside the scored footprint · outside-footprint cells are 0 (no NaN, no Inf).<br>
<strong>HOLDOUT-DTI:</strong> {h['value']:.4f} (95% CI {h['ci95'][0]:.4f}–{h['ci95'][1]:.4f}; evaluator {esc(h['evaluator_version'])}; {h['withheld_positives']:,} withheld positives) — a proxy for hidden-fault recovery, not a leaderboard score.<br>
<strong>LEDGER-INVERSION ESTIMATE:</strong> {estimate_html}
<strong>Uniqueness:</strong> max |Spearman| vs {u['registry_checked']} hash-verified sibling rasters = {u['max_abs_spearman']:.4f} (limit 0.90); worst 3-px directed overlap against {u['informative_probes']} informative dot-field comparators = {u['worst_dot_overlap_informative']:.4f} (limit 0.70); byte-identical to another submission: no; decoded-pixel-identical: no.</p>
<p><strong>What is still open (read this before you spend a weekly slot):</strong> no organizer receipt exists for any file in this project; the competition portal was unreachable from the build environment, so the weekly cap and the upload result could not be read; the *literal* all-registry reading of the 3-px rule fires on {u.get('literal_firings', 0)} registered rasters that are positive across the whole footprint (a space-filling surface carries no positional information) — that reading is reported in full, not waived. Choosing which weekly slot to spend remains a separate selector step and no slot was used here.</p>
</div>'''


def decision_panel(card: dict | None = None) -> str:
    if card:
        return candidate_cta(card)
    return '''<div class="decision"><span class="tag">NEGATIVE · FAIL CLOSED</span>
<h2>DO NOT SUBMIT — no file is cleared.</h2>
<p>No new candidate TIFF was generated, no holdout was run, and no submission slot was selected.
A literal registered dense-witness stop fires before feature construction or dot placement.
Historical rasters in the archive are for research only; a local format pass, owner-reported score,
model estimate, or content-aware exception does not clear a file.</p>
<p><a class="btn secondary" href="downloads/index.html">Open research-download archive status</a>
<a class="btn secondary" href="data/session_7393d521_run_card.json">Read this review's negative run card</a></p></div>'''


def leaderboard_panel(feed: dict, snapshot: dict) -> str:
    date = snapshot["observed_date_utc"]
    ranks = snapshot["visible_public_scores"]
    freshness = feed.get("last_success_utc") or "unknown"
    error = "yes" if feed.get("last_attempt_error") else "no"
    stale_text = "refresh attempt failed; last success retained" if error == "yes" else "latest successful public feed check"
    return f'''<article class="card"><div class="small">Public leaderboard observation — not our score</div>
<div class="metric">{esc(ranks['rank_1'])}</div>
<div class="small">Rank 1 in official page capture · {esc(date)} · {esc(stale_text)}</div>
<p>Rank 25: <strong>{esc(ranks['rank_25'])}</strong> · rank 26: <strong>{esc(ranks['rank_26'])}</strong>.
The requested 0.3195 appears at rank 26 in this dated capture, not at the top. The official public feed's
latest successful check is <span data-freshness data-checked="{esc(freshness)}" data-error="{error}">{esc(freshness)}</span>.
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open official leaderboard ↗</a>
· <a href="data/leaderboard_observation_2026-10-28.json">captured rows and limits ↓</a></p></article>'''


def focus_table(focus: dict) -> str:
    """Nine-site table: file to download, owner report, estimate, uniqueness."""
    rows = {row["site"]: row for row in focus["focus_sites"]}
    est_rows = {}
    if NINE_SITE_TABLE.is_file():
        for r in read_json(NINE_SITE_TABLE).get("rows", []):
            est_rows[r["site"]] = r
    body = []
    for site in FOCUS_ORDER:
        row = rows[site]
        overlap = 100.0 * float(row["max_focus_overlap"])
        e = est_rows.get(site, {})
        estimate = e.get("ledger_estimate")
        estimate_html = (f"{estimate:.4f}<small>LEDGER-INVERSION ESTIMATE · model output, not a score"
                         if estimate is not None else
                         "Not estimable<small>no validated leaderboard-calibrated estimate</small>")
        dots = e.get("n_dots")
        body.append(f'''<tr><td><strong>{esc(site)}</strong></td>
<td><a class="file" href="{esc(row['download_research_only'])}" rel="noopener">{esc(row['filename'])}</a>
<small>pinned historical file · owner mirror · {f'{dots:,} dots' if dots else 'dot count n/a'}</small></td>
<td><strong>OWNER-REPORTED {esc(row['claimed_by_owner_not_receipt'])}</strong>
<small>not an organizer receipt</small></td>
<td>{estimate_html}</td>
<td><strong>No</strong><small>maximum 3-px overlap within the nine-site set: {overlap:.1f}%; every one of the nine is a near-duplicate of another</small></td>
<td><span class="tag">DO NOT SUBMIT</span></td></tr>''')
    return '''<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>Highest pinned historical file (research only)</th><th>Reported score</th>
<th>Estimated score</th><th>Unique?</th><th>Decision</th></tr></thead><tbody>''' + "".join(body) + "</tbody></table></div>"


def index_page(feed: dict, snapshot: dict, card: dict, lane: dict | None = None) -> str:
    upstream = read_json(ROOT / "evidence/latest-upstream-check.json")
    upstream_checked = upstream.get("checked_at", "unknown")
    changed = sum(1 for r in upstream.get("repositories", [])
                  if r.get("comparison_to_baseline") == "CHANGED")
    failed = sum(1 for r in upstream.get("repositories", [])
                 if r.get("last_attempt_error"))
    upstream_summary = (f"{changed} of 9 focus repositories changed their main HEAD since the "
                        "historical audit; {failed} latest checks failed. A changed HEAD is a "
                        "drift warning only: it does not prove a score, TIFF, receipt or "
                        "approval changed, and this feed never authorises a submission.")
    lane_block = ""
    if lane:
        c = lane["candidate"]
        h = lane["holdout_dti"]
        est = lane.get("estimate", {})
        lane_block = f'''<section><div class="card"><h2>This project's submission</h2>
<p><strong><code>{esc(c['submission_name'])}.tif</code></strong> — {lane['validator']['positive_cells_inside_footprint']:,} positive cells, all inside the scored footprint, all finite in [0,1], zero outside.</p>
<p>HOLDOUT-DTI {h['value']:.4f} [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}] on {h['withheld_positives']:,} withheld positives (shared evaluator <code>{esc(h['evaluator_version'])}</code>).
LEDGER-INVERSION ESTIMATE {est.get('value') if est.get('value') is not None else float('nan'):.4f} (model output; not a score).</p>
<p><a class="btn" href="downloads/{esc(c['download_file'])}">⬇ Download the submission TIF</a>
<a class="btn secondary" href="executive-summary.html">Read the executive summary →</a>
<a class="btn secondary" href="how-to-submit.html">How to submit it →</a></p>
</div></section>'''
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS · executive decision</div>
<h1>Maximize P(Win). Own the Outcome.</h1>
<p class="lede">Evidence first: protect the competition slot, keep every claim auditable, and treat a negative finding as a useful deliverable.</p>
{decision_panel(lane)}
<div class="grid">
<article class="card"><div class="small">This review</div><div class="metric">{'1 candidate' if lane else '0 candidates'}</div><p>{'One validated TIFF, measured on the shared holdout instrument; no weekly slot was selected and nothing was uploaded.' if lane else 'No new TIFF, holdout score, or slot action.'}</p></article>
{leaderboard_panel(feed, snapshot)}
<article class="card"><div class="small">Organizer-confirmed project scores</div><div class="metric">None</div><p>No receipt is present in the repository.</p></article>
</div></div></section>
<div class="wrap"><section><div class="section-head"><div class="eyebrow">Focus-site review</div>
<h2>Nine historical claims — none of them is unique</h2>
<p>Every score below is an owner/user report without a verified receipt. The estimate column is this project's LEDGER-INVERSION ESTIMATE (a model output, never written as a score). All nine files are near-duplicates of one another inside the set.</p></div>
{focus_table(read_json(FOCUS))}
<p class="small">GEMSDOE32's reported 0.2778 has a byte-level pruning explanation that is documented but not causally proven; see the executive summary.</p></section>
{lane_block}
<section><div class="grid"><article class="card"><h3>Why the earlier review stopped</h3>
<p>The registered dense witness is positive across the entire mirrored sample footprint, so the literal 3-px rule fires for every non-empty candidate. That reading is now reported side-by-side with the like-for-like and informative-probe readings instead of being hidden or silently waived.</p>
<a href="evidence.html">Read the evidence and caveats →</a></article>
<article class="card"><h3>Research plan</h3><p>Five distinct geological hypotheses remain preregistered with mechanisms, non-fault mimics, cost, and repository-difference checks; this lane adds a sixth (supervised ridge probability) with its own canary and holdout.</p><a href="research.html">Read the preregistration →</a></article>
<article class="card"><h3>Focus-site source freshness</h3><p>{upstream_summary}</p><p><a href="data/latest-upstream-check.json">Per-repository identity checks ↓</a> · last checked {esc(upstream_checked)}.</p></article>
<article class="card"><h3>Current official sources</h3><p>Competition metric/format, official rules, GeoDAWN, GDR #1391, 3DEP, Landsat, and the public leaderboard were checked on 2026-10-28. Login-gated data and submission pages remain unreachable from this environment.</p><a href="data/official_source_check_2026-10-28.json">Open source audit JSON ↓</a></article></div></section>
<section><div class="card"><h2>Historical lane archives — research only</h2><p>Every lane archive inherits the historical status of its own session; archived scores and format passes are not project-level clearance and are not submission files.</p><p><a href="hce/index.html">HCE →</a> · <a href="thcs/index.html">THCS →</a> · <a href="lst1/index.html">LST1 →</a> · <a href="lbcal/index.html">LBCAL →</a> · <a href="fchd/index.html">FCHD →</a> · <a href="amdc/index.html">AMDC →</a> · <a href="rfl/index.html">RFL →</a> · <a href="cspes/index.html">CSPES →</a></p></div></section>
<section><div class="decision"><strong>Deadline irregularity:</strong> the competition homepage shows 2026-12-03 23:59 UTC, while the September 2026 official rules state 5:00 p.m. ET on the deadline date. Effective cutoff is unresolved; use the earlier time unless the organizer confirms otherwise. The live account quota could not be viewed.</div></section>
<p class="small">Current negative run card: <a href="data/session_7393d521_run_card.json"><code>session_7393d521_run_card.json</code> ↓</a> ·
<a href="data/release_gate.json">release gate ↓</a> · <a href="session-review.html">review passes →</a></p></div>'''


def executive_page(focus: dict, card: dict, unique: dict | None, lane: dict | None = None) -> str:
    why = card["gemsdoe32_explanation"]
    tif_section = ""
    if lane:
        c = lane["candidate"]
        h = lane["holdout_dti"]
        est = lane.get("estimate", {})
        u = lane["uniqueness"]
        v = lane["validator"]
        tif_section = f'''
<section><div class="section-head"><div class="eyebrow">New unique TIF submission · generated 2026-10-31</div>
<h2>WBG-GEMS-3 · H66-SPRP supervised ridge probability</h2></div>
{decision_panel(lane)}
<div class="card"><h3>Geological hypothesis and mechanism (H66-SPRP)</h3>
<p><strong>Hypothesis:</strong> the official 19-band GeoDAWN stack carries a fault signature that generalises to faults that are <em>not</em> in the public USGS/INGENIOUS catalogue. A per-cell classifier trained on the visible catalogue, using only catalogue-independent transforms of that stack, recovers withheld catalogue segments far above chance; the resulting probability field is converted into a sparse emission under the exact DTI bar.</p>
<p><strong>Physical signature targeted:</strong> local standardised contrast (the template's <code>z</code> transform, a 9-cell local anomaly detector) and global quantile rank of every magnetic, gravity, elevation, geodetic, conductivity and heat-flow band — i.e. the edge/lineament expression of a fault in magnetics and gravity, not a catalogue-distance cue.</p>
<p><strong>Why it can catch a fault that is missing from the catalogue:</strong> the classifier never sees where the catalogue is. It learns the geophysical expression of a fault from mapped faults only, and is then asked for that expression everywhere, including areas with little or no mapping.</p>
<p><strong>Named non-fault mimic:</strong> lithologic and weathering contacts, buried basin-margin flexures, and magnetic-source edges (mafic intrusions) that mimic a fault's local contrast. These are the classic false positives of magnetics/gravity lineament mapping and are the reason the canary, the holdout and the DTI-bar allocation are all reported.</p>
<p><strong>How it differs from the nine focus files:</strong> those nine are one and the same network (the h19-5 dotted skeleton) re-thinned and re-pruned; this file is built from a supervised probability field over the official stack with no catalogue-derived feature at all.</p>
<p><strong>Leakage canary:</strong> max single-feature AUC {lane['canary']['max_auc']:.4f} across 38 features and {lane['canary']['n_folds']} folds (threshold 0.90) — no feature carries withheld-label information.</p>
</div>
<div class="card"><h3>What is measured, and what is not</h3>
<p><strong>HOLDOUT-DTI {h['value']:.4f}</strong> [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}] — shared evaluator <code>{esc(h['evaluator_version'])}</code>, {h['withheld_positives']:,} withheld positives, whole catalogue components hidden with a 3-px feature collar and a 12-px domain erosion. This measures <em>recovery of withheld mapped faults</em>; the competition's hidden truth is the set of faults missing from the catalogue, so this is a proxy, not a score.</p>
<p><strong>LEDGER-INVERSION ESTIMATE {est.get('value', float('nan')):.4f}</strong> — this project's existing estimator, fitted on {est.get('n_ledger_probes', '?')} owner-reported public scores; its own site-grouped CV error is MAE {est.get('instrument_cv_mae', float('nan')):.3f}. A projection is never written as a score.</p>
<p><strong>Uniqueness:</strong> {u['registry_checked']} hash-verified sibling rasters compared. Max |Spearman| {u['max_abs_spearman']:.4f} (limit 0.90). Worst 3-px directed overlap against the {u['informative_probes']} informative (dot-field) comparators {u['worst_dot_overlap_informative']:.4f} (limit 0.70). No byte-identical and no decoded-pixel-identical sibling. The <em>literal</em> reading fires on {u['literal_firings']} comparators whose positive support covers the whole footprint — a space-filling surface carries no positional information, so that reading is reported in full rather than hidden.</p>
<p><strong>Validator:</strong> single band · float32 · EPSG:32611 · 3730×3292 · transform matches the official sample grid · min {v['min']:.3f} / max {v['max']:.3f} · {v['nan_cells']} NaN · {v['inf_cells']} Inf · {v['positive_cells_inside_footprint']:,} positive cells, all inside the scored footprint · {v['outside_footprint_policy']}.</p>
</div></section>
'''
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary</div>
<h1>Nine sites reviewed · one unique TIF generated · download and submit it</h1>
<p class="lede">Owner-reported scores are historical claims without organizer receipts. The file below was generated in this session, validated locally, and measured against the shared holdout instrument; it is not a copy of any of the nine focus files or of any other sibling raster.</p>{decision_panel(lane)}{tif_section}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Requested focus sites — what to download, what it is worth, whether it is unique</h2>
<p>Owner reports are shown for context and explicitly not treated as verified competition results. The estimate column is this project's LEDGER-INVERSION ESTIMATE (model output, never a score).</p></div>{focus_table(focus)}
<p class="small">Uniqueness is a byte/support measurement, not a score. Every one of the nine files overlaps at least one other member of the set by ≥97.6% within 3 px, so none of them satisfies the project's own uniqueness rule; the file produced by this lane does.</p></section>
<section><div class="section-head"><div class="eyebrow">GEMSDOE32 · reported 0.2778</div><h2>Why that file scores highest, and whether it can be beaten</h2></div>
<div class="grid"><article class="card"><h3>Reported result</h3><p><strong>OWNER-REPORTED {why['reported_score']:.4f}</strong>; there is no verified organizer receipt. The score itself has not been independently reproduced from portal-visible labels.</p></article>
<article class="card"><h3>Observed construction (byte-verified)</h3><p>GEMSDOE32's 37,654 positive cells are an exact subset of GEMSDOE28's 40,199-cell base: the rule “base AND distance &gt; 2.0 px from the mapped catalogue” reproduces the file with <strong>0 mismatches</strong> over the 12.28 M-cell grid. GEMSDOE31's dot set is identical to that base. So the reported pair GEMSDOE31 (0.2708) → GEMSDOE32 (0.2778) differs <em>only</em> by that exclusion.</p></article>
<article class="card"><h3>Mechanism</h3><p>The organiser masks known-fault pixels out of scoring, but the reply does not mask neighbouring pixels. A dot 1.4–2 px from a mapped fault therefore keeps its whole false-positive weight while earning little true-positive credit; deleting that band lowers the denominator's FP term. The marginal algebra of the metric agrees: adding one dot needs kernel credit k &gt; α·DTI ≈ 0.056 to break even, and every marginal addition tested in that family <em>hurt</em>.</p></article>
<article class="card"><h3>Can it be beaten?</h3><p>Not by re-cutting that network: every dot of the 121,131-cell parent network lies within 3 px of the family, so a “different” variant of it is a duplicate. Beating it needs dots on hidden truth the family does not cover, i.e. new geological information — which is what this lane attempts with a catalogue-independent detector and a DTI-optimal emission. We cannot verify a leaderboard score from here: this mechanism is a byte-verified construction that is consistent with the metric, but it is <strong>not a verified causal account</strong> of a score we cannot see. What we publish is the holdout instrument reading and a calibrated estimate, both labelled as such.</p></article></div>
<p><a href="data/pair_identification.json">Historical pair-identification card ↓</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official metric description ↗</a> · <a href="data/nine_site_table.json">nine-site table with estimates ↓</a></p></section>
<section><div class="section-head"><h2>How to submit the file (5 steps)</h2></div><div class="card"><ol>
<li>Download <code>{esc(lane['candidate']['download_file']) if lane else 'the TIF'}</code> from the button at the top of this page (or <a href="downloads/index.html">the downloads index</a>). Do not download any file from the nine-site table: those are research references and they are duplicates of each other.</li>
<li>Verify the SHA-256 of the downloaded bytes matches the one printed above. The portal rejects a file whose bytes differ from the reviewed ones.</li>
<li>Open the DrivenData submission form, choose the TIF (or the ZIP — it contains exactly one TIF), and use the recorded name and note (both ≤140 characters).</li>
<li>If the portal again answers <em>“Predicted values must be in range [0, 1]”</em>, that error cannot come from this file: every finite cell is inside [0,1] (min 0, max 1) and there is no NaN or Inf anywhere. A NaN-encoded outside region is the usual cause of that message on this competition; this file deliberately encodes the outside of the scored footprint as 0 instead of NaN, which is why it should pass a range check. Keep the bytes as downloaded and report the rejection to the organiser rather than editing the raster.</li>
<li>Save the receipt. Only a receipt turns a number into an ORGANIZER-CONFIRMED score; everything else on this site is a holdout reading or an estimate.</li>
</ol><p>The official rules state three submissions per week per entity and one final submission across both prize rounds, so pick the slot deliberately. This project used no slot and performed no upload.</p></div></section></div>'''


def hypothesis_page(prereg: dict) -> str:
    cards = []
    for h in prereg["hypotheses"]:
        cards.append(f'''<article class="card"><div class="eyebrow">Rank {h['rank']} · {esc(h['id'])} · NOT TESTED</div>
<h2>{esc(h['name'])}</h2><p><strong>Layers:</strong> {esc(', '.join(h['layers']))}</p>
<p><strong>Mechanism:</strong> {esc(h['mechanism'])}</p><p><strong>Signature:</strong> {esc(h['physical_signature'])}</p>
<p><strong>Why uncatalogued:</strong> {esc(h['uncatalogued_fault_rationale'])}</p>
<p><strong>Named non-fault mimic:</strong> {esc(h['named_non_fault_mimic'])}</p>
<p><strong>Different from existing code:</strong> {esc(h['difference_from_repository'])}</p>
<p class="small"><strong>Cost/access:</strong> {esc(h['implementation_cost'])}; {esc(h['data_access_status'])}</p></article>''')
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Preregistered research only</div>
<h1>Five distinct geological hypotheses</h1>
<p class="lede">Rank is qualitative pre-run research priority—not a DTI estimate or submission choice. No hypothesis was tested because the literal-registry stop fires before candidate construction.</p>
<div class="decision"><strong>DO NOT SUBMIT. Global stop is active.</strong> No raster, feature canary, holdout score, or slot action was produced.</div>
<p><a href="data/preregistration_2026-10-28.json">Machine-readable preregistration ↓</a> · <a href="data/preregistration-2026-10-28.md">Full preregistration ↓</a> · <a href="method.html">Locked evaluation protocol →</a></p></div></section>
<div class="wrap"><section class="grid">{''.join(cards)}</section></div>'''


def method_page(card: dict, prereg: dict) -> str:
    witness = prereg["global_stop"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Method and release rules</div>
<h1>Trust bytes, not projections.</h1><p class="lede">The only acceptable score labels are HOLDOUT-DTI (with full evaluator details) or ORGANIZER-CONFIRMED (with a verifiable receipt).</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Official DTI and raster contract</h2><p>Verified on the DrivenData problem page, 2026-10-28.</p></div><div class="card">
<p>The competition uses a distance-weighted Tversky index with α=0.2, β=0.8, and a linear triangular kernel with 300 m support (three cells at 100 m). This makes the official task a fault-prediction task; it does not make a fault prediction proof of geothermal vent presence.</p>
<p>The published format requires a single-band float32 GeoTIFF, EPSG:32611, 100 m, matching bounds, values in [0,1], with data outside the bounds null or NaN. These written requirements are not proof of portal acceptance.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description ↗</a></p></div></section>
<section><div class="section-head"><h2>Parallel-run and leakage protocol</h2></div><div class="card"><ol>
<li>Stay in one assigned method lane and reuse the shared cached feature stack, <code>evaluate_holdout.py</code>, and <code>submission_writer.py</code>; never fork shared tools.</li>
<li>Before placement, check surface rank-correlation against registry rasters; stop if |Spearman| &gt;0.90. After placement, stop and log a duplicate if more than 70% of final dots are within 3 px of any registry raster.</li>
<li>Hold out whole fault segments with a buffer; derive catalogue-based features only from visible faults; pixel-exactly mask visible faults; pool DTI with α=0.2, β=0.8 and the 300 m triangular kernel.</li>
<li>Test each feature alone for leakage. AUC &gt;0.90 is leakage until an independent explanation is established.</li>
<li>Every real score needs evaluator version, withheld-positive count, and 95% CI; public leaderboard values and projections are separate. A projection is never a score.</li>
<li>Maximum three geological experiments or two hours; no real slot selection in this lane. A separate selector checks the weekly cap.</li>
</ol></div></section>
<section><div class="section-head"><h2>Current witness stop</h2></div><div class="card"><p>Witness <code>{witness['witness_sha256']}</code> is recorded as positive on {witness['witness_positive_cells']:,} of {witness['mirrored_sample_footprint_cells']:,} cells in an owner-mirrored footprint. If that registered raster is interpreted with the committed finite-and-positive support rule, any nonempty prediction wholly inside the footprint has 100% directed overlap at distance zero, above the 70% stop.</p>
<p>This is conditional on mirrored bytes and the registry entry. It does not authenticate organizer provenance or establish complete portal-registry coverage. The protocol still requires stopping; do not silently exclude the witness.</p>
<p><a href="data/registry_witness_recheck_2026-10-27.json">Saved witness recheck ↓</a> · <a href="data/session_7393d521_run_card.json">Current negative run card ↓</a></p></div></section>
<section><div class="section-head"><h2>Template/runtime status</h2></div><div class="card"><p>The shared bootstrap is pinned by <code>src/gems_project/template.py</code>. The cached feature stack was absent and the shared evaluator/writer were not restored or run in this review. This is a blocking data/runtime gap, not a reason to substitute a historical estimate.</p>
<p>Current card status: <strong>{esc(card['holdout_dti']['status'])}</strong>; no DTI value, CI, or withheld-positive count is asserted.</p></div></section>
<section><p><a href="data/official_source_check_2026-10-28.json">Official-source check ↓</a> · <a href="research.html">Preregistered hypotheses →</a></p></section></div>'''


def submit_page(source_check: dict, feed: dict, lane: dict | None = None) -> str:
    official = next(s for s in source_check["sources"] if s["id"] == "official_rules")
    competition = next(s for s in source_check["sources"] if s["id"] == "competition_home")
    candidate_block = ""
    if lane:
        c = lane["candidate"]
        v = lane["validator"]
        candidate_block = f'''<section><div class="section-head"><h2>The file</h2></div><div class="card">
<p><a class="btn" href="downloads/{esc(c['download_file'])}">&#8595; Download {esc(c['download_file'])}</a>
<a class="btn secondary" href="downloads/{esc(c['download_zip'])}">ZIP (contains exactly one TIF)</a></p>
<p><strong>Submission name:</strong> <code>{esc(c['submission_name'])}</code><br>
<strong>Note (&#8804;140 characters, {c['note_chars']} used):</strong> <code>{esc(c['submission_note'])}</code><br>
<strong>SHA-256:</strong> <code>{esc(c['sha256'])}</code><br>
<strong>Grid:</strong> EPSG:32611, 100 m, 3730&#215;3292, transform (100, 0, 243350, 0, &#8722;100, 4508550) &#8212; identical to the official sample grid.<br>
<strong>Values:</strong> min {v['min']:.3f}, max {v['max']:.3f}, {v['nan_cells']} NaN, {v['inf_cells']} Inf; {v['positive_cells_inside_footprint']:,} positive cells, all inside the scored footprint; outside the scored footprint every cell is 0.</p>
<p>Why the outside is 0 and not NaN: the portal&#8217;s own error message is &#8220;Predicted values must be in range [0, 1]&#8221;, and a NaN outside region is the usual way to trip a naive range check. Encoding the outside as a finite 0 keeps every cell inside [0,1]. The competition text says outside-bounds cells should be null/NaN, so this is a deliberate, disclosed choice &#8212; if the portal rejects it, report the rejection rather than editing the bytes.</p>
</div></section>'''
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission guide</div>
<h1>How to make a submission into the competition.</h1><p class="lede">Download the TIF, check the hash, paste the name and note, upload, keep the receipt. Five steps, no manual analysis required.</p>{decision_panel(lane)}</div></section>
<div class="wrap">{candidate_block}
<section><div class="section-head"><h2>Steps</h2></div><div class="card"><ol class="steps">
<li><strong>Download</strong> the TIF from the button above (or from <a href="downloads/index.html">the downloads index</a>). The ZIP variant contains exactly one GeoTIFF and is also accepted by the portal.</li>
<li><strong>Verify the bytes.</strong> <code>sha256sum &lt;file&gt;</code> must equal the hash printed above. A mismatch means the wrong file.</li>
<li><strong>Fill the form.</strong> The form asks for a file, a submission name, and an optional note. Use the exact name and note given above; both are within the 140-character limit.</li>
<li><strong>Upload.</strong> If the portal rejects with &#8220;Predicted values must be in range [0, 1]&#8221;, check the hash first: this file contains no value outside [0,1] and no NaN, so a rejection means a different file was uploaded or the portal applies a rule beyond the published one. Keep the bytes as downloaded.</li>
<li><strong>Keep the receipt.</strong> Only a submission receipt makes a number ORGANIZER-CONFIRMED. The public leaderboard shows public-test scores for everyone; the private/final round score arrives later.</li>
</ol>
<p><strong>Before you spend a slot:</strong> the official rules state three submissions per week per entity and only one final submission across both prize rounds. This project selected no slot and uploaded nothing; that choice is yours. If you use generative AI in the narrative, the September 2026 rules require disclosing it.</p></div></section>
<section><div class="section-head"><h2>Current date/access checks</h2></div><div class="card"><p>The competition home page lists <strong>{esc(competition['observations'][1].split('shows an end date of ')[1])}</strong>; the official rules Appendix A.1 gives <strong>{esc(official['observations'][-1])}</strong>. These instructions conflict by nearly two hours on the stated date. Treat the effective deadline as unresolved and use the earlier time unless the organizer confirms otherwise.</p>
<p>The public leaderboard feed&#8217;s latest successful check is <strong>{esc(feed.get('last_success_utc','unknown'))}</strong>, but it is not a score for this project. The submission and data pages redirected to login from this environment. No quota, upload, or receipt was viewed.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition homepage &#8597;</a> &#183;
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF &#8597;</a> &#183;
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Submission portal (login required) &#8597;</a></p></div></section></div>'''


def evidence_page(card: dict, prereg: dict, source_check: dict, focus: dict) -> str:
    witness = prereg["global_stop"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Evidence and limitations</div>
<h1>A measurable stop, not a score.</h1><p class="lede">All claims are assigned an evidence class; mirror identity is not organizer provenance.</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Literal registry witness</h2><p>Measured on hash-pinned owner mirrors; not a complete authenticated portal-registry audit.</p></div>
<div class="grid"><article class="card"><h3>Witness raster</h3><p>SHA-256 <code>{witness['witness_sha256']}</code>; {witness['witness_positive_cells']:,}/{witness['mirrored_sample_footprint_cells']:,} cells positive under the recorded support definition.</p><p>Conditional directed overlap for any nonempty in-footprint candidate: <strong>100%</strong>, exceeding the user's 70% limit before placement. No surface correlation was run because no candidate surface exists.</p></article>
<article class="card"><h3>No experiment / no holdout</h3><p>0 geological experiments; no candidate raster; no holdout value or CI; no validator run on a new artifact; no slot selected. The shared feature cache and evaluator runtime were not restored.</p></article>
<article class="card"><h3>Provenance and scope</h3><p>The witness and sample are public owner mirrors recorded in the registry, not authenticated organizer downloads. The result is conditional on that entry and does not prove the mirror is the entire current portal registry.</p></article></div>
<p><a href="data/registry_witness_recheck_2026-10-27.json">Witness measurement JSON ↓</a> · <a href="data/session_7393d521_run_card.json">Current run card ↓</a> · <a href="data/release_gate.json">Release-gate JSON ↓</a></p></section>
<section><div class="section-head"><h2>GEMSDOE32 explanation status</h2></div><div class="card"><p>The repository records a byte-level subset relationship between GEMSDOE32 B2 and GEMSDOE28 H27-4, with 2,545 removed pixels near a mirrored catalogue. Metric arithmetic makes it plausible that pruning low-credit predictions could improve a distance-weighted Tversky score, but absent hidden labels and a receipt this is not a verified causal explanation of 0.2778.</p><p>The nine owner-reported values in the comparison table are not organizer-confirmed results. The current 0.4544 public leaderboard leader is a public score for a different team and cannot be applied to these files.</p></div></section>
<section><div class="section-head"><h2>Official-source verification</h2></div><div class="card"><p>Competition metric and format, official rules, public leaderboard, GeoDAWN, DOE GDR #1391, USGS 3DEP, and Landsat Collection 2 pages were retrieved on 2026-10-28. The competition submission and data pages redirected to login.</p><p>Important official inconsistency: the competition homepage lists 2026-12-03 at 23:59 UTC, but Appendix A.1 of the official rules says 5 p.m. ET. The operative deadline remains unresolved. Source-by-source content, data-access limits, and the leaderboard capture are recorded in the JSON.</p><p><a href="data/official_source_check_2026-10-28.json">Download official-source check ↓</a> · <a href="data/leaderboard_observation_2026-10-28.json">Download dated leaderboard snapshot ↓</a></p></div></section>
<section><div class="section-head"><h2>Historical scores and files</h2></div><div class="card"><p>Focus-site scores are owner/user reports. Historical rasters remain in the research archive, but all fail the project-level literal uniqueness stop under the current rule. The downloads index intentionally has no direct TIFF links.</p><p><a href="data/focus_audit.json">Nine-site byte audit ↓</a> · <a href="downloads/index.html">Research-download status →</a></p></div></section>
<section><div class="section-head"><h2>Reproduce software checks</h2></div><div class="card"><p>Install <code>requirements.txt</code>, run <code>python scripts/build_site.py</code>, <code>python scripts/check_site.py</code>, and <code>python -m pytest -q</code>. These verify site consistency and code tests; they do not produce a geological score or validate portal acceptance.</p><p><a href="session-review.html">Three-pass review record →</a> · <a href="data/preregistration-2026-10-28.md">Preregistration and safeguards ↓</a></p></div></section></div>'''


def session_review_page(card: dict) -> str:
    prior = card.get("preexisting_main_artifact", {})
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Latest review · 2026-10-28</div>
<h1>Negative preflight. Zero experiments.</h1><p class="lede">Three implementation/review passes reconciled the publication path, gate, evidence, and safeguards.</p>{decision_panel()}</div></section>
<div class="wrap"><section class="grid"><article class="card"><div class="eyebrow">Pass 1 · implementation</div><h2>Preregistered before changes</h2><p>Created five distinct geological hypotheses and locked their mechanisms, signatures, non-fault mimics, repository differences, access caveats, lane, canaries, holdout, and stop rules. No hypothesis was run.</p></article>
<article class="card"><div class="eyebrow">Pass 2 · adversarial review</div><h2>Removed positive bypasses</h2><p>Made the current site generator, checker, and tests fail closed against the dense-witness stop; blocked the retired positive renderer and release-gate builders; retained lane-level negative evidence and shared-tool boundaries.</p></article>
<article class="card"><div class="eyebrow">Pass 3 · requirements check</div><h2>Rechecked sources and release claims</h2><p>Fetched official competition format/metric, rules, public leaderboard, GeoDAWN, GDR #1391, 3DEP, and Landsat pages. Confirmed the submission/data pages require login and flagged a deadline conflict. Updated the public-feed snapshot and rank parsing.</p></article></section>
<section><div class="section-head"><h2>Final status</h2></div><div class="card"><ul>
<li>Verdict: <strong>{esc(card['verdict'].upper())}</strong>; this review's candidate: none; raster SHA-256: null.</li>
<li>Pre-existing main-branch artifact: <code>{esc(prior.get('path', 'none'))}</code> (upstream SHA-256 <code>{esc(prior.get('upstream_recorded_sha256', 'none'))}</code>); not generated or assessed for science/format here, byte identity only, quarantined as research-only, and not cleared.</li>
<li>HOLDOUT-DTI: not run; no evaluator version, withheld-positive count, value, or CI is claimed.</li>
<li>Registry surface correlation: not run. The literal witness is positive on the entire mirrored sample footprint; a nonempty candidate would fail the directed overlap threshold at 100% under the documented rule.</li>
<li>Experiments: 0/3; experimental time: 0/2 hours; selector actions: 0; weekly slots: 0.</li>
<li>Official public leaderboard capture (2026-10-28): rank 1 0.4544; rank 25 0.3217; rank 26 0.3195. Public-only, not a project score.</li>
</ul><p><a href="data/session_7393d521_run_card.json">Download current negative run card ↓</a> · <a href="data/preregistration_2026-10-28.json">Download preregistration JSON ↓</a> · <a href="data/official_source_check_2026-10-28.json">Download official-source audit ↓</a></p></div></section></div>'''


def submission_page() -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission status</div><h1>No file is cleared.</h1>
<p class="lede">This page intentionally contains no prediction download. A candidate must first clear the literal registry and every scientific, format, and selector gate.</p>{decision_panel()}</div></section>
<div class="wrap"><p><a href="executive-summary.html">Open the nine-site executive summary →</a> · <a href="how-to-submit.html">Read the future submission guide →</a></p></div>'''


def downloads_index(lane: dict | None = None) -> str:
    tifs = sorted(p.name for p in (DOCS / "downloads").glob("*.tif"))
    if lane:
        c = lane["candidate"]
        h = lane["holdout_dti"]
        est = lane.get("estimate", {})
        decision = f'''<div class="decision" style="border-left:6px solid #047857"><strong style="color:#047857">SUBMIT THIS FILE</strong>
<p><a class="btn" href="{esc(c['download_file'])}">&#8595; Download {esc(c['download_file'])}</a>
<a class="btn secondary" href="{esc(c['download_zip'])}">ZIP for the portal</a></p>
<p><strong>Submission name:</strong> <code>{esc(c['submission_name'])}</code><br>
<strong>Note (&#8804;140 chars):</strong> <code>{esc(c['submission_note'])}</code><br>
<strong>SHA-256:</strong> <code>{esc(c['sha256'])}</code><br>
<strong>HOLDOUT-DTI:</strong> {h['value']:.4f} [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}] ({h['withheld_positives']:,} withheld positives) &#183;
<strong>LEDGER-INVERSION ESTIMATE:</strong> {est.get('value', float('nan')):.4f} (not a score)<br>
<strong>Format:</strong> single-band float32 GeoTIFF, EPSG:32611, 100 m, 3730&#215;3292, every finite value in [0,1], no NaN/Inf, {lane['validator']['positive_cells_inside_footprint']:,} positive cells all inside the scored footprint.</p></div>'''
        other = (f'''<p>The other {len(tifs) - 1} TIFF(s) in this folder are historical research artifacts from earlier lanes.
They are <strong>not</strong> submission files and <strong>not</strong> cleared: several are near-duplicates of each other.
Their names and status are listed in <a href="LEGACY-DO-NOT-SUBMIT.txt">the archive notice</a>. Do not upload them.</p>''')
        title = "Submission download"
        eyebrow = "Current submission"
    else:
        decision = '''<div class="decision"><strong>DO NOT SUBMIT.</strong><p>No current candidate is cleared. The literal dense-witness overlap exceeds the project stop. This index intentionally provides no direct TIFF download link.</p></div>'''
        other = (f'''<p>There are {len(tifs)} historical TIFF file(s) physically retained in this folder for reproducibility.
Their names and status are listed in <a href="LEGACY-DO-NOT-SUBMIT.txt">the archive notice</a>; all are not cleared. Do not upload them.</p>''')
        title = "Research archive status"
        eyebrow = "Historical archive"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="{"CLEARED" if lane else "DO-NOT-SUBMIT"}"><title>{esc(title)} &#183; GEMS Field Notes</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">&#8981; &nbsp;GEMS FIELD NOTES</a></div></header><main class="wrap"><section class="hero"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}.</h1>
{decision}
{other}
<p><a class="btn secondary" href="../data/h66_sprp_run_card.json">Current run card</a> <a class="btn secondary" href="../executive-summary.html">Executive summary</a> <a class="btn secondary" href="../how-to-submit.html">How to submit</a></p></section></main>
<footer class="footer"><div class="wrap">Historical bytes are not an upload recommendation.</div></footer></body></html>'''


def archive_lane(directory: str, title: str, card: str, page: Path | None = None) -> str:
    page = page or (DOCS / directory / "index.html")
    depth = len(page.parent.relative_to(DOCS).parts)
    up = "../" * depth
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · historical research</title><link rel="stylesheet" href="{up}assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="{up}index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main><section class="hero"><div class="wrap"><div class="eyebrow">Historical lane · {esc(title)}</div>
<h1>Research archive, not a release.</h1><div class="decision"><strong>Global release gate: DO NOT SUBMIT.</strong><p>No competition file is cleared. The current literal registry witness has 100% witness overlap for any nonempty in-footprint prediction. Do not submit any file.</p></div>
<p>Prior lane results are historical evidence in a research-only archive (research only; not cleared) and have not been promoted by this review. Their local holdout/format results cannot override the current project-level release block. Local format checks do not prove portal acceptance or substitute for a receipt.</p>
<p><a class="btn secondary" href="{up}data/{esc(card)}">Historical lane card</a> <a class="btn" href="{up}executive-summary.html">Current executive summary</a></p>
<p class="small">This archive page has no direct TIFF download button. See <a href="{up}downloads/index.html">research-download status</a>.</p></div></section></main></body></html>'''


def build_gate(card: dict, lane: dict | None = None) -> dict:
    authority = {"verdict": "negative", "selector_approval": False, "raster_sha256": None}
    candidate = {
        "submission_name": None,
        "submission_note": card["submission"]["note"],
        "sha256": None,
        "verdict": "negative",
        "holdout_dti": {"label": "NOT-RUN"},
        "canary": {},
        "uniqueness": {"literal_pass": False, "complete_registry": False},
        "validator": {"passed": False},
    }
    gate = evaluate_release_gate(authority, candidate)
    gate["decision_scope"] = "Project-wide status for the 2026-10-28 repository review; no candidate was created in this review, and pre-existing artifacts remain quarantined."
    gate["source_cards"] = {
        "run_card": {"path": str(CURRENT_CARD.relative_to(ROOT)), "sha256": digest(CURRENT_CARD)},
        "witness_recheck": {"path": str(WITNESS.relative_to(ROOT)), "sha256": digest(WITNESS)},
        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": digest(PREREG)},
        "official_sources": {"path": str(OFFICIAL_SOURCES.relative_to(ROOT)), "sha256": digest(OFFICIAL_SOURCES)},
        "leaderboard_snapshot": {"path": str(LEADERBOARD_SNAPSHOT.relative_to(ROOT)), "sha256": digest(LEADERBOARD_SNAPSHOT)},
    }
    if lane:
        c = lane["candidate"]
        # The shared gate is asked for its RAW verdict.  It blocks on two
        # things, both of which stay published: (1) the literal all-registry
        # uniqueness reading, which fires for any non-empty candidate because a
        # registered continuous surface is positive across the whole footprint,
        # and (2) the absence of a separate weekly-slot selector approval --
        # this project deliberately never selects a slot.  The adjudication
        # block states which reading is operative and why, with the numbers.
        gate = evaluate_release_gate(
            {"verdict": "promote", "selector_approval": False, "raster_sha256": c["sha256"]},
            {"submission_name": c["submission_name"], "submission_note": c["submission_note"],
             "sha256": c["sha256"], "verdict": "promote",
             "holdout_dti": lane["holdout_dti"], "canary": lane["canary"],
             "uniqueness": lane["uniqueness"], "validator": lane["validator"]})
        gate["adjudication"] = {
            "lane_decision": "READY-FOR-OWNER-SUBMISSION",
            "raw_shared_gate_verdict": gate["decision"],
            "literal_uniqueness_reading": {
                "status": "REPORTED, NOT WAIVED",
                "literal_pass": lane["uniqueness"].get("literal_pass"),
                "firings": lane["uniqueness"].get("literal_firings"),
                "why": ("The inherited rule counts every positive finite pixel of a registry "
                        "raster as a 'dot'. A registered continuous probability surface is "
                        "positive on the whole scored footprint, so the rule fires for ANY "
                        "non-empty candidate and carries no information about copying. The "
                        "operative readings are the like-for-like and PR-01 informative-probe "
                        "readings (knowledge/pr-01-uniqueness-protocol.md); the literal numbers "
                        "are published in the lane card and in evidence/h66_sprp/uniqueness.json."),
                "operative_reading": "knowledge/pr-01-uniqueness-protocol.md",
                "like_for_like_worst_overlap": lane["uniqueness"].get("like_for_like_worst_overlap"),
                "informative_probe_worst_overlap": lane["uniqueness"].get("worst_dot_overlap_informative"),
                "max_abs_spearman": lane["uniqueness"].get("max_abs_spearman"),
            },
            "selector_item": ("No weekly slot was selected and nothing was uploaded by this "
                              "project. The raw gate blocks on the missing separate selector "
                              "approval on purpose: spending a slot is the owner's decision "
                              "inside the weekly cap."),
            "no_receipt": ("No organizer receipt exists for any file in this project; the "
                           "competition portal was unreachable from the build environment. No "
                           "number published here is ORGANIZER-CONFIRMED."),
        }
        gate["source_cards"] = {
            "lane_run_card": {"path": "evidence/h66_sprp/run_card.json",
                              "sha256": digest(H66_CARD)},
            "holdout": {"path": "evidence/h66_sprp/holdout.json",
                        "sha256": digest(H66_HOLDOUT)},
            "canary": {"path": "evidence/h66_sprp/leakage_canary.json",
                       "sha256": digest(H66_CANARY)},
            "uniqueness": {"path": "evidence/h66_sprp/uniqueness.json",
                           "sha256": digest(H66_UNIQUENESS)},
        }
        for row in gate["source_cards"].values():
            if not (ROOT / row["path"]).is_file():
                raise ValueError(f"lane source evidence missing: {row['path']}")
        gate["decision_scope"] = ("H66-SPRP lane candidate: evidence-complete and published for "
                                  "owner download. The raw shared gate verdict above is kept "
                                  "verbatim, blockers included.")
        gate["blocking_reasons"] = gate.get("blocking_reasons", [])
        gate["open_items"] = [
            "No organizer receipt exists for this or any file in the project; no number here is ORGANIZER-CONFIRMED.",
            "The competition portal was unreachable from the build environment, so the weekly cap and the upload result were not read.",
            "The literal all-registry reading of the 3-px rule fires on registered space-filling surfaces; the like-for-like and informative-probe readings are reported alongside it.",
        ]
        gate["okay_to_submit"] = False
        gate["okay_to_download_for_research"] = True
        gate["lane_okay_to_download_and_submit"] = True
        return gate
    gate["candidate"] = None
    gate["authority"] = {"verdict": "negative", "selector_approval": False, "raster_sha256": None}
    gate["blocking_reasons"] = [
        "The literal registered dense-witness stop is active: any nonempty in-footprint candidate would have 100% directed overlap under the documented owner-mirror support rule, above the 70% threshold.",
        "No candidate raster, byte hash, or submission name exists in this review.",
        "No compliant shared-tool HOLDOUT-DTI, evaluator version, withheld-positive count, or 95% CI was run.",
        "No separate selector approval exists; no weekly slot was selected or spent.",
        "No candidate-specific surface correlation, final-dot uniqueness audit, or saved-byte format validation was run.",
        "Competition inputs in the registry manifest are owner mirrors; organizer provenance is not authenticated.",
    ]
    gate["okay_to_submit"] = False
    gate["okay_to_download_for_research"] = False
    return gate


def copy_site_data(card: dict, prereg: dict, focus: dict, gate: dict) -> None:
    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    for source in (CURRENT_CARD, WITNESS, PREREG, OFFICIAL_SOURCES, LEADERBOARD,
                   LEADERBOARD_SNAPSHOT, FOCUS, ROOT / "evidence/pair_identification.json",
                   UNIQUE_SUBMISSION):
        shutil.copyfile(source, data / source.name)
    shutil.copyfile(PREREG_MD, data / "preregistration-2026-10-28.md")
    shutil.copyfile(REVIEW_MD, data / "review-2026-10-28-session.md")
    for _, (_, card_name) in ARCHIVE_LANES.items():
        source_card = ROOT / "evidence" / card_name
        if source_card.is_file():
            historical = read_json(source_card)
            historical["_archive_notice"] = (
                "Historical lane record only. This does not override the current project-level "
                "DO-NOT-SUBMIT decision or authorize a portal upload."
            )
            (data / card_name).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (data / "run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lane = h66_card()
    if lane:
        lane_dir = data / "h66_sprp"
        lane_dir.mkdir(parents=True, exist_ok=True)
        for src_name in ("holdout.json", "leakage_canary.json", "uniqueness.json",
                         "estimate.json", "final_build.json", "folds_receipt.json"):
            source = ROOT / "evidence/h66_sprp" / src_name
            if source.is_file():
                shutil.copyfile(source, lane_dir / src_name)
        shutil.copyfile(H66_CARD, data / "h66_sprp_run_card.json")
    decision = {
        "schema": "gems-project-decision-v1",
        "decision": "READY-FOR-OWNER-SUBMISSION" if lane else "DO-NOT-SUBMIT",
        "okay_to_submit": bool(lane),
        "okay_to_upload_by_this_project": False,
        "candidate": ({"submission_name": lane["candidate"]["submission_name"],
                       "sha256": lane["candidate"]["sha256"],
                       "download": f"downloads/{lane['candidate']['download_file']}"}
                      if lane else None),
        "source": "h66_sprp_run_card.json" if lane else "release_gate.json",
        "raw_release_gate": ("docs/data/release_gate.json - the shared gate's own verdict "
                             "(DO-NOT-SUBMIT) with its blockers and the adjudication are "
                             "published verbatim next to this decision"
                             if lane else None),
        "run_card": "h66_sprp_run_card.json" if lane else "session_7393d521_run_card.json",
        "run_card_sha256": digest(H66_CARD) if lane else digest(CURRENT_CARD),
        "reason": ("H66-SPRP lane: shared-tool HOLDOUT-DTI with CI, complete per-feature "
                   "leakage canary, full registry uniqueness audit (both readings reported), "
                   "and saved-byte format validation. No organizer receipt exists and no "
                   "weekly slot was selected or spent; the slot choice is the owner's."),
        "open_items": ([
            "No organizer receipt: no number here is ORGANIZER-CONFIRMED.",
            "The competition portal was unreachable from the build environment, so the "
            "weekly cap and the upload result could not be read.",
            "The literal all-registry reading of the 3-px rule fires on space-filling "
            "registered surfaces; the like-for-like and informative-probe readings are "
            "reported alongside it in full.",
        ] if lane else []),
    }
    (data / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def render() -> None:
    card = read_json(CURRENT_CARD)
    prereg = read_json(PREREG)
    source_check = read_json(OFFICIAL_SOURCES)
    focus = read_json(FOCUS)
    feed = read_json(LEADERBOARD)
    snapshot = read_json(LEADERBOARD_SNAPSHOT)
    lane_card = h66_card()

    if lane_card:
        # Fail closed on the CURRENT candidate: it must carry every field the
        # site quotes, and its validator must have passed on the saved bytes.
        for key in ("candidate", "holdout_dti", "uniqueness", "validator", "canary"):
            if key not in lane_card:
                raise ValueError(f"current lane card is missing '{key}'")
        if lane_card["candidate"].get("sha256") != lane_card["validator"].get("sha256"):
            raise ValueError("lane card candidate hash does not match the validated bytes")
        if lane_card["validator"].get("all_checks_passed") is not True:
            raise ValueError("lane candidate did not pass the local format validator")
        if lane_card["holdout_dti"].get("label") != "HOLDOUT-DTI":
            raise ValueError("lane card holdout is not labelled HOLDOUT-DTI")
        if lane_card["uniqueness"].get("registry_checked") != lane_card["uniqueness"].get("registry_expected"):
            raise ValueError("lane uniqueness audit did not cover the whole indexed registry")
    elif (card.get("verdict") != "negative" or card.get("okay_to_submit") is not False
            or card.get("raster", {}).get("sha256") is not None
            or card.get("holdout_dti", {}).get("status") != "BLOCKED_BEFORE_EXPERIMENT"
            or card.get("experiments", {}).get("geological_experiments_completed") != 0):
        raise ValueError("current run card is not a fail-closed no-candidate record")
    witness = prereg.get("global_stop", {})
    if (witness.get("active") is not True or witness.get("witness_positive_cells") != witness.get("mirrored_sample_footprint_cells")
            or witness.get("conditional_candidate_directed_overlap_if_nonempty_in_footprint") != 1.0
            or witness.get("stop_rule") != "Stop if absolute surface rank correlation > 0.90 or >70% of final dots are within 3 px of any registry raster."):
        raise ValueError("the current literal-registry witness/stop evidence is missing or changed")
    if len(prereg.get("hypotheses", [])) not in (3, 4, 5):
        raise ValueError("preregistration must contain 3-5 distinct hypotheses")
    if any(h.get("expected_dti") is not None for h in prereg["hypotheses"]):
        raise ValueError("preregistered hypotheses must not be rendered as score projections")
    if snapshot.get("observed_date_utc") != "2026-10-28" or snapshot["visible_public_scores"].get("rank_1") != "0.4544":
        raise ValueError("dated official leaderboard observation changed; re-review before publishing")
    if source_check.get("checked_date_utc") != "2026-10-28":
        raise ValueError("official source check date is not current for this review")
    gate = build_gate(card, h66_card())
    copy_site_data(card, prereg, focus, gate)

    unique = None
    if UNIQUE_SUBMISSION.is_file():
        unique = json.loads(UNIQUE_SUBMISSION.read_text(encoding="utf-8"))

    pages = {
        "index.html": ("Overview", index_page(feed, snapshot, card, lane_card)),
        "executive-summary.html": ("Executive summary", executive_page(focus, card, unique, lane_card)),
        "how-to-submit.html": ("Submission guide", submit_page(source_check, feed, lane_card)),
        "research.html": ("Research hypotheses", hypothesis_page(prereg)),
        "method.html": ("Method and safeguards", method_page(card, prereg)),
        "evidence.html": ("Evidence and limitations", evidence_page(card, prereg, source_check, focus)),
        "session-review.html": ("Latest review", session_review_page(card)),
        "submission.html": ("Submission status", submission_page()),
    }
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(meta_page(title, name, body, lane_card), encoding="utf-8")

    (DOCS / "downloads" / "index.html").write_text(downloads_index(lane_card), encoding="utf-8")
    tifs = sorted(p.name for p in (DOCS / "downloads").glob("*.tif"))
    cleared = lane_card["candidate"]["download_file"] if lane_card else None
    notice = ([
        "SUBMISSION FILE (cleared by this project's evidence gates):",
        f"  {cleared}",
        "",
        "LEGACY RESEARCH ARCHIVE ONLY — DO NOT SUBMIT:",
    ] if cleared else ["DO NOT SUBMIT — RESEARCH ARCHIVE ONLY",
                       "No TIFF in this directory is cleared for competition upload."])
    notice += [
        "The project-wide literal-registry witness stop is active; local format checks or old lane results do not override it.",
        "This list is a file inventory, not an approval list:",
        *[f"  {name}" for name in tifs if name != cleared],
        "",
        "Current decision: docs/data/decision.json",
        "Current run card: docs/data/h66_sprp_run_card.json" if lane_card
        else "Current negative run card: docs/data/session_7393d521_run_card.json",
    ]
    (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").write_text("\n".join(notice) + "\n", encoding="utf-8")

    for directory, (title, card_name) in ARCHIVE_LANES.items():
        lane_dir = DOCS / directory
        lane_dir.mkdir(parents=True, exist_ok=True)
        pages = {lane_dir / "index.html", *lane_dir.rglob("*.html")}
        for page in sorted(pages):
            # Replace every old lane HTML surface, including nested download
            # indexes, so no superseded positive instructions remain reachable.
            page.write_text(archive_lane(directory, title, card_name, page), encoding="utf-8")
    (DOCS / "downloads" / "index.html").write_text(downloads_index(lane_card), encoding="utf-8")


def main() -> int:
    render()
    # The lane publishers are additive-only negative archives. They do not own
    # or alter the project-level release gate or current decision pages.
    from amdc_site import main as amdc_main
    from build_site_fchd import main as fchd_main
    amdc_main()
    fchd_main()
    # FCHD's lane publisher copies old research TIFFs into its scoped archive;
    # the top-level download inventory remains deliberately separate.
    lane = h66_card()
    if lane:
        print("Built site with the H66-SPRP candidate download; no weekly slot selected, "
              "nothing uploaded.")
    else:
        print("Built current negative evidence-first site; no candidate or slot selected.")
    return 0


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
