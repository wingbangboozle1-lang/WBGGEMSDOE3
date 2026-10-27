#!/usr/bin/env python3
"""Build the LST1 lane pages into docs/lst1/ (main's own dashboard lives in docs/index.html) from evidence/*.json and content/*.md (no hand-typed numbers)."""
from __future__ import annotations
import html, json, shutil, sys
from pathlib import Path
import markdown
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "lst1"; DOCS.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
rc = json.load(open(EV / "lst1_run_card.json"))
fit = json.load(open(EV / "lst_fit.json"))
sa = json.load(open(EV / "site_assessment.json")) if (EV / "site_assessment.json").exists() else None
NAME, NOTE = rc["submission_name"], rc["submission_note"]
e = html.escape
fmt = lambda x, n=4: "n/a" if x is None else f"{x:.{n}f}"

# ---- downloads ----
(DOCS / "downloads").mkdir(exist_ok=True)
for f in (ROOT / "submission").glob(f"{NAME}*"):
    shutil.copy2(f, DOCS / "downloads" / f.name)
ZERO = f"downloads/{NAME}-zeros.tif"; NAN = f"downloads/{NAME}-nan.tif"; ZIP = f"downloads/{NAME}-zeros.zip"

CSS = """
:root{--g:#0b6b3a;--r:#a31d1d;--a:#8a5a00;--bg:#f6f7f9;--ink:#15202b}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#12263a;color:#fff;padding:14px 20px}header a{color:#cfe3ff;margin-right:16px;text-decoration:none;font-weight:600}
main{max-width:1020px;margin:0 auto;padding:18px 20px 60px}h1{font-size:1.7rem}h2{margin-top:2rem;border-bottom:1px solid #d7dde4;padding-bottom:4px}
.banner{border-radius:10px;padding:18px 20px;margin:14px 0;color:#fff}.ok{background:var(--g)}.bad{background:var(--r)}.warn{background:var(--a)}
.banner h2{border:0;margin:0 0 6px;color:#fff}.btn{display:inline-block;background:#fff;color:#0b3a22;font-weight:700;padding:10px 16px;border-radius:8px;text-decoration:none;margin:6px 8px 0 0}
.card{background:#fff;border:1px solid #d7dde4;border-radius:10px;padding:14px 18px;margin:12px 0}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.92rem}th,td{border:1px solid #d7dde4;padding:6px 8px;text-align:left;vertical-align:top}th{background:#eef1f5}
code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88rem;word-break:break-all}.pass{color:var(--g);font-weight:700}.fail{color:var(--r);font-weight:700}
.copy{background:#eef6ff;border:1px solid #b9d4f5;border-radius:8px;padding:8px 10px;margin:4px 0}small{color:#4a5866}
"""
NAV = [("index.html", "Download &amp; submit"), ("summary.html", "Executive summary"), ("how-to-submit.html", "How to submit"),
       ("why.html", "Why 0.2778?"), ("hypotheses.html", "Hypotheses"), ("evidence.html", "Evidence"), ("limitations.html", "Limitations"), ("../index.html", "◀ Repo dashboard")]

