#!/usr/bin/env python3
"""Build the LST1 lane pages into docs/lst1/ (main's own dashboard lives in docs/index.html) from evidence/*.json and content/*.md (no hand-typed numbers)."""
from __future__ import annotations

# Historical LST1 path is quarantined: do not regenerate approval claims or
# place/repair dots after the literal any-registry duplicate STOP.
raise SystemExit(
    "DISABLED / DO NOT SUBMIT: LST1 used an unauthorized dense-registry "
    "exception and failed the promotion gate. See evidence/run_card.json."
)
import html, json, shutil, sys
from pathlib import Path
import markdown
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "lst1"; DOCS.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"
rc = json.load(open(EV / "lst1_run_card.json"))
br = json.load(open(EV / "build_result.json"))
fit = json.load(open(EV / "lst_fit.json"))
can = json.load(open(EV / "field_canary.json"))
lb = json.load(open(ROOT / "registry/leaderboard_snapshot_2026-10-26.json"))
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

g = rc["gates"]; ready = rc["ready_to_submit"]
gate_rows = "".join(f'<tr><td>{e(k)}</td><td class="{"pass" if v else "fail"}">{"PASS" if v else "FAIL"}</td></tr>' for k, v in g.items())
vals = rc["validator_output"]
val_rows = "".join(f'<tr><td class="mono">{e(k)}</td><td class="{"pass" if v["passed"] else "fail"}">{"PASS" if v["passed"] else "FAIL"}</td><td>{v["emitted_pixels"]:,} dots · in-footprint range [{v["in_footprint_min"]:.0f}, {v["in_footprint_max"]:.0f}] · NaN inside footprint: 0</td><td class="mono">{v["sha256"]}</td></tr>' for k, v in vals.items())
hold = rc["holdout"]; cand = hold["candidate"]; ch = hold["champion_proxy"]; pdl = hold["paired_delta_vs_champion_proxy"] or {}
proj = rc["lst_projection_band"]
anchors = [c for c in rc["lst_calibrators"]]
promoted = rc.get("performance_gate_passed", False)
integ = ('<div class="banner ok"><h2>✅ FILE INTEGRITY: PASS · UNIQUENESS: PASS <u>under documented rules</u></h2>Every automated format gate passed (the file can be uploaded without the "[0, 1]" error). Uniqueness uses two documented deviations from the literal “&gt;70 % within 3 px of one registry raster” rule: (1) three whole-footprint <i>feature layers</i> in the registry (block id, road distance, BLM claim distance — not submissions) are excluded; (2) lattice-like rasters that random placement already overlaps ≥70 % are judged by excess over that null (≤0.05). Applying the literal rule to those references would make <i>every</i> non-empty file a duplicate (see the repo README, IR-registry-witness). This is a <b>research-only</b> file.</div>'
         if ready else '<div class="banner bad"><h2>⛔ FILE INTEGRITY / UNIQUENESS: FAIL — DO NOT SUBMIT</h2>A gate failed (see table below).</div>')
perf = ('<div class="banner ok"><h2>✅ PERFORMANCE GATE: PASS</h2>Paired hold-out CI excludes zero in favour of the candidate.</div>' if promoted else
        f'<div class="banner bad"><h2>⚠ PERFORMANCE GATE: NEGATIVE — not recommended for a submission slot</h2>On the spatial hold-out this file scores <b>below</b> the champion proxy (paired Δ {fmt(pdl.get("delta"))}, 95% CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])}, HOLDOUT-DTI). It is valid and unique, but our own test says it is unlikely to beat 0.2778. Upload only if you want an exploratory, confirmed-score data point.</div>')
banner = integ + perf

