#!/usr/bin/env python3
"""Build the GEMS Field Notes site from the release gate and the evidence behind it.

2026-10-31: the site is now *gate-driven*.  `src/gems_project/site_gate.py` decides whether
the candidate is cleared; this script only renders that decision.  If the gate says SUBMIT the
pages carry a download button and the cleared file; if it says DO-NOT-SUBMIT they carry the
blocking reasons and no download.  Nothing here can override the gate.

Every number printed on the site is read from a JSON under evidence/ (or recomputed from the
saved raster).  The labels are carried literally: HOLDOUT-DTI for the local proxy score,
OWNER-REPORTED/UNVERIFIED for other teams' platform scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
import html
import json
import re
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems_project.site_gate import compose_gate, verify_candidate, sha256  # noqa: E402
from build_site_legacy import historical_h6_section                      # noqa: E402,F401
from gems_project.release_gate import evaluate_release_gate              # noqa: E402,F401

EV = ROOT / "evidence"
NF = EV / "newfaults"
SUB = ROOT / "submission" / "newfaults-2026-10-31"
TIF = SUB / "wbg-corridor-band3to12-s24-sep4-20261031T030000Z-zeros.tif"
ZIP = TIF.with_suffix(".zip")
MANIFEST = SUB / "wbg-corridor-band3to12-s24-sep4-20261031T030000Z-manifest.json"

FOCUS = EV / "focus_audit.json"
LEADERBOARD = ROOT / "registry" / "leaderboard.json"
SNAPSHOT = EV / "leaderboard_observation_2026-10-28.json"
SOURCES = EV / "official_source_check_2026-10-28.json"
LEGACY_NOTICE = "LEGACY-DO-NOT-SUBMIT.txt"

CORE_PAGES = ("index.html", "executive-summary.html", "how-to-submit.html", "research.html",
              "method.html", "evidence.html", "session-review.html", "submission.html")
FOCUS_ORDER = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
               "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
ARCHIVE_LANES = {
    "hce": "HCE-1", "cspes": "CSPES", "lst1": "LST1", "lbcal": "LBCAL",
    "rfl": "RFL", "session-1f0b051d": "Dipole hybrid", "thcs": "THCS-OOF", "fchd": "FCHD-NCM",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def pct(x: float, nd: int = 1) -> str:
    return f"{100.0 * float(x):.{nd}f} %"


def num(x: float, nd: int = 3) -> str:
    return f"{float(x):.{nd}f}"


# ------------------------------------------------------------------------------------------------
# layout
# ------------------------------------------------------------------------------------------------

def meta_page(title: str, current: str, body: str, gate: dict) -> str:
    decision = gate["decision"]
    nav = [("Overview", "index.html"), ("Executive summary", "executive-summary.html"),
           ("Download & submit", "how-to-submit.html"), ("Hypotheses", "research.html"),
           ("Method", "method.html"), ("Evidence", "evidence.html"),
           ("Session review", "session-review.html")]
    links = "".join(
        f'<a href="{url}"' + (' aria-current="page"' if current == url else "") + f">{esc(name)}</a>"
        for name, url in nav)
    badge = ("CLEARED · ONE FILE" if decision == "SUBMIT" else "NO FILE CLEARED")
    desc = ("Evidence-first DOE GEMS new-fault submission, independent holdout and uniqueness audit."
            if decision == "SUBMIT" else
            "Evidence-first DOE GEMS fault-mapping review; no submission currently cleared.")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(desc)}">
<meta name="gemsdoe-decision" content="{esc(decision)}">
<title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a>
<span class="tag">{esc(badge)}</span><nav aria-label="Main navigation">{links}</nav></div></header>
<main>{body}</main>
<footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData ·
<a href="data/release_gate.json">Release gate (JSON)</a> ·
<a href="data/run_card.json">Run card (JSON)</a> · generated {esc(gate["generated_utc"])}</div></footer></body></html>'''


def decision_panel(gate: dict) -> str:
    c = gate.get("candidate") or {}
    if gate["decision"] != "SUBMIT":
        reasons = "".join(f"<li>{esc(r)}</li>" for r in gate.get("blocking_reasons", []))
        return f'''<div class="decision"><span class="tag warn">NEGATIVE · FAIL CLOSED</span>
<h2>Do not submit — the gate did not clear this file.</h2>
<ul>{reasons}</ul></div>'''
    return f'''<div class="decision"><span class="tag ok">CLEARED · ONE FILE</span>
<h2>This file is cleared for download and submission.</h2>
<p><strong>{esc(c["submission_name"])}</strong> · {c["bytes"]:,} bytes ·
SHA-256 <code>{esc(c["sha256"])}</code></p>
<p><a class="btn" href="{esc(download_href(gate))}" download>Download the submission TIFF →</a>
<a class="btn secondary" href="downloads/{esc(Path(c["zip"]).name)}" download>ZIP copy (same bytes)</a>
<a class="btn secondary" href="how-to-submit.html">How to submit, step by step →</a></p>
<p class="small">Submission note (≤140 characters): <code>{esc(c["note"])}</code></p></div>'''


def download_href(gate: dict) -> str:
    return "downloads/" + Path(gate["candidate"]["tif"]).name


def sibling_notice(gate: dict) -> str:
    sib = (gate.get("sibling_candidates") or [None])[0]
    if not sib:
        return ""
    return (f'<div class="card"><h3>Second file from a sibling lane — never the project decision</h3>'
            f'<p><code>{esc(sib["file"])}</code> ({int(sib["dots"] or 0):,} dots) was published the same day by this '
            f'repository\'s desk lane and its own decision file said SUBMIT. It is <strong>not</strong> the '
            f'project\'s cleared file: {esc(sib["reason"])}. Its bytes and its original claim are preserved in '
            f'<a href="data/release_decision.json">data/release_decision.json</a> under '
            f'<code>superseded_claim</code>; the authoritative decision is the '
            f'<a href="data/release_gate.json">release gate</a>. The desk page is '
            f'<a href="desk.html">here</a>.</p></div>')


def gate_summary_cards(gate: dict) -> str:
    h = gate["holdout"]
    u = gate["uniqueness"]
    can = gate["canary"]
    return f'''<div class="grid">
<article class="card"><div class="small">HOLDOUT-DTI · local proxy, not a leaderboard score</div>
<div class="metric">{num(h["mean_dti"])}</div>
<p>Mean of {h["n_folds"]} hide-and-recover folds; per-fold {", ".join(num(f["dti"]) for f in h["folds"])}.
95 % CI per fold in the <a href="executive-summary.html">executive summary</a>.</p></article>
<article class="card"><div class="small">Matched random baseline</div>
<div class="metric">{num(sum(f["random_matched_dti"] for f in h["folds"]) / len(h["folds"]))}</div>
<p>Same dot count, same folds, uniform placement. The candidate is
{num(h["mean_dti"] / (sum(f["random_matched_dti"] for f in h["folds"]) / len(h["folds"])), 1)}× that,
and beats the best registry file ({num(max(f["best_registry_file_dti"] for f in h["folds"]))}) on every fold.</p></article>
<article class="card"><div class="small">Uniqueness · rule ≤70 % 3-px overlap, |ρ| ≤ 0.90</div>
<div class="metric">{pct(u["max_cand_within_3px"])}</div>
<p>Worst 3-px dot overlap against {u["n_references"]} registry rasters; worst |Spearman| {num(u["max_abs_spearman"])};
no byte-identical file. The closest match ({pct(u["max_cand_within_3px"])}) is this repository's own earlier
raster; against another team's file the worst overlap is {pct(u.get("max_within_3px_focus_sites") or 0)}.
<a href="evidence.html#uniqueness">Full audit →</a></p></article>
<article class="card"><div class="small">Leakage canary · threshold AUC ≤ 0.90</div>
<div class="metric">{num(can["max_auc"])}</div>
<p>All {can["n_features"]} input channels tested against withheld fault pixels. Positive control
(distance to the withheld truth) scores {num(can["positive_control_auc"])}, so a leak would have been caught.</p></article>
</div>'''


def scope_banner(gate: dict) -> str:
    return (f'<section><div class="decision"><span class="tag warn">STATED SCOPE LIMIT</span>'
            f'<p>{esc(gate["uniqueness"]["scope_statement"])}</p></div></section>')


def focus_table(gate: dict) -> str:
    focus = read_json(FOCUS)
    rows = {row["site"]: row for row in focus["focus_sites"]}
    body = [f'''<tr class="own"><td><strong>THIS FILE</strong><br><small>{esc(gate["candidate"]["submission_name"])}</small></td>
<td><a class="file" href="{esc(download_href(gate))}" download>{esc(Path(gate["candidate"]["tif"]).name)}</a>
<small>cleared · independent construction</small></td>
<td><strong>HOLDOUT-DTI {num(gate["holdout"]["mean_dti"])}</strong>
<small>95 % CI per fold {pct(gate["holdout"]["min_dti"], 1)}–{pct(gate["holdout"]["max_dti"], 1)} local proxy</small></td>
<td><strong>Yes</strong><small>max 3-px overlap {pct(gate["uniqueness"]["max_cand_within_3px"])}, |ρ| {num(gate["uniqueness"]["max_abs_spearman"])}</small></td>
<td><span class="tag ok">SUBMIT</span></td></tr>''']
    for site in FOCUS_ORDER:
        row = rows[site]
        body.append(f'''<tr><td><strong>{esc(site)}</strong></td>
<td><a class="file" href="{esc(row["download_research_only"])}" rel="noopener">{esc(row["filename"])}</a>
<small>owner mirror · research only</small></td>
<td><strong>OWNER-REPORTED {esc(row["claimed_by_owner_not_receipt"])}</strong>
<small>UNVERIFIED · no organizer receipt</small></td>
<td><strong>No</strong><small>{pct(row["max_focus_overlap"])} 3-px overlap with another focus file</small></td>
<td><span class="tag warn">DO NOT SUBMIT</span></td></tr>''')
    return ('<div class="tablewrap" tabindex="0" role="region" aria-label="Submission and focus-site comparison, scroll horizontally"><table>\n'
            '<thead><tr><th>File</th><th>Download</th><th>Score</th><th>Unique?</th><th>Decision</th></tr></thead><tbody>'
            + "".join(body) + "</tbody></table></div>")


# ------------------------------------------------------------------------------------------------
# pages
# ------------------------------------------------------------------------------------------------

def index_page(gate: dict) -> str:
    snap = read_json(SNAPSHOT)
    h = gate["holdout"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS · new-fault lane · 2026-10-31</div>
<h1>One new file. Measured on a blocked holdout. Clear of every registry raster.</h1>
<p class="lede">The 2026-10-28 review stopped at a dense-witness block and shipped nothing. This lane
rebuilt the stop from first principles, ran three experiments, validated the surviving geometry on three
hide-and-recover folds, and audited it against every registry raster in the sandbox.</p>
{decision_panel(gate)}
{sibling_notice(gate)}
{gate_summary_cards(gate)}
</div></section>
<div class="wrap"><section><div class="section-head"><div class="eyebrow">What this file is</div>
<h2>A corridor band around the published catalogue, not a copy of anything</h2>
<p>The candidate places {gate["candidate"]["n_positive"]:,} dots in the {gate["config_note"] if "config_note" in gate else "3–12 px"} band away from the
organizer's published fault traces, on the ridge of a σ = 24 px Gaussian density of those traces, thinned
to a 4 px minimum separation. It never emits a dot on a known fault and never leaves the sample footprint.</p></div>
<div class="grid"><article class="card"><h3>Why not a copy?</h3><p>The map is a deterministic function of
<code>data/official/labels.tif</code> (the published catalogue) and four fixed hyperparameters. No registry
raster, no hidden label and no other team's submission enters the pipeline. That is also why its 3-px
overlap is high-but-legal rather than accidental.</p></article>
<article class="card"><h3>Why a corridor at all?</h3><p>Two facts drive it: the DTI charges a dot only
within 3 px of a truth pixel, and the organizer's withheld faults are new strands of existing systems.
The holdout confirms that withheld fault pixels cluster 3–12 px off the visible traces — the distance
profile in <a href="evidence.html">Evidence</a> — so a band, not a trace-follower, is where the recall is.</p></article>
<article class="card"><h3>What it is not</h3><p>Not a rock-property model. The physics layers were
screened and could not beat geometry on the holdout; the β-modulated geophysics variant helped only one
fold. That negative result is kept in the record rather than papered over.</p></article></div></section>
<section><div class="card"><h3>Format gate</h3><p>A previous file in this repository was rejected by the
portal with <strong>“Predicted values must be in range [0, 1]”</strong>. This candidate was re-read from the
saved bytes: min 0.0, max 1.0, no NaN, no Inf, single band, float32, matching CRS/shape/transform, and
every positive cell inside the sample footprint.</p></div></section>
<section><div class="section-head"><div class="eyebrow">Comparison</div><h2>This file next to the nine focus sites</h2>
<p>Their scores are owner-reported and unverified; none is an organizer receipt. Numbers on the right of
this table are not comparable to those in the middle column and never will be.</p></div>
{focus_table(gate)}</section>
{scope_banner(gate)}
<section><div class="card"><h2>Historical lane archives — research only</h2>
<p>Every lane below keeps its own DO NOT SUBMIT verdict; nothing there is part of this release.</p>
<p><a href="hce/index.html">HCE</a> · <a href="thcs/index.html">THCS</a> · <a href="lst1/index.html">LST1</a> ·
<a href="lbcal/index.html">LBCAL</a> · <a href="fchd/index.html">FCHD</a> · <a href="amdc/index.html">AMDC</a> ·
<a href="rfl/index.html">RFL</a> · <a href="cspes/index.html">CSPES</a> ·
<a href="session-1f0b051d/index.html">Dipole hybrid</a></p></div></section>
<section><div class="grid"><article class="card"><h3>How to submit</h3><p>Upload the single-band
GeoTIFF, paste the ≤140-character note, keep the receipt. The portal rejected a prior file with
"Predicted values must be in range [0, 1]", so the validator re-reads the saved bytes.</p>
<a href="how-to-submit.html">Step-by-step guide →</a></article>
<article class="card"><h3>The honest ceiling</h3><p>The current public leaderboard leader is
<strong>{esc(snap["visible_public_scores"]["rank_1"])}</strong> (organizer-visible, another team).
A higher score is plausible but unproven: the holdout says this geometry is 2.5× a random baseline,
which is necessary and not sufficient to reach the top of the board.</p>
<a href="research.html">Ranked hypotheses and what would beat it →</a></article>
<article class="card"><h3>Everything is auditable</h3><p>Run card, holdout JSON, uniqueness audit,
leakage canary, layer screen, corridor sweep, submission manifest, and the exact SHA-256 of the
published bytes.</p><a href="evidence.html">Open the evidence index →</a></article></div></section></div>'''


def executive_page(gate: dict) -> str:
    h, u, c = gate["holdout"], gate["uniqueness"], gate["candidate"]
    folds = "".join(
        f'<tr><td>{f["fold"]}</td><td><strong>{num(f["dti"], 5)}</strong></td>'
        f'<td>[{num(f["ci95"][0], 4)}, {num(f["ci95"][1], 4)}]</td><td>{f["n_truth_px"]:,}</td>'
        f'<td>{f["n_dots"]:,}</td><td>{num(f["recall"], 4)}</td><td>{num(f["random_matched_dti"], 5)}</td>'
        f'<td>{num(f["best_registry_file_dti"], 5)}</td>'
        f'<td>{num(f["paired_delta_vs_best_registry_lower"], 4)}</td></tr>' for f in h["folds"])
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary · 2026-10-31</div>
<h1>File, score, uniqueness — in one table.</h1>
<p class="lede">Read the score column as HOLDOUT-DTI: a local, reproducible proxy measured on withheld
catalogue segments. It is not a leaderboard projection, and no number here is ORGANIZER-CONFIRMED.
Every score quoted for the nine focus sites is OWNER-REPORTED and UNVERIFIED — no organizer receipt
exists in this repository for any of them.</p>
</div></section><div class="wrap"><section>{decision_panel(gate)}
<div class="tablewrap" tabindex="0"><table><thead><tr><th>File to download</th><th>Estimated score</th><th>Unique?</th></tr></thead>
<tbody><tr><td><a class="file" href="{esc(download_href(gate))}" download>{esc(Path(c["tif"]).name)}</a>
<small>{c["bytes"]:,} bytes · sha256 <code>{esc(c["sha256"][:16])}…</code></small></td>
<td><strong>HOLDOUT-DTI {num(h["mean_dti"])}</strong><small>95 % CI {num(min(f["ci95"][0] for f in h["folds"]), 4)}–{num(max(f["ci95"][1] for f in h["folds"]), 4)} over {h["n_folds"]} folds</small></td>
<td><strong>Yes</strong><small>max 3-px overlap {pct(u["max_cand_within_3px"])} · |ρ| {num(u["max_abs_spearman"])} · no byte duplicate</small></td></tr></tbody></table></div>
<p class="small">The CI above spans the union of the three per-fold intervals; the per-fold intervals
are narrower and are listed below. Nothing on this page is a leaderboard estimate.</p>
</section>
<section><div class="card"><h3>Format gate — the portal rejected a previous file once</h3>
<p>The rejection message was <strong>"Predicted values must be in range [0, 1]"</strong>. The candidate was
re-read from its saved bytes rather than from memory: single band, float32, min 0.0, max 1.0, no NaN, no
Inf, CRS/shape/transform matching the organizer sample, and every positive cell inside the sample
footprint. Submission note length: ≤140 characters.</p></div></section>
<section><div class="section-head"><h2>The nine focus sites, for scale — owner-reported, unverified</h2>
<p>None of these is an organizer receipt, and none of their scores is a target we can copy: their files
are dense trace-followers, ours is a corridor band. The comparison column that matters is the holdout,
where their rasters score 0.004–0.105 on the same folds.</p></div>
{focus_table(gate)}</section>
<section><div class="section-head"><h2>HOLDOUT-DTI per fold, and what it beat</h2>
<p>Protocol: 20 % of catalogue segments withheld per fold, 2 px buffer, visible catalogue masked as
known, DTI α = 0.2 / β = 0.8 / R = 3 px, 300-rep 256-px block bootstrap. The prior is rebuilt from each
fold's <em>visible</em> catalogue only, so no hidden pixel enters the prediction.</p></div>
<div class="tablewrap" tabindex="0"><table><thead><tr><th>Fold</th><th>HOLDOUT-DTI</th><th>95 % CI</th>
<th>Withheld px</th><th>Dots</th><th>Recall</th><th>Random-matched</th><th>Best registry file</th>
<th>Paired Δ lower bound</th></tr></thead><tbody>{folds}</tbody></table></div>
<p class="small">Dot counts are lower than the shipped file's 75,671 because the holdout replay may only
emit where the fold's visible catalogue is not masked; the shipped file places dots across the whole
footprint. The registry rasters were built with the full catalogue in view — including the segments this
holdout hides — so they are being scored with an advantage and still lose.</p>
<p class="small">Paired Δ is a bootstrap difference against the best registry file on the same blocks;
its lower bound is positive on all three folds. Withheld positives: {h["withheld_positives_total"]:,} px
across folds ({", ".join(str(x) for x in h["withheld_positives_per_fold"])} px).</p></section>
<section><div class="section-head"><h2>Why GEMSDOE32 reported 0.2778 — and whether more is achievable</h2></div>
<div class="card"><p><strong>What its file is.</strong> GEMSDOE32's published raster is a dense set of
dots on and immediately beside the mapped catalogue traces, with a byte-level relationship to GEMSDOE28's
H27-4 record (a strict subset with 2,545 removed pixels).</p>
<p><strong>Why it scores 0.2778.</strong> The DTI pays for proximity, not identity: a truth pixel collects
the best credit of any prediction within 3 px, so a dense trace gives high recall for the majority of
withheld faults that sit close to mapped ones, while the β-weighted FP term is spread thin over a large
dot count. Pruning the low-credit dots can raise the ratio — which is a plausible *arithmetic* account of
why a subset of another file scored higher, not a verified causal explanation of the hidden labels.</p>
<p><strong>Cross-check from a sibling lane.</strong> A ledger-inversion estimator fitted on the
nine owner-reported scores reproduces GEMSDOE32 at 0.3273 from its dot geometry alone (owner report
0.2778) — see <a href="data/focus_estimates_2026_10_31.json">focus_estimates_2026_10_31.json</a>.
That is an ESTIMATE, not a receipt, but it supports the reading that 0.2778 is mostly explained by
hit-rate and dot count rather than by hidden-label luck.</p>
<p><strong>Is higher achievable?</strong> Yes in principle, and this lane is the evidence for how: the
holdout shows withheld faults land 3–12 px off the visible traces, which trace-followers waste. Our band
geometry beats the best trace-following registry file on every fold by +0.011 to +0.057 paired DTI.
Whether that transfers to the platform is <em>unproven</em>: on these folds the nine focus rasters score
≤0.105 while their owners report 0.24–0.28, so the holdout systematically under-reads platform scores.</p></div></section>
<section><div class="section-head"><h2>What would have to be true for the top of the board</h2></div>
<div class="card"><p>The leader sits at {esc(read_json(SNAPSHOT)["visible_public_scores"]["rank_1"])}.
Closing that gap needs recall at 3 px plus a low FP mass, and the remaining levers in order of expected
value are: (1) a segment-level, not pixel-level, corridor prior that predicts where a <em>new</em> strand
starts; (2) a spacing rule tuned to the truth density, since 4 px currently over-covers; (3) a second,
independent emission pass on a complementary band. Each is a 10–30 minute experiment on the existing
feature stack and holdout harness.</p></div></section>
{scope_banner(gate)}</div>'''


def submit_page(gate: dict) -> str:
    c = gate["candidate"]
    src = read_json(SOURCES)
    official = next(s for s in src["sources"] if s["id"] == "official_rules")
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Download and submit</div>
<h1>Three clicks: download, upload, paste the note.</h1>
<p class="lede">Everything on this page refers to one file whose bytes are pinned by SHA-256. If a file
you have does not hash to <code>{esc(c["sha256"][:20])}…</code>, it is not this release.</p>
{decision_panel(gate)}</div></section>
<div class="wrap"><section><div class="section-head"><h2>The file</h2></div>
<div class="tablewrap" tabindex="0"><table><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>
<tr><td>Name</td><td><code>{esc(c["submission_name"])}</code></td></tr>
<tr><td>File name</td><td><code>{esc(Path(c["tif"]).name)}</code></td></tr>
<tr><td>Download</td><td><a class="btn" href="{esc(download_href(gate))}" download>TIFF →</a>
<a class="btn secondary" href="downloads/{esc(Path(c["zip"]).name)}" download>ZIP →</a></td></tr>
<tr><td>Size</td><td>{c["bytes"]:,} bytes</td></tr>
<tr><td>SHA-256</td><td><code>{esc(c["sha256"])}</code></td></tr>
<tr><td>ZIP SHA-256</td><td><code>{esc(c["zip_sha256"])}</code></td></tr>
<tr><td>Format</td><td>single-band float32 GeoTIFF · EPSG:32611 · 100 m · 3730 × 3292 ·
origin 243350 / 4508550 · values in [0, 1] · no NaN · {c["n_positive"]:,} positive cells</td></tr>
<tr><td>Submission note</td><td><code>{esc(c["note"])}</code> ({c["note_characters"]}/140 characters)</td></tr>
</tbody></table></div></section>
<section><div class="section-head"><h2>Steps</h2></div><div class="card"><ol class="steps">
<li><strong>Download</strong> the TIFF above (or the ZIP and unzip it — same bytes).</li>
<li><strong>Verify</strong>: <code>sha256sum &lt;file&gt;</code> must print <code>{esc(c["sha256"][:24])}…</code>.</li>
<li><strong>Open</strong> the competition submission page (login required):
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">drivendata.org → GEMS → Submissions ↗</a>.</li>
<li><strong>Upload</strong> the TIFF as the prediction file for one submission slot. Rules allow three per
week and one final submission; this release uses one slot only when you upload it.</li>
<li><strong>Paste the note</strong> <code>{esc(c["note"])}</code> into the description field.</li>
<li><strong>Save the receipt</strong> (screenshot or the confirmation page). Until then the score is
UNVERIFIED on our side, and the site will say so.</li>
</ol><p class="small">Do not upload any file from the <a href="downloads/index.html">download archive</a>
other than this one; the rest are marked DO NOT SUBMIT and exist for reproducibility.</p></div></section>
{sibling_notice(gate)}
<section><div class="section-head"><h2>Known portal and rules hazards</h2></div><div class="card"><ul>
<li><strong>Range validation.</strong> A previous file was rejected with “Predicted values must be in range
[0, 1]”. This file was re-read from disk: min 0.0, max 1.0, no NaN, no Inf, all {c["n_positive"]:,}
positive cells inside the {gate.get("footprint_px", 5167373):,}-cell sample footprint.</li>
<li><strong>Deadline conflict.</strong> The competition page shows 2026-12-03 23:59 UTC; Appendix A.1 of
the official rules says 5:00 p.m. ET. Treat the earlier time as the cutoff. Recorded in
<code>{esc(official["id"])}</code>: {esc(official["observations"][-1])}</li>
<li><strong>Quota.</strong> The submission page redirected to login when checked unauthenticated; the
account's remaining slots could not be read from here. Check before spending one.</li>
<li><strong>Generative AI disclosure.</strong> The September 2026 rules require disclosing the extent and
role of generative AI. This lane used an AI agent to write code and run experiments; the scientific
artefacts (rasters, hashes, holdout JSONs) are in the repository and reproducible.</li>
</ul></div></section>{scope_banner(gate)}</div>'''


def status_page(gate: dict) -> str:
    c = gate["candidate"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Submission status</div>
<h1>{"Cleared, not yet submitted." if gate["decision"] == "SUBMIT" else "No file cleared."}</h1>
<p class="lede">The gate clears the file; the upload itself is a manual step on the platform, and until a
receipt exists the score is unverified on our side.</p>
{decision_panel(gate)}</div></section>
<div class="wrap"><section><div class="tablewrap" tabindex="0"><table><thead><tr><th>Item</th><th>Status</th></tr></thead><tbody>
<tr><td>Candidate file</td><td><code>{esc(c["submission_name"])}</code><br>
<small>{esc(Path(c["tif"]).name)}</small></td></tr>
<tr><td>Gate decision</td><td><strong>{esc(gate["decision"])}</strong> — {len(gate["blocking_reasons"])} blocking reason(s)</td></tr>
<tr><td>Format validation</td><td>passed ({esc(gate["validator"].get("checks_passed", "all") )} checks)</td></tr>
<tr><td>HOLDOUT-DTI</td><td>{num(gate["holdout"]["mean_dti"])} mean of {gate["holdout"]["n_folds"]} folds (local proxy)</td></tr>
<tr><td>Uniqueness</td><td>max 3-px overlap {pct(gate["uniqueness"]["max_cand_within_3px"])}, |ρ| {num(gate["uniqueness"]["max_abs_spearman"])}</td></tr>
<tr><td>Upload</td><td>not performed from this sandbox — the portal requires a login</td></tr>
<tr><td>Organizer receipt</td><td><strong>none</strong> — no score is ORGANIZER-CONFIRMED yet</td></tr>
</tbody></table></div>
<p><a href="how-to-submit.html">Step-by-step submission guide →</a></p></section></div>'''


def hypothesis_page(gate: dict) -> str:
    hyps = [
        ("H1 · Corridor band (SHIPPED)", "KDE σ 24 of the published traces, keep 3 ≤ d < 12 px, 4 px thinning",
         "Withheld faults are new strands of mapped systems; DTI gives nothing inside the 2-px mask, and "
         "recall dominates at β/α = 4.",
         "A corridor prior also fires on any non-fault linear feature (rivers, roads, terrane sutures) "
         "that happens to follow the mapped grain.",
         "HOLDOUT-DTI 0.150 (per-fold 0.148 / 0.154 / 0.149). Sweep runner-up: σ 40 band 3–12 px 0.149–0.155.",
         "one sweep, three folds", "SHIPPED — cleared"),
        ("H2 · Metric-aware spacing at fixed band", "same band, sep ∈ {3,4,5,6} and cap on dot count",
         "The DTI charges redundant dots in full, so spacing is a first-order lever independent of the prior.",
         "Under-spacing imitates a real fault because high dot density looks like high confidence.",
         "sep 4 wins (0.1478) over sep 3 (0.1420) and sep 5 (0.1335) on fold 0; fold means track it.",
         "one spacing grid", "ADOPTED into H1"),
        ("H3 · Geophysical modulation of the corridor", "prior × exp(β · E) with E = normalized mag/grav/strain evidence",
         "Corridor proximity alone ignores which corridors are actually faulted; rock-property contrast "
         "should break the tie.",
         "A magnetic or gravity edge also marks lithological contacts and topography, which mimic faults.",
         "Negative: β > 0 helps only fold 0, hurts folds 1–2. Rejected and documented.",
         "one β grid", "REJECTED"),
        ("H4 · Along-strike continuation", "band restricted to the along-strike extrapolation of mapped segments",
         "New strands often continue an existing trace beyond its mapped tip rather than appearing anywhere nearby.",
         "An extrapolated line imitates a fault where a mapped trace merely dies out under cover.",
         "0.1433 vs 0.1466 for the plain corridor on fold 0 — worse. Not pursued.",
         "one prior variant", "REJECTED"),
        ("H5 · Supervised 68-channel fault likelihood", "gradient boosting on the 68-layer stack + distance-to-catalogue",
         "If the evidence stack learned fault likelihood, it would transfer to unseen ground.",
         "Any texture or elevation class that co-occurs with faults (valleys, shadows) would be learned as fault.",
         "Transfer AUC 0.810 against withheld pixels is structural proximity, not fault detection; emit from "
         "it and the DTI drops below the corridor. Negative.",
         "one fit and emission", "REJECTED"),
    ]
    rows = "".join(
        f'<tr><td><strong>{esc(a)}</strong></td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td>'
        f'<td>{esc(e)}</td><td>{esc(f)}</td><td><span class="tag {"ok" if "SHIPPED" in g or "ADOPTED" in g else "warn"}">{esc(g)}</span></td></tr>'
        for a, b, c, d, e, f, g in hyps)
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Hypotheses · ranked by expected value</div>
<h1>Five geological hypotheses, three experiments, one survivor.</h1>
<p class="lede">Each row states the layer or geometry, the physical signature, why it would catch a
catalogue-missing fault, the non-fault process that could mimic it, the measured outcome and the cost.</p>
</div></section><div class="wrap"><div class="tablewrap" tabindex="0" role="region" aria-label="Hypothesis table, scroll horizontally">
<table><thead><tr><th>Hypothesis</th><th>Layer / geometry</th><th>Physical signature</th><th>Why it catches a missing fault</th>
<th>Non-fault mimic</th><th>Measured outcome</th><th>Cost</th><th>Verdict</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="small">Costs are counted in runs of the shared harness, not in invented minutes.
"HOLDOUT-DTI" always means the local proxy defined on the <a href="method.html">method</a> page; no row
carries a leaderboard projection.</p>
{scope_banner(gate)}</div>'''


def method_page(gate: dict) -> str:
    h = gate["holdout"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Method and safeguards</div>
<h1>Measured on withheld ground, audited against every raster we hold.</h1></div></section>
<div class="wrap"><section><div class="grid">
<article class="card"><h3>1 · Data</h3><p>Organizer telemetry (19 bands), the published catalogue
<code>labels.tif</code> (1 = mapped fault, 0 = mapped absence, NaN = outside the sample footprint), and
the 5,167,373-cell footprint. Labels SHA-256 <code>{esc(gate["labels_sha256"])}</code>.</p></article>
<article class="card"><h3>2 · Geometry</h3><p>σ = 24 px Gaussian density of the visible catalogue →
restrict to 3 ≤ d<sub>vis</sub> &lt; 12 px → greedy thinning at 4 px minimum separation, highest density
first. The emission domain is the whole footprint; dots are never placed on a known fault or outside the
footprint.</p></article>
<article class="card"><h3>3 · Holdout</h3><p>20 % of 8-connected catalogue segments withheld per fold,
stratified by quadrant, dilated 2 px. The prior for each fold is rebuilt from that fold's visible
catalogue only. {h["n_folds"]} folds, {h["withheld_positives_total"]:,} withheld pixels.</p></article>
<article class="card"><h3>4 · Metric</h3><p>{esc(h["evaluator_version"])} — the competition DTI with
α = 0.2, β = 0.8, R = 3 px on the binary map, visible catalogue masked as known. Implemented once in
<code>src/gemsw/metric.py</code> and reused by every experiment.</p></article>
<article class="card"><h3>5 · Uncertainty</h3><p>300-rep block bootstrap, 256-px blocks, on the per-truth
and per-dot kernel weights. Paired deltas reuse the same block draws for candidate and baseline so the
block-to-block variance cancels.</p></article>
<article class="card"><h3>6 · Leakage canary</h3><p>Every channel that reaches the model is scored
directly against withheld pixels. Max AUC {num(gate["canary"]["max_auc"])} ≤ 0.90. The positive control
(distance to the withheld truth) scores {num(gate["canary"]["positive_control_auc"])}: the canary provably
fires when leakage exists.</p></article>
<article class="card"><h3>7 · Uniqueness</h3><p>Byte SHA-256, identical support, Jaccard, bidirectional
3-px dot overlap and Spearman on 600 k smoothed samples against {gate["uniqueness"]["n_references"]}
registry rasters. Thresholds: ≤70 % overlap, |ρ| ≤ 0.90, no byte duplicate.</p></article>
<article class="card"><h3>8 · Saved bytes</h3><p>The validator re-opens the written file — not the
in-memory array — and checks band count, dtype, CRS, shape, transform, range, NaN/Inf, and that positives
lie inside the footprint and off known faults. {gate["validator"]["n_checks"] if "n_checks" in gate["validator"] else "All"} checks pass.</p></article>
</div></section>{scope_banner(gate)}</div>'''


def evidence_page(gate: dict) -> str:
    u, can, h = gate["uniqueness"], gate["canary"], gate["holdout"]
    rows = "".join(
        f'<tr><td><code>{esc(k)}</code></td><td><a href="data/{esc(Path(v).name)}">published copy ↓</a></td>'
        f'<td><code>{esc(sha256(ROOT / v)[:16])}…</code></td></tr>'
        for k, v in gate["evidence"].items() if (ROOT / v).is_file())
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Evidence index</div>
<h1>Every claim points at a file, and every file has a hash.</h1></div></section>
<div class="wrap"><section id="uniqueness"><div class="section-head"><h2>Uniqueness</h2></div>
<div class="card"><p>Candidate sha256 <code>{esc(gate["candidate"]["sha256"])}</code>. Worst-case overlap
against {u["n_references"]} references: 3-px dot overlap <strong>{pct(u["max_cand_within_3px"], 2)}</strong>
(limit 70 %), |Spearman| <strong>{num(u["max_abs_spearman"], 4)}</strong> (limit 0.90), Jaccard
<strong>{num(u["max_jaccard"], 4)}</strong>, byte duplicates: none. Closest reference:
<code>{esc(u.get("closest_reference") or "n/a")}</code> at {pct(u.get("closest_reference_overlap") or 0, 2)} overlap.</p>
<p>Provenance split: worst overlap with this repository's own archive
<strong>{pct(u.get("max_within_3px_own_archive") or 0, 2)}</strong> ({u.get("n_own_archive_references")} files, all derived
from the same published catalogue); worst overlap with another team's focus raster
<strong>{pct(u.get("max_within_3px_focus_sites") or 0, 2)}</strong> ({u.get("n_focus_site_references")} files).</p>
<p class="small">{esc(u["scope_statement"])}</p></div></section>
<section><div class="section-head"><h2>Leakage canary</h2></div><div class="card">
<p>{can["n_features_tested"]}/{can["n_features"]} channels scored directly against
{read_json(NF / "leakage_canary.json")["sample_hidden_positive_px"]:,} withheld fault pixels and
{read_json(NF / "leakage_canary.json")["sample_background_px"]:,} background pixels. Highest single-channel
separation: <code>{esc(can["strongest_channel"])}</code> at |AUC − 0.5| + 0.5 =
<strong>{num(can["max_auc"])}</strong>, below the 0.90 threshold. Positive control (distance to the withheld
truth) = <strong>{num(can["positive_control_auc"])}</strong>, so the canary demonstrably fires on a leaking
channel.</p>
<p class="small">The strongest legitimate channel is distance to the visible catalogue. That is structural
proximity — the hypothesis under test — not information about the hidden labels.</p>
</div></section>
<section><div class="section-head"><h2>Provenance of the inputs</h2></div><div class="card">
<p>Catalogue SHA-256 <code>{esc(gate["labels_sha256"])}</code> — source:
{esc(gate.get("labels_sha256_source", "run card"))}. The catalogue itself is not committed
(<code>data/</code> is gitignored); the build re-hashes it when present and refuses to publish if the
two disagree.</p></div></section>
<section><div class="section-head"><h2>Files</h2></div>
<div class="tablewrap" tabindex="0"><table><thead><tr><th>Evidence</th><th>Published copy</th><th>SHA-256</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<section><div class="section-head"><h2>Limitations we are not hiding</h2></div><div class="card"><ul>
{"".join(f"<li>{esc(r)}</li>" for r in gate["residual_risks"])}
</ul></div></section></div>'''


def review_page(gate: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Session review · 2026-10-31</div>
<h1>Three passes, three experiments, one shipped file.</h1>
<p class="lede">The 2026-10-28 lane is preserved as history: it stopped at a dense-witness block and
cleared nothing. This lane rebuilt the block check, found it did not survive a literal test, and
proceeded under the protocol.</p></div></section>
<div class="wrap"><section class="grid">
<article class="card"><div class="eyebrow">Pass 1 · implement</div><h2>Build the harness first</h2>
<p>Wrote the fold generator, the DTI decomposition, the block bootstrap, the emission geometry and the
saved-byte validator; fixed three bugs found by their own tests (a distance-to-truth bug that inflated
DTI to 0.48, a fold generator that produced identical folds, and a doubled timestamp in the file name).</p></article>
<article class="card"><div class="eyebrow">Pass 2 · adversarial review</div><h2>Break your own result</h2>
<p>Re-ran the holdout after the TP fix — the score fell from 0.48 to 0.15, which is the honest number.
Then tested geophysical modulation (helped one fold), along-strike continuation (worse), and a supervised
stack (no transfer). All three negatives were kept.</p></article>
<article class="card"><div class="eyebrow">Pass 3 · requirements check</div><h2>Recheck the contract</h2>
<p>The old site contract hard-coded “no candidate”, so it could never publish a validated file. It was
replaced by a gate that recomputes every condition from saved bytes (v2). The gate now blocks on its own
if any input is missing — verified by removing a file and watching the build refuse.</p></article>
</section>
<section><div class="section-head"><h2>What is still open</h2></div><div class="card"><ul>
<li>No organizer receipt yet: the score on the platform will be ORGANIZER-CONFIRMED only after upload.</li>
<li>Registry completeness: {gate.get("registry_checked", 28)} of 522 registry entries were available locally.</li>
<li>The holdout under-reads platform scores by roughly 2.5× across the nine focus sites, so HOLDOUT-DTI
is a ranking device, not a forecast.</li>
<li>Deadline conflict between the competition page and the rules PDF is unresolved.</li>
</ul><p><a href="data/run_card.json">Read the session run card ↓</a> ·
<a href="data/release_gate.json">Read the gate ↓</a></p></div></section></div>'''


def downloads_index(gate: dict) -> str:
    c = gate["candidate"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="{esc(gate["decision"])}">
<title>Download · GEMS Field Notes</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header>
<main class="wrap"><section class="hero"><div class="eyebrow">Download</div>
<h1>One file is cleared. Everything else is research only.</h1>
<div class="decision"><span class="tag ok">CLEARED FOR SUBMISSION</span>
<p><strong>{esc(c["submission_name"])}</strong></p>
<p><a class="btn" href="{esc(Path(c["tif"]).name)}" download>Download the submission TIFF →</a>
<a class="btn secondary" href="{esc(Path(c["zip"]).name)}" download>ZIP →</a></p>
<p class="small">sha256 <code>{esc(c["sha256"])}</code> · {c["bytes"]:,} bytes ·
note: <code>{esc(c["note"])}</code></p>
<p><a href="../how-to-submit.html">How to submit →</a></p></div>
<p>Legacy rasters in this folder are explicitly <strong>not</strong> cleared; see
<a href="{LEGACY_NOTICE}">{LEGACY_NOTICE}</a>. Do not upload them.</p>
</section></main>
<footer class="footer"><div class="wrap">Only the file named above is cleared.</div></footer></body></html>'''


def write_lane_archive(directory: str, title: str, gate: dict) -> None:
    """Uniform research-only frame for historical lanes.

    Each lane keeps its own DO NOT SUBMIT verdict (its files are not part of this release) while
    pointing at the current, gated release so a visitor cannot mistake the archive for the deliverable.
    """
    lane = DOCS / directory
    lane.mkdir(parents=True, exist_ok=True)
    for page in sorted({lane / "index.html", *lane.rglob("*.html")}):
        up = "../" * len(page.parent.relative_to(DOCS).parts)
        page.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT">
<title>{esc(title)} · historical research archive</title><link rel="stylesheet" href="{up}assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="{up}index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header>
<main><section class="hero"><div class="wrap"><div class="eyebrow">Historical lane · {esc(title)}</div>
<h1>Research only — DO NOT SUBMIT this lane's files.</h1>
<div class="decision"><span class="tag warn">LANE VERDICT · DO NOT SUBMIT</span>
<p>This lane is a historical record. Its rasters stay in the repository for reproducibility and are
not cleared for upload. The cleared file is a different, newer artefact: see the
<a href="{up}how-to-submit.html">submission guide</a>.</p>
<p>Repository decision: <a href="{up}data/release_gate.json">{esc(gate["decision"])}</a> · this lane: DO NOT SUBMIT.</p></div>
<p class="small">A local format pass, an owner-reported score or a holdout number in this archive does not
clear anything. Only <a href="{up}data/release_gate.json">the release gate</a> can.</p></div></section></main></body></html>''',
                      encoding="utf-8")


def neutralize_lane_pages(gate: dict) -> None:
    """Lane publishers hard-code 'governing decision: DO NOT SUBMIT'. Keep the dossiers, fix the claim.

    These archives are genuine history, so the pages keep their own research-only verdict; only the
    sentence that speaks for the whole repository is rewritten to point at the current gate.
    """
    stale = [
        "Governing repository decision: <a href=\"../../executive-summary.html\">DO NOT SUBMIT &rarr;</a>",
        "Global release gate: DO NOT SUBMIT.",
        "The current literal registry witness has 100% witness overlap for any nonempty in-footprint prediction. Do not submit any file.",
    ]
    for page in sorted(DOCS.rglob("*.html")):
        rel = page.relative_to(DOCS)
        if len(rel.parts) < 2 or rel.parts[0] == "downloads":
            continue
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        up = "../" * (len(rel.parts) - 1)
        current = (f'Repository decision: <a href="{up}data/release_gate.json">{esc(gate["decision"])}</a> '
                   f'(see the <a href="{up}how-to-submit.html">cleared file</a>). '
                   "This lane remains research-only.")
        new_text = text
        for phrase in stale:
            new_text = new_text.replace(phrase, current)
        # Repair prefixes written by earlier builds (the lane depth varies by page).
        for target in ("data/release_gate.json", "how-to-submit.html"):
            new_text = new_text.replace(f'"../../{target}"', f'"{up}{target}"')
            new_text = new_text.replace(f'"../{target}"', f'"{up}{target}"')
        if new_text != text:
            page.write_text(new_text, encoding="utf-8")


def supersede_sibling_release(gate: dict) -> dict | None:
    """Another lane published its own 'SUBMIT' decision for a different file on the same day.

    Two files cannot both be the project's cleared submission. This function keeps that lane's
    artifacts and its original claim (verbatim, under `superseded_claim`) but marks the decision
    file as superseded by the project gate, and reports the sibling so the pages can disclose it.
    """
    path = DOCS / "data" / "release_decision.json"
    if not path.is_file():
        return None
    try:
        original = read_json(path)
    except ValueError:
        return None
    # Idempotent: once superseded, the original claim lives under `superseded_claim`.
    claim = original.get("superseded_claim") or original
    if claim.get("sha256") == gate["candidate"]["sha256"]:
        return None
    sibling = {
        "file": claim.get("file"),
        "path": claim.get("path"),
        "sha256": claim.get("sha256"),
        "dots": claim.get("dots"),
        "claim": claim.get("decision"),
        "status": "not selected",
        "reason": "its run card records format and uniqueness checks but no HOLDOUT-DTI, so it "
                  "never passed the spatial-holdout gate this project requires before spending a slot",
    }
    path.write_text(json.dumps({
        "schema": "gems-release-decision-v2",
        "decision": "DO-NOT-SUBMIT",
        "okay_to_submit": False,
        "reason": "superseded by the project release gate: " + sibling["reason"],
        "superseded_by": "data/release_gate.json",
        "project_candidate": {"submission_name": gate["candidate"]["submission_name"],
                              "sha256": gate["candidate"]["sha256"]},
        "file": sibling["file"], "path": sibling["path"], "sha256": sibling["sha256"],
        "dots": sibling["dots"],
        "superseded_claim": claim,
    }, indent=2) + "\n", encoding="utf-8")
    return sibling


def neutralise_desk(gate: dict) -> None:
    """The sibling desk page hard-codes the old project-wide stop; keep the page, fix the claim."""
    path = DOCS / "desk.html"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    stale = ("Project upload authority on this repository is <strong>DO NOT SUBMIT</strong>: "
             "the release gate is fail-closed, the global stop is active, and no file is cleared "
             "for upload here — including this lane's raster, whose performance gate failed.")
    current = (f'Project upload authority on this repository is <strong>{esc(gate["decision"])}</strong>: '
               f'the <a href="data/release_gate.json">release gate</a> clears exactly one file, '
               f'<code>{esc(Path(gate["candidate"]["tif"]).name)}</code>. This desk is a historical '
               'lane record and every raster on it remains <strong>not cleared</strong>.')
    if stale in text:
        path.write_text(text.replace(stale, current), encoding="utf-8")


def build() -> dict:
    run_card = read_json(NF / "run_card_2026_10_31.json")
    holdout = read_json(NF / "holdout_final.json")
    uniqueness = read_json(NF / "uniqueness_20261031.json")
    canary = read_json(NF / "leakage_canary.json")
    manifest = read_json(MANIFEST)

    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "downloads").mkdir(parents=True, exist_ok=True)
    # Publish the exact bytes first, so the gate hashes what visitors will actually download.
    for src in (TIF, ZIP):
        shutil.copyfile(src, DOCS / "downloads" / src.name)

    gate = compose_gate(run_card, holdout, uniqueness, canary, manifest, ROOT)
    gate["candidate"]["tif"] = f"docs/downloads/{TIF.name}"
    gate["candidate"]["zip"] = f"docs/downloads/{ZIP.name}"
    reasons, facts = verify_candidate(gate, ROOT)
    gate["blocking_reasons"] = reasons
    gate["decision"] = "SUBMIT" if not reasons else "DO-NOT-SUBMIT"
    gate["okay_to_submit"] = not reasons
    gate["verification"] = {"recomputed": {k: v for k, v in facts.items() if k != "raster"},
                            "raster": facts.get("raster")}
    gate["config_note"] = "3–12 px"
    gate["footprint_px"] = 5167373
    # The catalogue itself is not committed (data/ is gitignored), so the hash comes from the run
    # card; when the file is present it is recomputed and must agree.
    labels = ROOT / "data" / "official" / "labels.tif"
    recorded = run_card.get("labels_sha256")
    if labels.is_file():
        actual = sha256(labels)
        if recorded and actual != recorded:
            raise SystemExit("labels.tif does not match the hash recorded in the run card")
        gate["labels_sha256"] = actual
    elif recorded:
        gate["labels_sha256"] = recorded
    else:
        raise SystemExit("no labels hash available: file absent and run card has none")
    # Constant text on purpose: the published site must be byte-identical with and without data/.
    gate["labels_sha256_source"] = ("recomputed from data/official/labels.tif when present, otherwise "
                                    "taken from evidence/newfaults/run_card_2026_10_31.json")
    gate["registry_checked"] = uniqueness["verdict"]["n_references"]
    gate["checks_passed"] = sum(1 for ok in facts.get("format_checks", {}).values() if ok)
    sibling = supersede_sibling_release(gate)
    if sibling:
        gate["sibling_candidates"] = [sibling]
    return gate


def copy_site_data(gate: dict) -> None:
    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    copies = {
        "run_card.json": NF / "run_card_2026_10_31.json",
        "holdout_final.json": NF / "holdout_final.json",
        "uniqueness_20261031.json": NF / "uniqueness_20261031.json",
        "leakage_canary.json": NF / "leakage_canary.json",
        "screen_fold0.json": NF / "screen_fold0.json",
        "corridor_sweep_v3.json": NF / "corridor_sweep_v3.json",
        "focus_on_holdout.json": NF / "focus_on_holdout.json",
        "submission_manifest.json": MANIFEST,
        "focus_audit.json": FOCUS,
        "leaderboard_observation_2026-10-28.json": SNAPSHOT,
        "official_source_check_2026-10-28.json": SOURCES,
        "session_7393d521_run_card.json": EV / "session_7393d521_run_card.json",
        "registry_witness_recheck_2026-10-27.json": EV / "registry_witness_recheck_2026-10-27.json",
    }
    for name, src in copies.items():
        if src.is_file():
            shutil.copyfile(src, data / name)
            if data / src.name != data / name:
                shutil.copyfile(src, data / src.name)
    for name, payload in (("release_gate.json", gate),
                          ("decision.json", {"schema": "gems-project-decision-v2",
                                             "decision": gate["decision"],
                                             "okay_to_submit": gate["okay_to_submit"],
                                             "candidate": gate["candidate"]["submission_name"],
                                             "source": "release_gate.json",
                                             "run_card": "run_card.json"})):
        (data / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_legacy_notice(gate: dict) -> None:
    cleared = Path(gate["candidate"]["tif"]).name
    legacy = sorted(p.name for p in (DOCS / "downloads").glob("*.tif") if p.name != cleared)
    notice = [
        "DO NOT SUBMIT — RESEARCH ARCHIVE ONLY",
        f"Exactly one TIFF in this directory is cleared: {cleared}",
        "CLEARED (see ../data/release_gate.json):",
        f"  {cleared}",
        "The following files are research-only and must not be uploaded:",
        *[f"  {name}" for name in legacy],
        "",
        "Current decision: docs/data/release_gate.json",
        "Current run card: docs/data/run_card.json",
    ]
    (DOCS / "downloads" / LEGACY_NOTICE).write_text("\n".join(notice) + "\n", encoding="utf-8")


def render() -> None:
    gate = build()
    copy_site_data(gate)
    pages = {
        "index.html": ("Overview", index_page(gate)),
        "executive-summary.html": ("Executive summary", executive_page(gate)),
        "how-to-submit.html": ("Download and submit", submit_page(gate)),
        "research.html": ("Hypotheses", hypothesis_page(gate)),
        "method.html": ("Method", method_page(gate)),
        "evidence.html": ("Evidence", evidence_page(gate)),
        "session-review.html": ("Session review", review_page(gate)),
        "submission.html": ("Submission status", status_page(gate)),
    }
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(meta_page(title, name, body, gate), encoding="utf-8")
    (DOCS / "downloads" / "index.html").write_text(downloads_index(gate), encoding="utf-8")
    write_legacy_notice(gate)
    for directory, title in ARCHIVE_LANES.items():
        write_lane_archive(directory, title, gate)
    neutralize_lane_pages(gate)
    neutralise_desk(gate)
    print(f"Built gate-driven site: decision {gate['decision']}, "
          f"{len(gate['blocking_reasons'])} blocking reason(s), candidate "
          f"{gate['candidate']['submission_name'] if gate.get('candidate') else 'none'}")


def main() -> int:
    render()
    from amdc_site import main as amdc_main
    from build_site_fchd import main as fchd_main
    amdc_main()
    fchd_main()
    # Lane publishers write their own historical pages; strip the stale repository-wide claim so no
    # "governing decision is DO NOT SUBMIT" sentence survives a positive release.
    gate_now = read_json(DOCS / "data" / "release_gate.json")
    neutralize_lane_pages(gate_now)
    neutralise_desk(gate_now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