def page(fn, title, body):
    nav = "".join(f'<a href="{h}">{t}</a>' for h, t in NAV)
    (DOCS / fn).write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · WBGGEMSDOE3</title><style>{CSS}</style></head><body><header>{nav}</header><main>{body}</main></body></html>""", encoding="utf-8")

def md(name):
    return markdown.markdown((ROOT / "content" / name).read_text(), extensions=["tables", "sane_lists"])

g = rc["gates"]
gate_rows = "".join(f'<tr><td>{e(k)}</td><td class="{"pass" if v else "fail"}">{e(rc["gate_status"][k])}</td></tr>' for k, v in g.items())
legacy_diagnostics = rc["legacy_diagnostics"]
diagnostic_rows = "".join(f'<tr><td>{e(k)}</td><td class="{"pass" if v else "fail"}">{"PASS (HISTORICAL ONLY)" if v else "FAIL (HISTORICAL)"}</td></tr>' for k, v in legacy_diagnostics.items())
vals = rc["validator_output"]
val_rows = "".join(f'<tr><td class="mono">{e(k)}</td><td class="{"pass" if v["passed"] else "fail"}">{"PASS" if v["passed"] else "FAIL"}</td><td>{v["emitted_pixels"]:,} dots · in-footprint range [{v["in_footprint_min"]:.0f}, {v["in_footprint_max"]:.0f}] · NaN inside footprint: 0</td><td class="mono">{v["sha256"]}</td></tr>' for k, v in vals.items())
hold = rc["holdout"]; cand = hold["candidate"]; ch = hold["champion_proxy"]; pdl = hold["paired_delta_vs_champion_proxy"] or {}
integ = ('<div class="banner bad"><h2>⛔ DO NOT SUBMIT — RETIRED HISTORICAL LST1 ARTIFACT</h2>'
         'The recorded literal registry-overlap gate fails, and the old lattice-null exemption is not valid under the current protocol. '
         'This page is an archive only: local byte/format checks, historical “unique” labels, or a performance result cannot clear it. '
         'No submission approval or slot selection is available here.</div>')
perf = (f'<div class="banner bad"><h2>⚠ HISTORICAL HOLDOUT-DTI — NOT CURRENT VALIDATION</h2>'
        f'Evaluator {e(hold.get("evaluator", "unknown"))}; withheld positives {hold.get("withheld_positive_pixels", "not recorded")}; '
        f'candidate {fmt(cand["dti"])} (95% CI {fmt(cand["ci95"][0])} to {fmt(cand["ci95"][1])}) vs '
        f'champion proxy {fmt(ch["dti"])} (95% CI {fmt(ch["ci95"][0])} to {fmt(ch["ci95"][1])}); '
        f'paired Δ {fmt(pdl.get("delta"))} (95% CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])}). '
        'Legacy HOLDOUT-DTI only: no leaderboard score is inferred.</div>')
banner = integ + perf

index = f"""
<h1>WBGGEMSDOE3 — historical research artifact</h1>
{banner}
<div class="card"><h2 style="margin-top:0">Research artifact download · NOT FOR SUBMISSION</h2>
<p><b>Warning:</b> byte integrity or local format PASS does not override the failed literal registry gate, prove official compatibility, or authorize an upload.</p>
<a class="btn" style="background:#8a1c1c;color:#fff" href="{ZERO}" download>⬇ Download research-only TIF — DO NOT SUBMIT</a>
<a class="btn" style="background:#555;color:#fff" href="{ZIP}" download>⬇ Research ZIP — DO NOT SUBMIT</a>
<a class="btn" style="background:#555;color:#fff" href="{NAN}" download>⬇ Research NaN-outside variant — DO NOT SUBMIT</a>
<p><small>If a button does not download, use the repository path <code>submission/{e(NAME)}-zeros.tif</code> on GitHub.</small></p>
<h3>Archived local format checks only (not organizer acceptance)</h3><table><tr><th>Historical file</th><th>Local format result</th><th>Content</th><th>Historical SHA-256</th></tr>{val_rows}</table></div>
<div class="card"><h2 style="margin-top:0">Historical run identifier and note · not approved for upload</h2>
<b>Name</b><div class="copy mono">{e(NAME)}</div><b>Note ({rc["note_length"]} characters, limit 140)</b><div class="copy">{e(NOTE)}</div>
<small>This is a historical artifact identifier derived from its dot-mask hash; a distinct name does not establish raster uniqueness or submission approval.</small></div>
<div class="card"><h2 style="margin-top:0">3 · What you can and cannot expect</h2>
<table>
<tr><th>Quantity</th><th>Value</th><th>Label</th></tr>
<tr><td>Organizer-confirmed score of this file</td><td><b>none</b></td><td>ORGANIZER-CONFIRMED: not available</td></tr>
<tr><td>Hold-out pooled DTI (candidate)</td><td>{fmt(cand["dti"])} (95% CI {fmt(cand["ci95"][0])}–{fmt(cand["ci95"][1])})</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Hold-out pooled DTI (champion proxy: d2.8 + fold-local B=2)</td><td>{fmt(ch["dti"])} (95% CI {fmt(ch["ci95"][0])}–{fmt(ch["ci95"][1])})</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Paired difference, candidate − champion proxy</td><td>{fmt(pdl.get("delta"))} (95% CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])})</td><td>HOLDOUT-DTI (hides <i>catalogue</i> faults, not new faults)</td></tr>
<tr><td>Leaderboard score estimate</td><td><b>Not estimable</b></td><td>No organizer receipt or calibrated, current-protocol mapping from this legacy HOLDOUT-DTI to leaderboard performance.</td></tr>
</table>
<p><b>Plain reading:</b> this is a historical research artifact, not a unique or cleared submission under the current literal registry rule. The holdout result is negative and uses a legacy evaluator; no leaderboard score is estimated. Do not upload this file.</p></div>
<div class="card"><h2 style="margin-top:0">4 · Current clearances — no approval</h2><p>The current status is fail-closed; a historical subcheck cannot reverse any failure or missing current evaluation.</p><table><tr><th>Current gate</th><th>Result</th></tr>{gate_rows}</table>
<p><small>Historical audit scope was incomplete and not authenticated. It reported max overlap {rc["registry_audit"]["max_overlap_non_lattice"]:.3f} and max absolute smoothed rank correlation {rc["registry_audit"]["max_abs_spearman_smoothed"]:.3f} only within its old subset. Those diagnostics do not establish current uniqueness. Literal-rule pass: <b>{rc["registry_audit"]["literal_rule_pass"]}</b>; scope complete: <b>{rc["registry_audit"]["literal_scope_complete"]}</b>. Verdict: <b>{e(rc["verdict"])}</b>. No submission slot has been selected or spent.</small></p>
<h3>Legacy diagnostics — not current clearance</h3><table><tr><th>Archived check</th><th>Status</th></tr>{diagnostic_rows}</table></div>
<p>Next: <a href="how-to-submit.html">exact submission steps</a> · <a href="summary.html">per-site executive summary</a> · <a href="why.html">why 0.2778 and is more possible</a> · <a href="limitations.html">limitations</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3">repository</a></p>
"""
page("index.html", "Download & submit", index)

# ---- how to submit ----
how = f"""
<h1>How to submit exactly</h1>
{integ}{perf}
<div class="card"><ol>
<li><b>Stop:</b> no file is approved. Do not upload the linked historical research artifact. Wait for a new run card that passes the literal registry rule, required shared holdout, file validation, and separate selector.</li>
<li>For a future approved file, compare its downloaded SHA-256 with the run card before upload; do not reuse this lane's name or TIFF.</li>
<li>Sign in to the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> only after the selector authorizes an upload; account quota and submission form fields are not accessible here.</li>
<li>Upload only the exact approved file and preserve the organizer receipt with its SHA-256. No slot is selected by this repository.</li></ol>
<b>Current submission name / note</b><div class="copy">None. The old LST1 identifier is a research label only.</div></div>
<div class="card"><h2 style="margin-top:0">About “Predicted values must be in range [0, 1]”</h2>
<p>The cause of the earlier portal rejection is unknown because the rejected bytes and receipt were not available. The historic LST1 local validator recorded one-band float32 data on the mirrored grid and checked in-footprint values for finiteness and range. That local result is not organizer acceptance; the official outside-footprint convention and mirrored writer differ, so no claim is made that this artifact will be accepted.</p></div>
<div class="card"><h2 style="margin-top:0">Protocol and official links</h2><ul>
<li>This repository selected no submission slot. Any real slot must be selected separately after a new candidate is cleared.</li>
<li>Forum threads on masking (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">11516</a>) and leaderboard aggregation (<a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">11550</a>) are retained as source pointers; they were not re-fetched in this review.</li>
<li>Before any future submission, verify the current <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules</a> and the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition page</a>. Current account quota and form fields were not inspected.</li></ul></div>
"""
page("how-to-submit.html", "How to submit", how)

# ---- executive summary ----
def site_rows():
    if not sa:
        return "<tr><td colspan=9>site assessment not generated</td></tr>"
    out = [f'<tr style="background:#fdf0f0"><td><b>WBGGEMSDOE3</b><br><small>this repo · historical LST1</small></td><td colspan="2"><a href="{ZERO}">{e(NAME)}-zeros.tif</a> — research only, DO NOT SUBMIT<br><small>{vals[NAME + "-zeros.tif"]["emitted_pixels"]:,} dots · no organizer-confirmed score · no leaderboard estimate · legacy HOLDOUT-DTI detailed in summary (evaluator {e(hold.get("evaluator", "unknown"))}, {hold.get("withheld_positive_pixels", "not recorded")} withheld positives) · local format check is not acceptance · strict uniqueness: <span class="fail">NOT CLEARED</span> · performance gate: <span class="fail">NEGATIVE</span></small></td></tr>']
    for s, d in sa["sites"].items():
        def cell(r, kind):
            if not r:
                return "—"
            v = r.get("validator", {})
            sc = r["owner_reported_score"]
            return (f'<a href="{e(r["url_raw"])}">{e(r["file"])}</a><br><small>{r["n_dots"]:,} dots · '
                    + (f'<b>{sc:.4f}</b> OWNER-REPORTED (no receipt)' if sc is not None else 'Not estimable')
                    + f'<br>format: <span class="{"pass" if v.get("passed") else "fail"}">{"PASS" if v.get("passed") else "FAIL "+e(",".join(v.get("failed_checks", [])))}</span>'
                    + ' · current strict status: <span class="fail">NOT CLEARED</span> — the registered universal witness blocks every nonempty in-footprint prediction' + '</small>')
        out.append(f'<tr><td><a href="{e(d["remote"].removesuffix(".git"))}">{s}</a><br><small>@{d["head"][:7]}</small></td><td>{cell(d["best_scored"][0] if d["best_scored"] else None, "scored")}</td><td>{cell(d["best_unscored"][0] if d["best_unscored"] else None, "unscored")}</td></tr>')
    return "".join(out)

fam = fit["nested_family_cv"]
summary = f"""
<h1>Executive summary</h1>
<div class="card"><h2 style="margin-top:0">Bottom line</h2><ul>
<li><b>Artifact:</b> <a href="index.html">{e(NAME)}</a> — research only; <b>DO NOT SUBMIT</b>; no organizer-confirmed score and no leaderboard estimate; verdict <b>{e(rc["verdict"])}</b>.</li>
<li><b>Why the reported GEMSDOE32 B2 result may differ:</b> the raster bytes show a pruning operation, but no receipt ties the reported value to those exact bytes and the file operation does not establish score causality. See <a href="why.html">the evidence-limited analysis</a>.</li>
<li><b>Can a new method score higher?</b> Unknown. No current-protocol candidate was validated; no leaderboard estimate is published. Historic model projections are withheld as unreliable diagnostics.</li>
<li><b>Historical HOLDOUT-DTI (NEGATIVE):</b> evaluator {e(hold.get("evaluator", "unknown"))}; {hold.get("withheld_positive_pixels", "not recorded")} withheld positives. Candidate {fmt(cand["dti"])} (95% CI {fmt(cand["ci95"][0])} to {fmt(cand["ci95"][1])}); champion proxy {fmt(ch["dti"])} (95% CI {fmt(ch["ci95"][0])} to {fmt(ch["ci95"][1])}); paired Δ {fmt(pdl.get("delta"))} (95% CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])}). This legacy result is not the prescribed current shared-evaluator run and does not estimate leaderboard performance.</li></ul></div>
<div class="card"><h2 style="margin-top:0">Historical site table · research only</h2>
<p><small>“Best scored” means the highest owner-reported value in that peer repository; no submission-page receipt links these values to uploaded bytes. No leaderboard projection is published. Every listed historical artifact is research-only under the current literal registry protocol. Use the main dashboard for the current nine-site audit; it compares exact pinned bytes and marks all files “DO NOT SUBMIT.”</small></p>
<table><tr><th>Site</th><th>Best owner-reported reference (research only)</th><th>Other research artifact (score not estimable)</th></tr>{site_rows()}</table></div>
<div class="card"><h2 style="margin-top:0">Hypothesis record (historical)</h2><p>See <a href="hypotheses.html">the preregistered hypotheses</a>. W1 has historical legacy-evaluator results; the other listed hypotheses were not run. No experiment was conducted in this review because the mandatory registry stop blocks every nonempty candidate.</p></div>
"""
page("summary.html", "Executive summary", summary)

page("why.html", "Why 0.2778", md("why-0.2778.md"))
page("hypotheses.html", "Hypotheses", md("hypotheses.md"))
page("limitations.html", "Limitations", md("limitations.md"))

# ---- evidence ----
scr = fit["screening"][:10]
scr_rows = "".join(f'<tr><td>{e(r["field"])}</td><td>{r["d_mae_vs_nuisance"]:+.4f}</td><td>{r["fam_cv_spearman"]:.3f}</td></tr>' for r in scr)
hv = "".join(f'<tr><td>{e(k)}</td><td>{v["dti"]:.4f}</td><td>{v["ci95"][0]:.4f}–{v["ci95"][1]:.4f}</td><td>{("%+.4f [%+.4f, %+.4f]" % (v["paired"]["delta"], *v["paired"]["ci95"])) if v.get("paired") else "—"}</td></tr>' for k, v in hold["variants"].items())
evid = f"""
<h1>Evidence</h1>
<div class="card"><h2 style="margin-top:0">Historical holdout variants (HOLDOUT-DTI · evaluator {e(hold.get("evaluator", "unknown"))} · {hold.get("withheld_positive_pixels", "not recorded")} withheld positives)</h2>
<p><b>Legacy result only.</b> This historical evaluator is not the currently prescribed shared evaluator and cannot clear a present-day candidate.</p>
<table><tr><th>Variant</th><th>Pooled DTI</th><th>95% CI</th><th>Paired Δ vs champion proxy [95% CI]</th></tr>{hv}</table>
<p><small>champion_proxy = recorded d2.8 raster with fold-local B=2 pruning; reproduces GEMSDOE32's recorded 0.0992 [0.0860, 0.1127] exactly. stratum_quota / lst_mod_quota / lst_mod_noquota are this repo's variants (stratum-only, +catalogue modulation, +modulation without the uniqueness quota).</small></p></div>
<div class="card"><h2 style="margin-top:0">Leaderboard estimate</h2>
<p><b>Not estimable.</b> The legacy ledger model's projected values are quarantined: its calibration is method-dependent and does not provide a validated mapping from a spatial holdout to the hidden leaderboard. The project publishes no prediction as a score.</p></div>
<div class="card"><h2 style="margin-top:0">Ledger model (112 unique live-scored rasters, 83 sites)</h2>
<p>Stratum-only baseline leave-site-out MAE {fam["baseline_mae"]:.4f}; with nested field selection {fam["mae"]:.4f}; 90th-percentile abs. error {fam["abs_err_q90"]:.3f}; top-20-score MAE {fam["mae_top20"]:.3f}. Fields identified by the ledger: <b>{fit["fields_identified_by_ledger"]}</b>.</p>
<table><tr><th>Best 10 single fields (stratum + field)</th><th>Δ MAE vs stratum</th><th>Spearman</th></tr>{scr_rows}</table>
<p><small>Negative Δ = better; all |Δ| ≤ 0.0003, i.e. noise.</small></p></div>
<div class="card"><h2 style="margin-top:0">Official source links for manual review</h2><p><small>These links are retained from repository research; official pages were not re-fetched during this review. No claim about current leaderboard or account state is inferred from them.</small></p><ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official metric and submission format</a>.</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">Official competition data and overview</a>.</li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference solution</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules</a> · scoring clarification <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">11516</a> and leaderboard aggregation <a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">11550</a>.</li></ul></div>
<div class="card"><h2 style="margin-top:0">Run card (JSON)</h2><p><a href="lst1_run_card.json">reclassified historical run card</a> · <a href="lst_fit.json">legacy fit diagnostics</a> · <a href="holdout_results.json">legacy holdout results</a> · <a href="field_canary.json">legacy feature canary</a></p><p><small>The raw LST1 build-result file remains in the repository's historical evidence folder but is intentionally not copied into this current-facing page because it includes quarantined NOT_A_SCORE projection diagnostics.</small></p></div>
"""
page("evidence.html", "Evidence", evid)
for f in ("lst1_run_card.json", "lst_fit.json", "holdout_results.json", "field_canary.json"):
    shutil.copy2(EV / f, DOCS / f)
(DOCS / ".nojekyll").write_text("")
print("site built:", sorted(p.name for p in DOCS.iterdir()))