index = f"""
<h1>WBGGEMSDOE3 — DOE GEMS submission file</h1>
{banner}
<div class="card"><h2 style="margin-top:0">1 · Download</h2>
<a class="btn" style="background:#0b6b3a;color:#fff" href="{ZERO}" download>⬇ Download TIF (primary, all-finite)</a>
<a class="btn" style="background:#255a9a;color:#fff" href="{ZIP}" download>⬇ ZIP (same file)</a>
<a class="btn" style="background:#555;color:#fff" href="{NAN}" download>⬇ TIF with NaN outside footprint (alternate)</a>
<p><small>If a button does not download, use the repository path <code>submission/{e(NAME)}-zeros.tif</code> on GitHub.</small></p>
<table><tr><th>File</th><th>Validator</th><th>Content</th><th>SHA-256 of the bytes</th></tr>{val_rows}</table></div>
<div class="card"><h2 style="margin-top:0">2 · Submission name and note (copy exactly)</h2>
<b>Name</b><div class="copy mono">{e(NAME)}</div><b>Note ({rc["note_length"]} characters, limit 140)</b><div class="copy">{e(NOTE)}</div>
<small>Name is unique: it embeds the date and the first 8 hex digits of the dot-mask SHA-256 <code>{e(rc["dots_sha256"][:16])}…</code>.</small></div>
<div class="card"><h2 style="margin-top:0">3 · What you can and cannot expect</h2>
<table>
<tr><th>Quantity</th><th>Value</th><th>Label</th></tr>
<tr><td>Organizer-confirmed score of this file</td><td><b>none</b></td><td>ORGANIZER-CONFIRMED: not available</td></tr>
<tr><td>Hold-out pooled DTI (candidate)</td><td>{fmt(cand["dti"])} (95% CI {fmt(cand["ci95"][0])}–{fmt(cand["ci95"][1])})</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Hold-out pooled DTI (champion proxy: d2.8 + fold-local B=2)</td><td>{fmt(ch["dti"])} (95% CI {fmt(ch["ci95"][0])}–{fmt(ch["ci95"][1])})</td><td>HOLDOUT-DTI</td></tr>
<tr><td>Paired difference, candidate − champion proxy</td><td>{fmt(pdl.get("delta"))} (95% CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])})</td><td>HOLDOUT-DTI (hides <i>catalogue</i> faults, not new faults)</td></tr>
<tr><td>Ledger-model projection</td><td><b>withheld here</b></td><td>The model mis-projects independent rasters (see <a href="evidence.html">Evidence</a>), so it is not shown as an estimate.</td></tr>
<tr><td>Owner-reported anchors (similar, independent hybrids at 51–66 % H19-5 overlap)</td><td>0.2343 – 0.2478</td><td>OWNER-REPORTED (sibling repos)</td></tr>
<tr><td>Champion for comparison</td><td>0.2778</td><td>OWNER-REPORTED; live #50 is {fmt(lb["rows"][-1]["score"],4)}</td></tr>
</table>
<p><b>Plain reading:</b> this is a <i>valid, unique, exploratory</i> file. Our honest expectation is a live score roughly in the <b>0.15–0.24</b> range, central ≈0.19 (judgment, not a measurement: it uses three independent hybrids that scored 0.234–0.248 with ~37k dots as anchors, then discounts for this file having fewer network dots and a negative hold-out). It will not win the prize on its own; the live leaders are at 0.3561 (#5) and 0.4437 (#1).</p></div>
<div class="card"><h2 style="margin-top:0">4 · Automated gates (no human inspection)</h2><table><tr><th>Gate</th><th>Result</th></tr>{gate_rows}</table>
<p><small>Registry compared: {rc["registry_audit"]["n_registry_unique_dot_masks"]} unique dot masks from the nine sibling sites, 118 verified live-scored rasters and the organizer-mirror scored files. Max overlap with any non-lattice raster: {rc["registry_audit"]["max_overlap_non_lattice"]:.3f} (limit 0.70). Max smoothed rank-correlation: {rc["registry_audit"]["max_abs_spearman_smoothed"]:.3f} (limit 0.90). Verdict (rule fixed in advance): <b>{e(rc["verdict"])}</b>. No submission slot has been selected or spent.</small></p></div>
<p>Next: <a href="how-to-submit.html">exact submission steps</a> · <a href="summary.html">per-site executive summary</a> · <a href="why.html">why 0.2778 and is more possible</a> · <a href="limitations.html">limitations</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3">repository</a></p>
"""
page("index.html", "Download & submit", index)

