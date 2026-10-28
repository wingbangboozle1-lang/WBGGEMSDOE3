#!/usr/bin/env python3
"""Render the evidence-first, fail-closed Pages site from committed evidence.

This builder publishes *only* a negative decision. Historical lane renderers
are not invoked: several of them asserted upload clearance despite an explicit
literal-registry failure. A future positive release needs a separately reviewed,
hash-bound selector and a publication path that validates all its evidence.
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
sys.path.insert(0, str(ROOT / "scripts"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402
from hce_banner import HCE_BANNER  # noqa: E402,F401 -- historical compatibility
from build_site_legacy import historical_h6_section  # noqa: E402,F401 -- historical compatibility

AUTHORITY = ROOT / "evidence/session_9b794637_run_card.json"
SGCE_CARD = ROOT / "evidence/session2_run_card.json"
RECHECK = ROOT / "evidence/session_c1e656ce_witness_recheck.json"
FOCUS = ROOT / "evidence/focus_audit.json"
PAIR = ROOT / "evidence/pair_identification.json"
INDEPENDENT_FOCUS = ROOT / "evidence/focus_uniqueness_independent_2026-10-27.json"
INDEPENDENT_NAN = ROOT / "evidence/format_independent_sgce_nan_2026-10-27.json"
INDEPENDENT_ZERO = ROOT / "evidence/format_independent_sgce_zeros_2026-10-27.json"
FEED = ROOT / "registry/leaderboard.json"
LEADERBOARD_OBSERVATION = ROOT / "evidence/leaderboard_observation_2026-10-27.json"
REPO_REVIEW = ROOT / "evidence/session_c1e656ce_run_card.json"
SESSION_REVIEW = ROOT / "evidence/session_c1e656ce_run_card.json"
SHA_CANDIDATE = "0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09"
CANDIDATE_FILE = "wbggems3-sgce-20261027-f52d35d8-zeros.tif"
PRIOR_COMMIT = "1dcca8bb473f732403213928b7c633cd2a22b403"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mark_archive_json(path: Path, notice: str) -> None:
    """Add a minimal, deterministic archive banner without reformatting historical evidence."""
    payload = read(path)
    if not isinstance(payload, dict):
        return
    if payload.get("_archive_notice") == notice and payload.get("current_repository_decision") == "DO-NOT-SUBMIT":
        return
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "{":
        payload["_archive_notice"] = notice
        payload["current_repository_decision"] = "DO-NOT-SUBMIT"
        path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return
    indent = " "
    if len(lines) > 1 and lines[1].lstrip().startswith('"'):
        indent = lines[1][:len(lines[1]) - len(lines[1].lstrip())]
    additions = (f'{indent}"_archive_notice": {json.dumps(notice)},\n'
                 f'{indent}"current_repository_decision": "DO-NOT-SUBMIT",\n')
    path.write_text(lines[0] + additions + "".join(lines[1:]), encoding="utf-8")

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def human_age(feed: dict) -> str:
    checked = feed.get("last_success_utc")
    if not checked:
        return "No successful observation"
    try:
        datetime.fromisoformat(checked)
    except (TypeError, ValueError):
        return "Invalid observation timestamp"
    prefix = "Latest refresh failed · last success " if feed.get("last_attempt_error") else "Last checked · "
    return prefix + checked.replace("+00:00", " UTC")


def layout(title: str, current: str, body: str) -> str:
    nav = [("Overview", "index.html"), ("Executive summary", "executive-summary.html"),
           ("Submission guide", "how-to-submit.html"), ("Research", "research.html"),
           ("Method", "method.html"), ("Evidence", "evidence.html"),
           ("Latest review", "session-review.html"), ("FCHD-NCM lane", "fchd/index.html"),
           ("AMDC lane", "amdc/index.html")]
    links = "".join(f'<a href="{url}"' + (' aria-current="page"' if current == url else '') + f'>{name}</a>'
                    for name, url in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Evidence-first DOE GEMS fault discovery audit; no submission currently cleared.">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a><nav aria-label="Main navigation">{links}</nav></div></header>
<main>{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData · <a href="data/release_gate.json">Machine-readable decision</a> · No competition slot spent by this audit.</div></footer></body></html>'''


def adjdis_card() -> dict | None:
    """Load the current session's generated candidate card, if it exists."""
    path = ROOT / "evidence" / "adjdis_run_card.json"
    if not path.is_file():
        return None
    try:
        return read(path)
    except (OSError, ValueError):
        return None


def decision_block() -> str:
    c = adjdis_card()
    prior = ""
    if c:
        fname = c["submission_file"]
        published_path = DOCS / "downloads" / fname
        published = published_path.is_file()
        h = c["holdout"]
        u = c["uniqueness"]
        g = c["gates"]
        n_pass = sum(1 for k in ("gate0_leakage_canary", "gate1_holdout_beats_gemsdoe32_sig",
                                 "gate2_dot_budget_discipline", "gate3_full_universe_uniqueness",
                                 "gate4_portal_geotiff_0_to_1") if g.get(k))
        button = (f'<a class="btn secondary" href="downloads/{esc(fname)}" download>'
                  "Download prior ADJDIS research TIFF (not submission-cleared)</a> " if published else "")
        sha = digest(published_path) if published else c["raster_sha256"]
        prior = f'''<div class="generated"><span class="tag">PRIOR RESEARCH ARTIFACT · NOT CLEARED</span>
<p><strong><code>{esc(fname)}</code></strong> was generated by the earlier ADJDIS lane, not by this repository review.
Its recorded <strong>HOLDOUT-DTI {h["pooled_dti"]:.5f}</strong> is a historical local result
(gems57-pooled-hide-v2; {h["n_withheld_positives"]:,} withheld positives; 95% CI
{h["ci95_cluster_bootstrap"][0]:.5f}–{h["ci95_cluster_bootstrap"][1]:.5f}); it is not an organizer score.
That lane's sparse-mask comparison was {100 * u["U3_max_nonlattice_overlap_3px"]:.1f}% maximum, but its
literal dense-witness overlap is 100%, so the controlling duplicate stop fails. {n_pass}/5
lane gates passed. <strong>Do not submit.</strong> {button}</p></div>'''
    return f'''<div class="decision"><span class="tag">NEGATIVE · STOP</span><h2>DO NOT SUBMIT — no file is cleared.</h2>
<p>The current review generated no candidate, raster, holdout score, or submission. The recorded mirrored witness is positive on every cell of the mirrored sample footprint under the finite-and-positive support definition; conditional on those bytes, any nonempty in-footprint candidate triggers the literal &gt;70% duplicate stop. The witness is one public owner mirror, not an authenticated or complete registry audit. No upload was made; a separate selector has not approved a slot.</p>
{prior}
<p><a class="btn secondary" href="downloads/{CANDIDATE_FILE}" download>Download prior SGCE TIFF for research only</a> <a class="btn secondary" href="evidence.html">See the blocker and checks</a></p>
<p class="small">Every TIFF in the archive is research-only and <strong>not submission-ready</strong>. A local format pass is not organizer acceptance.</p></div>'''


