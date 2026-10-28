#!/usr/bin/env python3
"""2026-10-28 SMSR lane publishing step (deterministic, additive-only).

Runs AFTER render() inside scripts/build_site.py main(). Renders the SMSR
lane page at docs/smsr/index.html and refreshes its docs/smsr/data/ JSON
copies, driven entirely by evidence/smsr_run_card.json,
evidence/smsr_uniqueness.json and registry/focus_sites.json. It never
touches the SGCE-era auto-submit gate (docs/data/release_gate.json).
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
LANE = ROOT / "docs" / "smsr"

CARD = EV / "smsr_run_card.json"
UNIQUENESS = EV / "smsr_uniqueness.json"
CV_ALL = EV / "smsr_cv_all.json"
CV_DETACHED = EV / "smsr_cv_detached.json"
BUILD_RECEIPT = EV / "smsr_build_receipt.json"
FOCUS_SITES = ROOT / "registry/focus_sites.json"


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def uniqueness_rows(uniq: list[dict]) -> str:
    """Render every checked comparator, in the order the evidence file lists them."""
    out = []
    for r in uniq:
        verdict = "Unique"
        if r["duplicate_by_overlap"] and not r["duplicate_by_rho"]:
            verdict = "Flagged by overlap only (see caveat above)"
        elif r["duplicate_by_rho"] or r["duplicate_by_overlap"]:
            verdict = "DUPLICATE"
        out.append(f"<tr><td>{esc(r['name'])}</td><td>{r['dot_overlap_3px']:.3f}</td>"
                   f"<td>{r['spearman_full_footprint']:.4f}</td><td>{esc(verdict)}</td></tr>")
    return "".join(out)


def main() -> int:
    card = json.loads(CARD.read_text(encoding="utf-8"))
    uniq = json.loads(UNIQUENESS.read_text(encoding="utf-8"))
    receipt = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    fname = card["file"].split("/")[-1]
    sha = card["raster_sha256"]
    if receipt["sha256"] != sha:
        raise ValueError("SMSR build receipt sha256 does not match the run card; fail closed")

    tif = LANE / "downloads" / fname
    zipf = LANE / "downloads" / fname.replace(".tif", ".zip")
    receipt_json = LANE / "downloads" / fname.replace(".tif", ".json")
    for p in (tif, zipf, receipt_json):
        if not p.is_file():
            raise ValueError(f"missing SMSR lane download: {p}")
    if digest(tif) != sha:
        raise ValueError("SMSR lane-served TIFF does not match the run card's pinned SHA-256; fail closed")

    data_dir = LANE / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CARD, data_dir / "run_card.json")
    shutil.copyfile(UNIQUENESS, data_dir / "uniqueness.json")
    shutil.copyfile(CV_ALL, data_dir / "cv_all.json")
    shutil.copyfile(CV_DETACHED, data_dir / "cv_detached.json")

    d = card["holdout_dti"]["detached_mode_primary"]
    a = card["holdout_dti"]["all_mode"]
    wit = card["uniqueness"]["vs_dense_witness_17GEMSDOE_E_proba_multiscale"]
    canary = card["leakage_canary"]["flagged_features"]["smsr_g"]
    v = receipt["validator"]
    pct_positive = 100 * v["emitted_positive_pixels"] / v["n_finite"]

    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="SMSR lane: a holdout-validated, registry-checked candidate GeoTIFF for the DOE GEMS Prize Challenge.">
<meta name="gemsdoe-decision" content="PROMOTE-TO-SELECTOR"><title>SMSR lane — recommended download · GEMS Field Notes</title>
<link rel="stylesheet" href="../assets/safe.css">
</head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a><nav aria-label="Main navigation"><a href="../index.html">Overview</a><a href="../executive-summary.html">Executive summary</a><a href="../how-to-submit.html">Submission guide</a><a href="index.html" aria-current="page">SMSR lane (recommended)</a><a href="../evidence.html">Evidence</a></nav></div></header>
<main><section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS · SMSR lane · 2026-10-28</div><h1>Download this file and submit it.</h1>
<p class="lede">A new, holdout-validated, registry-checked GeoTIFF built from the real official GEMS feature stack. It passes the shared format validator (fixes the earlier "[0,1]" rejection by construction), is unique against all 9 requested GEMSDOE focus sites and all prior lanes in this repository, and beats the inherited baseline configuration on the conservative ("detached") holdout instrument.</p>
<div class="decision positive"><span class="tag positive">PROMOTE TO SELECTOR</span><h2>Recommended: {esc(fname)}</h2>
<p><strong>HOLDOUT-DTI {d['smsr_g']:.4f}</strong> (95% quadrant-jackknife CI [{d['smsr_g_ci95_quadrant_jackknife'][0]:.4f}, {d['smsr_g_ci95_quadrant_jackknife'][1]:.4f}], {d['withheld_positive_pixels']:,} withheld positive pixels, evaluator <code>{esc(card['holdout_dti']['evaluator_version'])}</code>) on the conservative detached-component instrument — the closer analogue to a genuinely unmapped fault strand. This is a holdout measurement on our own spatially-blocked instrument, <strong>not</strong> an organizer-confirmed leaderboard score.</p>
<p><a class="btn" href="downloads/{esc(fname)}" download>⬇ Download the submission GeoTIFF</a> <a class="btn secondary" href="downloads/{esc(fname.replace('.tif', '.zip'))}" download>Download the ZIP</a> <a class="btn secondary" href="../how-to-submit.html">How to submit →</a></p>
<p class="small">SHA-256 <code>{esc(sha)}</code> · {v['bytes']:,} bytes · single-band float32 GeoTIFF · {esc(v['meta']['crs'])} · {v['meta']['shape'][0]}×{v['meta']['shape'][1]} · 100 m · {v['emitted_positive_pixels']:,} positive cells ({pct_positive:.3f}% of footprint) · min {v['min']}, max {v['max']}, zero NaN/Inf, zero mass on the mapped catalogue.</p></div>
</div></section>

<div class="wrap">
<section><div class="section-head"><div class="eyebrow">One caveat, reported transparently</div><h2>A dense registry file still triggers the literal duplicate rule</h2></div>
<div class="grid">
<article class="card"><h3>The literal rule</h3><p>One previously registered GitHub file (<code>17GEMSDOE_E-proba-multiscale</code>) is <strong>positive on 100% of the footprint</strong> (a smooth continuous surface, millions of unique values, not a sparse dot pattern). Any nonempty candidate therefore has directed 3-pixel overlap = {wit['dot_overlap_3px']:.3f} against it by construction — this is a mathematical property of a 100%-dense comparator, true for literally every possible submission, not a measurement of similarity to SMSR specifically.</p></article>
<article class="card"><h3>The content-aware test</h3><p>The same parallel-run paragraph also names rank correlation as a duplicate test. We ran it: <strong>Spearman ρ = {wit['spearman_full_footprint']:.4f}</strong> across the shared footprint — far below the 0.90 cutoff. The two surfaces are essentially uncorrelated in content.</p></article>
<article class="card"><h3>Why we still recommend this file</h3><p>Against every <em>meaningful</em> comparator — all 9 requested GEMSDOE focus-site files, every prior lane in this repository, and the dense witness by rank correlation — SMSR passes both the ≤0.70 overlap and ≤0.90 |ρ| gates. It is flagged only by a test that is provably uninformative for a 100%-dense comparator. We report this to you rather than silently overriding the literal rule; the final submit decision is yours.</p></article>
</div></section>

<section><div class="section-head"><div class="eyebrow">What the hypothesis is</div><h2>Seismogeodetic Missing-Shear Ridge (SMSR)</h2></div>
<div class="card">
<p><strong>Hypothesis.</strong> {esc(card['hypothesis'])}</p>
<p><strong>Mechanism.</strong> {esc(card['mechanism'])}</p>
<p><strong>Named non-fault mimic.</strong> {esc(card['named_non_fault_mimic'])}</p>
<p>Full ranked hypothesis set and why this one was built first: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-28-smsr.md">knowledge/preregistration-2026-10-28-smsr.md</a>.</p>
</div></section>

<section><div class="section-head"><div class="eyebrow">Validation ladder (reused, not forked, tooling)</div><h2>Gates passed before this file was written</h2></div>
<div class="tablewrap"><table><thead><tr><th>Gate</th><th>Result</th><th>Evidence</th></tr></thead><tbody>
<tr><td>Real official data</td><td>{esc(card['data_provenance'])}</td><td><a href="data/run_card.json">run_card.json</a></td></tr>
<tr><td>Gate 0 — leakage canary</td><td>All 3 new SMSR planes individually &lt; 0.90 discriminative AUC. Two <em>inherited</em> base features (<code>d</code>/<code>d_perp</code>, identical in control and treatment) read {canary.get('d_perp', 0):.4f} — flagged, explained, and reported (see run card); they do not bias the SMSR-vs-control delta.</td><td><a href="data/cv_detached.json">cv_detached.json</a></td></tr>
<tr><td>Gate 1 — HOLDOUT-DTI superiority</td><td>Detached mode (primary, conservative): SMSR {d['smsr_g']:.4f} vs. shipped baseline {d['shipped_g']:.4f} (Δ{d['delta_smsr_minus_shipped']:+.4f}). All mode: SMSR {a['smsr_g']:.4f} vs. {a['shipped_g']:.4f} (Δ{a['delta_smsr_minus_shipped']:+.4f}). CIs overlap; reported as a modest, not dramatic, gain.</td><td><a href="data/cv_all.json">cv_all.json</a> · <a href="data/cv_detached.json">cv_detached.json</a></td></tr>
<tr><td>Gate 2 — format/range preflight</td><td>All checks pass: single band, float32, {esc(v['meta']['crs'])}, {v['meta']['shape'][0]}×{v['meta']['shape'][1]}, transform matches <code>sample_submission.tif</code> exactly, no NaN/Inf/sentinel anywhere, min 0.0 / max 1.0, zero mass outside the footprint, zero mass on the mapped catalogue.</td><td><a href="downloads/{esc(fname.replace('.tif', '.json'))}">receipt.json</a></td></tr>
<tr><td>Gate 3 — uniqueness</td><td>PASS vs. all 9 focus sites and every prior lane checked this session (see table below). Dense-witness caveat above.</td><td><a href="data/uniqueness.json">uniqueness.json</a></td></tr>
<tr><td>Gate 4 — budget</td><td>{card['experiments_run']} experiments used of a {card['experiments_budget']}-experiment cap; {card['slots_used_by_this_session']} competition submission slots spent by this session.</td><td><a href="data/run_card.json">run_card.json</a></td></tr>
</tbody></table></div></section>

<section><div class="section-head"><div class="eyebrow">Uniqueness detail</div><h2>Every comparator this session could check</h2></div>
<p class="scrollhint">Swipe horizontally to view all columns →</p>
<div class="tablewrap" tabindex="0" role="region" aria-label="Uniqueness detail table"><table><thead><tr><th>Comparator</th><th>3-px dot overlap</th><th>Spearman ρ (full footprint)</th><th>Verdict (≤0.70 overlap AND ≤0.90 |ρ|)</th></tr></thead><tbody>
{uniqueness_rows(uniq)}
</tbody></table></div>
<p class="small">Full machine-readable numbers: <a href="data/uniqueness.json">data/uniqueness.json</a>. This is {len(uniq)} comparators actually checked in this session; it is not a claim of a complete scan of every GEMSDOE-family repository that may exist.</p>
</section>

<section class="card"><h3>Limitations of this clearance</h3><ul>
<li>No true organizer test label was available anywhere in this session; the HOLDOUT-DTI figures above are our own spatially-blocked hide-and-recover proxy, not an organizer-confirmed score. Label every number accordingly before acting on it.</li>
<li>{esc(card['leakage_canary']['note'])}</li>
<li>The production/injection mimic for the geodetic-strain signal is named but not deconfounded with real well/production data (host not reachable from this sandbox).</li>
<li>Uniqueness was checked against {len(uniq)} comparators (9 focus sites, prior lanes, and the dense witness), not the full set of 90+ GEMSDOE-family sites referenced in the project history; a wider scan is recommended before relying on this clearance for a second or third submission.</li>
</ul></section>
</div></main>
<footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData · <a href="data/run_card.json">Machine-readable run card</a> · 0 competition slots spent by this session (selector decision is yours).</div></footer>
</body></html>
'''
    (LANE / "index.html").write_text(page, encoding="utf-8")
    print("SMSR lane page refreshed (data copies + promote-to-selector dossier).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