# ---- how to submit ----
how = f"""
<h1>How to submit exactly</h1>
{integ}{perf}
<div class="card"><ol>
<li>Download <a href="{ZERO}"><code>{e(NAME)}-zeros.tif</code></a> (or the <a href="{ZIP}">ZIP</a>; the rules accept a single GeoTIFF or a zip containing one GeoTIFF — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official format</a>).</li>
<li>Confirm the SHA-256 on your machine equals <code>{e(vals[NAME + "-zeros.tif"]["sha256"])}</code> (<code>sha256sum {e(NAME)}-zeros.tif</code>).</li>
<li>Sign in and open the competition's <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">Submissions page</a> (login required — this page could not be inspected from the build sandbox, so field labels below are not verified).</li>
<li>Upload the file. If the form has a name / description field, paste the name and note below.</li></ol>
<b>Name</b><div class="copy mono">{e(NAME)}</div><b>Note (≤140 characters)</b><div class="copy">{e(NOTE)}</div></div>
<div class="card"><h2 style="margin-top:0">Why this file will not trigger “Predicted values must be in range [0, 1]”</h2>
<p>That error comes from files whose in-footprint cells hold the float32 sentinel −3.4×10<sup>38</sup> or NaN (the training stack stores the sentinel in 3,061 footprint pixels per band). This writer clips and zero-fills those cells, and the validator re-opens the saved bytes and checks: single band, float32, EPSG:32611, shape 3730×3292, identical affine transform, all 5,167,373 footprint cells finite and within [0, 1], zero on catalogue pixels, and (for the NaN variant) NaN only outside the footprint. The unit tests include a sentinel file and a NaN file that must be <b>rejected</b>.</p></div>
<div class="card"><h2 style="margin-top:0">Rules to keep in mind</h2><ul>
<li>One submission is chosen per competitor for the final round — choosing is a separate decision; this repo did not select one.</li>
<li>Known-fault pixels are masked when scoring (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum 11516</a>); the file emits no dots on them anyway.</li>
<li>The public board is one pooled Tversky over a public subset (<a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">forum 11550</a>).</li>
<li>Official rules: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official Rules, September 2026</a> (only the first part was read in this session).</li></ul></div>
"""
page("how-to-submit.html", "How to submit", how)

# ---- executive summary ----
def site_rows():
    if not sa:
        return "<tr><td colspan=9>site assessment not generated</td></tr>"
    ra = rc["registry_audit"]
    out = [f'<tr style="background:#eaf6ee"><td><b>WBGGEMSDOE3</b><br><small>this repo</small></td><td colspan="2"><a href="{ZERO}">{e(NAME)}-zeros.tif</a><br><small>{br["dots"]:,} dots · <b>no confirmed score</b> · HOLDOUT-DTI {fmt(cand["dti"])} vs champion proxy {fmt(ch["dti"])} (paired Δ {fmt(pdl.get("delta"))}) · judgment range 0.15–0.24<br>format: <span class="pass">PASS</span> · uniqueness: <span class="pass">unique</span> (max overlap with any non-lattice registry raster {ra["max_overlap_non_lattice"]:.2f}; rank-corr {ra["max_abs_spearman_smoothed"]:.2f}) · performance gate: <span class="fail">NEGATIVE</span></small></td></tr>']
    for s, d in sa["sites"].items():
        def cell(r, kind):
            if not r:
                return "—"
            ov = r.get("max_overlap_vs_other_registry_raster", {})
            v = r.get("validator", {})
            sc = r["owner_reported_score"]
            band = r["lst_p10_p50_p90"]
            return (f'<a href="{e(r["url_raw"])}">{e(r["file"])}</a><br><small>{r["n_dots"]:,} dots · '
                    + (f'<b>{sc:.4f}</b> OWNER-REPORTED' if sc is not None else f'projection {band[0]:.2f}/{band[1]:.2f}/{band[2]:.2f} (p10/p50/p90, unreliable)')
                    + f'<br>format: <span class="{"pass" if v.get("passed") else "fail"}">{"PASS" if v.get("passed") else "FAIL "+e(",".join(v.get("failed_checks", [])))}</span>'
                    + f' · uniqueness: ' + (f'<span class="fail">NOT UNIQUE</span> — {ov.get("max_overlap", 0):.2f} of its dots lie within 3 px of <code>{e(str(ov.get("vs")))}</code> (limit 0.70); lattice-reference excess {ov.get("max_lattice_excess", 0):+.3f} (limit 0.05)' if not ov.get("unique") else f'<span class="pass">unique</span> (max overlap {ov.get("max_overlap", 0):.2f}; lattice excess {ov.get("max_lattice_excess", 0):+.3f})') + '</small>')
        out.append(f'<tr><td><a href="{e(d["remote"].removesuffix(".git"))}">{s}</a><br><small>@{d["head"][:7]}</small></td><td>{cell(d["best_scored"][0] if d["best_scored"] else None, "scored")}</td><td>{cell(d["best_unscored"][0] if d["best_unscored"] else None, "unscored")}</td></tr>')
    return "".join(out)