def adjdis_section() -> str:
    """Show the prior ADJDIS artifact as research-only, never as a current candidate."""
    c = adjdis_card()
    if not c:
        return ""
    fname = c["submission_file"]
    published = (DOCS / "downloads" / fname).is_file()
    h = c["holdout"]
    u = c["uniqueness"]
    g = c["gates"]
    file_cell = (f'<a class="file" href="downloads/{esc(fname)}" download>Research-only download: <code>{esc(fname)}</code></a>'
                 if published else f"<code>{esc(fname)}</code> (not present in downloads)")
    gate_bits = "".join(
        f'<div class="small">{"PASS" if g.get(k) else "FAIL"} · {esc(label)}</div>'
        for k, label in (
            ("gate0_leakage_canary", "prior lane canary"),
            ("gate1_holdout_beats_gemsdoe32_sig", "prior lane paired holdout gate"),
            ("gate2_dot_budget_discipline", "prior lane dot-budget gate"),
            ("gate3_full_universe_uniqueness", "prior lane full-registry gate"),
            ("gate4_portal_geotiff_0_to_1", "prior lane local format gate"),
        ))
    holdout = (f'HOLDOUT-DTI <strong>{h["pooled_dti"]:.5f}</strong> '
               f'<small>{esc(h["evaluator_version"])} · {h["n_withheld_positives"]:,} withheld positives · '
               f'95% CI {h["ci95_cluster_bootstrap"][0]:.5f}–{h["ci95_cluster_bootstrap"][1]:.5f} · '
               f'historical local holdout, not a leaderboard score</small>')
    uniqueness = (f'Prior sparse-comparator measurement: {100 * u["U3_max_nonlattice_overlap_3px"]:.1f}% maximum; '
                  f'pre-placement |Spearman| {u["pre_placement_max_abs_spearman"]:.3f}. '
                  f'But the registered dense witness gives 100% directed overlap under the literal support rule: '
                  f'<strong>DUPLICATE STOP — not unique under the controlling protocol.</strong>')
    return f'''<section><div class="section-head"><div class="eyebrow">Prior lane artifact · research only</div>
<h2>Historical ADJDIS file — not a current candidate</h2>
<p>This is an older artifact, not generated in the current review. Its local measurements are shown only for provenance; the literal uniqueness stop controls.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="Prior research artifact status"><table>
<thead><tr><th>File for research only</th><th>Historical HOLDOUT-DTI</th><th>Registry result</th><th>Prior lane checks</th><th>Current decision</th></tr></thead>
<tbody><tr class="me"><td>{file_cell}<small>generated {esc(c["generated_utc"])} · {c["emitted_dots"]:,} dots · SHA-256 <code>{esc(c["raster_sha256"])}</code></small></td>
<td>{holdout}</td><td>{uniqueness}</td><td>{gate_bits}</td><td><span class="tag">DO NOT SUBMIT</span></td></tr></tbody></table></div>
<p class="small">Historical source cards: <a href="data/adjdis_run_card.json">lane run card</a> · <a href="data/adjdis_leakage_canary.json">leakage canary</a> · <a href="data/adjdis_uniqueness_audit.json">uniqueness audit</a> · <a href="data/adjdis_experiments.json">experiment ledger</a>. These results are not re-run or promoted by the current review.</p></section>'''


def focus_table(audit: dict) -> str:
    rows = []
    for r in audit["focus_sites"]:
        detail = f"{100 * r['max_focus_overlap']:.1f}% vs {r['max_focus_overlap_site']}"
        rows.append(f'''<tr><td><strong>{esc(r['site'])}</strong></td>
<td><a class="file" href="{esc(r['download_research_only'])}">{esc(r['filename'])}</a><small>pinned historical file · research only</small></td>
<td><strong>OWNER-REPORTED {esc(r['claimed_by_owner_not_receipt'])}</strong><small>no authenticated submission receipt</small></td>
<td>Not estimable<small>no independent calibrated estimate</small></td>
<td><strong>No</strong><small>{esc(detail)} within 3 px</small></td><td><span class="tag">DO NOT SUBMIT</span></td></tr>''')
    return '''<p class="scrollhint">Swipe horizontally to view all columns →</p><div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>File to review</th><th>Best reported claim</th><th>Estimated score</th><th>Unique vs other eight?</th><th>Decision</th></tr></thead><tbody>''' + "".join(rows) + "</tbody></table></div>"


def page_top(eyebrow: str, title: str, subtitle: str) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p class="lede">{esc(subtitle)}</p>{decision_block()}</div></section>'''


def nine_site_section(audit: dict) -> str:
    return f'''<section><div class="section-head"><div class="eyebrow">Focus-site review</div><h2>Historical leaders are not new submissions</h2><p>Highest claims supplied for each requested site; none is tied to a verified organizer receipt in this repository. The overlap comparison is limited to these nine pinned historical files and is not a current full-registry audit.</p></div>{focus_table(audit)}
<p class="small">“Not estimable” is intentional. The old LEDGER-INVERSION ESTIMATE and other forecasts are disputed extrapolations, not competition scores or reliable evidence for choosing a new slot. Overlap is a raster measurement, not a leaderboard result.</p></section>'''


def mechanism_section(audit: dict) -> str:
    h = audit["h33_mechanism"]
    return f'''<section><div class="section-head"><div class="eyebrow">GEMSDOE32 reported result</div><h2>What the bytes show — and what they do not</h2><p>The reported 0.2778 is an <strong>OWNER-REPORTED</strong> historical value; no receipt linking it to these exact bytes is available here.</p></div><div class="grid">
