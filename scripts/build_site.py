#!/usr/bin/env python3
"""Render the evidence-first GEMS site from current, committed evidence.

This publisher is fail-closed: it never creates/promotes a candidate, authorizes
a TIFF download, or selects a competition slot. Historical lane files remain
quarantined and the rendered pages contain no direct TIFF/ZIP links.
"""
from __future__ import annotations

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

CURRENT_CARD = ROOT / "evidence/session_2026-10-31_run_card.json"
LEGACY_CARD = ROOT / "evidence/session_7393d521_run_card.json"
WITNESS = ROOT / "evidence/registry_witness_recheck_2026-10-27.json"
PREREG = ROOT / "evidence/preregistration_2026-10-31.json"
PREREG_MD = ROOT / "knowledge/preregistration-2026-10-31.md"
OFFICIAL_SOURCES = ROOT / "evidence/official_source_check_2026-10-31.json"
LEADERBOARD = ROOT / "registry/leaderboard.json"
LEADERBOARD_SNAPSHOT = ROOT / "evidence/leaderboard_observation_2026-10-31.json"
FOCUS = ROOT / "evidence/focus_audit.json"
REVIEW_MD = ROOT / "knowledge/review-2026-10-31.md"
UPSTREAM = ROOT / "evidence/latest-upstream-check.json"
WHY_032 = ROOT / "content/why-0.2778.md"

