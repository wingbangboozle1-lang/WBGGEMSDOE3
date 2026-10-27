#!/usr/bin/env python3
"""Build docs/session-1f0b051d/{index,how-to-submit}.html + map PNG from evidence JSONs only."""
from __future__ import annotations

import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
LANE = ROOT / "docs" / "session-1f0b051d"
SESS = ROOT / ".cache" / "session"

audit = json.loads((ROOT / "evidence/session_1f0b051d_audit.json").read_text())
card = json.loads((ROOT / "evidence/session_1f0b051d_run_card.json").read_text())
verify = json.loads((ROOT / "evidence/session_1f0b051d_verify.json").read_text())["checks"]
lst_fit = json.loads((SESS / "lst_fit_session.json").read_text())
lane_lst = json.loads((SESS / "lane_lst_projections.json").read_text())
canary = json.loads((SESS / "canary.json").read_text())
e1 = json.loads((SESS / "E1_dipole_result.json").read_text())
e2 = json.loads((SESS / "E2_dipole_suppressed_result.json").read_text())
e3 = json.loads((SESS / "E3_hybrid_result.json").read_text())

NAME = card["submission_name"]
ZIP = Path(card["download"]["site_zip"]).name
SHA = card["raster_sha256"]
NOTE = card["submission_note"]
OWNER = {"GEMSDOE24": 0.2477, "GEMSDOE25": 0.2600, "GEMSDOE27": 0.2449, "GEMSDOE28": 0.2710,
         "GEMSDOE30": 0.2600, "GEMSDOE31": 0.2708, "GEMSDOE32": 0.2778, "GEMSDOE33": 0.2632,
         "GEMSDOE36": 0.2750}
SITE_URL = {"GEMSDOE24": "https://buffedlizard55-lab.github.io/GEMSDOE24/",
            "GEMSDOE25": "https://buffedlizard55-lab.github.io/GEMSDOE25/",
            "GEMSDOE27": "https://buffedlizard55-lab.github.io/GEMSDOE27/",
            "GEMSDOE28": "https://buffedlizard55-lab.github.io/GEMSDOE28/",
            "GEMSDOE30": "https://buffedlizard55-lab.github.io/GEMSDOE30/",
            "GEMSDOE31": "https://buffedlizard55-lab.github.io/GEMSDOE31/docs/",
            "GEMSDOE32": "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html",
            "GEMSDOE33": "https://buffedlizard55-lab.github.io/GEMSDOE33/",
            "GEMSDOE36": "https://buffedlizard55-lab.github.io/GEMSDOE36/docs/"}

# LOO projections by sha (ledger index sha -> submission -> per_raster)
idx = json.load(open(ROOT / "data/ledger/index.json"))
sha2sub = {}
pins = json.loads((ROOT / "registry/upstream_live_ledger_rasters.json").read_text())["rows"]
for r in pins:
    if r.get("sha256"):
        sha2sub[r["sha256"]] = r["submission"]
loo = {r["submission"]: r["loo_projection"] for r in lst_fit["per_raster"]}


def f3(x):
    return "—" if x is None else f"{x:.3f}"


def f4(x):
    return "—" if x is None else f"{x:.4f}"


# ---------- map PNG (pure numpy+zlib, same technique as scripts/gd_map_png.py)
def write_png(path, rgb):
    H, W, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(H))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def pool(mask, step=4):
    H, W = mask.shape
    H2, W2 = H // step, W // step
    return mask[:H2 * step, :W2 * step].reshape(H2, step, W2, step).max(axis=(1, 3))