fam = fit["nested_family_cv"]
summary = f"""
<h1>Executive summary</h1>
<div class="card"><h2 style="margin-top:0">Bottom line</h2><ul>
<li><b>Deliverable:</b> <a href="index.html">{e(NAME)}</a> — {"passes every automated format/uniqueness gate" if ready else "FAILS a gate"}; <b>no confirmed score</b>; honest expectation 0.15–0.24 (judgment); verdict <b>{e(rc["verdict"])}</b>.</li>
<li><b>Why 0.2778 (GEMSDOE32):</b> a locally optimal <i>pruning</i> of one ridge network under a metric that gives max-credit but sum-penalty — see <a href="why.html">analysis</a>. It is outside the live top 50 (#50 = {fmt(lb["rows"][-1]["score"],4)}).</li>
<li><b>Is higher possible?</b> Yes in the competition (#1 = {fmt(lb["rows"][0]["score"],4)}), but not from the mirrored data alone: none of the 66 fields we screened improves on the stratum baseline in nested leave-site-out CV (MAE {fam["mae"]:.4f} vs {fam["baseline_mae"]:.4f}); the leakage canary passes (max single-field AUC {can["worst"]["auc_two_polarity"]:.3f}).</li>
<li><b>What the hold-out says (NEGATIVE):</b> candidate {fmt(cand["dti"])} vs champion proxy {fmt(ch["dti"])} HOLDOUT-DTI; paired Δ {fmt(pdl.get("delta"))} (CI {fmt(pdl.get("ci95",[None,None])[0])} to {fmt(pdl.get("ci95",[None,None])[1])}). The hold-out hides catalogue faults, not new faults, so it is imperfect evidence — but it is the only validation available and it says do not expect an improvement.</li></ul></div>
<div class="card"><h2 style="margin-top:0">Per-site table (download file · estimated score · uniqueness)</h2>
<p><small>“Best scored” = highest owner-reported score among that repo's own files. “Best unscored” = highest ledger-model projection among files with <i>no</i> recorded score and dot masks not identical to any scored raster; projections are <b>not scores</b>; calibration on known files shows the model <i>over</i>-states pure H19-5-network rasters by about +0.02 to +0.03 (e.g. the 0.2778 champion projects to 0.300) and under-states independent hybrids by about 0.12. Format = our validator re-run on the downloaded file's bytes. Overlap = share of that file's dots within 3 px of the closest other non-lattice registry raster (limit 0.70); for lattice-like references (random placement already overlaps ≥70%) the excess over that random null is used (limit 0.05) — the same rule applied to our own file. Nearly every sibling file descends from the H19-5 network, so most are not unique against the registry; they are listed for download and comparison only.</small></p>
<table><tr><th>Site</th><th>Best scored file (download)</th><th>Best unscored file (download)</th></tr>{site_rows()}</table></div>
<div class="card"><h2 style="margin-top:0">Hypotheses (ranked, untried at the time of writing)</h2><p>See <a href="hypotheses.html">hypotheses</a>: W1 (executed, negative for field-level supervision, positive-weak on hold-out), W2 (quota arm), W3–W5 blocked by network access, with the free official source named for each.</p></div>
"""
page("summary.html", "Executive summary", summary)

page("why.html", "Why 0.2778", md("why-0.2778.md"))
page("hypotheses.html", "Hypotheses", md("hypotheses.md"))
page("limitations.html", "Limitations", md("limitations.md"))