<article class="card"><h3>Observed construction</h3><p>Decoded-byte comparison: GEMSDOE32 H33-B2 has {h['champion_positive']:,} positive cells and is a subset of the GEMSDOE28 H27-4 base with {h['base_positive']:,}. The H33-B2 support removes {h['base_pixels_removed']:,} cells; their measured distance from the mirrored catalogue ranges from {h['removed_min_distance_to_catalogue_pixels']:.3f} to {h['removed_max_distance_to_catalogue_pixels']:.1f} pixels. This is a raster construction measurement, not a score or score-causality test.</p></article>
<article class="card"><h3>Plausible, unproven explanation</h3><p>If the documented mask/kernel behavior matches organizer scoring, pruning predictions close to already mapped faults could reduce low-value false-positive mass while retaining some distance-tolerant credit. It could also remove credit for hidden faults. The reported score change is consistent with that trade-off, but the hidden labels and organizer receipt are unavailable, so the cause of OWNER-REPORTED 0.2778 is not established.</p></article>
<article class="card"><h3>Not a basis for a new score claim</h3><p>The nine focus TIFFs are not unique under the recorded pairwise 3-pixel comparison; the universal mirrored witness also triggers the controlling literal stop for any nonempty in-footprint file. A different geological mechanism might perform differently, but no new candidate or comparable holdout has been tested. Fault predictions are not proof of geothermal vents.</p></article></div><p class="small">Sources: <a href="data/pair_identification.json">pair arithmetic (owner-reported inputs; not hidden-truth measurement) ↓</a> · <a href="data/focus_audit.json">decoded-byte focus audit ↓</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE32/raw/8953b986b2ce6eb5ee8b7eda23fe3ad529720986/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif">pinned GEMSDOE32 source file ↗</a></p></section>'''


def steps() -> str:
    return '''<section><div class="section-head"><div class="eyebrow">Submission guide</div><h2>What to do when a file actually clears</h2><p>These are future steps, not an instruction to upload any current artifact.</p></div><div class="card"><ol class="steps">
<li>Wait for a separately selected candidate with a <strong>passing literal registry audit</strong>, a comparable buffered holdout and a positive paired confidence interval, complete canaries, and a saved-byte validator report. No such candidate is available now.</li>
<li>Download the exact approved single-band GeoTIFF or single-TIFF ZIP, and verify its SHA-256 against the approved run card. It must match the official sample’s CRS, shape and transform and contain valid predictions in [0,1].</li>
<li>Sign in to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData’s submission page</a>; check the current quota and rules there. The selector, not this automation, decides whether to spend a slot.</li>
<li>Select the approved file, enter that file’s unique name and note (no more than 140 characters), submit, and save the receipt with the exact file hash. Only an actual receipt establishes an ORGANIZER-CONFIRMED result.</li>
</ol><p><strong>Earlier portal error “Predicted values must be in range [0, 1]”:</strong> inspect the exact rejected bytes for NaN, infinity, nodata sentinels, values outside [0,1], and grid/mask mismatches. The rejected bytes and full portal receipt are unavailable here, so the cause is not established and no future acceptance is guaranteed. A parallel audit interpreted the official outside-footprint wording as requiring NaN there; its independent check fails the old zeros-outside file. This session could not re-open the official page or test portal acceptance, so neither encoding is cleared.</p></div></section>'''


def home(audit: dict, feed: dict, observation: dict) -> str:
    val = feed.get("best_public_dti") or "—"
    checked = feed.get("last_success_utc") or ""
    err = "yes" if feed.get("last_attempt_error") else "no"
    rank25 = observation.get("rank_25_public_dti", "not recorded")
    observed_date = observation.get("observed_date_utc", "unknown date")
    return page_top("DOE GEMS · executive decision", "Evidence first. No slot wasted.", "An automated, auditable review of the nine requested sites and the current competition-file decision.") + f'''<div class="wrap">
<div class="grid"><article class="card"><div class="small">Best reported focus-site claim</div><div class="metric">0.2778</div><div class="small">OWNER-REPORTED · GEMSDOE32 · no authenticated receipt</div></article>
<article class="card"><div class="small">Public leaderboard observation</div><div class="metric">{esc(val)}</div><div class="small" data-freshness data-checked="{esc(checked)}" data-error="{err}">{esc(human_age(feed))} · not our score</div><p class="small">The saved official-page snapshot from {esc(observed_date)} listed {esc(rank25)} at rank 25. The user's 0.3195-as-current claim is not verified by this dated snapshot; current live ranking was not rechecked. <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Check official leaderboard ↗</a> · <a href="data/leaderboard_observation_2026-10-27.json">snapshot details</a></p></article>
<article class="card"><div class="small">Current candidate / weekly slot</div><div class="metric">None / 0 used</div><div class="small">No valid leaderboard estimate available</div></article></div>
{adjdis_section()}{nine_site_section(audit)}{mechanism_section(audit)}
<section><div class="section-head"><div class="eyebrow">Explore</div><h2>Research, not recommendations</h2></div><div class="grid"><article class="card"><h3>Four hypotheses</h3><p>Physical mechanisms, counterexamples and input availability, all preregistered as prospective only.</p><a href="research.html">Read research →</a></article><article class="card"><h3>Historical lane records</h3><p>Prior TIFFs and lane reports remain available to reproduce measurements, not to submit.</p><a href="hce/index.html">HCE archive →</a> · <a href="thcs/index.html">THCS archive →</a> · <a href="cspes/index.html">CSPES archive →</a></article><article class="card"><h3>Sources and feed</h3><p>Leaderboard observations and peer HEAD checks are timestamped and can become stale. No receipt is inferred from them.</p><a href="evidence.html">Open audit →</a></article></div></section></div>'''


def executive(audit: dict) -> str:
    return page_top("Executive summary", "The clearest decision is to wait.", "Each requested site is listed below, together with its historical file, an honest estimate status and a uniqueness decision.") + f'''<div class="wrap">{adjdis_section()}{nine_site_section(audit)}{mechanism_section(audit)}{steps()}</div>'''


