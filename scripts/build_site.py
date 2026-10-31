#!/usr/bin/env python3
"""Build the evidence-first GEMS site from current, committed evidence.

This renderer publishes the *archive* lane: the 2026-10-30 review and its
negative preflight, plus earlier lanes in marked research archives. It never
promotes a TIFF. The live release decision is rendered by
``build_release_site.py``, which runs last and owns index.html,
executive-summary.html, research.html and how-to-submit.html. Every page built
here carries a banner pointing at that single live decision so that a visitor
cannot mistake an archived "do not submit" for the current status.
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
LEADERBOARD_SNAPSHOT = ROOT / "evidence/leaderboard_observation_2026-10-28.json"  # gate provenance pin
LATEST_LEADERBOARD = ROOT / "evidence/leaderboard_observation_2026-10-29.json"
OBS_1031_LEADERBOARD = ROOT / "evidence/leaderboard_observation_2026-10-31.json"
TWR1_CARD = ROOT / "evidence/twr1_run_card.json"
TWR1_UNIQUE = ROOT / "evidence/twr1r_uniqueness.json"
TWR1_READBACK = ROOT / "evidence/twr1_focus_readback.json"
TWR1_HOLDOUT = ROOT / "evidence/twr1_holdout.json"
TWR1_CANARY = ROOT / "evidence/twr1_canary.json"
FOCUS = ROOT / "evidence/focus_audit.json"
REVIEW_MD = ROOT / "knowledge/review-2026-10-31-session.md"
UNIQUE_SUBMISSION = ROOT / "evidence/unique_submission_run_card.json"
UPSTREAM_CHECK = ROOT / "evidence/latest-upstream-check.json"

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


RELEASE_CARD = ROOT / "evidence" / "release" / "candidate_run_card.json"


def release_lane_state() -> tuple[str, str]:
    """Return (lane word, sentence) for the live release lane, from its card."""
    try:
        card = json.loads(RELEASE_CARD.read_text())
        ok = (card.get("verdict") == "promote"
              and card.get("format_validator", {}).get("passed") is True
              and card.get("uniqueness_audit", {}).get("passed") is True)
    except (OSError, ValueError):
        return "unknown", ("The release lane has no readable run card, so nothing on this site "
                           "is cleared.")
    if ok:
        return "positive", ("The live release lane has a cleared file. Its decision sentence and "
                            "download link are on <a href=\"index.html\">the landing page</a>.")
    return "negative", ("The live release lane is stopped too: there is no cleared file. See "
                        "<a href=\"index.html\">the landing page</a>.")


def legacy_banner() -> str:
    _lane, sentence = release_lane_state()
    return ('<div class="banner"><b>Archive lane page.</b> The text below records the '
            '2026-10-30 repository review, whose own verdict was <b>DO NOT SUBMIT</b> for every '
            'file it examined. It is kept for audit and is not the project decision. '
            f'{sentence}</div>')


def meta_page(title: str, current: str, body: str) -> str:
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
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Evidence-first DOE GEMS fault-mapping review; no submission currently cleared.">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a>
<nav aria-label="Main navigation">{links}</nav></div></header>
<main>{legacy_banner()}{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData ·
<a href="data/decision.json">Machine-readable decision</a> · 0 portal slots used in this review.</div></footer></body></html>'''


def decision_panel() -> str:
    return '''<div class="decision"><span class="tag">NEGATIVE · FAIL CLOSED</span>
<h2>DO NOT SUBMIT to a competition slot — no file is cleared.</h2>
<p>Update 2026-10-31: one unique candidate was generated and fully gated by this project
(<code>wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif</code>). The shared validator PASSes it
(single-band float32, EPSG:32611, 100 m, values in [0,1], finite inside the footprint, zero on the mapped
catalogue) and the ratified uniqueness audit PASSes it against 140 hash-verified sibling rasters
(0 duplicate flags; worst |Spearman| 0.162). It <strong>fails</strong> the pre-registered promotion bar
(HOLDOUT-DTI 0.02879 vs comparable holdout best 0.0992), so no clearance is granted and no slot is spent.
Download for research and learning is fine; portal upload of any file in this repository is not authorized
by this project. A local format pass, owner-reported score, or uniqueness pass does not clear a file.</p>
<p><a class="btn secondary" href="downloads/index.html">Open research-download archive status</a>
<a class="btn secondary" href="data/twr1_run_card.json">Read the 2026-10-31 run card</a>
<a class="btn secondary" href="data/session_7393d521_run_card.json">Prior negative review card</a></p></div>'''


def leaderboard_panel(feed: dict, snapshot: dict) -> str:
    date = snapshot["observed_date_utc"]
    ranks = snapshot["visible_public_scores"]
    freshness = feed.get("last_success_utc") or "unknown"
    error = "yes" if feed.get("last_attempt_error") else "no"
    stale_text = "refresh attempt failed; last success retained" if error == "yes" else "automated feed last succeeded"
    return f'''<article class="card"><div class="small">Public leaderboard observation — not our score</div>
<div class="metric">{esc(ranks['rank_1'])}</div>
<div class="small">Rank 1 in saved official-page capture · {esc(date)} · {esc(stale_text)}</div>
<p>Automated leaderboard feed last success: <span data-freshness data-checked="{esc(freshness)}" data-error="{error}">{esc(freshness)}</span>. The separately saved official-page observation is dated {esc(date)}; neither is a project-file score or receipt.</p>
<p>Rank 25: <strong>{esc(ranks['rank_25'])}</strong> · rank 26: <strong>{esc(ranks['rank_26'])}</strong>.
The cited 0.3195 was rank 26 on 2026-10-28; the latest saved capture has rank 26 at 0.3328. Rank 1 is 0.4544 in both dated captures. These public scores are not project-file scores or receipts.
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open official leaderboard ↗</a>
· <a href="data/leaderboard_observation_2026-10-29.json">latest saved capture ↓</a> · <a href="data/leaderboard_observation_2026-10-31.json">2026-10-31 capture ↓</a> (rank 2 = 0.3925, rank 3 = 0.3917; churn ongoing; the brief's 0.4413/0.3195 are stale: IR-31-01)</p></article>'''


def upstream_freshness_card(upstream: dict) -> str:
    checked = esc(upstream.get("checked_at", "unknown"))
    rows = upstream.get("repositories", [])
    fetched = sum(row.get("fetch_status") == "FETCHED" for row in rows)
    changed = sum(row.get("comparison_to_baseline") == "CHANGED" for row in rows)
    return f'''<article class="card"><h3>Focus-site source freshness</h3>
<p>GitHub HEAD identity check: <strong>{fetched}/{len(rows)} repositories fetched</strong>; {changed} differ from the historical 2026-10-26 baseline. Checked {checked}.</p>
<p>This only detects repository-head changes. It does not prove a score, TIFF, receipt, full registry coverage, or changed submission bytes; every focus site remains unapproved for submission.</p>
<a href="data/latest-upstream-check.json">Open machine-readable freshness check ↓</a></article>'''


READBACK_NAME = {"GEMSDOE24": "GEMSDOE24.tif", "GEMSDOE25": "GEMSDOE25.tif", "GEMSDOE27": "GEMSDOE27.tif",
                 "GEMSDOE28": "GEMSDOE28.tif", "GEMSDOE30": "GEMSDOE30.tif", "GEMSDOE31": "GEMSDOE31.tif",
                 "GEMSDOE32": "GEMSDOE32.tif", "GEMSDOE33": "GEMSDOE33.tif", "GEMSDOE36": "GEMSDOE36.tif"}


def focus_table(focus: dict, readback: dict | None = None) -> str:
    rows = {row["site"]: row for row in focus["focus_sites"]}
    rb = (readback or {}).get("results", {})
    body = []
    for site in FOCUS_ORDER:
        row = rows[site]
        overlap = 100.0 * float(row["max_focus_overlap"])
        r = rb.get(READBACK_NAME.get(site, ""), {})
        rb_txt = (f"HOLDOUT-DTI {r['pooled_dti']:.4f}<small>shared instrument read-back (evaluator "
                  f"{r.get('evaluator_version','?')}); full-catalogue file, not fold-local — "
                  f"NOT a leaderboard estimate</small>" if r else "Not measured")
        body.append(f'''<tr><td><strong>{esc(site)}</strong></td>
<td><a class="file" href="{esc(row['download_research_only'])}" rel="noopener">{esc(row['filename'])}</a>
<small>pinned historical file · external research mirror only</small></td>
<td><strong>OWNER-REPORTED {esc(row['claimed_by_owner_not_receipt'])}</strong>
<small>not an organizer receipt</small></td>
<td><strong>Not estimable</strong><small>no leaderboard-calibrated estimator is validated (see review);
the closest quantitative proxy is the read-back column</small></td>
<td>{rb_txt}</td>
<td><strong>No</strong><small>maximum 3-px overlap within the nine-site set: {overlap:.1f}%</small></td>
<td><span class="tag">DO NOT SUBMIT</span></td></tr>''')
    return '''<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>Highest pinned historical file (research only)</th><th>Reported score</th>
<th>Estimated score</th><th>Shared-instrument read-back (2026-10-31)</th><th>Unique within the set?</th>
<th>Decision</th></tr></thead><tbody>''' + "".join(body) + "</tbody></table></div>"


def index_page(feed: dict, snapshot: dict, card: dict, upstream: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS · executive decision</div>
<h1>Maximize P(Win). Own the Outcome.</h1>
<p class="lede">Evidence first: protect the competition slot, keep every claim auditable, and treat a negative finding as a useful deliverable.</p>
{decision_panel()}
<div class="grid">
<article class="card"><div class="small">This review (2026-10-31)</div><div class="metric">1 candidate</div>
<p>3 geological experiments · shared validator PASS · uniqueness PASS · holdout bar FAIL → verdict negative ·
0 portal slots used.</p></article>
{leaderboard_panel(feed, snapshot)}
{upstream_freshness_card(upstream)}
<article class="card"><div class="small">Organizer-confirmed project scores</div><div class="metric">None</div><p>No receipt is present in the repository.</p></article>
</div></div></section>
<div class="wrap"><section><div class="section-head"><div class="eyebrow">Focus-site review</div>
<h2>Nine historical claims, no submission recommendation</h2>
<p>Every score below is an owner/user report without a verified receipt. Historical file links are research references, not approved downloads.</p></div>
{focus_table(read_json(FOCUS), read_json(TWR1_READBACK))}
<p class="small">GEMSDOE32's reported 0.2778 has a plausible byte-level pruning explanation, not a verified causal explanation; see the executive summary. No candidate has a trustworthy score estimate.</p></section>
<section><div class="grid"><article class="card"><h3>What blocks clearance now</h3>
<p>The 2026-10-29 degenerate-literal stop was resolved by the owner-ratified, documented comparator rule
(2026-10-31): thresholds unchanged (|ρ| ≤ 0.90; 70% at 3 px), overlap judged symmetrically so space-filling
comparators cannot universal-block; every literal number stays published per comparator. The candidate now
fails on <em>science</em>: HOLDOUT-DTI 0.02879 vs the 0.0992 comparable holdout best. A projection is never
written as a score; no organizer receipt exists for any focus file.</p>
<a href="evidence.html">Read the evidence and caveats →</a></article>
<article class="card"><h3>Research plan</h3><p>Five distinct geological hypotheses are preregistered with mechanisms, non-fault mimics, cost, and repository-difference checks. None was tested because the stop is active.</p><a href="research.html">Read the preregistration →</a></article>
<article class="card"><h3>Latest saved official-source check</h3><p>Competition metric/format, rules, GeoDAWN, GDR #1391, 3DEP, Landsat, and the public leaderboard were checked on 2026-10-29. This is a dated observation, not a live check; login-gated data and submission pages remain inaccessible.</p><a href="data/official_source_check_2026-10-29.json">Open source audit JSON ↓</a></article></div></section>
<section><div class="card"><h2>Historical lane archives — research only</h2><p>Every lane archive inherits the current DO NOT SUBMIT decision; archived scores and format passes are not project-level clearance.</p><p><a href="hce/index.html">HCE →</a> · <a href="thcs/index.html">THCS →</a> · <a href="lst1/index.html">LST1 →</a> · <a href="lbcal/index.html">LBCAL →</a> · <a href="fchd/index.html">FCHD →</a> · <a href="amdc/index.html">AMDC →</a> · <a href="rfl/index.html">RFL →</a> · <a href="cspes/index.html">CSPES →</a></p></div></section>
<section><div class="decision"><strong>Deadline irregularity:</strong> the competition homepage shows 2026-12-03 23:59 UTC, while the September 2026 official rules state 5:00 p.m. ET on the deadline date. Effective cutoff is unresolved; use the earlier time unless the organizer confirms otherwise. The live account quota could not be viewed.</div></section>
<section><div class="section-head"><h2>Decision questions, answered by machine evidence</h2></div>
<div class="grid">
<article class="card"><h3 id="Q1">Q1 — Is any file cleared for portal upload?</h3><p>No. The 2026-10-31 candidate clears the shared validator and the ratified uniqueness audit but fails the pre-registered holdout promotion bar (0.02879 vs 0.0992), so it is not cleared for a slot. Machine record: <a href="data/twr1_run_card.json">run card ↓</a>.</p></article>
<article class="card"><h3 id="Q2">Q2 — Can I download the unique TIF?</h3><p>Yes, for research and learning: <a href="downloads/wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif">TIF ↓</a> · <a href="downloads/wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.zip">ZIP ↓</a>. Uploading it to the portal is a personal, un-cleared decision, not a project recommendation.</p></article>
<article class="card"><h3 id="Q3">Q3 — Which focus file should I submit?</h3><p>None of the nine. All are legacy DO-NOT-SUBMIT research mirrors; their scores are owner-reported, receipts are absent, and every one fails uniqueness inside the family (3-px dot overlap up to 100%).</p></article>
<article class="card"><h3 id="Q4">Q4 — How fresh is the evidence?</h3><p>Leaderboard captured 2026-10-31; focus-site source identity feed: <a href="data/latest-upstream-check.json">latest-upstream-check.json ↓</a> (approved-for-submission flag is false inside). Full gate state: <a href="data/release_gate.json">release gate ↓</a>.</p></article>
</div></section>
<p class="small">Current negative run card: <a href="data/session_7393d521_run_card.json"><code>session_7393d521_run_card.json</code> ↓</a> ·
<a href="data/release_gate.json">release gate ↓</a> · <a href="session-review.html">review passes →</a></p></div>'''


def executive_page(focus: dict, card: dict, unique: dict | None) -> str:
    why = card["gemsdoe32_explanation"]
    twr = read_json(TWR1_CARD)
    uni = read_json(TWR1_UNIQUE)
    u = uni["summary"]
    c = twr["submission"]
    v = twr["validator"]
    h = twr["holdout_dti"]
    tif_section = f'''
<section><div class="section-head"><div class="eyebrow">Unique TIF generated by this project · 2026-10-31</div>
<h2>TWR-1r2 — fold-local multi-sensor anisotropic crest core, halo-avoided</h2></div>
<div class="decision"><span class="tag" style="background:#d97706;color:#fff;">DOWNLOAD FOR RESEARCH: YES · CLEARED FOR PORTAL SUBMISSION: NO</span>
<p><strong>File:</strong> <code>{esc(c['name'])}.tif</code> · ZIP also provided (single-TIFF, as the portal accepts)</p>
<p><strong>Direct downloads:</strong>
<a class="btn" href="downloads/{esc(c['name'])}.tif">Download TIF ↓</a>
<a class="btn" href="downloads/{esc(c['name'])}.zip">Download ZIP ↓</a>
<a class="btn secondary" href="data/twr1_run_card.json">Machine-readable run card ↓</a></p>
<p><strong>SHA-256 (bytes as published):</strong> {esc(twr['raster_sha256'])}<br>
<strong>Format:</strong> single-band float32 GeoTIFF · EPSG:32611 · 100 m · 3730×3292 · values in [0,1] ·
finite inside footprint · zero on mapped catalogue · zero outside footprint (all-finite writer policy).
Shared writer + validator: <strong>PASS</strong>.</p>
<p><strong>Uniqueness (ratified rule, thresholds unchanged):</strong> {u['n']} hash-verified sibling comparators ·
{u['duplicate_flags']} duplicate flags · worst non-degenerate forward 3-px overlap below 0.70 by construction
(3 comparator halos excluded) · worst |Spearman| {u['worst_abs_spearman']} ≤ 0.90 · dense space-filling
comparators reported, never waived → <strong>PASS</strong>. Literal forward-rule numbers are published
per comparator in <a href="data/twr1r_uniqueness.json">the audit JSON</a>.</p>
<p><strong>Science gate (promotion bar):</strong> HOLDOUT-DTI <strong>{h['repaired_fold_local']['value']}</strong>
(95% CI {h['repaired_fold_local']['ci95']}; evaluator {esc(h['evaluator_version'])};
{h['withheld_positives']:,} withheld positives) vs comparable holdout best <strong>{h['comparable_holdout_best']['value']}</strong> →
<strong>FAIL · verdict negative</strong>. Do not spend a weekly slot on this file. The portal will accept it
format-wise (validator pass + [0,1]-safe zeros), which also answers the earlier
“Predicted values must be in range [0, 1]” rejection: files whose outside-footprint NaN were read as out-of-range;
this candidate avoids that by construction.</p>
<p><strong>Portal note text (≤140 chars, use verbatim if the owner overrides and submits anyway):</strong>
<code>{esc(c['note'])}</code></p>
</div>
<div class="card"><h3>Lane mechanism and the named non-fault mimic</h3>
<p>{esc(twr['mechanism'])}</p>
<p><strong>Named non-fault mimic:</strong> {esc(twr['named_non_fault_mimic'])}</p>
<p><strong>Hypothesis and refutation:</strong> the “soft 1–3 px crest halo” envelope arm was decisively negative on
the shared instrument (HOLDOUT-DTI 0.00795 vs core 0.02082), while widening the dot-spacing NMS from 2 px to 3 px
plus flagged-comparator halo avoidance raised the core from 0.0628 to 0.0837, and the final published emission
lands at 0.02879 after the third comparator halo was respected — the full trajectory is in
<a href="data/twr1_holdout.json">data/twr1_holdout.json</a> and <a href="data/twr1_e3_variants.json">data/twr1_e3_variants.json</a>.</p></div></section>
'''
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary</div>
<h1>Nine sites reviewed · one unique TIF generated · holdout bar not met</h1>
<p class="lede">Owner-reported scores are historical claims without organizer receipts. The generated TIFF below is validator-clean and uniqueness-passing, carries an honest negative HOLDOUT-DTI, and is not cleared for a slot — download for research and learning.</p>{decision_panel()}{tif_section}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Requested focus sites</h2><p>Owner reports are shown for context and explicitly not treated as verified competition results.</p></div>{focus_table(focus, read_json(TWR1_READBACK))}
<p class="small">“Not estimable” is deliberate: the repository's model projections are not sufficiently validated to select a real submission. Uniqueness is a byte/support measurement, not a score.</p></section>
<section><div class="section-head"><div class="eyebrow">GEMSDOE32 · reported 0.2778</div><h2>What the saved bytes suggest</h2></div>
<div class="grid"><article class="card"><h3>Reported result</h3><p><strong>OWNER-REPORTED {why['reported_score']:.4f}</strong>; there is no verified organizer receipt. The score itself has not been independently reproduced from portal-visible labels.</p></article>
<article class="card"><h3>Observed construction</h3><p>The saved-support analysis reports GEMSDOE32 B2 as an exact subset of the GEMSDOE28 H27-4 base, removing 2,545 cells near a mirrored catalogue. This is a raster measurement, not a score measurement.</p></article>
<article class="card"><h3>Mechanistic possibility—not proof</h3><p>Under distance-weighted Tversky, pruning low-credit predictions could reduce false-positive mass while retaining useful coverage. This is a plausible explanation, not a verified causal account: hidden labels and the official receipt are unavailable.</p></article></div>
<p><a href="data/pair_identification.json">Historical pair-identification card ↓</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official metric description ↗</a></p></section>
<section><div class="section-head"><h2>Decision and path to a future submission</h2></div><div class="card"><ol>
<li>Resolve the literal registered-witness stop using an evidence-based, documented interpretation. Do not waive it or treat a content-aware audit as a substitute.</li>
<li>Restore and verify the shared feature cache and the common holdout/writer tools. Remain in the assigned method lane.</li>
<li>Run per-feature leakage canaries and a whole-fault-segment buffered holdout only when the duplicate stop is resolved; report evaluator version, withheld positives, 95% CI, and matched paired baseline.</li>
<li>Run pre-placement surface correlation and final-dot overlap against the full registry. Stop if |Spearman| &gt;0.90 or &gt;70% of dots lie within 3 px of any raster.</li>
<li>Only after scientific gates pass may a separate selector review the portal's three-per-week cap and choose a single final submission. No slot was selected here. Any future submission note must remain ≤140 characters.</li>
</ol><p>The reported “Predicted values must be in range [0, 1]” rejection remains unexplained. Recheck exact saved bytes and ask the organizer; never silently clip values. Passing a local validator does not prove portal acceptance.</p></div></section></div>'''



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


def submit_page(source_check: dict, feed: dict) -> str:
    official = next(s for s in source_check["sources"] if s["id"] == "official_rules")
    competition = next(s for s in source_check["sources"] if s["id"] == "competition_home")
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission guide</div>
<h1>No submission is currently authorized.</h1><p class="lede">This page documents how to proceed only after an exact candidate clears science, uniqueness, format, and separate-selector gates.</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Future steps after clearance</h2></div><div class="card"><ol class="steps">
<li>Wait for a candidate-specific negative/positive run card and release gate. There is no cleared candidate today.</li>
<li>For the exact selected bytes, verify SHA-256, single-band float32, EPSG:32611, 100 m grid/shape/transform/bounds, values in [0,1], no NaN/Inf inside the footprint, and null/NaN outside the bounds per the official text.</li>
<li>Have a separate selector review the live account quota. The official rules say three submissions per week per entity and only one final submission across both prize rounds. The unauthenticated submission page redirected to login; current account quota/usage is unknown.</li>
<li>On the official platform, upload only the exact approved file, use its recorded name and note (≤140 characters), and retain the receipt with the file hash. A receipt is required for an ORGANIZER-CONFIRMED score.</li>
<li>If generative AI was used, disclose its extent and role in the narrative as required by the September 2026 official rules; ensure all required scientific/code assets and attribution are complete.</li>
</ol><p>No candidate name or upload note is assigned because no candidate exists. The negative run-card note is not an upload instruction.</p></div></section>
<section><div class="section-head"><h2>Current date/access checks</h2></div><div class="card"><p>The competition home page lists <strong>{esc(competition['observations'][1].split('shows an end date of ')[1])}</strong>; the official rules Appendix A.1 gives <strong>{esc(official['observations'][-1])}</strong>. These instructions conflict by nearly two hours on the stated date. Treat the effective deadline as unresolved and use the earlier time unless the organizer confirms otherwise.</p>
<p>The public leaderboard feed's latest successful check is <strong>{esc(feed.get('last_success_utc','unknown'))}</strong>, but it is not a score for this project. The submission and data pages redirected to login. No quota, upload, or receipt was viewed.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition homepage ↗</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF ↗</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Submission portal (login required) ↗</a></p></div></section></div>'''


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


def session_review_page(card: dict, latest_snapshot: dict) -> str:
    prior = card.get("preexisting_main_artifact", {})
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Current repository review · 2026-10-31</div>
<h1>No submission candidate cleared.</h1><p class="lede">The current review refreshed focus-site GitHub identities, found publication freshness/status gaps, hardened the site generator, and reran verification. It did not run a geological experiment or create a TIFF.</p>{decision_panel()}
<div class="card"><h2>Current review record</h2><p>GitHub HEAD identities: 9/9 repositories fetched; all changed from the 2026-10-26 baseline. This is not a TIFF-content, score, or receipt audit. Latest saved public leaderboard capture is dated 2026-10-29 and was not live-refreshed today. Automated checks: site checker PASS; 260 passed, 4 skipped.</p><p><a href="data/review-2026-10-31.md">Read the full three-pass repository review ↓</a> · <a href="data/executive-summary-2026-10-31.md">Measured nine-site executive summary ↓</a> · <a href="data/focus_measure_2026_10_31.json">Raster measurements ↓</a> · <a href="data/review_2026-10-31_run_card.json">Negative run card ↓</a></p></div></div></section>
<div class="wrap"><section><div class="section-head"><h2>Previous evidence review · 2026-10-28</h2><p>Historical gate record, retained below for audit context.</p></div></section><section class="grid"><article class="card"><div class="eyebrow">Pass 1 · implementation</div><h2>Preregistered before changes</h2><p>Created five distinct geological hypotheses and locked their mechanisms, signatures, non-fault mimics, repository differences, access caveats, lane, canaries, holdout, and stop rules. No hypothesis was run.</p></article>
<article class="card"><div class="eyebrow">Pass 2 · adversarial review</div><h2>Removed positive bypasses</h2><p>Made the current site generator, checker, and tests fail closed against the dense-witness stop; blocked the retired positive renderer and release-gate builders; retained lane-level negative evidence and shared-tool boundaries.</p></article>
<article class="card"><div class="eyebrow">Pass 3 · requirements check</div><h2>Rechecked sources and release claims</h2><p>Fetched official competition format/metric, rules, public leaderboard, GeoDAWN, GDR #1391, 3DEP, and Landsat pages. Confirmed the submission/data pages require login and flagged a deadline conflict. Updated the public-feed snapshot and rank parsing.</p></article></section>
<section><div class="section-head"><h2>Final status</h2></div><div class="card"><ul>
<li>Verdict: <strong>{esc(card['verdict'].upper())}</strong>; this review's candidate: none; raster SHA-256: null.</li>
<li>Pre-existing main-branch artifact: <code>{esc(prior.get('path', 'none'))}</code> (upstream SHA-256 <code>{esc(prior.get('upstream_recorded_sha256', 'none'))}</code>); not generated or assessed for science/format here, byte identity only, quarantined as research-only, and not cleared.</li>
<li>HOLDOUT-DTI: not run; no evaluator version, withheld-positive count, value, or CI is claimed.</li>
<li>Registry surface correlation: not run. The literal witness is positive on the entire mirrored sample footprint; a nonempty candidate would fail the directed overlap threshold at 100% under the documented rule.</li>
<li>Experiments: 0/3; experimental time: 0/2 hours; selector actions: 0; weekly slots: 0.</li>
<li>Latest saved public leaderboard capture (2026-10-29): rank 1 0.4544; rank 25 0.3330; rank 26 0.3328. Public-only, not a project score; no live refresh was available in this sandbox.</li>
<li>Latest repository identity check (2026-10-31): 9/9 focus-site GitHub HEADs fetched; all differ from the 2026-10-26 audit baseline. This is not a content or score re-audit.</li>
<li>Open decisions Q1 (dot definition) and Q2 (lattice comparator) remain unresolved; the literal stop remains active.</li>
</ul><p><a href="data/session_7393d521_run_card.json">Download project negative run card ↓</a> · <a href="data/preregistration_2026-10-28.json">Download preregistration JSON ↓</a> · <a href="data/official_source_check_2026-10-29.json">Download latest saved official-source audit ↓</a> · <a href="data/latest-upstream-check.json">Focus-site HEAD freshness ↓</a></p></div></section></div>'''


def submission_page() -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission status</div><h1>No file is cleared for a slot.</h1>
<p class="lede">One candidate (TWR-1r2, 2026-10-31) clears the format validator and the ratified uniqueness audit and may be downloaded for research; it fails the pre-registered holdout promotion bar, so it is not cleared for portal upload. The slot decision belongs to the account owner, informed by the run card on the executive summary.</p>{decision_panel()}</div></section>
<div class="wrap"><p><a href="executive-summary.html">Open the nine-site executive summary →</a> · <a href="how-to-submit.html">Read the future submission guide →</a></p></div>'''


def downloads_index() -> str:
    tifs = sorted(p.name for p in (DOCS / "downloads").glob("*.tif"))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"><title>Research archive status · GEMS Field Notes</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main class="wrap"><section class="hero"><div class="eyebrow">Historical archive</div><h1>Research downloads only.</h1>
<div class="decision"><strong>DO NOT SUBMIT.</strong><p>No current candidate is cleared. The literal dense-witness overlap exceeds the project stop. This index intentionally provides no direct TIFF download link.</p></div>
<p>There are {len(tifs)} historical TIFF file(s) physically retained in this folder for reproducibility. Their names and status are listed in <a href="LEGACY-DO-NOT-SUBMIT.txt">the archive notice</a>; all are not cleared. Do not upload them.</p>
<p><a class="btn secondary" href="../data/session_7393d521_run_card.json">Current negative run card</a> <a class="btn secondary" href="../executive-summary.html">Executive summary</a></p></section></main>
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


def build_gate(card: dict) -> dict:
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
                   LEADERBOARD_SNAPSHOT, LATEST_LEADERBOARD, OBS_1031_LEADERBOARD, UPSTREAM_CHECK, FOCUS,
                   ROOT / "evidence/official_source_check_2026-10-29.json",
                   ROOT / "evidence/session_2026-10-29_gate-recheck_run_card.json",
                   ROOT / "evidence/focus_measure_2026_10_31.json",
                   ROOT / "evidence/pair_identification.json", UNIQUE_SUBMISSION,
                   TWR1_CARD, TWR1_UNIQUE, TWR1_READBACK, TWR1_HOLDOUT, TWR1_CANARY,
                   ROOT / "evidence/twr1_e3_variants.json", ROOT / "evidence/hypotheses-2026-10-31.json"):
        shutil.copyfile(source, data / source.name)
    shutil.copyfile(PREREG_MD, data / "preregistration-2026-10-28.md")
    shutil.copyfile(REVIEW_MD, data / REVIEW_MD.name)
    shutil.copyfile(ROOT / "knowledge/review-2026-10-31.md", data / "review-2026-10-31.md")
    shutil.copyfile(ROOT / "knowledge/executive-summary-2026-10-31.md", data / "executive-summary-2026-10-31.md")
    shutil.copyfile(ROOT / "evidence/review_2026-10-31_run_card.json", data / "review_2026-10-31_run_card.json")
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
    decision = {
        "schema": "gems-project-decision-v1",
        "decision": "DO-NOT-SUBMIT",
        "okay_to_submit": False,
        "candidate": None,
        "source": "release_gate.json",
        "run_card": "session_7393d521_run_card.json",
        "run_card_sha256": digest(CURRENT_CARD),
        "reason": "Literal registry witness stop; no candidate or shared holdout run.",
    }
    (data / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def render() -> None:
    card = read_json(CURRENT_CARD)
    prereg = read_json(PREREG)
    source_check = read_json(OFFICIAL_SOURCES)
    focus = read_json(FOCUS)
    feed = read_json(LEADERBOARD)
    snapshot = read_json(LEADERBOARD_SNAPSHOT)  # immutable provenance for the existing gate
    latest_snapshot = read_json(LATEST_LEADERBOARD)
    upstream = read_json(UPSTREAM_CHECK)

    if (card.get("verdict") != "negative" or card.get("okay_to_submit") is not False
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
    if (read_json(OBS_1031_LEADERBOARD).get("observed_date_utc") != "2026-10-31"
            or read_json(OBS_1031_LEADERBOARD).get("visible_public_scores", {}).get("rank_1") != "0.4544"):
        raise ValueError("the 2026-10-31 leaderboard observation is missing or changed; re-review before publishing")
    if source_check.get("checked_date_utc") != "2026-10-28":
        raise ValueError("official source check date is not current for this review")
    if (latest_snapshot.get("observed_date_utc") != "2026-10-29"
            or latest_snapshot.get("visible_public_scores", {}).get("rank_26") != "0.3328"):
        raise ValueError("latest saved public leaderboard observation changed; re-review before publishing")
    if (len(upstream.get("repositories", [])) != 9
            or upstream.get("approved_for_submission") is not False):
        raise ValueError("focus-site identity feed is incomplete or does not fail closed")

    gate = build_gate(card)
    copy_site_data(card, prereg, focus, gate)

    # Historical candidate artifacts remain quarantined. Do not surface them as
    # downloadable candidates without a fresh candidate-specific selector approval.
    pages = {
        "index.html": ("Overview", index_page(feed, latest_snapshot, card, upstream)),
        "executive-summary.html": ("Executive summary", executive_page(focus, card, None)),
        "how-to-submit.html": ("Submission guide", submit_page(source_check, feed)),
        "research.html": ("Research hypotheses", hypothesis_page(prereg)),
        "method.html": ("Method and safeguards", method_page(card, prereg)),
        "evidence.html": ("Evidence and limitations", evidence_page(card, prereg, source_check, focus)),
        "session-review.html": ("Latest review", session_review_page(card, latest_snapshot)),
        "submission.html": ("Submission status", submission_page()),
    }
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(meta_page(title, name, body), encoding="utf-8")

    (DOCS / "downloads" / "index.html").write_text(downloads_index(), encoding="utf-8")
    tifs = sorted(p.name for p in (DOCS / "downloads").glob("*.tif"))
    notice = [
        "DO NOT SUBMIT — RESEARCH ARCHIVE ONLY",
        "No TIFF in this directory is cleared for competition upload.",
        "The project-wide literal-registry witness stop is active; local format checks or old lane results do not override it.",
        "This list is a file inventory, not an approval list:",
        *[f"  {name}" for name in tifs],
        "",
        "Current decision: docs/data/release_gate.json",
        "Current negative run card: docs/data/session_7393d521_run_card.json",
    ]
    (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").write_text("\n".join(notice) + "\n", encoding="utf-8")

    for directory, (title, card_name) in ARCHIVE_LANES.items():
        lane = DOCS / directory
        lane.mkdir(parents=True, exist_ok=True)
        pages = {lane / "index.html", *lane.rglob("*.html")}
        for page in sorted(pages):
            # Replace every old lane HTML surface, including nested download
            # indexes, so no superseded positive instructions remain reachable.
            page.write_text(archive_lane(directory, title, card_name, page), encoding="utf-8")
    (DOCS / "downloads" / "index.html").write_text(downloads_index(), encoding="utf-8")


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
    # The four top-level pages are owned by the release renderer, which publishes
    # whatever the machine-readable release card says (positive or negative).
    # It runs last so the published landing page can never contradict the card.
    from build_release_site import main as release_main
    release_main()
    print("Built legacy lane archives and the release pages from "
          "evidence/release/candidate_run_card.json.")
    return 0


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