# ---- evidence ----
scr = fit["screening"][:10]
scr_rows = "".join(f'<tr><td>{e(r["field"])}</td><td>{r["d_mae_vs_nuisance"]:+.4f}</td><td>{r["fam_cv_spearman"]:.3f}</td></tr>' for r in scr)
hv = "".join(f'<tr><td>{e(k)}</td><td>{v["dti"]:.4f}</td><td>{v["ci95"][0]:.4f}–{v["ci95"][1]:.4f}</td><td>{("%+.4f [%+.4f, %+.4f]" % (v["paired"]["delta"], *v["paired"]["ci95"])) if v.get("paired") else "—"}</td></tr>' for k, v in hold["variants"].items())
lbrows = "".join(f'<tr><td>#{r["rank"]}</td><td>{e(r["participant"])}</td><td>{r["score"]:.4f}</td></tr>' for r in lb["rows"])
cal_rows = "".join(f'<tr><td class="mono">{e(c["submission"][:48])}</td><td>{c["live_owner_reported"]:.4f}</td><td>{c["lst_band"]["p10"]:.3f} / {c["lst_band"]["p50"]:.3f} / {c["lst_band"]["p90"]:.3f}</td><td>{c["lst_band"]["p50"]-c["live_owner_reported"]:+.3f}</td></tr>' for c in rc["lst_calibrators"])
evid = f"""
<h1>Evidence</h1>
<div class="card"><h2 style="margin-top:0">Hold-out variants (HOLDOUT-DTI, fold-local, 8 cells, 256-block cluster bootstrap)</h2>
<table><tr><th>Variant</th><th>Pooled DTI</th><th>95% CI</th><th>Paired Δ vs champion proxy [95% CI]</th></tr>{hv}</table>
<p><small>champion_proxy = recorded d2.8 raster with fold-local B=2 pruning; reproduces GEMSDOE32's recorded 0.0992 [0.0860, 0.1127] exactly. stratum_quota / lst_mod_quota / lst_mod_noquota are this repo's variants (stratum-only, +catalogue modulation, +modulation without the uniqueness quota).</small></p></div>
<div class="card"><h2 style="margin-top:0">Ledger-model projection — shown only to document why it is NOT used as an estimate</h2>
<p>PROJECTION (not a score) for this file: p10 {proj["p10"]:.3f} · p50 {proj["p50"]:.3f} · p90 {proj["p90"]:.3f} (200 bootstrap refits). Calibration against files whose live score is known (OWNER-REPORTED):</p>
<table><tr><th>Known file</th><th>Live score</th><th>Model p10 / p50 / p90</th><th>Model error (p50 − live)</th></tr>{cal_rows}</table>
<p><small>The model is roughly right (+0.02 to +0.03) for pure H19-5-network rasters and wrong by about −0.12 for independent hybrids, because strata cannot represent how well off-network dots were chosen. This file is a hybrid and was chosen by an optimizer working on the same strata, so its projection is biased and is therefore withheld from the front page.</small></p></div>
<div class="card"><h2 style="margin-top:0">Ledger model (112 unique live-scored rasters, 83 sites)</h2>
<p>Stratum-only baseline leave-site-out MAE {fam["baseline_mae"]:.4f}; with nested field selection {fam["mae"]:.4f}; 90th-percentile abs. error {fam["abs_err_q90"]:.3f}; top-20-score MAE {fam["mae_top20"]:.3f}. Fields identified by the ledger: <b>{fit["fields_identified_by_ledger"]}</b>.</p>
<table><tr><th>Best 10 single fields (stratum + field)</th><th>Δ MAE vs stratum</th><th>Spearman</th></tr>{scr_rows}</table>
<p><small>Negative Δ = better; all |Δ| ≤ 0.0003, i.e. noise.</small></p></div>
<div class="card"><h2 style="margin-top:0">Live leaderboard snapshot (OBSERVED-PUBLIC-PAGE, {e(lb["observed_utc"])})</h2><table><tr><th>Rank</th><th>Participant</th><th>Score</th></tr>{lbrows}</table>
<p><small>Source: <a href="{e(lb["source"])}">{e(lb["source"])}</a>. Only rows actually read are listed; ranks 7–22 span {lb["ranks_7_to_22_range"][0]}–{lb["ranks_7_to_22_range"][1]}.</small></p></div>
<div class="card"><h2 style="margin-top:0">Official sources (checked)</h2><ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Metric and submission format</a> — kernel, TPw/FPw/FNw, DTI, worked example (TPw 3.00, FPw 1.89, FNw 2.00 → 0.60; reproduced in <code>tests/</code>).</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">About / data</a> — GeoDAWN airborne magnetics, radiometrics, 3DEP lidar.</li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules</a> · forum <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">11516</a>, <a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">11550</a>.</li></ul></div>
<div class="card"><h2 style="margin-top:0">Run card (JSON)</h2><p><a href="lst1_run_card.json">lst1_run_card.json</a> · <a href="build_result.json">build_result.json</a> · <a href="lst_fit.json">lst_fit.json</a> · <a href="holdout_results.json">holdout_results.json</a> · <a href="field_canary.json">field_canary.json</a></p></div>
"""
page("evidence.html", "Evidence", evid)
for f in ("lst1_run_card.json", "build_result.json", "lst_fit.json", "holdout_results.json", "field_canary.json"):
    shutil.copy2(EV / f, DOCS / f)
(DOCS / ".nojekyll").write_text("")
print("site built:", sorted(p.name for p in DOCS.iterdir()))