def howto() -> str:
    return page_top("Submission guide", "No file is cleared to upload.", "This page explains the future workflow only. No current filename, note, or candidate TIFF is approved.") + f'''<div class="wrap">
<section class="card"><h2>Before downloading or submitting</h2><p><strong>Do not upload any TIFF in the research archive.</strong> A separate selector must first approve the exact bytes after the literal all-registry uniqueness check, leakage canaries, comparable buffered holdout, and exact-byte validation pass. No candidate meets those conditions here. No submission name or note is assigned for this review.</p><p>The current blocker and data limitation are recorded in the <a href="data/release_gate.json">machine-readable release gate</a>, <a href="session-review.html">latest review</a>, and <a href="research.html">research hypotheses</a>. The agent cannot access a private DrivenData account, inspect its quota, or submit on the user's behalf.</p></section>
{steps()}
<section class="card"><h2>Official instructions and the previous range error</h2><p>Read the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem/format description</a>, <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">competition data page</a>, and <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">competition rules PDF</a> before any authorized upload. The data page requires authentication; no credentials are present in this environment.</p><p>The prior portal error was “Predicted values must be in range [0, 1]”. Its rejected bytes and receipt are not available, so the cause is unknown. Check the actual file for all non-finite values, sentinels and values outside [0,1], then verify exact CRS, shape, transform, mask and outside-footprint encoding against the current official instructions. A local diagnostic cannot establish portal acceptance.</p></section>
<section class="card"><h2>Historical research TIFFs</h2><p>Files may be downloaded from the <a href="downloads/index.html">archive</a> for inspection or reproducibility only. Their download links are not submission approval. Do not rename or re-encode one to make it appear new.</p></section>
</div>'''


def research() -> str:
    rows = [
        ("1 · Depth-consistent oblique contact displacement", "Conceptual layers: magnetic field, gravity, magnetic-source depth (only if authenticated and documented).", "Multi-height upward continuation; signed cross-profile gradient displacement with stable dip direction and cross-scale coherence.", "A buried dipping boundary might offset potential-field gradients without a surface trace or catalogue-distance feature.", "Dipping lithologic contact; test mapped-geology controls and depth/profile nulls.", "Relative upside: highest of these options, very uncertain. Cost: medium. Different from a single Euler cluster or one-height edge score; novelty versus all peer code is unproven."),
        ("2 · Scale-conditioned magnetic / conductivity halo", "Conceptual layers: magnetic field and surface conductivity (presence, units, and semantics unverified).", "Local-background removal; signed low-magnetization residual flanking a narrow conductivity crest across repeated profiles.", "An alteration/conductivity halo could be offset from mapped surface fault traces.", "Conductive clay, basin fill, fresh volcanic contacts, survey seams; compare geology-matched and flight-block controls.", "Relative upside: moderate. Cost: medium. Tests a joint signed residual rather than a generic conductivity ridge; peer novelty is unproven."),
        ("3 · Drainage-independent displaced scarp pairs", "Conceptual layers: elevation and magnetic field (DEM resolution/alignment unverified).", "Pair curvature zero-crossings on opposite sides of a magnetic edge; reject drainage-aligned curvature and long planar terraces.", "A small offset surface may be absent from regional mapping; the tested feature is paired displacement, not slope alone.", "Shoreline terraces, roads, and alluvial channels; use drainage/terrace masks, rotated profiles, and matched terrain nulls.", "Relative upside: low-to-moderate. Cost: high. Different from stand-alone slope, curvature, step, or tip continuation; novelty is unproven."),
        ("4 · Radiometric mixture-boundary discordance", "Conceptual layers: K/Th/U and magnetic field (channels and units unverified).", "Fit a local compositional-mixture manifold; score persistent residuals normal to magnetic discontinuities, not raw band ratios.", "Hydrothermal redistribution could depart from a local lithologic mixing trend near a buried structure.", "Soil moisture, transported sediment, lithologic contacts, or survey seams; require moisture/geology/flight-block controls.", "Relative upside: low-to-moderate with high confounding risk. Cost: medium-high. A local mixture residual differs from a simple edge vote; novelty is unproven."),
    ]
    rows_html = "".join(
        f'<tr><th scope="row">{esc(name)}</th><td>{esc(layers)}</td><td>{esc(signature)}</td>'
        f'<td>{esc(rationale)}</td><td>{esc(mimic)}</td><td>{esc(rank_cost)}</td></tr>'
        for name, layers, signature, rationale, mimic, rank_cost in rows)
    return page_top("Scientific research", "Four hypotheses; none tested.", "Qualitative relative DTI-upside versus implementation-cost ranking only. No numerical DTI forecast, selected lane, or validated model.") + f'''<div class="wrap"><section><div class="section-head"><h2>Prospective geological hypotheses</h2><p>The “single method paragraph” is not identifiable. No model experiment ran; the pre-placement literal registry stop remains active. These conceptual layers are not verified as present or physically documented in this checkout.</p></div><div class="tablewrap" tabindex="0" role="region" aria-label="Ranked geological hypotheses"><table><thead><tr><th>Rank / hypothesis</th><th>Conceptual layers</th><th>Target signature</th><th>Why it might find an uncatalogued fault</th><th>Named non-fault mimic / falsification</th><th>Relative DTI upside and cost / implementation distinction</th></tr></thead><tbody>{rows_html}</tbody></table></div><p class="small">Full caveats and source availability: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/hypotheses.md">hypothesis preregistration ↗</a>. No idea is claimed novel across the wider peer ecosystem.</p></section>
<section><div class="section-head"><h2>Required data and official sources</h2><p>The specific source for authenticated features, labels, sample geometry, and metadata is the DrivenData data page; it requires account authentication, which is unavailable here. The local competition stack/cache is absent. GitHub mirror hashes prove mirror identity, not organizer origin.</p></div><div class="grid"><article class="card"><h3>Competition data &amp; problem</h3><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">DrivenData data page ↗</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem and scoring ↗</a></p></article><article class="card"><h3>Reference implementation</h3><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference on GitHub ↗</a></p></article><article class="card"><h3>Geophysics</h3><p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN ↗</a></p></article><article class="card"><h3>Geothermal compilation</h3><p><a href="https://gdr.openei.org/submissions/1391">DOE GDR INGENIOUS ↗</a></p></article><article class="card"><h3>Elevation</h3><p><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP ↗</a></p></article></div><p class="small">The non-GitHub official hosts above were not fetched in this review. They are source links for manual review, not verified availability or license claims. The contest target is fault prediction; even a fault-map improvement would not establish geothermal vents or a resource.</p></section></div>'''