def build_map():
    from gemsdoe import io as gio, config as C, validation as V
    with rasterio.open(ROOT / "submission" / NAME) as ds:
        ours = ds.read(1) > 0
    with rasterio.open(ROOT / ".cache/focus/GEMSDOE32.tif") as ds:
        champ = np.where(np.isfinite(ds.read(1)), ds.read(1), 0) > 0
    cat = gio.read_labels()
    de = gio.read_band(C.FEATURES_TIF, 12)
    z = ndi.gaussian_filter(np.nan_to_num(de, nan=float(np.nanmedian(de))), 2.0)
    gy, gx = np.gradient(z)
    shade = np.clip(128 + 40 * (-gx - gy), 0, 255)
    H2, W2 = 3730 // 4, 3292 // 4
    base = shade[:H2 * 4, :W2 * 4].reshape(H2, 4, W2, 4).mean(axis=(1, 3))
    img = np.zeros((H2, W2, 3), np.uint8)
    img[..., 0] = np.clip(base * 0.62, 0, 255).astype(np.uint8)
    img[..., 1] = np.clip(base * 0.66, 0, 255).astype(np.uint8)
    img[..., 2] = np.clip(base * 0.72, 0, 255).astype(np.uint8)
    img[pool(cat)] = (120, 200, 120)
    img[pool(champ)] = (255, 190, 40)
    img[pool(ours)] = (255, 70, 60)
    out = LANE / "map.png"
    write_png(out, img)
    return out.name


CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0f1420;color:#e8ecf3;line-height:1.55}
.wrap{max-width:1080px;margin:0 auto;padding:28px 18px 64px}
h1{font-size:1.7rem;margin:.2em 0} h2{margin-top:2em;border-bottom:1px solid #2a3550;padding-bottom:.3em}
a{color:#7db4ff} code{background:#1a2236;padding:.1em .35em;border-radius:4px;font-size:.86em;word-break:break-all}
table{border-collapse:collapse;width:100%;font-size:.88rem;margin:1em 0}
th,td{border:1px solid #2a3550;padding:.45em .55em;text-align:left;vertical-align:top}
th{background:#16203a} tr:nth-child(even) td{background:#121a2e}
.banner{border-radius:12px;padding:18px 20px;margin:18px 0}
.ok{background:#12351f;border:1px solid #2f9e5f}.warn{background:#3a2c10;border:1px solid #d9a441}
.no{background:#3a1420;border:1px solid #d94a5f}
.btn{display:inline-block;background:#2f9e5f;color:#fff!important;padding:.7em 1.2em;border-radius:8px;text-decoration:none;font-weight:700;margin:.3em .4em .3em 0}
.btn.alt{background:#2456a6}
.tag{display:inline-block;padding:.05em .5em;border-radius:20px;font-size:.78em;font-weight:700}
.yes{background:#2f9e5f;color:#fff}.noo{background:#d94a5f;color:#fff}.mid{background:#d9a441;color:#111}
small{color:#a9b4c8}.mono{font-family:ui-monospace,monospace;font-size:.85em}
img{max-width:100%;border:1px solid #2a3550;border-radius:8px}
"""


def focus_rows():
    fmt = audit["A_format_audit"]
    pair = audit["B_focus_pairwise"]
    order = sorted(OWNER, key=lambda s: -OWNER[s])
    rows = ""
    for s in order:
        r = fmt[s]
        fname = Path(r["path"]).name
        sub = sha2sub.get(r["sha256"])
        proj = loo.get(sub) if sub else None
        # unique vs other 8: any pair with min-direction within3 <= 0.70?
        w3 = []
        for k, v in pair.items():
            a, b = k.split("__")
            if a == s:
                w3.append(v["a_within3_of_b"])
            elif b == s:
                w3.append(v["b_within3_of_a"])
        worst = max(w3) if w3 else None
        rows += (f"<tr><td><a href=\"{SITE_URL[s]}\">{s}</a></td><td class='mono'>{fname}</td>"
                 f"<td>{OWNER[s]:.4f}</td><td>{f3(proj)}</td><td>{r['support_px_gt0_in_foot']:,}</td>"
                 f"<td><span class='tag noo'>NO</span> worst {worst:.1%} within 3 px</td>"
                 f"<td><b>DO NOT SUBMIT</b> (duplicate family)</td></tr>\n")
    return rows


def main():
    raise RuntimeError("BLOCKED: superseded renderer or generator bypasses the literal registry gate; use scripts/build_site.py and see evidence/session_9b794637_run_card.json")
    LANE.mkdir(parents=True, exist_ok=True)
    mapname = build_map()
    dm = card["density_matched_proxy"]["by_target"]
    est = card["analog_frontier_estimate"]
    u = card["correlation_overlap_vs_registry"]
    h = card["holdout_dti"]
    gates_rows = "".join(
        f"<tr><td>{k}</td><td>{'<span class=tag yes>PASS</span>' if v else '<span class=tag noo>FAIL</span>'}</td></tr>"
        for k, v in card["gates"].items())
    can_rows = "".join(f"<tr><td>{r['field']}</td><td>{r['auc_raw']:.3f}</td><td>{r['auc_two_polarity']:.3f}</td></tr>"
                       for r in canary["fields"])
    uniq_top = "".join(
        f"<tr><td class='mono'>{r['comparator']}</td><td>{r['n_other']:,}</td><td>{r['coverage3px_footprint']:.3f}</td>"
        f"<td>{(r['cand_within3'] if r['cand_within3'] is not None else float('nan')):.3f}</td><td>{r['jaccard']:.4f}</td><td>{r['class']}</td></tr>"
        for r in u["rows"][:15])
    analog_rows = "".join(
        f"<tr><td>{r['site']}</td><td class='mono'>{r['submission']}</td><td>{r['owner_reported']:.4f}</td>"
        f"<td>{r['dots']:,}</td><td>{r['frac_gt3px_from_champion']:.2f}</td><td>{r['frac_dh_gt2']:.2f}</td></tr>"
        for r in est["analogs"][:10])

    index = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WBGGEMSDOE3 session 2026-10-27 — executive summary</title><style>{CSS}</style></head><body><div class="wrap">
<p><small>WBGGEMSDOE3 · parallel lane session <b>2026-10-27</b> (branch <code>arena/1f0b051d-wbggemsdoe3</code>) ·
<a href="../index.html">main site</a> · <a href="data/run_card.json">run card JSON</a> ·
<a href="how-to-submit.html">exactly how to submit</a></small></p>
<h1>Executive summary — the one unique file, and what it is honestly worth</h1>

<div class="banner ok"><h2 style="margin-top:0;border:0">✅ DOWNLOAD — the only unique, format-valid candidate</h2>
<p class="mono">{NAME}</p>
<p><a class="btn" href="downloads/{NAME}">⬇ Download TIF</a>
<a class="btn alt" href="downloads/{ZIP}">⬇ Download ZIP (single TIF)</a></p>
<p>SHA-256 <code>{SHA}</code> · {card['dots']:,} dots · single-band float32 · EPSG:32611 · 3730×3292 ·
<b>every cell finite and in [0,1]</b> (zeros outside the footprint — this is the fix for the portal error
“Predicted values must be in range [0, 1]”) · 0 dots on the public catalogue · min catalogue distance √5 px ·
saved-byte validator <b>PASS</b> (vendor + independent re-audit).</p>
<p><b>Unique?</b> YES vs all {u['n_comparators']} restored registry rasters under the protocol rule:
max {u['max_cand_within3_sparse']:.1%} of dots within 3 px of any sparse comparator (limit 70%),
max Jaccard {u['max_jaccard_sparse']:.3f}, max |density-Spearman| {u['max_abs_density_spearman']:.2f} (limit 0.90).
One space-filling lattice (99.87% footprint coverage) is listed and excluded under protocol revision R1.</p></div>

<div class="banner warn"><h2 style="margin-top:0;border:0">⚠️ VERDICT: negative on “beat 0.2778” — selector decision required</h2>
<p>This lane ran its 3 preregistered experiments and <b>could not demonstrate</b> a unique file that beats the
champion family's owner-reported 0.2778 in the initial round. Planning estimate for this file:
<b>≈ {est['analog_median']:.2f}</b> (archive-analog median; analog range {est['analog_range'][0]:.3f}–{est['analog_range'][1]:.3f},
n={est['analog_set_n']}) — an <b>ESTIMATE</b>, not a score. It is the best <i>unique</i> candidate this project has:
submit it only as the unique-lane / final-round-discovery entry (expert review can add its novel scarps to the
final-round label set), not as a claimed 0.2778-beater. No weekly slot was used by this session.
Public leaderboard observed 2026-10-27: top = <b>0.4544</b> (public split; <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>).</p></div>

<h2>The decision table — every focus site, every previous lane, this candidate</h2>
<p><small>“Owner-reported” = user-supplied submission log, <b>no organizer receipt exists for any of them</b>.
“LST LOO” = leave-one-out ledger-tomography projection refit this session on 112 unique restored scored rasters
(LOO MAE {lst_fit['loo_mae']:.4f}, Spearman {lst_fit['loo_spearman']:.3f}) — a projection, never a score.
Uniqueness for focus files is pairwise among the nine (this session's audit); for this candidate it is vs all
{u['n_comparators']} registry rasters.</small></p>
<table><tr><th>Site</th><th>Best historical file (in <code>data/ledger</code> / focus cache)</th><th>Owner-reported</th>
<th>LST LOO projection</th><th>Dots</th><th>Unique?</th><th>Decision</th></tr>
{focus_rows()}
<tr><td>this repo (prev lane)</td><td class="mono">wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif</td>
<td>not submitted</td><td>{lane_lst['skarpline_union']['projection']:.3f}*</td><td>97,608</td>
<td><span class="tag yes">YES</span> vs focus 9</td><td><b>DO NOT SUBMIT on its 0.428 claim</b> — estimate withdrawn by this audit (§3)</td></tr>
<tr><td>this repo (prev lane)</td><td class="mono">wbggems3-hce1-congruence-…-bc1edfe6-zeros.tif</td>
<td>not submitted</td><td>{lane_lst['hce1_congruence']['projection']:.3f}*</td><td>169,968</td>
<td><span class="tag mid">lane-audited</span></td><td>Research only (its own card: projection does not support beating 0.2778)</td></tr>
<tr><td>this repo (prev lane)</td><td class="mono">wbggems3-cspes-edgestab-37654d-…-zeros.tif</td>
<td>not submitted</td><td>{lane_lst['cspes_edgestab']['projection']:.3f}*</td><td>37,654</td>
<td><span class="tag mid">lane-audited</span></td><td>DO NOT SUBMIT (negative holdout in its own card)</td></tr>
<tr><td>this repo (prev lane)</td><td class="mono">wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif</td>
<td>not submitted</td><td>{lane_lst['lst1_hybrid']['projection']:.3f}*</td><td>32,810</td>
<td><span class="tag noo">archived</span></td><td>DO NOT SUBMIT (archived: literal-rule violation; LST number is circular — it was LST-allocated)</td></tr>
<tr style="outline:2px solid #2f9e5f"><td><b>THIS SESSION</b></td><td class="mono">{NAME}</td>
<td>not submitted</td><td>{card['ledger_projection']['projection']:.3f}* (lower-bound-shaped; §5)</td><td>{card['dots']:,}</td>
<td><span class="tag yes">YES</span> max {u['max_cand_within3_sparse']:.1%} within 3 px vs {u['n_comparators']} files</td>
<td><b>DOWNLOAD ✅ · SUBMIT only as unique-lane entry ⚠️</b><br>Estimate ≈ {est['analog_median']:.2f} (analog median)</td></tr>
</table>
<p><small>* Full-fit LST projection (not LOO) for unscored files. All nine focus files fail uniqueness against each other
(pairwise Jaccard 0.342–1.000; GEMSDOE25 ≡ GEMSDOE30 identical support; ≥86.7% of dots within 3 px in the worst
direction of every pair) — resubmitting any of them would be a duplicate, whatever its historical score.</small></p>

<h2>1 · Why and how did GEMSDOE32's 0.2778 get the family's highest score?</h2>
<p>Measured from the pinned bytes this session (not inferred): the B2 mask (37,654 px) is an <b>exact subset</b> of
GEMSDOE31's 40,199-dot base and of GEMSDOE30's 44,090-dot mask. Against GEMSDOE31 it removes exactly
<b>2,545 dots, all at catalogue distance 1.414–2.0 px</b>; its nearest retained dot is √5 ≈ 2.236 px from the
catalogue. So B2 = the shared dotted H19-5-family network <b>plus a catalogue-proximity trim</b> — plausibly
removing mass that sits in the organiser-masked/known-fault neighbourhood and on mis-registered catalogue
shoulders, where it can only earn FP. The owner-reported gain over its base is +0.0070 (0.2708 → 0.2778).
There is no new detector in B2; the whole 0.2449–0.2778 cluster is one network at different trims/budgets.
A causal proof is impossible without the hidden labels and an upload receipt, neither of which exists in this
project — the anatomy above is what the bytes establish. <b>Our candidate adopts the √5 px trim</b> (verified:
min catalogue distance = {verify['min_distance_to_catalogue_px']:.3f} px).</p>

<h2>2 · Can a unique submission beat 0.2778? What the archive actually proves</h2>
<ul>
<li>Ledger tomography (refit here; LOO Spearman {lst_fit['loo_spearman']:.3f}) puts essentially all identified
hidden-truth density <b>on the H19-5 network itself</b>. The λ-optimal allocation that also satisfies the
&gt;3 px uniqueness rule vs champion+skarpline projects only <b>0.098</b> (champion itself: 0.303) — because only
<b>679</b> on-network cells lie &gt;3 px from champion dots. Under that model, uniqueness and beating 0.2778 are
mutually exclusive.</li>
<li>But λ off-network is <b>unidentified, not measured zero</b>: archived files with ~45–57% of dots &gt;3 px from
the champion scored <b>0.2478 / 0.2376 / 0.2343 / 0.2303 / 0.2190</b> (owner-reported) — impossible if off-network
dots earned nothing. The empirical frontier for unique files is therefore ≈ <b>0.22–0.25</b>, reached by
~50/50 corridor/novel hybrids at 37–44k dots. Our candidate is built exactly on that frontier.</li>
<li>Hide-and-recover (protocol holdout) is an <b>anti-proxy</b> for off-catalogue strategies: the champion scores
0.0045 static on it. We report it with its strata-shuffled control instead of as a ranking (§5).</li>
</ul>

<h2>3 · Correction: the previous lane's “estimated 0.428” for skarpline-union is withdrawn</h2>
<p>Its estimator converts SGMC-proxy hit-rate into a leaderboard number. This session measured two fatal
counterexamples: (a) the space-filling lattice (owner-reported <b>0.0904</b>) is “estimated” at <b>0.399</b> and was
trimmed out of its own fit as an outlier (overall R² = −0.65, LOO RMS 0.096); (b) the SGMC proxy itself as a
prediction has hit-rate 1.0 → “estimate” ≈ 1.66, while owner-reported SGMC-off-catalogue submissions score
<b>0.0512 / 0.0492</b>. Density-matched SGMC DTI also ranks the lattice above the champion. The skarpline file
remains a legitimate unique research artifact, but <b>0.428 must not be used for any submission decision</b>;
its LST projection is {lane_lst['skarpline_union']['projection']:.3f} and its density-matched proxy is high
only because SGMC faults live where its scarps are (bedrock ranges).</p>

<h2>4 · This lane's method (H1) and the three experiments</h2>
<p><b>Hypothesis.</b> {card['hypothesis']}</p>
<p><b>Mechanism.</b> {card['mechanism']}</p>
<p><b>Named non-fault mimic.</b> {card['named_non_fault_mimic']}</p>
<table><tr><th>Experiment</th><th>HOLDOUT-DTI (v3.0, fold-legal)</th><th>LEDGER-PROJECTION</th><th>Uniqueness (worst)</th><th>Outcome</th></tr>
<tr><td>E1 pure dipole, 40k</td><td>{e1['holdout']['pooled_dti']:.4f} {e1['holdout']['ci95']}</td><td>{e1['lst']['projection']:.3f}</td>
<td>74.2% vs skarpline — FAIL</td><td>Bedrock-dipole population; duplicate of skarpline lane</td></tr>
<tr><td>E2 + coherence + piedmont + suppressions</td><td>{e2['holdout']['pooled_dti']:.4f} {e2['holdout']['ci95']}</td><td>{e2['lst']['projection']:.3f}</td>
<td>38.7% (subset)</td><td>Unique but strata-empty → frontier diagnostic</td></tr>
<tr><td>E3 frontier hybrid (→ final, after repair)</td><td>{e3['holdout']['pooled_dti']:.4f} {e3['holdout']['ci95']}</td><td>{e3['lst']['projection']:.3f}</td>
<td>{u['max_cand_within3_sparse']:.1%} vs {u['n_comparators']} files</td><td>Delivered; pools after repair {card['poolA_corridor_dots']:,} corridor / {card['poolB_novel_dots']:,} novel</td></tr></table>
<p><small>Other hypotheses generated and ranked before implementation (preregistration): H2 evidence-gated tip
extension, H3 contour-crossing gate (folded into E2 as a soft factor), H4 radiometric-alteration gating,
H5 drainage-deflection corridors (<b>blocked</b>: needs raw USGS 3DEP tiles, unreachable from this sandbox —
free official source named in the preregistration). Full text:
<code>knowledge/preregistration-2026-10-27-session-1f0b051d.md</code>.</small></p>
<img src="{mapname}" alt="Candidate (red) vs champion (amber) vs public catalogue (green) on hillshade">
<p><small>Red = this candidate · amber = GEMSDOE32 champion · green = public catalogue (masked in scoring) · grey = detrended-elevation hillshade. 4× downsampled.</small></p>

<h2>5 · Validation — every number labelled</h2>
<table><tr><th>Instrument</th><th>Label</th><th>This candidate</th><th>References</th></tr>
<tr><td>Hide-and-recover, {h['n_withheld_positives']:,} withheld positives</td><td><b>HOLDOUT-DTI</b> ({h['evaluator_version']})</td>
<td>static read-back {h['final_saved_file_static_readback']['pooled_dti']:.4f} {h['final_saved_file_static_readback']['ci95']};<br>
fold-legal E3 {h['fold_legal_E3_pre_repair']['pooled_dti']:.4f} {h['fold_legal_E3_pre_repair']['ci95']};<br>
strata-shuffled control {h['strata_shuffled_control']['pooled_dti']:.4f}, paired Δ CI {h['strata_shuffled_control']['paired_delta_ci95']} (&gt;0)</td>
<td>champion static 0.0045 · d2.8 static 0.0967 · skarpline static 0.0305 (anti-proxy regime; see §2)</td></tr>
<tr><td>Leakage canary (single-field AUC vs withheld segments, n={canary['n_withheld_positives']:,})</td><td><b>CANARY</b></td>
<td>worst non-catalogue field {canary['worst_non_catalogue_field']['field']} AUC₂={canary['worst_non_catalogue_field']['auc_two_polarity']:.3f} ≤ 0.90 — PASS</td><td>lidar fields ≤ 0.578</td></tr>
<tr><td>Density-matched SGMC segments</td><td><b>PROXY-DTI</b></td>
<td>@8,430: {dm['8430']['final']['mean']:.3f} · @12,691: {dm['12691']['final']['mean']:.3f} · @15,672: {dm['15672']['final']['mean']:.3f}</td>
<td>champion @12,691: {dm['12691']['champion_GEMSDOE32']['mean']:.3f} · GEMSDOE70: {dm['12691']['GEMSDOE70_frontier']['mean']:.3f} (proxy also ranks lattice &gt; champion — weak instrument)</td></tr>
<tr><td>Ledger tomography (112 scored rasters, refit)</td><td><b>LEDGER-PROJECTION</b></td>
<td>{card['ledger_projection']['projection']:.3f} (LOO MAE {lst_fit['loo_mae']:.3f} in-family; off-network unidentified → lower-bound-shaped)</td>
<td>champion in-fit 0.303 · λ-optimal unique bound 0.098</td></tr>
<tr><td>Archive-analog frontier (n={est['analog_set_n']} similar allocations)</td><td><b>ESTIMATE</b></td>
<td>median <b>{est['analog_median']:.3f}</b>, mean {est['analog_mean']:.3f}, range {est['analog_range'][0]:.3f}–{est['analog_range'][1]:.3f} (owner-reported analog scores)</td>
<td>best analog GEMSDOE70 = 0.2478</td></tr>
<tr><td>Organizer receipt</td><td><b>ORGANIZER-CONFIRMED</b></td><td>none — not submitted</td><td>none exists for any file in this project</td></tr></table>
<h3>Gates</h3><table><tr><th>Gate</th><th>Result</th></tr>{gates_rows}</table>
<p><small>G4 (density-matched proxy ≥ champion) fails: candidate {dm['12691']['final']['mean']:.3f} vs champion
{dm['12691']['champion_GEMSDOE32']['mean']:.3f} at |G|=12,691. Recorded, not hidden — it is one reason the
verdict is negative. The same proxy ranks the 0.0904 lattice above the champion, so it cannot be the sole gate;
all three instruments are shown.</small></p>
<h3>Leakage canary (all fields)</h3><table><tr><th>Field</th><th>AUC</th><th>AUC two-polarity</th></tr>{can_rows}</table>
<h3>Uniqueness — worst 15 of {u['n_comparators']} comparators</h3>
<table><tr><th>Comparator</th><th>Dots</th><th>3 px coverage</th><th>Our dots within 3 px</th><th>Jaccard</th><th>Class</th></tr>{uniq_top}</table>
<h3>Top archive analogs (allocation twins)</h3>
<table><tr><th>Site</th><th>Submission</th><th>Owner-reported</th><th>Dots</th><th>Frac &gt;3 px from champion</th><th>Frac off-network</th></tr>{analog_rows}</table>

<h2>6 · Exactly how to submit (selector step — not done by this session)</h2>
<ol><li>Download <a href="downloads/{NAME}">{NAME}</a> (or the ZIP) and verify SHA-256 = <code>{SHA}</code>.</li>
<li>Go to the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> → <b>New submission</b>.</li>
<li><b>File to submit:</b> choose the TIF (single-band float32 GeoTIFF; a .zip containing that single TIF is also accepted).</li>
<li><b>Note:</b> paste exactly:<br><code>{NOTE}</code> ({card['submission_note_chars']} chars)</li>
<li>Submit. The file was rebuilt so that <b>every</b> cell — inside and outside the scored footprint — is finite and in
[0,1] (outside = 0.0, nodata unset): that removes the “Predicted values must be in range [0, 1]” failure mode caused
by NaN/−9999/sentinel outside values. Check your account's weekly quota first (rules: up to 3/week); one final
choice covers both prize rounds.</li></ol>

<h2>7 · Limitations, irregularities flagged for review, and next steps</h2>
<ul>
<li><b>IR-S1 (corrected claim):</b> the main site still says “SUBMIT skarpline, estimated 0.428”. §3 withdraws that
estimate with measured counterexamples; the selector should reconcile the main decision before spending a slot.</li>
<li><b>IR-S2:</b> all historical scores are owner-reported without receipts; byte↔score linkage is unverified.
Public-leaderboard values are a public-chunk split, not the private initial-round set.</li>
<li><b>IR-S3:</b> data are SHA-pinned public GitHub mirrors, not organizer-authenticated downloads (DrivenData
data tab requires login; sandbox egress is allowlisted). Pins prove mirror consistency only.</li>
<li><b>IR-S4:</b> the three available estimators disagree by design (ledger λ unidentified off-network; SGMC proxy
ranks lattice &gt; champion; hide-and-recover anti-correlated for off-catalogue placement). No instrument here can
certify beating 0.2778 — only an organizer receipt can.</li>
<li><b>IR-S5:</b> uniqueness repair moved the pool ratio from 50/50 to {card['poolA_corridor_dots']/card['dots']:.0%}/
{card['poolB_novel_dots']/card['dots']:.0%} (corridor refills were cap-blocked by broad cover rasters); recorded in the run card.</li>
<li><b>IR-S6:</b> outside-footprint convention: official text says null/NaN outside bounds and the sample is NaN
outside; we emit 0.0 (finite, in-range; scored footprint identical). If the portal ever rejects zeros, regenerate
with the shared writer's <code>outside="nan"</code> twin.</li>
<li><b>Next steps (selector / next session):</b> (1) decide skarpline-vs-this-file as the unique entry — do not use
0.428; if a slot is spent, our evidence ranks this file's <i>expected</i> initial-round score below the duplicate
family but its novel scarps carry final-round discovery value; (2) obtain organizer-authenticated data + a receipt
for one file to anchor all estimators; (3) H5 drainage-deflection needs an unrestricted machine for USGS 3DEP tiles;
(4) reconcile the main-site decision banner with §3.</li>
</ul>

<h2>Sources (official / primary)</h2>
<ul>
<li>Competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">overview</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem &amp; metric</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">about</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data (login)</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF (NLR/DOE)</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> ·
staff masking clarification: <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">known-fault pixels are masked in both rounds</a> ·
aggregation: <a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550">pooled public split</a></li>
<li>Data: <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> ·
<a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> ·
<a href="https://pubs.usgs.gov/publication/ds1052">USGS SGMC DS 1052</a> (<a href="https://doi.org/10.5066/F7WH2N65">data DOI</a>) ·
<a href="https://gdr.openei.org/submissions/1391">INGENIOUS GDR 1391</a> ·
<a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS project</a> ·
<a href="https://epsg.io/32611">EPSG:32611</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
<li>Reproduce: <code>scripts/restore_session_data.py</code> → <code>scripts/session_audit.py</code> →
<code>scripts/session_experiments.py fields|canary|lst|e1|e2|e3</code> → <code>scripts/session_finalize.py</code> →
<code>scripts/session_verify.py</code> → <code>scripts/build_session_site.py</code> (this page).
Evidence: <code>evidence/session_1f0b051d_audit.json</code>, <code>evidence/session_1f0b051d_run_card.json</code>,
<code>evidence/session_1f0b051d_verify.json</code>.</li></ul>
<p><small>Generated by <code>scripts/build_session_site.py</code> from evidence JSONs. No organizer-confirmed score
exists for this file. Negative results are deliverables: verdict <b>negative</b> on beating 0.2778.</small></p>
</div></body></html>"""

    howto = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>How to submit — session 2026-10-27 candidate</title><style>{CSS}</style></head><body><div class="wrap">
<p><small><a href="index.html">← Executive summary</a></small></p>
<h1>Exactly how to submit this file</h1>
<div class="banner warn"><p><b>Read first:</b> verdict is <b>negative</b> on beating 0.2778 (see executive summary §2/§5).
This page exists so the separate selector step can act without ambiguity <i>if</i> it chooses this unique-lane entry.
No slot has been used.</p></div>
<ol>
<li><b>Download</b> <a href="downloads/{NAME}">{NAME}</a> (829 KB) or <a href="downloads/{ZIP}">{ZIP}</a>.</li>
<li><b>Verify</b> SHA-256 equals <code>{SHA}</code> (e.g. <code>sha256sum {NAME}</code>). Do not submit any other bytes under this name.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">the competition</a>, sign in, open <b>New submission</b>. Confirm your remaining weekly quota (rules allow up to 3/week; one final selection covers both prize rounds — <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a>).</li>
<li><b>File to submit:</b> select the downloaded <code>.tif</code> (or the <code>.zip</code> — it contains exactly that one TIF).</li>
<li><b>Note (paste exactly, {card['submission_note_chars']} chars):</b><br><code>{NOTE}</code></li>
<li>Click submit and <b>save the receipt/screenshot with the resulting score</b> — that is the only way any number
for this file becomes ORGANIZER-CONFIRMED; add it to <code>evidence/</code> with the date.</li>
</ol>
<h2>Why the earlier “[0, 1]” portal error will not recur with this file</h2>
<p>The portal validates the submitted array's value range. This file was written with the pinned shared writer in
<code>outside="zero"</code> mode and re-audited from its saved bytes: single float32 band, shape/CRS/transform
identical to the pinned sample, <b>all 12,279,160 cells finite</b>, min 0.0 / max 1.0, values only {{0.0, 1.0}},
0.0 outside the scored footprint, no nodata sentinel. NaN-outside, −9999-style sentinels and rescaled-byte rasters
are the usual causes of that portal message; none is present here.</p>
<h2>What to expect</h2>
<p>Planning estimate ≈ <b>{est['analog_median']:.2f}</b> initial-round public-split DTI (archive-analog median,
range {est['analog_range'][0]:.3f}–{est['analog_range'][1]:.3f}) — below the duplicate family's owner-reported
0.2778. The strategic value is uniqueness plus final-round expert review of its {card['poolB_novel_dots']:,}
novel off-network dots. If the goal is only the highest initial-round public number, the evidence says that
requires the (non-unique) H19-5 family — which this project must not resubmit as new.</p>
</div></body></html>"""

    (LANE / "index.html").write_text(index)
    (LANE / "how-to-submit.html").write_text(howto)
    # evidence copies for the lane page
    for src, dst in [(SESS / "canary.json", "canary.json"), (SESS / "lst_fit_session.json", "lst_fit_session.json"),
                     (SESS / "comparator_coverage.json", "comparator_coverage.json"),
                     (ROOT / "evidence/session_1f0b051d_audit.json", "audit.json"),
                     (ROOT / "evidence/session_1f0b051d_verify.json", "verify.json")]:
        if src.exists():
            shutil.copyfile(src, LANE / "data" / dst)
    print(f"wrote {LANE/'index.html'} + how-to-submit + {mapname}")


if __name__ == "__main__":
    main()
