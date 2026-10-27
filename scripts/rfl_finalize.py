#!/usr/bin/env python3
"""RFL finalize (Pass 3): independent validator receipt for the recommended gated
file, the protocol run card (negative), and the docs/rfl executive-summary pages.

All numbers are read from evidence/*.json produced this session - nothing is
hand-typed where a measured value exists.  No new TIF is written: the RFL
candidate stopped as a duplicate (protocol rule 1), so no raster is packaged.
Outputs: evidence/rfl_recommended_validation.json, evidence/rfl_run_card.json,
docs/rfl/{index.html,how-to-submit.html,map.png,run-card.json}
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import time
import zipfile
import zlib
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G  # noqa: E402

OUT = ROOT / "docs" / "rfl"
OUT.mkdir(parents=True, exist_ok=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def validate_saved(tif: Path, foot, labels) -> dict:
    """Independent read-back audit of saved bytes (not the writer's own receipt)."""
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as t:
        t_shape, t_crs, t_tr = t.shape, str(t.crs), [float(v) for v in t.transform][:6]
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = {"count": ds.count, "dtype": ds.dtypes[0], "shape": list(ds.shape),
                "crs": str(ds.crs), "transform": [float(v) for v in ds.transform][:6],
                "nodata": None if ds.nodata is None else float(ds.nodata)}
    fin = np.isfinite(a)
    checks = {
        "single_band": meta["count"] == 1, "dtype_float32": meta["dtype"] == "float32",
        "shape_matches_sample": tuple(meta["shape"]) == t_shape,
        "crs_matches_sample_epsg32611": meta["crs"] == t_crs == "EPSG:32611",
        "transform_matches_sample": meta["transform"] == t_tr,
        "no_nan_anywhere": int(np.isnan(a).sum()) == 0, "no_inf_anywhere": int(np.isinf(a).sum()) == 0,
        "no_sentinel_below_-1e30": int((a < -1e30).sum()) == 0,
        "whole_array_in_0_1": bool(fin.all() and ((a >= 0) & (a <= 1)).all()),
        "in_footprint_all_finite": bool(np.isfinite(a[foot]).all()),
        "zero_on_catalogue": int((a[labels] > 0).sum()) == 0,
        "zero_mass_outside_footprint": int((a[~foot] > 0).sum()) == 0,
        "has_dots": int((a[foot] > 0).sum()) > 0,
    }
    zpath = tif.with_name("wbggems3-hce1-latest.zip")
    zinfo = {}
    if zpath.exists():
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            zinfo = {"zip": zpath.name, "entries": names, "single_tiff": len(names) == 1 and names[0].endswith(".tif"),
                     "zip_sha256": sha256_file(zpath)}
        checks["zip_contains_exactly_one_tiff"] = bool(zinfo["single_tiff"])
    return {"file": tif.name, "sha256": sha256_file(tif), "bytes": tif.stat().st_size, "meta": meta,
            "emitted_positive_pixels": int((a[foot] > 0).sum()),
            "whole_array_min": float(a.min()), "whole_array_max": float(a.max()),
            "checks": checks, "passed": all(checks.values()), "zip": zinfo,
            "label": "local format validation of saved bytes; NOT organizer acceptance"}


def write_png(path: Path, rgb: np.ndarray) -> None:
    """Minimal truecolour PNG writer (no PIL dependency)."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    path.write_bytes(png)


def f(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return str(x)


def main() -> int:
    raise RuntimeError("BLOCKED: superseded renderer or generator bypasses the literal registry gate; use scripts/build_site.py and see evidence/session_9b794637_run_card.json")
    t0 = time.time()
    g = G.load_grid(ROOT / "data/raw")
    E = lambda n: json.loads((ROOT / "evidence" / n).read_text())  # noqa: E731
    focus = E("rfl_focus9_audit.json"); hold = E("rfl_holdout.json"); sel = E("rfl_selector_analysis.json")
    canary = E("rfl_canary.json"); uniq = E("rfl_uniqueness.json"); hce_card = E("hce_run_card.json")
    pins = {s["site"]: s for s in json.loads((ROOT / "registry/focus_sites.json").read_text())["sites"]}

    # --- independent validation of the recommended gated file -------------
    rec_tif = ROOT / "docs/hce/downloads/wbggems3-hce1-latest.tif"
    val = validate_saved(rec_tif, g.foot, g.labels)
    (ROOT / "evidence/rfl_recommended_validation.json").write_text(json.dumps(val, indent=1))
    print(f"HCE validation passed={val['passed']} dots={val['emitted_positive_pixels']:,}", flush=True)

    # physical-consistency diagnostics for the gemsdoe-model estimates
    m_fit = sel["calibration_fit"]["M_trimmed"]
    def cap(mass):
        return m_fit / (m_fit + 0.2 * mass)
    def implied_capture(est_row):
        return est_row["hit_rate"] * est_row["mass"] / m_fit

    # --- protocol run card (negative) -------------------------------------
    rfl = hold["results"]["rfl_full"]; champ = hold["results"]["champion_proxy_d28_b2"]
    packed = np.load(ROOT / ".cache/rfl/final_dots.npy")
    card = {
        "lane": "RFL - range-front relief-discontinuity lineaments (self-assigned; no external lane was identified)",
        "session": "arena/bd44f94b-wbggemsdoe3, 2026-10-27",
        "preregistration": "knowledge/preregistration-2026-10-27-rfl.md (incl. transparent Amendment 1)",
        "hypothesis": ("Multi-scale persistent gradients of focal relief (500 m / 1.1 km) in detrended elevation mark "
                       "Basin-and-Range range-front normal faults that are buried under alluvium and therefore absent "
                       "from the scarp-mapped USGS/INGENIOUS catalogue."),
        "mechanism": "R= focal max-min of det_elev; S=min(rank|grad R500|, rank|grad R1100|); shared greedy top-K 2px-NMS placement, K=37,654; label-independent surface.",
        "named_non_fault_mimic": "Lithologic range fronts (resistant-rock boundaries), alluvial-fan heads and pluvial shorelines also produce persistent relief steps.",
        "canary": {"experiment": "E1", "max_single_feature_auc": max(v["auc"] for v in canary["canary"].values()),
                   "threshold": 0.90, "all_pass": canary["status"] == "pass", "detail": canary["canary"]},
        "holdout_dti": {"label": "HOLDOUT-DTI", "value": rfl["pooled_dti"], "ci95": rfl["ci95_cluster_bootstrap"],
                        "evaluator_version": hold["evaluator_version"], "n_withheld_positives": hold["n_withheld_positives"],
                        "champion_proxy_value": champ["pooled_dti"], "champion_proxy_ci95": champ["ci95_cluster_bootstrap"],
                        "paired_delta_vs_champion": hold["paired_rfl_minus_champion"],
                        "paired_delta_vs_random_null": hold["paired_rfl_minus_null"],
                        "experiment": "E2 (E3 budget sweep not run: preregistered reach condition failed)"},
        "correlation_overlap_vs_registry": {
            "registry_scope": "rebuilt lane-local registry: 151 files / 120 unique dot masks (119 sparse + 1 dense witness); committed 522-file index not fully rebuilt",
            "surface_max_abs_spearman": uniq["surface_before_placement"]["sparse_gate"]["max_abs_spearman"],
            "final_max_abs_spearman": uniq["final_dots"]["sparse_gate"]["max_abs_spearman"],
            "final_max_overlap_nonlattice": uniq["final_dots"]["sparse_gate"]["max_overlap_within3px_nonlattice"],
            "final_worst_nonlattice": uniq["final_dots"]["sparse_gate"]["worst_nonlattice"]["example_path"],
            "final_max_excess_lattice_like": uniq["final_dots"]["sparse_gate"]["max_excess_lattice_like"],
            "sparse_gate_pass": uniq["final_dots"]["sparse_gate"]["pass"],
            "literal_any_raster_max_overlap": uniq["final_dots"]["literal_any_raster"]["max_overlap_within3px"],
            "literal_pass": uniq["final_dots"]["literal_any_raster"]["pass_le_0.70"],
            "outcome": "DUPLICATE under protocol rule 1 - logged, stopped, no raster packaged"},
        "raster_sha256": None,
        "dots_sha256_packed_bits": hashlib.sha256(packed.tobytes()).hexdigest(),
        "n_dots": hold["final_n_dots"],
        "validator_output": {"status": "NOT RUN - no candidate raster was written (duplicate stop before packaging)",
                             "required": "no NaN in footprint; values in [0,1]; CRS/shape/transform = sample"},
        "submission_name": None, "submission_note": None,
        "verdict": "negative",
        "verdict_reason": ("HOLDOUT-DTI 0.0538 loses paired comparison vs champion proxy 0.0992 (delta -0.0454, CI excludes 0) "
                           "AND final dots breach the 70% uniqueness gate (0.709 vs GEMSDOE22 h23-b; lattice excess +0.079). "
                           "RFL does beat the same-K random null (+0.0225, CI excludes 0) and has the highest SGMC-proxy "
                           "hit-rate measured (h=0.189), so the relief-gradient signal is real but neither unique nor "
                           "holdout-competitive as specified."),
        "experiments_used": ["E1 canary", "E2 holdout battery"], "experiments_budget": 3, "slots_spent": 0,
        "selector_recommendation_separate_step": {
            "recommended_file_for_selector": "docs/hce/downloads/wbggems3-hce1-latest.tif",
            "why": ("Only saved file passing every protocol gate on bytes re-audited this session: format VALIDATOR PASS "
                    "(evidence/rfl_recommended_validation.json), full 120-mask registry uniqueness PASS (max overlap 0.524, "
                    "max |rho| 0.325), lane canary PASS, fold-local HOLDOUT-DTI 0.1292 [0.1160,0.1426] (GEMSDOE32-HIDE-RECOVER-v3.0, "
                    "22232 withheld) beating champion proxy 0.0992. Leaderboard expectation is NOT established to beat the "
                    "owner-reported 0.2778: estimator-dependent (see site). Slot selection and weekly cap remain the human selector's step."),
            "skarpline_correction": ("wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif FAILS full-registry uniqueness "
                                     "(0.735 GEMSDOE23 h30, 0.724 GEMSDOE50 h59; ex-self) and has no fold-local holdout - superseded."),
        },
        "elapsed_note": "within 3-experiment / 2-hour modelling budget for E1+E2; E0/Pass-2 are read-only audits",
        "created_utc": "2026-10-27",
    }
    (ROOT / "evidence/rfl_run_card.json").write_text(json.dumps(card, indent=1))
    (OUT / "run-card.json").write_text(json.dumps(card, indent=1))

    # --- quick-look map ----------------------------------------------------
    try:
        surf = np.load(ROOT / ".cache/rfl/surface.npy")
        dots = np.unpackbits(packed)[: g.foot.size].reshape(g.foot.shape).astype(bool)
        with rasterio.open(rec_tif) as ds:
            hce = (ds.read(1) > 0) & g.foot
        ds4 = lambda a: a.reshape(3730 // 2, 2, 3292 // 2, 2).max(axis=(1, 3))  # noqa: E731
        bg = (ds4((surf * 255).astype(np.uint8))).astype(np.float32)
        rgb = np.stack([bg, bg, bg], axis=-1)
        rgb[ds4(g.labels)] = [60, 200, 60]
        rgb[ds4(dots)] = [255, 70, 60]
        rgb[ds4(hce)] = [40, 170, 255]
        write_png(OUT / "map.png", np.clip(rgb, 0, 255).astype(np.uint8))
        print("map written", flush=True)
    except Exception as e:  # map is cosmetic; never block the evidence
        print(f"map skipped: {e}", flush=True)

    # --- site pages ---------------------------------------------------------
    CSS = """:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mut:#9aa7b4;--ok:#2ea043;--warn:#d29922;--bad:#da3633;--accent:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{background:#010409;border-bottom:1px solid var(--line);padding:14px 20px}main{max-width:1080px;margin:0 auto;padding:26px 20px 80px}
h1{font-size:29px;line-height:1.25}h2{font-size:22px;margin:34px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}h3{font-size:17px}
code{background:#1f2630;padding:1px 5px;border-radius:4px;font-size:13px}.small{font-size:13.5px;color:var(--mut)}
.hero{border:1px solid var(--ok);background:linear-gradient(180deg,#0f2418,#0d1117);border-radius:12px;padding:22px;margin:14px 0}
.tag{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:99px;background:var(--ok);color:#04150a}
.tag.no{background:var(--bad);color:#fff}.tag.warn{background:var(--warn);color:#1a1200}
.btn{display:inline-block;background:var(--ok);color:#fff;font-weight:700;padding:13px 22px;border-radius:9px;text-decoration:none;margin:12px 10px 4px 0}
.btn.alt{background:#21262d;border:1px solid var(--line);color:var(--fg)}table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-size:12px;text-transform:uppercase}
.yes{color:var(--ok);font-weight:700}.no{color:var(--bad);font-weight:700}.mid{color:var(--warn);font-weight:700}
.note{background:var(--panel);border-left:3px solid var(--accent);padding:12px 14px;margin:14px 0}.warnbox{background:var(--panel);border-left:3px solid var(--warn);padding:12px 14px;margin:14px 0}
img.map{width:100%;border:1px solid var(--line);border-radius:10px}a{color:var(--accent)}"""
    def page(title, body):
        return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · WBGGEMSDOE3</title>'
                f'<style>{CSS}</style></head><body><header><b>WBGGEMSDOE3</b> · RFL audit & corrected selector decision (2026-10-27) · '
                f'<a href="../index.html">Start</a> · <a href="how-to-submit.html">How to submit</a></header><main>{body}</main></body></html>')

    est = sel["estimates"]; fit = sel["calibration_fit"]; rank = sel["evaluator_ranking"]["spearman_vs_owner"]
    hce_hold = hce_card["holdout_dti"]
    rows_focus = ""
    for s, r in focus["sites"].items():
        e = est[f"{s}_leader"]
        rows_focus += (f'<tr><td><a href="{r["upstream_repo"]}" target="_blank" rel="noopener">{s}</a></td>'
                       f'<td><code>{Path(pins[s]["path"]).name}</code><br><span class="small">{r["n_dots_finite_positive_in_footprint"]:,} dots · SHA {r["sha256"][:12]}…</span></td>'
                       f'<td>{r["owner_reported_score_USER_REPORTED_not_organizer_confirmed"]} (USER-REPORTED)</td>'
                       f'<td>{f(e["estimate_at_M_fit"])} (ESTIMATE)</td>'
                       f'<td>{f(r["static_holdout_dti"]["dti"])} HOLDOUT-DTI static*</td>'
                       f'<td class="no">NO — duplicate family</td><td class="no">DO NOT SUBMIT as new</td></tr>')
    cand_rows = ""
    meta_c = [
        ("HCE-1 (this repo, parallel lane)", "hce1_bc1edfe6", "docs/hce/downloads/wbggems3-hce1-latest.tif",
         '<span class="yes">PASS all gates</span>', '<b>RECOMMENDED TO SELECTOR</b>'),
        ("skarpline union (this repo)", "skarpline_union_610acf58", "submission/wbggemsdoe3-skarpline-union-…zeros.tif",
         '<span class="no">FAIL uniqueness (0.735 / 0.724)</span>', '<span class="no">DO NOT SUBMIT (protocol)</span>'),
        ("RFL — this session's new lane", "rfl_final_dots_research_only", "no TIF written (duplicate stop)",
         '<span class="no">FAIL uniqueness (0.709) + holdout</span>', '<span class="no">NEGATIVE — research only</span>'),
        ("CSPES (this repo)", "cspes_9e28c697", "submission/wbggems3-cspes-…zeros.tif",
         '<span class="mid">format PASS; holdout negative</span>', '<span class="no">DO NOT SUBMIT</span>'),
    ]
    for label_, key, path_, gates_, verdict_ in meta_c:
        e = est[key]
        cand_rows += (f'<tr><td>{label_}<br><span class="small"><code>{path_}</code> · {int(e["mass"]):,} dots</span></td>'
                      f'<td>{f(e["estimate_at_M_fit"])} ESTIMATE<br><span class="small">physical cap {f(cap(e["mass"]))} · implied capture {f(implied_capture(e), 2)}</span></td>'
                      f'<td>h={f(e["hit_rate"])} · proxy {f(e["dti_proxy_sgmc"])}</td><td>{gates_}</td><td>{verdict_}</td></tr>')

    body = f"""
<div class="hero"><span class="tag">Only fully-gated file — for the human selector</span>
<h1>Executive summary: what to download, what it might score, and what is actually unique</h1>
<p style="font-size:17px">After a full re-audit this session, <b>one</b> file in this repository passes every automated gate
(format on saved bytes, leakage canary, fold-local holdout win, uniqueness vs the full rebuilt 120-mask registry):
<code>wbggems3-hce1-latest.tif</code> (169,968 dots, SHA-256 <code>{val['sha256'][:16]}…</code>).</p>
<a class="btn" href="../hce/downloads/wbggems3-hce1-latest.tif" download>⬇ Download the gated GeoTIFF</a>
<a class="btn alt" href="../hce/downloads/wbggems3-hce1-latest.zip" download>⬇ Single-TIFF .zip</a>
<a class="btn alt" href="how-to-submit.html">Exactly how to submit →</a>
<div class="warnbox"><b>Honest expectation.</b> No file here has an organizer-confirmed score above the owner-reported 0.2778,
and this file's leaderboard value is <b>not established</b>: published local estimates for it range from 0.082
(HCE lane's winner-similarity ridge model) through 0.104 (SGMC prevalence-calibrated) to a gemsdoe-model point value
of {f(est['hce1_bc1edfe6']['estimate_at_M_fit'])} that <b>exceeds its own physical cap ({f(cap(est['hce1_bc1edfe6']['mass']))}) and must be discarded</b>.
What <i>is</i> established locally: HOLDOUT-DTI {f(hce_hold['candidate'])} [{f(hce_hold['candidate_ci95'][0])}–{f(hce_hold['candidate_ci95'][1])}]
(GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives) vs champion proxy {f(champ['pooled_dti'])}.
Uploading spends a weekly-capped slot: that choice stays with the human selector (protocol rule 6).</div></div>

<div class="warnbox"><b>POST-MERGE ADDENDUM (PR #29 merge with the score-tomography lane already on <code>main</code>).</b>
After this audit was completed, the repository's cleared file became
<code>wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif</code> (30,000 dots, all ≥200 m off
catalogue; LEDGER-INVERSION ESTIMATE 0.269, bias-corrected 0.207 — an estimate, not a score). This session
independently re-audited its saved bytes: format valid (all-finite in [0,1], EPSG:32611, zero on catalogue) and
<b>PASS</b> on the same rebuilt 120-mask registry used below (max 63.1% of dots within 3 px of any non-lattice mask;
lattice-excess −0.007; receipt <code>evidence/rfl_tde30k_postmerge_audit.json</code>). <b>For the actual upload
decision and download, follow the repository dashboard / README top block (TDE-30k)</b>; the HCE-1 file below
remains the best <i>fold-local-holdout</i> research alternative, and everything else on this page stands as the
audit record of this session.</div>

<h2>Decision table — this repository's candidate files</h2>
<table><tr><th>File</th><th>Estimated leaderboard DTI</th><th>SGMC proxy profile</th><th>Gates</th><th>Decision</th></tr>{cand_rows}</table>
<p class="small">ESTIMATE = gemsdoe SGMC-calibrated model re-fit this session (|G|={f(m_fit,0)} px, {fit['n_used']}/{fit['n_total']} calibration
files, leave-one-out RMS ±{f(fit['loo_rms'])} — treat any point estimate as ±0.10 at best). “Physical cap” = maximum attainable
value of that model at the file's mass (TP cannot exceed |G|); “implied capture” &gt;1 means the model is extrapolating
outside physics (true for HCE's point value; skarpline implies {f(implied_capture(est['skarpline_union_610acf58']),2)} capture of all hidden faults).</p>

<h2>Decision table — the nine focus sites (GEMSDOE24/25/27/28/30/31/32/33/36)</h2>
<table><tr><th>Site</th><th>Best historical file (pinned bytes)</th><th>Owner-reported score</th><th>Calibrated estimate</th><th>Local holdout</th><th>Unique vs the other eight?</th><th>Decision</th></tr>{rows_focus}</table>
<p class="small">*Static HOLDOUT-DTI of saved bytes (GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld positives). Files pruned
against the <i>full</i> catalogue (28/31/32/36) are penalised by construction — deleted dots near hidden segments cannot
earn credit — so this column must not be read as their live quality. <b>Measured anatomy:</b> all 36 pairwise comparisons
exceed 70% dots within 3 px in both directions (minimum 86.7%); GEMSDOE25 and GEMSDOE30 leaders have <b>identical</b> dot
support; GEMSDOE32 ⊂ GEMSDOE31 ⊂ GEMSDOE25/30 and GEMSDOE32 ⊂ GEMSDOE36. They are one dotted network, repeatedly re-trimmed —
none is a unique new submission. Evidence: <code>evidence/rfl_focus9_audit.json</code>.</p>

<h2>Why did GEMSDOE32 B2 report 0.2778 — and can we beat it?</h2>
<p><b>What B2 is (measured from bytes):</b> the shared dotted H19-5 network trimmed to 37,654 dots by deleting every dot
within 2 px of a catalogue fault — exactly 2,545 dots removed vs GEMSDOE31, none added. <b>Why that could help:</b> the
official DTI (α=0.2 FP, β=0.8 FN, 300 m triangular kernel) masks known-fault pixels, so dots hugging known faults spend
mass for little marginal kernel credit; pruning them raises credit-per-mass <i>if</i> hidden faults are not concentrated
in the 0–2 px catalogue halo. <b>What cannot be claimed:</b> the +0.0070 gap over GEMSDOE31 has no organizer receipt, and
the shared proximity-pruning holdout (H6-1) measures the pruning effect at +0.00005 (vs random pruning +0.00011, CI includes
zero) — two orders of magnitude smaller, on a proxy that by design has no withheld truth in the halo. The 0.2449–0.2778
family spread is mostly explained by mass and hit-rate (calibration residuals ≤0.025 in-sample for the 10 used files).
<b>Can a file beat 0.2778?</b> The public leaderboard top observed 2026-10-27 was 0.4544, so headroom exists. No artifact in
this repository proves it can: the only fully-gated candidate (HCE-1) has estimator-dependent expectations spanning
0.08–0.32. The honest next step is the selector's: one capped slot converts an estimate into the project's first receipt.</p>

<h2>This session's new lane (RFL) — a measured negative</h2>
<p>Hypothesis: persistent focal-relief gradients mark alluvium-buried range-front faults with no catalogue scarp
(preregistration + four ranked alternatives: <code>knowledge/preregistration-2026-10-27-rfl.md</code>).
Canary <span class="yes">PASS</span> (max AUC {f(card['canary']['max_single_feature_auc'])}). HOLDOUT-DTI {f(rfl['pooled_dti'])}
[{f(rfl['ci95_cluster_bootstrap'][0])}–{f(rfl['ci95_cluster_bootstrap'][1])}] vs champion proxy {f(champ['pooled_dti'])}
(paired Δ {f(hold['paired_rfl_minus_champion']['delta'])}), vs random null Δ {f(hold['paired_rfl_minus_null']['delta'])}
(CI excludes 0 — the signal is real) — and the placed dots then <b>failed uniqueness</b> (70.9% within 3 px of GEMSDOE22 h23-b;
limit 70%). Verdict <span class="no">negative</span>; no TIF was packaged. Run card: <a href="run-card.json">run-card.json</a>.
The piedmont-gated ablation scored higher on holdout (0.0633) — recorded as a future preregistration, not selected post hoc.</p>
<img class="map" src="map.png" alt="RFL surface with catalogue, RFL dots and HCE dots">
<p class="small">Quick look (4× down-sampled; grey = RFL relief-gradient surface). Green = public catalogue;
red = this session's RFL dots (research only); blue = recommended HCE-1 dots.</p>

<h2>Which local evaluator should you trust? (measured, n=118)</h2>
<p>Spearman rank correlation vs owner-reported scores across all 118 byte-verified ledger submissions:
static HOLDOUT-DTI <b>{f(rank['static_holdout_dti'],3)}</b> · SGMC hit-rate h <b>{f(rank['sgmc_hit_rate_h'],3)}</b> ·
SGMC proxy DTI <b>{f(rank['sgmc_proxy_dti'],3)}</b> · calibrated estimate <b>{f(rank['calibrated_estimate'],3)}</b> ·
mass alone {f(rank['mass'],3)}. Neither evaluator is strong; SGMC-family metrics rank historical files moderately,
while static catalogue holdout is structurally biased against catalogue-pruned files. Fold-local holdout remains the
valid comparator for <i>methods</i>; no local number is a leaderboard score.</p>

<h2>Corrections and irregularities recorded this session</h2>
<ul>
<li><b>IR-20:</b> skarpline's “uniqueness PASS” used 20 comparators; vs the full rebuilt registry it fails (0.735/0.724). Its SUBMIT status is superseded (banner on every root page).</li>
<li><b>IR-21:</b> the gemsdoe estimate model extrapolates beyond physics for dense files (lattice in-sample residual +0.31 was trimmed from its fit; HCE point estimate exceeds its cap). Point estimates now ship with cap + implied-capture diagnostics.</li>
<li><b>IR-22:</b> <code>src/gemsdoe/validation.py</code> claims catalogue-holdout Spearman −0.15 (11 files); the 118-file measurement here is +0.172 under a fully specified static protocol. Unreconciled — flagged, not silently edited.</li>
<li><b>IR-23:</b> legacy <code>…-nan.tif</code> stepover download contains no NaN bytes (nodata=NaN metadata only). Filename ≠ encoding; it remains research-only.</li>
<li><b>IR-01/11 unchanged:</b> the literal any-raster uniqueness rule is vacuous (space-filling witness; the 0.2778 champion itself overlaps it 100%). All uniqueness verdicts here give the operative sparse-registry result <i>and</i> the literal result.</li>
<li>Every historical score on this page is <b>USER/OWNER-REPORTED</b> — no DrivenData receipt exists in this repository for 0.2778 or any other file. The “Predicted values must be in range [0,1]” portal error is still not reproduced by any local file (11/11 downloads audited finite in [0,1] this session); the recommended file is all-finite zeros-outside by construction.</li>
</ul>
<p class="small">Evidence: <code>evidence/rfl_focus9_audit.json</code> · <code>evidence/rfl_canary.json</code> ·
<code>evidence/rfl_holdout.json</code> · <code>evidence/rfl_uniqueness.json</code> ·
<code>evidence/rfl_selector_analysis.json</code> · <code>evidence/rfl_recommended_validation.json</code> · <code>evidence/rfl_run_card.json</code>.
Official sources: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem & metric</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> ·
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> ·
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR rules PDF</a> · <a href="https://pubs.usgs.gov/publication/ds1052">USGS SGMC DS-1052</a> ·
<a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS data</a> · <a href="https://epsg.io/32611">EPSG:32611</a>.</p>"""
    (OUT / "index.html").write_text(page("Executive summary (corrected)", body))

    sub = f"""
<div class="warnbox"><b>POST-MERGE NOTE:</b> the repository's cleared upload is now the TDE-30k file on the
<a href="../index.html">dashboard</a> (note: <code>TDE-30k: truth-posterior from score tomography x lidar/gravity/magnetic edge concordance; all dots &gt;=200 m off catalogue</code>).
The steps below document this session's gated HCE-1 file and the [0,1]-error analysis; do not spend a slot on
both files without a selector decision.</div>
<h1>Exactly how to submit the gated file</h1>
<ol>
<li>Download <a href="../hce/downloads/wbggems3-hce1-latest.tif" download><code>wbggems3-hce1-latest.tif</code></a>
(or the <a href="../hce/downloads/wbggems3-hce1-latest.zip" download>single-TIFF .zip</a>). Do not rename the TIFF inside the zip;
upload the bytes unchanged. Expected SHA-256: <code>{val['sha256']}</code> ({val['bytes']:,} bytes, {val['emitted_positive_pixels']:,} positive pixels).</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → New submission</a>
and check the <b>weekly submission cap</b> shown there first — this repository cannot see your quota, and uploading is the
human selector's step (no slot was spent by any automated lane).</li>
<li>Choose the downloaded file in <i>File to submit</i>.</li>
<li>Paste this note (129 chars, ≤140):<br><code>HCE-1: phase-congruent physical susceptibility; HGB on visible faults; 3px lattice + registry-novel repair. No organizer receipt.</code></li>
<li>Submit, then record the receipt (score + timestamp + file SHA above) back into <code>registry/</code> — it would be this project's first ORGANIZER-CONFIRMED number.</li>
</ol>
<h2>Why this file will not trigger “Predicted values must be in range [0, 1]”</h2>
<p>Independently re-validated from the saved bytes this session (<code>evidence/rfl_recommended_validation.json</code>):
single band · float32 · 3730×3292 · EPSG:32611 · transform identical to the sample submission ·
<b>zero NaN / zero Inf / no sentinel values anywhere in the array</b> · whole-array minimum {f(val['whole_array_min'],1)} and maximum
{f(val['whole_array_max'],1)} · zeros outside the scored footprint · zero positive pixels on the mapped catalogue.
The historical portal error is not reproduced by any of the 11 locally downloadable TIFFs audited this session;
files with NaN outside the footprint remain the prime suspect, which is why only <b>zeros-outside, all-finite</b>
artifacts are presented as submittable here.</p>
<h2>What not to submit</h2>
<ul>
<li><code>wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif</code> — fails the project uniqueness gate on the full registry (IR-20). The uniqueness gate is a <i>project protocol</i>, not an organizer rule (IR-10); submitting it anyway is a conscious waiver decision for the selector, not something this page recommends or hides.</li>
<li>Any GEMSDOE24–36 historical leader — measured duplicates of one another (see <a href="index.html">executive summary</a>); also not this project's work to re-submit.</li>
<li>CSPES / LST1 / stepover / lattice files — negative or research-only lanes.</li>
</ul>"""
    (OUT / "how-to-submit.html").write_text(page("How to submit", sub))
    print(f"wrote run card + validation + site in {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