def method_page() -> str:
    return page_top("Method and scoring", "Evidence about the bytes; not a score explanation.", "The historical GEMSDOE32 result can be investigated, but the available evidence does not prove why it scored as reported or predict a new result.") + '''<div class="wrap">
<section><div class="section-head"><h2>GEMSDOE32 0.2778: the defensible interpretation</h2><p><strong>OWNER-REPORTED 0.2778</strong> is not linked to an authenticated submission receipt in this repository.</p></div><div class="card"><p>The pinned raster audit records GEMSDOE32 H33-B2 as a subset of the GEMSDOE28 H27-4 base. H33-B2 has 37,654 positive cells versus 40,199 in the base; 2,545 cells were removed, all at measured catalogue distances from 1.414 to 2.000 pixels. This is observed support geometry, not hidden-label truth.</p><p>A plausible mechanism is that pruning cells near already mapped faults reduces low-value false-positive mass while retaining distance-kernel credit. That would be compatible with the recorded metric convention, but the removed cells could also be near hidden faults. Without the hidden labels in an authenticated form and a receipt that binds the reported value to these bytes, the causal explanation is not established.</p><p>The stored pair analysis algebraically infers hidden-truth quantities from the two <strong>OWNER-REPORTED</strong> inputs under the repository's assumed binary DTI identity. Those are model-dependent inferred quantities—not observed hidden-truth counts, not a validated score estimate, and not evidence that a new geological method would score higher. See <a href="data/pair_identification.json">the pair-analysis record ↓</a> and <a href="data/focus_audit.json">the decoded-byte audit ↓</a>.</p></div></section>
<section><div class="section-head"><h2>Why there is no current candidate</h2></div><div class="grid"><article class="card"><h3>Literal uniqueness stop</h3><p>The saved mirrored witness is positive on all cells of the mirrored sample footprint under the recorded finite-and-positive rule. Conditional on those bytes, every nonempty in-footprint candidate exceeds the 70% directed-overlap stop. A content-aware waiver is not authorized; see <a href="evidence.html">the witness limitations</a>.</p></article><article class="card"><h3>Holdout prerequisites missing</h3><p>The shared competition feature stack, labels, sample raster, segment IDs and saved buffered folds/cache are not in this checkout. No new candidate could be tested with the requested shared evaluator and writer. A historic lane holdout is not a result for a new candidate.</p></article><article class="card"><h3>Format is separate</h3><p>A future candidate must be validated on exact saved bytes for finite values, no NaN in the footprint, all predictions in [0,1], and CRS/shape/transform agreement. Outside-footprint encoding remains disputed; the earlier portal error's cause is unknown without the rejected bytes and receipt. No local check establishes portal acceptance.</p></article></div></section>
<section><div class="section-head"><h2>What would establish a result</h2></div><div class="card"><ol class="steps"><li>Identify the one assigned method paragraph and restore authenticated inputs plus the shared cache. Do not substitute mirror bytes without marking provenance.</li><li>Resolve the literal pre-placement registry comparison under the controlling rule; if it exceeds either threshold, log a duplicate and stop.</li><li>Only then preregister a candidate, test each feature alone for leakage, and run whole buffered segment holdout using visible-only catalogue features and pixel-exact visible-fault masks.</li><li>Report pooled <strong>HOLDOUT-DTI</strong> with evaluator version, withheld-positive count and spatial 95% CI. Do not call a model projection a score.</li><li>Repeat registry checks on final dots, hash and validate exact GeoTIFF bytes, then let the separate selector consider a slot. Only an actual submission receipt creates an <strong>ORGANIZER-CONFIRMED</strong> result.</li></ol></div></section>
<section><div class="section-head"><h2>Domain boundary</h2></div><div class="card"><p>The competition target is fault prediction. Faults may be relevant to fluid pathways, but a fault map alone does not locate a geothermal vent, demonstrate discharge, or establish a viable geothermal resource. The four ideas on the <a href="research.html">Research page</a> are untested hypotheses with explicit non-fault mimics.</p></div></section>
</div>'''


def evidence_page(recheck: dict, independent_focus: dict) -> str:
    w, c = recheck["witness"], recheck["candidate"]
    focus_overlap_percent = 100 * independent_focus["max_candidate_overlap_with_focus"]
    return page_top("Evidence and limitations", "One witness is enough to stop.", "Independent saved-byte recheck, with no new model training, new prediction or submission.") + f'''<div class="wrap"><section><div class="section-head"><h2>Literal uniqueness proof</h2><p>Measured {esc(recheck['checked_utc'])} against hash-pinned public owner mirrors, not authenticated organizer downloads.</p></div><div class="grid"><article class="card"><h3>Registry witness</h3><p>The <a href="{esc(w['source'])}">registered 17GEMSDOE probability raster</a> is positive on all {w['footprint_cells']:,} finite, GDAL-valid cells of the mirrored sample. For any nonempty prediction whose support lies inside that footprint, every positive pixel coincides with witness support. Directed 3-pixel overlap is therefore 100%, exceeding the requested 70% stop.</p><p class="small">Witness SHA-256 <code>{esc(w['sha256'])}</code>. This proves failure against one comparator; it does not constitute a complete current registry audit.</p></article>
<article class="card"><h3>Previously advertised SGCE file</h3><p>Reopened saved TIFF: {c['positive_pixels_all']:,} positive pixels; {c['positive_pixels_within_3px_of_witness']:,} overlap the witness. Literal uniqueness: <strong>FAIL</strong>. Its pre-placement surface was not replayed. Its old content-aware exemption does not override the stated rule.</p><p class="small">SHA-256 <code>{esc(c['sha256'])}</code> · <a href="data/session_c1e656ce_witness_recheck.json">Current review recheck JSON ↓</a></p></article>
<article class="card"><h3>Format is a different gate</h3><p>For the old zeros-outside research file, our local range/grid diagnostic passes, but a parallel independent check interprets the outside-footprint rule as requiring NaN and therefore <strong>fails that file</strong>. Its NaN-outside variant passes that parallel local format check. The official wording could not be re-read in this session and neither encoding has a portal receipt. Format checks alone never clear upload.</p><p class="small"><a href="data/format_independent_sgce_zeros_2026-10-27.json">Zeros diagnostic ↓</a> · <a href="data/format_independent_sgce_nan_2026-10-27.json">NaN diagnostic ↓</a> · <a href="data/session_c1e656ce_run_card.json">Current review run card ↓</a></p></article></div></section>
<section><div class="section-head"><h2>Independent focus-only comparison</h2></div><div class="card"><p>A parallel review independently compared the older NaN-outside SGCE bytes to the nine pinned focus-site files. The largest directed 3-pixel overlap was {focus_overlap_percent:.2f}%. We reran that comparison after adding grid and cached-sample hash checks and obtained the same numbers. It excludes other registry files: the separate witness overlaps 100%, so focus-only agreement does <strong>not</strong> clear the literal all-registry gate.</p><p><a href="data/focus_uniqueness_independent_2026-10-27.json">Nine-file comparison and pairwise matrix ↓</a></p></div></section>
<section><div class="section-head"><h2>What remains unknown</h2></div><div class="card"><ul><li>The original rejected upload bytes and portal receipt are unavailable, so the [0,1] error’s cause cannot be established.</li><li>Historical site scores are user/owner reports, not organizer-confirmed receipts. Some previous pages wrongly labeled them confirmed or recommended files despite failing the literal rule.</li><li>The active data/feature cache was not restored, nor was any feature canary or holdout rerun. Pinned mirror identity does not authenticate the organizer source or physical-band semantics.</li><li>The request does not identify its “single method paragraph”; the witness stop independently blocks the generation of a compliant nonempty candidate. The shared template tests signed positive rank correlation; the project has also used a stricter absolute-rank convention, which the user’s wording does not explicitly require. Agree on that convention and reconcile outside-footprint handling before release.</li><li>DrivenData, USGS, GDR and the rules PDF are outside this sandbox’s permitted outbound hosts. The <a href="https://github.com/drivendataorg/gems-prize-reference-solution">organizer reference repository</a> was accessible via GitHub; no current portal quota or receipt was obtained.</li></ul></div></section>
<section><div class="section-head"><h2>Latest repository review</h2></div><div class="card"><p>The 2026-10-28 review rechecked the nine focus sites, the literal uniqueness stop, candidate/score claims, and the build/tests. It produced no new TIFF and no holdout score. The saved official-page snapshot is dated 2026-10-27: it records 0.4544 at the top and 0.3195 at rank 25; this is not a live check for 2026-10-28.</p><p><a href="data/session_c1e656ce_run_card.json">Current review run card ↓</a> · <a href="data/leaderboard_observation_2026-10-27.json">Dated public leaderboard snapshot ↓</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Open official live page ↗</a></p></div></section>
<section><div class="section-head"><h2>Repeat the independent audit</h2></div><div class="card"><p><code>python -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt</code><br><code>.venv/bin/python scripts/recheck_registry_witness.py --fetch --output evidence/session_c1e656ce_witness_recheck.json</code><br><code>.venv/bin/python -m pytest -q</code></p><p class="small">GitHub access is required for pinned inputs. Cached rasters are ignored by Git. This command never creates or uploads a submission.</p></div></section></div>'''