FOCUS_ORDER = (
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
)
ARCHIVE_LANES = {
    "hce": ("HCE-1", "hce_run_card.json"),
    "cspes": ("CSPES", "cspes_run_card.json"),
    "fchd": ("FCHD-NCM", "fchd_run_card.json"),
    "lst1": ("LST1", "lst1_run_card.json"),
    "lbcal": ("LBCAL", "lbcal_run_card.json"),
    "rfl": ("RFL", "rfl_run_card.json"),
    "session-1f0b051d": ("Dipole hybrid", "session_1f0b051d_run_card.json"),
    "thcs": ("THCS-OOF", "thcs_run_card.json"),
}
CORE_PAGES = (
    "index.html", "executive-summary.html", "how-to-submit.html", "research.html",
    "method.html", "evidence.html", "session-review.html", "submission.html",
)
PUBLISHED_DATA_ALLOWLIST = {
    "session_2026-10-31_run_card.json", "session_7393d521_run_card.json", "run_card.json",
    "decision.json", "release_gate.json", "registry_witness_recheck_2026-10-27.json",
    "preregistration_2026-10-31.json", "preregistration-2026-10-31.md",
    "official_source_check_2026-10-31.json", "leaderboard_observation_2026-10-31.json",
    "leaderboard.json", "latest-upstream-check.json", "focus_audit.json", "focus_estimates.json",
    "why-0.2778.md", "h6_1_proximity_pruning_holdout.json", "master_audit_2026-10-27.json",
    "review-2026-10-31.md",
    "hce_run_card.json", "cspes_run_card.json", "fchd_run_card.json", "lst1_run_card.json",
    "lbcal_run_card.json", "rfl_run_card.json", "session_1f0b051d_run_card.json", "thcs_run_card.json",
    "amdc_run_card.json", "sgce_bytes_audit.json", "amdc_ranking.json", "amdc_paired.json",
    "amdc_projection.json", "amdc_exps.json", "amdc_canary.json", "amdc_uniqueness_remeasured.json",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def esc(value) -> str:
    return html.escape(str(value), quote=True)


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
<main>{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData ·
<a href="data/decision.json">Machine-readable decision</a> · 0 portal slots used in this review.</div></footer></body></html>'''


def decision_panel() -> str:
    return '''<div class="decision"><span class="tag">NEGATIVE · FAIL CLOSED</span>
<h2>DO NOT DOWNLOAD OR SUBMIT — no file is cleared.</h2>
<p>This review generated no TIFF and no candidate is safe to download for submission. No geological experiment, holdout, or slot selection was run. The literal registered-witness stop is active, the method lane is unassigned, and the shared cache/runtime is unavailable. Historical TIFFs are research archives only.</p>
<p><a class="btn secondary" href="downloads/index.html">View research-archive status</a>
<a class="btn secondary" href="data/session_2026-10-31_run_card.json">Read the current negative run card</a></p></div>'''


def leaderboard_panel(feed: dict, snapshot: dict) -> str:
    ranks = snapshot["visible_public_scores"]
    date = snapshot["observed_date_utc"]
    auto = feed.get("automated_refresh_status", "not reported")
    captured = feed.get("captured_ranks", {})
    if captured.get("1"):
        auto_text = (
            f"Last successful automated fragment ({feed.get('last_success_utc', 'time unknown')}): "
            f"rank 1 {captured.get('1', 'n/a')}, rank 2 {captured.get('2', 'n/a')}, "
            f"rank 25 {captured.get('25', 'n/a')}, rank 26 {captured.get('26', 'n/a')}, "
            f"rank 48 {captured.get('48', 'n/a')}. Latest refresh status: {auto}."
        )
    else:
        auto_text = f"Automated fragment refresh status: {auto}."
    return f'''<article class="card"><div class="small">Official public leaderboard · dated observation only, not our score</div>
<div class="metric">{esc(ranks['rank_1'])}</div>
<div class="small">Rank 1 in the manual page capture on {esc(date)} · exact capture time unavailable</div>
<p>That capture also shows rank 2: <strong>{esc(ranks['rank_2'])}</strong> · rank 25: <strong>{esc(ranks['rank_25'])}</strong> ·
rank 26: <strong>{esc(ranks['rank_26'])}</strong> · rank 50: <strong>{esc(ranks['rank_50'])}</strong>.
In this capture, 0.3195 is rank 50, not the leader. These are public scores for other entries, not a project-file result or receipt.
<strong>{esc(auto_text)}</strong>
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open official leaderboard ↗</a>
· <a href="data/leaderboard_observation_2026-10-31.json">dated snapshot ↓</a>
· <a href="data/leaderboard.json">feed record ↓</a></p></article>'''


def upstream_panel(upstream: dict) -> str:
    rows = upstream.get("repositories", [])
    fetched = sum(row.get("fetch_status") == "FETCHED" for row in rows)
    changed = sum(row.get("comparison_to_baseline") == "CHANGED" for row in rows)
    unknown = len(rows) - fetched
    return f'''<article class="card"><div class="eyebrow">Focus-site source freshness</div>
<h2>{changed} changed · {fetched}/9 fetched · {unknown} failed/unknown</h2>
<p>GitHub <code>main</code> HEAD identities checked {esc(upstream.get('checked_at', 'unknown'))}; all nine differ from their 2026-10-26 audit baseline. This identity monitor does not prove a score, TIFF, receipt, or that the pinned prediction bytes changed.</p>
<p><a href="data/latest-upstream-check.json">Open per-site HEAD and baseline record ↓</a></p></article>'''


def focus_table(focus: dict) -> str:
    rows = {row["site"]: row for row in focus["focus_sites"]}
    body = []
    for site in FOCUS_ORDER:
        row = rows[site]
        overlap = 100.0 * float(row["max_focus_overlap"])
        comparator = row.get("max_focus_overlap_site") or "another focus file"
        body.append(f'''<tr><td><strong>{esc(site)}</strong></td>
<td><code>{esc(row['filename'])}</code><small>historical research reference; no direct download link</small></td>
<td><strong>OWNER-REPORTED {esc(row['claimed_by_owner_not_receipt'])}</strong><small>not an organizer receipt</small></td>
<td><strong>NOT ESTIMABLE</strong><small>no validated score-calibration model</small></td>
<td><strong>No</strong><small>{overlap:.1f}% 3-px overlap with {esc(comparator)} in this focus set; global literal stop also applies</small></td>
<td><span class="tag">DO NOT SUBMIT</span></td></tr>''')
    return '''<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>Historical file (not approved for download)</th><th>Reported score</th>
<th>Estimated score</th><th>Unique?</th><th>Decision</th></tr></thead><tbody>''' + "".join(body) + "</tbody></table></div>"


def historical_h6_section() -> str:
    """Render the scoped H6-1 proxy without extrapolating it to GEMSDOE32."""
    h = read_json(ROOT / "evidence/h6_1_proximity_pruning_holdout.json")
    unpruned = h["scores"]["unpruned"]
    pruned = h["scores"]["proximity_prune"]
    random_delta = h["paired_differences"]["random_prune"]
    nearest = h["holdout_scope_limitation"]["nearest_visible_to_any_withheld_truth_px"]
    return f'''<section><div class="section-head"><div class="eyebrow">Historical holdout · scoped proxy only</div>
<h2>A small proxy result cannot explain a public owner report</h2></div><div class="card">
<p>This is prior HOLDOUT-DTI evidence, not run or independently replayed here, from evaluator <code>{esc(h['evaluator_version'])}</code> with {unpruned['withheld_positive_pixels']:,} withheld positive pixels. Unpruned: {unpruned['dti']:.5f} [{unpruned['ci95'][0]:.5f}, {unpruned['ci95'][1]:.5f}]; 2-px proximity-pruned: {pruned['dti']:.5f} [{pruned['ci95'][0]:.5f}, {pruned['ci95'][1]:.5f}].</p>
<p>The proxy's paired gain over random pruning is {random_delta['delta']:+.6f} [{random_delta['ci95'][0]:+.6f}, {random_delta['ci95'][1]:+.6f}], whose interval crosses zero. Its nearest withheld truth was {nearest:.3f} px from visible catalogue context; there was <strong>no withheld truth within 3 pixels</strong>. Therefore the proxy does not test GEMSDOE32's near-catalogue regime and cannot prove or disprove why its owner-reported score was 0.2778.</p>
<p><a href="data/h6_1_proximity_pruning_holdout.json">Read the scoped historical holdout card ↓</a></p></div></section>'''


def index_page(feed: dict, snapshot: dict, focus: dict, upstream: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS · executive decision · 2026-10-31</div>
<h1>Maximize P(Win). Own the Outcome.</h1>
<p class="lede">Evidence first: protect the competition slot, keep every claim auditable, and treat a negative finding as a useful deliverable.</p>
{decision_panel()}
<div class="grid">
<article class="card"><div class="small">This review</div><div class="metric">0 candidates</div><p>No new TIFF, holdout score, or slot action.</p></article>
{leaderboard_panel(feed, snapshot)}
<article class="card"><div class="small">Organizer-confirmed project scores</div><div class="metric">None</div><p>No receipt is present in the repository.</p></article>
</div></div></section>
<div class="wrap"><section><div class="section-head"><div class="eyebrow">Focus-site review</div>
<h2>Nine historical claims, no submission recommendation</h2>
<p>Every score below is an owner/user report without a verified receipt. Historical filenames are references only; none is an approved download.</p></div>
{focus_table(focus)}
<p class="small">GEMSDOE32's reported 0.2778 has a plausible byte-level pruning explanation, not a verified causal explanation. No focus-site score estimate is validated.</p></section>
<section><div class="grid"><article class="card"><h3>Why generation stopped</h3>
<p>The registered owner-mirrored witness is positive across the mirrored sample footprint. Under the current literal support rule, any nonempty in-footprint dot set would exceed the 70% overlap stop. This is conditional on mirrored bytes, not organizer provenance or a complete authenticated portal-registry census.</p>
<a href="evidence.html">Read the evidence and caveats →</a></article>
<article class="card"><h3>Research plan</h3><p>Three distinct, untested hypotheses are ranked with mechanisms, mimics, cost, and data-access status. None was run because the lane is unassigned and the stop is active.</p><a href="research.html">Read the preregistration →</a></article>
<article class="card"><h3>Official-source checks</h3><p>The competition metric/format, current public leaderboard, USGS heat-flow and GeoDAWN records, GDR #1391, ComCat API, Landsat, and ECOSTRESS pages were checked or explicitly carried forward with dates and access limitations.</p><a href="data/official_source_check_2026-10-31.json">Open source audit JSON ↓</a></article></div></section>
<section>{upstream_panel(upstream)}</section>
<section><div class="card"><h2>Historical lane archives — research only</h2><p>Every archived lane inherits the current DO NOT SUBMIT decision. Historical scores and format passes are not project-level clearance.</p><p><a href="hce/index.html">HCE →</a> · <a href="thcs/index.html">THCS →</a> · <a href="lst1/index.html">LST1 →</a> · <a href="lbcal/index.html">LBCAL →</a> · <a href="fchd/index.html">FCHD →</a> · <a href="amdc/index.html">AMDC →</a> · <a href="rfl/index.html">RFL →</a> · <a href="cspes/index.html">CSPES →</a></p></div></section>
<section><div class="decision"><strong>Deadline/account status:</strong> a previously recorded discrepancy between the competition homepage and official rules was not rechecked on 2026-10-31. Recheck the current official pages before any future selector action. The authenticated account quota remains unknown.</div></section>
<p class="small">Current negative run card: <a href="data/session_2026-10-31_run_card.json"><code>session_2026-10-31_run_card.json</code> ↓</a> ·
<a href="data/release_gate.json">release gate ↓</a> · <a href="session-review.html">three-pass review →</a></p></div>'''


def executive_page(focus: dict, card: dict) -> str:
    why = card["gemsdoe32_explanation"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary · current review</div>
<h1>Nine sites reviewed · no eligible TIFF</h1>
<p class="lede">No file is safe to download or submit. Owner-reported scores are historical claims without organizer receipts; the current review generated no candidate.</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Requested focus sites</h2><p>Names and reports below are historical references, not approved download links.</p></div>{focus_table(focus)}
<p class="small">“NOT ESTIMABLE” is deliberate: no validated calibration from these historical owner reports to an independent holdout or organizer score is available.</p></section>
<section><div class="section-head"><div class="eyebrow">GEMSDOE32 · reported 0.2778</div><h2>Evidence-bounded explanation</h2></div>
<div class="grid"><article class="card"><h3>What is reported</h3><p><strong>OWNER-REPORTED {why['reported_score']:.4f}</strong>; no receipt ties the value to the exact bytes or hidden labels.</p></article>
<article class="card"><h3>What the saved bytes show</h3><p>{esc(why['finding'])}</p></article>
<article class="card"><h3>What could explain it</h3><p>{esc(why['mechanism_status'])}</p></article></div>
<p class="small">This remains a plausible mechanism, not a verified causal account of the reported score.</p>
<p><a href="data/why-0.2778.md">Full evidence and limitations ↓</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official metric description ↗</a></p></section>
{historical_h6_section()}
<section><div class="section-head"><h2>What would have to happen before another TIFF</h2></div><div class="card"><ol>
<li>Obtain the missing assigned method-lane paragraph; do not infer one.</li>
<li>Resolve the literal registry stop through documented, evidence-based protocol clarification. Do not silently waive it or invent a dense-raster exemption.</li>
<li>Restore and verify the shared cache, evaluator, and writer. Use only the shared tooling; remain in the assigned lane.</li>
<li>Before placement, measure surface rank correlation; stop if |Spearman| &gt;0.90. Stop if &gt;70% of final dots lie within 3 px of any registry raster.</li>
<li>Only after eligibility, run per-feature leakage canaries and the whole-segment buffered holdout. Report evaluator version, withheld positives, 95% CI, and matched baseline.</li>
<li>Validate exact saved bytes against the official format contract. A separate selector—not this research lane—must review the live portal cap and approve a real slot.</li>
</ol><p>No slot was selected. Any future submission note must be ≤140 characters. The prior portal error “Predicted values must be in range [0, 1]” remains unexplained; no local test proves portal acceptance.</p></div></section></div>'''


def hypothesis_page(prereg: dict) -> str:
    cards = []
    for h in prereg["hypotheses"]:
        cards.append(f'''<article class="card"><div class="eyebrow">Rank {h['rank']} · {esc(h['id'])} · NOT TESTED</div>
<h2>{esc(h['name'])}</h2><p><strong>Layers:</strong> {esc('; '.join(h['layers']))}</p>
<p><strong>Mechanism:</strong> {esc(h['mechanism'])}</p><p><strong>Signature:</strong> {esc(h['physical_signature'])}</p>
<p><strong>Why uncatalogued:</strong> {esc(h['uncatalogued_fault_rationale'])}</p>
<p><strong>Named non-fault mimic:</strong> {esc(h['named_non_fault_mimic'])}</p>
<p><strong>Different from existing code:</strong> {esc(h['difference_from_repository'])}</p>
<p><strong>Expected gain vs cost:</strong> {esc(h['expected_gain_vs_cost'])}</p>
<p class="small"><strong>Implementation cost/access:</strong> {esc(h['implementation_cost'])}; {esc(h['data_access_status'])}</p>
<p class="small"><strong>Eligibility:</strong> {esc(h['validation_status'])}</p></article>''')
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Preregistered research only · 2026-10-31</div>
<h1>Three distinct, untested candidates</h1>
<p class="lede">Ranks express qualitative expected research value relative to cost. They are not DTI estimates, score projections, or submission choices.</p>
<div class="decision"><strong>DO NOT SUBMIT. No candidate is eligible.</strong> The assigned lane is absent, the literal-registry stop is active, and the shared cache/runtime is not restored.</div>
<p><a href="data/preregistration_2026-10-31.json">Machine-readable preregistration ↓</a> · <a href="data/preregistration-2026-10-31.md">Full preregistration ↓</a> · <a href="method.html">Locked evaluation protocol →</a></p></div></section>
<div class="wrap"><section><div class="card"><h2>Novelty correction</h2><p>Do not relabel GDR #1391 2 m probes, sinter/tufa, well/spring temperatures, silica/cation geothermometry, or vent proximity as new: active THCS/FCHD code already uses them. Previously proposed Landsat, ECOSTRESS, simple focal-mechanism clustering, and raw GeoDAWN crossover ideas are also not counted as new candidates here.</p></div></section>
<section class="grid">{''.join(cards)}</section></div>'''


def method_page(card: dict, prereg: dict) -> str:
    witness = prereg["global_stop"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Method and release rules</div>
<h1>Trust bytes, not projections.</h1><p class="lede">The only acceptable score labels are HOLDOUT-DTI (with evaluator details and CI) or ORGANIZER-CONFIRMED (with a verifiable receipt).</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Official DTI and raster contract</h2><p>Rechecked from the official problem page on 2026-10-31.</p></div><div class="card">
<p>The competition uses distance-weighted Tversky with α=0.2, β=0.8, and a 300 m triangular support kernel. The official task is fault prediction; it is not a geothermal-vent label task.</p>
<p>The published format requires one float32 GeoTIFF band, EPSG:32611, 100 m, matching bounds, values in [0,1], and null/NaN outside the stated bounds. These written requirements do not prove portal acceptance.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description ↗</a></p></div></section>
<section><div class="section-head"><h2>Parallel-run and leakage protocol</h2></div><div class="card"><ol>
<li>Remain in one explicitly assigned method lane and reuse the shared cached feature stack, <code>evaluate_holdout.py</code>, and <code>submission_writer.py</code>. Never fork shared tools. The current lane is unassigned.</li>
<li>Before placement, check surface rank correlation against every registry raster; stop if |Spearman| &gt;0.90. After placement, stop and log a duplicate if more than 70% of final dots are within 3 px of any registry raster.</li>
<li>Hold out whole fault segments with a buffer; derive catalogue features only from visible faults; pixel-exactly mask visible faults; pool DTI using α=0.2, β=0.8, and a 300 m triangular kernel.</li>
<li>Test every feature alone for leakage. AUC &gt;0.90 is leakage until an independent explanation is established.</li>
<li>Every actual score needs evaluator version, withheld-positive count, and 95% CI. Public leaderboard values and model projections are separate; a projection is never a score.</li>
<li>Stop after three geological experiments or two hours. No real slot selection in this lane; a separate selector checks the live cap.</li>
</ol></div></section>
<section><div class="section-head"><h2>Current literal witness stop</h2></div><div class="card"><p>Witness SHA-256 <code>{witness['witness_sha256']}</code> is recorded as positive on {witness['witness_positive_cells']:,} of {witness['mirrored_sample_footprint_cells']:,} cells in the owner-mirrored footprint. Under the documented finite-and-positive rule, a nonempty in-footprint candidate has conditional directed overlap 100%, above the 70% threshold.</p>
<p>The finding is conditional on mirrored bytes and the registry entry. It does not authenticate organizer provenance or prove a complete portal registry. The protocol still requires stopping.</p>
<p><a href="data/registry_witness_recheck_2026-10-27.json">Saved witness measurement ↓</a> · <a href="data/session_2026-10-31_run_card.json">Current negative run card ↓</a></p></div></section>
<section><div class="section-head"><h2>Runtime and candidate status</h2></div><div class="card"><p>Shared cached feature stack: <strong>not present</strong>. Shared evaluator/writer runtime: <strong>not restored or verified for an assigned lane</strong>. Historical repository copies are not a substitute.</p>
<p>Current card status: <strong>{esc(card['holdout_dti']['status'])}</strong>; no DTI value, CI, or withheld-positive count is asserted. No candidate TIFF was created and no validator was run.</p></div></section>
<section><p><a href="data/official_source_check_2026-10-31.json">Official-source check ↓</a> · <a href="research.html">Preregistered hypotheses →</a></p></section></div>'''


def submit_page(source_check: dict, feed: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission guide</div>
<h1>No submission is authorized.</h1><p class="lede">There is no current candidate file. Do not download or submit any historical TIFF.</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Current file and slot status</h2></div><div class="card"><p><strong>File to upload:</strong> none. <strong>Safe download:</strong> none. <strong>Slot selected/used:</strong> no / 0.</p>
<p>The competition's written contract is a single-band float32 GeoTIFF, EPSG:32611, 100 m, matching bounds, values in [0,1], and null/NaN outside. Local format validity alone does not establish a score, uniqueness, or portal acceptance.</p></div></section>
<section><div class="section-head"><h2>Future steps, only after every gate clears</h2></div><div class="card"><ol class="steps">
<li>Obtain the assigned method-lane paragraph and resolve the literal registry stop through documented, evidence-based protocol clarification.</li>
<li>Restore and verify the shared cache, `evaluate_holdout.py`, and `submission_writer.py`; do not use a private fork.</li>
<li>Before placement, check surface rank correlation; stop if |Spearman| &gt;0.90. Stop if more than 70% of final dots fall within 3 px of any registry raster.</li>
<li>Run each feature's leakage canary, then a whole-fault-segment buffered holdout with visible-only catalogue features and pixel-exact masking. Report the shared evaluator version, withheld-positive count, and 95% CI.</li>
<li>For exact saved bytes, validate dtype, band count, CRS, shape, transform, bounds, finite/range constraints, and outside-footprint encoding. Hash the final file and preserve the validator report.</li>
<li>A separate selector checks current account quota/usage and approves a slot. Only then upload the approved exact file, use the recorded submission name/note (≤140 characters), and keep the receipt with the file hash.</li>
</ol><p>Submission-page access and current quota are not available in this review. No note or filename is assigned without a candidate.</p></div></section>
<section><div class="section-head"><h2>Official links and access limits</h2></div><div class="card"><p>The latest saved public-leaderboard observation is {esc(feed.get('last_success_utc', 'unknown'))}; it is not a project score. The 2026-10-31 source audit records the official-page checks and their limitations, including that rules/deadline details were carried forward from 2026-10-29 and not rechecked today.</p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition home ↗</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description ↗</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF ↗</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Submission portal (login may be required) ↗</a> ·
<a href="data/official_source_check_2026-10-31.json">Source/access audit ↓</a></p></div></section></div>'''


def evidence_page(card: dict, prereg: dict, source_check: dict, focus: dict) -> str:
    witness = prereg["global_stop"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Evidence and limitations</div>
<h1>A measurable stop, not a score.</h1><p class="lede">Every claim has an evidence class; owner-mirror identity is not organizer provenance.</p>{decision_panel()}</div></section>
<div class="wrap"><section><div class="section-head"><h2>Literal registry witness</h2><p>Hash-pinned owner mirrors; not a complete authenticated portal-registry audit.</p></div>
<div class="grid"><article class="card"><h3>Witness raster</h3><p>SHA-256 <code>{witness['witness_sha256']}</code>; {witness['witness_positive_cells']:,}/{witness['mirrored_sample_footprint_cells']:,} footprint cells positive under the recorded support definition.</p><p>Conditional directed overlap for a nonempty in-footprint candidate: <strong>100%</strong>, above the 70% limit. No surface correlation was run because no candidate surface exists.</p></article>
<article class="card"><h3>No experiment / no holdout</h3><p>0 geological experiments; no candidate raster; no holdout value or CI; no candidate-specific leakage canary or validator; no slot selected. The lane is unassigned and shared cache/runtime unavailable.</p></article>
<article class="card"><h3>Provenance and scope</h3><p>The witness and sample are public owner mirrors. The measurement is conditional on that registry entry and does not prove organizer provenance or current complete portal-registry coverage.</p></article></div>
<p><a href="data/registry_witness_recheck_2026-10-27.json">Witness measurement JSON ↓</a> · <a href="data/session_2026-10-31_run_card.json">Current run card ↓</a> · <a href="data/release_gate.json">Release gate ↓</a></p></section>
<section><div class="section-head"><h2>GEMSDOE32 reported 0.2778</h2></div><div class="card"><p>The saved byte/mask audit reports B2 as a 37,654-cell subset of a 40,199-cell H27-4 base, with 2,545 cells removed near a mirrored catalogue. Tversky metric arithmetic makes it plausible that pruning low-credit predictions could reduce false-positive mass, but hidden labels and a receipt are absent; this is not a verified causal account of 0.2778.</p><p>The focus-site values are owner/user reports. The 2026-10-31 public leaderboard leader is a public score for a different entry, not a score for any file here.</p><p><a href="data/why-0.2778.md">Full GEMSDOE32 analysis ↓</a> · <a href="data/focus_audit.json">Focus-site byte audit ↓</a></p></div></section>
<section><div class="section-head"><h2>Official-source verification</h2></div><div class="card"><p>Competition metric/format, current public leaderboard, USGS Great Basin heat-flow and GeoDAWN records, DOE GDR #1391, the USGS ComCat API, Landsat Collection 2, and ECOSTRESS pages were fetched on 2026-10-31. Rules/deadline and portal-access observations are clearly carried forward from 2026-10-29, not rechecked today.</p><p>External page listings do not prove local archive download, file schema, exact AOI coverage, an organizer receipt, or a candidate score.</p><p><a href="data/official_source_check_2026-10-31.json">Download current source audit ↓</a> · <a href="data/leaderboard_observation_2026-10-31.json">Download dated leaderboard snapshot ↓</a></p></div></section>
<section><div class="section-head"><h2>Historical scores and files</h2></div><div class="card"><p>The focus-site table shows owner reports and pinned historical filenames. None is an approved submission. The downloads index provides no direct TIFF or ZIP links; old files remain quarantined for audit.</p><p><a href="data/focus_audit.json">Nine-site byte audit ↓</a> · <a href="data/focus_estimates.json">Retired historical projections (not scores) ↓</a> · <a href="downloads/index.html">Research-archive status →</a></p></div></section>
<section><div class="section-head"><h2>Reproduce software checks</h2></div><div class="card"><p>Install <code>requirements.txt</code>, run <code>python scripts/build_site.py</code>, <code>python scripts/check_site.py</code>, and <code>python -m pytest -q</code>. These checks validate repository/site consistency, not geological performance or portal acceptance.</p><p><a href="session-review.html">Three-pass review record →</a> · <a href="data/preregistration-2026-10-31.md">Preregistration and safeguards ↓</a></p></div></section></div>'''


def session_review_page(card: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Latest review · {esc(card['review_date_utc'])}</div>
<h1>Negative preflight. Zero experiments.</h1><p class="lede">Three passes reconciled the task, evidence, active publisher/checker, and release safeguards.</p>{decision_panel()}</div></section>
<div class="wrap"><section class="grid"><article class="card"><div class="eyebrow">Pass 1 · evidence and hypotheses</div><h2>Corrected novelty and source claims</h2><p>Reviewed the nine pinned focus files, checked active THCS/FCHD features, excluded already-implemented GDR layers from novelty claims, and ranked three source-specific untested hypotheses. No hypothesis was tested.</p></article>
<article class="card"><div class="eyebrow">Pass 2 · code and publication safety</div><h2>Removed stale candidate paths</h2><p>Updated the active site generator/checker to fail closed, remove direct candidate TIFF/ZIP links, label archived files as research-only, bind the current negative card to the gate, and keep the FCHD publisher from restoring old downloads.</p></article>
<article class="card"><div class="eyebrow">Pass 3 · requirements and checks</div><h2>Refreshed the dated evidence</h2><p>Recorded the official 2026-10-31 leaderboard page capture, checked official source pages/listings, documented access and coverage gaps, and reran repository/site tests. The exact leaderboard-fetch time was not exposed.</p></article></section>
<section><div class="section-head"><h2>Final status</h2></div><div class="card"><ul>
<li>Verdict: <strong>{esc(card['verdict'].upper())}</strong>; no new candidate or raster SHA-256.</li>
<li>HOLDOUT-DTI: not run; no evaluator version, withheld-positive count, value, or CI is claimed.</li>
<li>Pre-placement surface correlation: not run; there is no candidate surface. Final-dot overlap: not run; there are no candidate dots.</li>
<li>The literal owner-mirror witness stop remains at conditional 100% directed overlap for a nonempty in-footprint candidate.</li>
<li>Lane: unassigned. Experiments: 0/3; time: 0/2 hours; selector actions: 0; weekly slots: 0.</li>
<li>Public leaderboard capture (2026-10-31): rank 1 0.4544; rank 2 0.3925; rank 50 0.3195. Public-only, not a project score.</li>
</ul><p><a href="data/session_2026-10-31_run_card.json">Current negative run card ↓</a> · <a href="data/preregistration_2026-10-31.json">Preregistration JSON ↓</a> · <a href="data/official_source_check_2026-10-31.json">Official-source audit ↓</a> · <a href="data/review-2026-10-31.md">Three-pass review record ↓</a></p></div></section></div>'''


def submission_page() -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission status</div><h1>No file is cleared.</h1>
<p class="lede">This page intentionally provides no prediction download. No candidate TIFF was generated in this review.</p>{decision_panel()}</div></section>
<div class="wrap"><p><a href="executive-summary.html">Open the nine-site executive summary →</a> · <a href="how-to-submit.html">Read the future submission guide →</a></p></div>'''


def downloads_index() -> str:
    artifacts = sorted(p.name for p in (DOCS / "downloads").iterdir()
                       if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"})
    tifs = [name for name in artifacts if Path(name).suffix.lower() in {".tif", ".tiff"}]
    zips = [name for name in artifacts if Path(name).suffix.lower() == ".zip"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"><title>Research archive status · GEMS Field Notes</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main class="wrap"><section class="hero"><div class="eyebrow">Historical archive</div><h1>Research files only — not cleared.</h1>
<div class="decision"><strong>DO NOT DOWNLOAD FOR SUBMISSION OR SUBMIT.</strong><p>No current candidate exists. The literal registry stop remains active. This index intentionally provides no direct TIFF or ZIP download link.</p></div>
<p>{len(tifs)} historical TIFF(s) and {len(zips)} ZIP bundle(s) are physically retained here for reproducibility; their names are inventoried in <a href="LEGACY-DO-NOT-SUBMIT.txt">the archive notice</a>. These bytes are not cleared for competition use.</p>
<p><a class="btn secondary" href="../data/session_2026-10-31_run_card.json">Current negative run card</a> <a class="btn secondary" href="../executive-summary.html">Executive summary</a></p></section></main>
<footer class="footer"><div class="wrap">Historical bytes are not an upload recommendation.</div></footer></body></html>'''


def archive_lane(directory: str, title: str, card: str, page: Path | None = None) -> str:
    page = page or (DOCS / directory / "index.html")
    depth = len(page.parent.relative_to(DOCS).parts)
    up = "../" * depth
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · historical research</title><link rel="stylesheet" href="{up}assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="{up}index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main><section class="hero"><div class="wrap"><div class="eyebrow">Research only · historical lane · {esc(title)}</div>
<h1>Research archive, not a release.</h1><div class="decision"><strong>Global release gate: DO NOT SUBMIT.</strong><p>No competition file is cleared. Do not submit any file. Do not download any lane artifact.</p></div>
<p>The current literal witness implies <strong>100% witness overlap</strong> for nonempty in-footprint dots under the recorded support definition. This is a conditional owner-mirror measurement, not a full authenticated portal registry. Prior lane results are historical research records. Their local holdout or format results cannot override the current project-level stop. Local format checks do not prove portal acceptance or substitute for a receipt.</p>
<p><a class="btn secondary" href="{up}data/{esc(card)}">Historical lane card</a> <a class="btn" href="{up}executive-summary.html">Current executive summary</a></p>
<p class="small">This is a research-only archive page with no direct TIFF or ZIP download link. See <a href="{up}downloads/index.html">research-archive status</a>.</p></div></section></main></body></html>'''


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
    gate["decision_scope"] = "Project-wide status for the 2026-10-31 review; no candidate was created, no experiment was run, and no slot was selected."
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
        "The literal owner-mirror witness stop is active: any nonempty in-footprint candidate has 100% conditional directed overlap under the documented support rule, above the 70% threshold.",
        "The assigned single method lane paragraph is absent; no lane was inferred.",
        "The shared cached feature stack and assigned shared evaluator/writer runtime are unavailable or unverified.",
        "No candidate raster, byte hash, submission name, surface correlation, or final-dot overlap exists in this review.",
        "No compliant shared-tool HOLDOUT-DTI, leakage canary, evaluator version, withheld-positive count, or 95% CI was run.",
        "No separate selector approval exists; no weekly slot was selected or spent.",
        "The registry witness and competition inputs are owner mirrors; organizer provenance and complete portal-registry coverage are not authenticated.",
    ]
    gate["okay_to_submit"] = False
    gate["okay_to_download_for_research"] = False
    return gate


def copy_site_data(card: dict, prereg: dict, focus: dict, gate: dict) -> None:
    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    sources = (
        CURRENT_CARD, LEGACY_CARD, WITNESS, PREREG, OFFICIAL_SOURCES, LEADERBOARD,
        LEADERBOARD_SNAPSHOT, FOCUS, ROOT / "evidence/h6_1_proximity_pruning_holdout.json",
        ROOT / "evidence/master_audit_2026-10-27.json", UPSTREAM, WHY_032,
    )
    for source in sources:
        if source.is_file():
            shutil.copyfile(source, data / source.name)
    shutil.copyfile(PREREG_MD, data / "preregistration-2026-10-31.md")
    shutil.copyfile(REVIEW_MD, data / "review-2026-10-31.md")
    shutil.copyfile(ROOT / "evidence/focus_estimates_retired_2026-10-31.json", data / "focus_estimates.json")

    for _, (_, card_name) in ARCHIVE_LANES.items():
        source_card = ROOT / "evidence" / card_name
        if source_card.is_file():
            historical = read_json(source_card)
            historical["_archive_notice"] = (
                "Historical lane record only. It does not override the current project-level "
                "DO-NOT-SUBMIT decision or authorize a portal upload."
            )
            (data / card_name).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    shutil.copyfile(CURRENT_CARD, data / "run_card.json")
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    decision = {
        "schema": "gems-project-decision-v1",
        "decision": "DO-NOT-SUBMIT",
        "okay_to_submit": False,
        "candidate": None,
        "source": "release_gate.json",
        "run_card": CURRENT_CARD.name,
        "run_card_sha256": digest(CURRENT_CARD),
        "reason": "Literal registry witness stop, missing lane assignment, and unavailable shared runtime; no candidate or holdout run.",
    }
    (data / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    # Remove the prior candidate card copy from the site. The source evidence remains in evidence/.
    old_unique_copy = data / "unique_submission_run_card.json"
    if old_unique_copy.exists():
        old_unique_copy.unlink()


def prune_published_data() -> None:
    """Remove unlinked legacy JSON copies from the Pages output.

    The full historical evidence remains under evidence/ in the repository. The
    public site exposes only current negative evidence and explicitly quarantined
    lane cards; stale promoted/submit-ready cards and old score projections are
    not left accessible under docs/data/.
    """
    data = DOCS / "data"
    for path in data.iterdir():
        if path.is_file() and path.name not in PUBLISHED_DATA_ALLOWLIST:
            path.unlink()


def render() -> None:
    card = read_json(CURRENT_CARD)
    prereg = read_json(PREREG)
    source_check = read_json(OFFICIAL_SOURCES)
    focus = read_json(FOCUS)
    feed = read_json(LEADERBOARD)
    snapshot = read_json(LEADERBOARD_SNAPSHOT)

    if (card.get("verdict") != "negative" or card.get("okay_to_submit") is not False
            or card.get("okay_to_download_for_submission") is not False
            or card.get("raster", {}).get("generated") is not False
            or card.get("raster", {}).get("sha256") is not None
            or card.get("holdout_dti", {}).get("status") != "BLOCKED_BEFORE_EXPERIMENT"
            or card.get("experiments", {}).get("geological_experiments_completed") != 0
            or card.get("selector", {}).get("weekly_slots_used") != 0
            or card.get("lane_assignment", {}).get("assigned") is not False):
        raise ValueError("current run card is not a fail-closed, unassigned, no-candidate record")
    witness = prereg.get("global_stop", {})
    if (witness.get("active") is not True
            or witness.get("witness_positive_cells") != witness.get("mirrored_sample_footprint_cells")
            or witness.get("conditional_candidate_directed_overlap_if_nonempty_in_footprint") != 1.0):
        raise ValueError("the current literal-registry witness/stop evidence is missing or changed")
    hypotheses = prereg.get("hypotheses", [])
    if len(hypotheses) not in (3, 4, 5):
        raise ValueError("preregistration must contain 3-5 distinct hypotheses")
    if any(h.get("expected_dti") is not None for h in hypotheses):
        raise ValueError("preregistered hypotheses must not be rendered as score projections")
    if snapshot.get("observed_date_utc") != "2026-10-31":
        raise ValueError("the dated leaderboard observation is not current for this review")
    scores = snapshot.get("visible_public_scores", {})
    if (scores.get("rank_1") != "0.4544" or scores.get("rank_2") != "0.3925"
            or scores.get("rank_50") != "0.3195"):
        raise ValueError("leaderboard values do not match the 2026-10-31 public page capture")
    if source_check.get("checked_date_utc") != "2026-10-31":
        raise ValueError("official source check date is not current for this review")
    if {row.get("site") for row in focus.get("focus_sites", [])} != set(FOCUS_ORDER):
        raise ValueError("focus audit does not contain exactly the nine requested sites")

    gate = build_gate(card)
    copy_site_data(card, prereg, focus, gate)

    pages = {
        "index.html": ("Overview", index_page(feed, snapshot, focus, read_json(UPSTREAM))),
        "executive-summary.html": ("Executive summary", executive_page(focus, card)),
        "how-to-submit.html": ("Submission guide", submit_page(source_check, feed)),
        "research.html": ("Research hypotheses", hypothesis_page(prereg)),
        "method.html": ("Method and safeguards", method_page(card, prereg)),
        "evidence.html": ("Evidence and limitations", evidence_page(card, prereg, source_check, focus)),
        "session-review.html": ("Latest review", session_review_page(card)),
        "submission.html": ("Submission status", submission_page()),
    }
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(meta_page(title, name, body), encoding="utf-8")

    (DOCS / "downloads" / "index.html").write_text(downloads_index(), encoding="utf-8")
    artifacts = sorted(p.name for p in (DOCS / "downloads").iterdir()
                       if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"})
    tifs = [name for name in artifacts if Path(name).suffix.lower() in {".tif", ".tiff"}]
    zips = [name for name in artifacts if Path(name).suffix.lower() == ".zip"]
    notice = [
        "DO NOT SUBMIT — RESEARCH ARCHIVE ONLY",
        "No TIFF or ZIP in this directory is cleared for competition use.",
        "No new TIFF was generated by the 2026-10-31 review.",
        "The project-wide literal-registry witness stop is active; local format checks or old lane results do not override it.",
        f"Historical inventory only: {len(tifs)} TIFF(s), {len(zips)} ZIP bundle(s); not an approval list:",
        *[f"  {name}" for name in artifacts],
        "",
        "Current decision: docs/data/release_gate.json",
        "Current negative run card: docs/data/session_2026-10-31_run_card.json",
    ]
    (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").write_text("\n".join(notice) + "\n", encoding="utf-8")

    for directory, (title, card_name) in ARCHIVE_LANES.items():
        lane = DOCS / directory
        lane.mkdir(parents=True, exist_ok=True)
        pages_to_replace = {lane / "index.html", *lane.rglob("*.html")}
        for page in sorted(pages_to_replace):
            page.write_text(archive_lane(directory, title, card_name, page), encoding="utf-8")
    (DOCS / "downloads" / "index.html").write_text(downloads_index(), encoding="utf-8")


def main() -> int:
    render()
    # AMDC publishes a negative dossier and JSON evidence only; it does not link to a TIFF.
    from amdc_site import main as amdc_main
    amdc_main()
    prune_published_data()
    print("Built current fail-closed site: no candidate, no TIFF download links, stale candidate data pruned, and no slot selected.")
    return 0


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