def latest_review_page(card: dict) -> str:
    verification = card["verification"]
    holdout = card["holdout_dti"]
    witness = card["registry_comparison"]["witness_measurement"]
    return page_top("Latest review · 2026-10-28", "Negative preflight; no experiment.", "Three review passes on the repository release path. No new candidate or competition slot was produced.") + f'''<div class="wrap"><section><div class="grid">
<article class="card"><h2>Decision</h2><p><strong>DO NOT SUBMIT.</strong> This review generated no TIFF, candidate HOLDOUT-DTI, live leaderboard check, or submission. The result is a negative release-safety finding.</p><p>Experiments: {card['experiments_run']} of {card['experiment_budget_max']} allowed. Slots used: {card['weekly_slots_used']}.</p></article>
<article class="card"><h2>Registry stop</h2><p>The saved mirrored witness is positive on {witness['witness_positive_inside']:,} of {witness['footprint_cells']:,} footprint cells. Under the recorded finite-and-positive support definition, any nonempty in-footprint candidate would have 100% directed overlap. This is conditional evidence from one owner mirror, not a score, authenticated organizer source, or complete registry audit. Witness SHA-256: <code>{esc(witness['registered_witness_sha256'])}</code>.</p></article>
<article class="card"><h2>Holdout</h2><p>{esc(holdout['status'])}. No current-candidate HOLDOUT-DTI value or confidence interval is reported. The feature stack, labels, segment identifiers, and saved folds/cache are absent from this checkout.</p></article>
<article class="card"><h2>Checks</h2><p>Site builder: {esc(verification.get('site_builder', 'NOT RUN'))}. Site checker: {esc(verification.get('site_checker', 'NOT RUN'))}. Pytest: {esc(verification.get('pytest', 'NOT RUN'))}. These validate repository behavior only; they do not validate a prediction.</p></article>
</div></section><section><div class="section-head"><h2>Reported GEMSDOE32 result</h2><p>GEMSDOE32's 0.2778 is an OWNER-REPORTED historical value, not a receipt-confirmed result.</p></div><div class="card"><p>The pinned byte comparison finds the 37,654-cell H33-B2 raster is a subset of the 40,199-cell H27-4 base; 2,545 cells were pruned close to the mirrored mapped-fault catalogue. That construction is consistent with a precision/false-positive trade-off, but cannot establish score causality without hidden labels and a receipt.</p><p><a href="method.html">Read the evidence and limitations →</a></p></div></section><section><div class="section-head"><h2>What happens next</h2><p>Resolve the literal duplicate stop only through an authorized protocol decision, identify the assigned method paragraph, and restore authenticated inputs and the shared cache before any experiment.</p></div><div class="card"><p>Do not apply a content-aware waiver silently. If prerequisites become available, run visible-only feature canaries and the prescribed buffered holdout before any final placement; recheck the final dots and exact TIFF bytes; let the separate selector control any slot.</p><p><a href="data/session_c1e656ce_run_card.json">Download machine-readable review card →</a> · <a href="evidence.html">Review evidence and limits →</a> · <a href="research.html">Review candidate hypotheses →</a></p></div></section></div>'''


LANES = {
    "hce": (["index.html", "how-to-submit.html", "why-0.2778.html", "hypotheses.html", "evidence.html", "sources.html", "limitations.html"], "HCE-1", "hce_run_card.json"),
    "cspes": (["index.html", "how-to-submit.html"], "CSPES", "cspes_run_card.json"),
    "lst1": (["index.html", "summary.html", "how-to-submit.html", "why.html", "hypotheses.html", "evidence.html", "limitations.html"], "LST1", "lst1_run_card.json"),
    "lbcal": (["index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "sources.html"], "LBCAL", "lbcal_run_card.json"),
    "rfl": (["index.html", "how-to-submit.html"], "RFL", "rfl_run_card.json"),
    "session-1f0b051d": (["index.html", "how-to-submit.html"], "Dipole hybrid", "session_1f0b051d_run_card.json"),
    "thcs": (["index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html"], "THCS-OOF", "thcs_run_card.json"),
}


def lane_stub(directory: str, title: str, card: str) -> str:
    extra = ('<p><a class="btn secondary" href="downloads/wbggems3-hce1-latest.tif" download>DOWNLOAD RESEARCH TIF</a></p>'
             if directory == "hce" else "")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · historical research</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main><section class="hero"><div class="wrap"><div class="eyebrow">Historical lane · {esc(title)}</div><h1>Research archive, not a release.</h1>
<div class="decision"><strong>Global release gate: DO NOT SUBMIT.</strong><p>No competition file is cleared. Do not submit any historical TIFF. The literal registry has a 100% witness overlap for any nonempty in-footprint candidate; a local format pass is not portal acceptance. Not cleared for upload.</p></div>
<p>These artifacts are research only. Earlier versions of this lane’s pages contained inconsistent approval, score or portal-acceptance claims. They are retained in version history for provenance, not as current instructions. Their holdout and source claims have not been independently replayed by this audit.</p>{extra}
<p><a class="btn" href="../executive-summary.html">Current executive summary</a><a class="btn secondary" href="../data/{esc(card)}">Historical lane card</a></p>
<p class="small">For historical context only: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/tree/{PRIOR_COMMIT}/docs/{esc(directory)}">superseded page snapshot ↗</a>. The governing decision is the <a href="../index.html">main site</a>.</p></div></section></main></body></html>'''


def downloads_index() -> str:
    files = sorted((DOCS / "downloads").glob("*.tif"), key=lambda p: p.name.lower())
    rows = []
    for path in files:
        rows.append(
            f'<tr><td><a href="{esc(path.name)}" download>{esc(path.name)}</a></td>'
            f'<td><strong>RESEARCH ONLY · DO NOT SUBMIT</strong></td>'
            f'<td>{path.stat().st_size:,} bytes</td><td><code>{digest(path)}</code></td></tr>')
    body = "".join(rows) or '<tr><td colspan="4">No TIFF files are present in the archive.</td></tr>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"><title>Research-only TIFF archive</title><link rel="stylesheet" href="../assets/safe.css"></head><body><main class="wrap"><section class="hero"><div class="eyebrow">Historical archive</div><h1>Research downloads only.</h1><div class="decision"><strong>DO NOT SUBMIT.</strong><p>No file in this directory is cleared. Each link below is for inspection/reproduction only. The literal all-registry stop and missing candidate holdout block release. A local format check is not portal acceptance.</p></div><p><a href="LEGACY-DO-NOT-SUBMIT.txt">Read the plain-text archive notice →</a> · <a href="../data/release_gate.json">Current release gate →</a></p>
<div class="tablewrap" tabindex="0" role="region" aria-label="Research-only historical TIFFs"><table><thead><tr><th>File (research only)</th><th>Submission status</th><th>Size</th><th>SHA-256 of archived bytes</th></tr></thead><tbody>{body}</tbody></table></div>
<p class="small">The listed hashes identify these archived bytes only. They do not certify organizer provenance, uniqueness, a holdout result, portal acceptance, or submission authorization. Do not rename or re-encode an artifact to imply it is new.</p><p><a href="../executive-summary.html">← Executive summary</a> · <a href="../how-to-submit.html">Future submission steps →</a></p></section></main></body></html>'''


def legacy_download_notice() -> str:
    """Describe every archived TIFF as research-only; never designate a cleared file."""
    paths = sorted((DOCS / "downloads").glob("*.tif"), key=lambda p: p.name.lower())
    lines = [
        "DO NOT SUBMIT — HISTORICAL / RESEARCH TIFF ARCHIVE",
        "",
        "No TIFF in this directory is cleared for competition submission.",
        "All files are preserved for inspection or reproducibility only. A filename,",
        "local format pass, historical lane verdict, or download link is not approval.",
        "Do not rename, re-encode, or copy an archived TIFF as a new candidate.",
        "The current release gate is docs/data/release_gate.json (DO-NOT-SUBMIT).",
        "",
        "Archived GeoTIFFs (hashes identify bytes only; they are not scores/receipts):",
    ]
    for path in paths:
        lines.append(f"  {path.name}  bytes={path.stat().st_size}  sha256={digest(path)}")
    return "\n".join(lines) + "\n"


def render() -> None:
    authority, candidate, recheck, audit, feed = map(read, (AUTHORITY, SGCE_CARD, RECHECK, FOCUS, FEED))
    leaderboard_observation, repository_review = map(read, (LEADERBOARD_OBSERVATION, REPO_REVIEW))
    focus_only, nan_format, zero_format = map(read, (INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO))
    gate = evaluate_release_gate(authority, candidate)
    if (repository_review.get("branch") != "arena/c1e656ce-wbggemsdoe3"
            or repository_review.get("verdict") != "negative"
            or repository_review.get("raster_sha256") is not None
            or repository_review.get("submission_name") is not None
            or repository_review.get("selector_approval") is not False
            or repository_review.get("experiments_run") != 0
            or repository_review.get("weekly_slots_used") != 0
            or len(repository_review.get("submission_note", "")) > 140
            or repository_review.get("holdout_dti", {}).get("status") != "NOT RUN"
            or repository_review.get("registry_comparison", {}).get("new_candidate_tested") is not False
            or repository_review.get("validator_output", {}).get("new_raster_generated") is not False
            or leaderboard_observation.get("observed_date_utc") != "2026-10-27"
            or leaderboard_observation.get("best_public_dti") != "0.4544"
            or leaderboard_observation.get("rank_25_public_dti") != "0.3195"):
        raise ValueError("current review card or dated leaderboard snapshot changed; review before publishing")
    w, c = recheck.get("witness", {}), recheck.get("candidate", {})
    if (gate["okay_to_submit"] or authority.get("verdict") != "negative"
            or authority.get("selector_approval") is not False
            or recheck.get("verdict") != "negative" or recheck.get("approved_for_submission") is not False
            or w.get("universal_blocker") is not True or not w.get("footprint_cells")
            or w.get("witness_positive_inside") != w.get("footprint_cells")
            or c.get("sha256") != SHA_CANDIDATE or c.get("literal_duplicate") is not True
            or c.get("directed_overlap_within_3px_all_positive") != 1.0
            or digest(ROOT / w["registry"]) != w.get("registry_sha256")
            or digest(DOCS / "downloads" / CANDIDATE_FILE) != SHA_CANDIDATE
            or digest(ROOT / "submission" / CANDIDATE_FILE) != SHA_CANDIDATE):
        raise ValueError("Evidence no longer supports the negative publication; fail closed and review")
    wanted = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    independent_rows = focus_only.get("per_file", [])
    nan_file = DOCS / "downloads/wbggems3-sgce-20261027-f52d35d8-nan.tif"
    if (len(independent_rows) != 9 or {r.get("site") for r in independent_rows} != wanted
            or any(r.get("same_grid_as_candidate") is not True for r in independent_rows)
            or focus_only.get("errors") or focus_only.get("n_focus_files_checked") != 9
            or focus_only.get("max_candidate_overlap_with_focus") != max(r["candidate_dots_within_3px_of_focus"] for r in independent_rows)
            or focus_only.get("candidate_sha256") != digest(nan_file)
            or nan_format.get("sha256") != digest(nan_file) or nan_format.get("passed") is not True
            or zero_format.get("sha256") != SHA_CANDIDATE or zero_format.get("passed") is not False):
        raise ValueError("independent focus or format evidence does not match the recorded research bytes")
    rows = audit.get("focus_sites", [])
    if len(rows) != 9 or {r.get("site") for r in rows} != wanted or any(r.get("focus_literal_unique") is not False for r in rows):
        raise ValueError("focus-site audit is incomplete or inconsistent")
    gate["source_cards"] = {"authority": str(AUTHORITY.relative_to(ROOT)), "authority_sha256": digest(AUTHORITY),
                            "candidate": str(SGCE_CARD.relative_to(ROOT)), "candidate_sha256": digest(SGCE_CARD),
                            "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK)}
    gate["blocking_reasons"].insert(0, "The registered dense witness overlaps every in-footprint candidate; SGCE's measured overlap is 100%.")
    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n")
    (data / "decision.json").write_text(json.dumps({"decision": "DO-NOT-SUBMIT", "okay_to_submit": False,
                                                    "candidate": None, "source": "release_gate.json"}, indent=2) + "\n")
    for path in (AUTHORITY, RECHECK, FOCUS, PAIR, FEED, LEADERBOARD_OBSERVATION, REPO_REVIEW,
                 INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO, SESSION_REVIEW):
        shutil.copyfile(path, data / path.name)
    shutil.copyfile(AUTHORITY, data / "run_card.json")
    if (ROOT / "evidence" / "adjdis_run_card.json").is_file():
        for name in ("adjdis_run_card.json", "adjdis_leakage_canary.json",
                     "adjdis_uniqueness_audit.json", "adjdis_experiments.json",
                     "adjdis_ir28_04_diagnostic.json", "adjdis_ir28_05_fullphase_replay.json",
                     "session_6984642c_run_card.json"):
            src = ROOT / "evidence" / name
            if not src.is_file():
                raise ValueError(f"adjdis run card present but evidence file missing: {src}")
            shutil.copyfile(src, data / name)
    for _, (_, _, card) in LANES.items():
        path = ROOT / "evidence" / card
        if not path.is_file():
            raise ValueError(f"missing historical lane card: {path}")
        historical = read(path)
        notice = "SUPERSEDED historical lane record; its claims were not replayed in this review and do not authorize an upload. See release_gate.json."
        prior_notice = historical.pop("_archive_notice", None)
        historical = {"_archive_notice": notice + (" " + prior_notice if prior_notice else ""), **historical}
        (data / card).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n")
    old = {"_archive_notice": "SUPERSEDED historical lane claims; no repository-wide upload approval. See release_gate.json.",
           "current_repository_decision": "DO-NOT-SUBMIT", **candidate}
    (data / "session2_run_card.json").write_text(json.dumps(old, indent=2, allow_nan=False) + "\n")
    archive_notice = (
        "HISTORICAL EVIDENCE COPY; not a current release decision. "
        "Current repository decision is DO-NOT-SUBMIT; see release_gate.json.")
    for name in ("candidate_run_card.json", "estimate.json", "focus_estimates.json",
                 "focus_pairwise.json", "gemsdoe_run_card.json", "uniqueness.json"):
        archived = data / name
        if archived.is_file():
            mark_archive_json(archived, archive_notice)
    (data / "khd_release.json").write_text(json.dumps({
        "schema": "gems-historical-lane-publication-v1",
        "decision": "DO-NOT-SUBMIT",
        "okay_to_submit": False,
        "archive_notice": ("A superseded publisher marked the KHD artifact SUBMISSION-READY despite its negative lane card "
                           "and failed literal uniqueness gate. That publisher is retired; this record does not authorize upload."),
        "current_release_gate": "release_gate.json",
        "historical_run_card": "evidence/khd_run_card.json"
    }, indent=2) + "\n")
    pages = {"index.html": ("Overview", home(audit, feed, leaderboard_observation)), "executive-summary.html": ("Executive summary", executive(audit)),
             "how-to-submit.html": ("Submission guide", howto()), "research.html": ("Research", research()),
             "method.html": ("Method and scoring", method_page()),
             "evidence.html": ("Evidence", evidence_page(recheck, focus_only)),
             "session-review.html": ("Latest review", latest_review_page(read(SESSION_REVIEW))),
             "submission.html": ("Submission", page_top("Submission status", "No file is currently cleared.", "See the executive summary and future submission guide; no upload is authorized.") + '<div class="wrap"><p><a href="executive-summary.html">Open executive summary →</a></p></div>')}
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(layout(title, name, body), encoding="utf-8")
    (DOCS / "downloads/index.html").write_text(downloads_index(), encoding="utf-8")
    (DOCS / "downloads/LEGACY-DO-NOT-SUBMIT.txt").write_text(legacy_download_notice(), encoding="utf-8")
    (data / "ARCHIVE-NOT-SUBMIT.txt").write_text(
        "Current decision: DO-NOT-SUBMIT. release_gate.json and session_c1e656ce_run_card.json are the current site records. Other JSON files in docs/data are historical evidence copies unless explicitly identified otherwise; their claims do not authorize an upload. Source cards under evidence/ remain the provenance record.\n",
        encoding="utf-8")
    for directory, (names, title, card) in LANES.items():
        for name in names:
            (DOCS / directory / name).write_text(lane_stub(directory, title, card), encoding="utf-8")
    for directory in ("lbcal", "thcs"):
        path = DOCS / directory / "downloads/index.html"
        path.write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Research archive</title></head><body><h1>DO NOT SUBMIT</h1><p>Historical research files only; no candidate is cleared. <a href="../../executive-summary.html">Current executive summary</a>.</p></body></html>''', encoding="utf-8")
    print("Built negative evidence-first pages and quarantined historical lane pages.")


def main() -> int:
    """Always render the fail-closed current site, then refresh negative lane archives."""
    from amdc_site import main as _amdc_main
    from build_site_fchd import main as _fchd_main
    render()
    r1 = _amdc_main() or 0
    r2 = _fchd_main() or 0
    return r1 or r2


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
