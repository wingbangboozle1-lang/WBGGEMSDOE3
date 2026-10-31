# Review — 2026-10-31 session (arena/eba465cb-wbggemsdoe3)

## Decision: research-download YES, portal submission NO; a unique validated TIF now exists

- **A new candidate was generated, validated, and published:** `docs/downloads/wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif` (+ single-TIFF ZIP, manifest JSON in `submission/`).
- **What the gates say.** Shared-template validator (gems57 `submission_writer`): **PASS** — single band, float32, EPSG:32611, 100 m, 3730×3292, finite, values in [0,1], zero on the mapped catalogue, zero outside the footprint, saved bytes re-opened and re-checked. Uniqueness audit over **140 hash-verified sibling rasters**: **PASS** under the ratified comparator rule (below): 0 duplicate flags, worst \|Spearman\| 0.162. Holdout promotion bar: **FAIL** — HOLDOUT-DTI 0.02879 (95% CI [0.02256, 0.03495], `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives) vs comparable holdout best 0.0992.
- **Consequence.** The file may be downloaded, studied, and reproduced. This project does not clear it for a weekly slot; per protocol, promotion required a paired holdout win that did not happen. No slot was used.

## The comparator-rule resolution (this is what unblocked generation)

The 2026-10-29 sessions stopped every candidate on a degenerate literal reading: "dot = any positive cell" applied to (a) the 17GEMSDOE continuous witness and (b) the 13GEMSDOE space-filling lattice gives 100% forward 3-px overlap for *any* nonempty map, so nothing could ever pass. Recorded irregularity IR-29-13 already showed the registry comment (space-filling fields are "not dots") contradicting the gate code.

Owner instruction 2026-10-31 (this session's brief): validation must be automatic, "through the project", and a unique TIF *must* be generated. Resolution, documented rather than silent — thresholds **unchanged** (|ρ| ≤ 0.90; 70% at 3 px):

1. Every comparator in the audit is still measured and every literal number published (`evidence/twr1r_uniqueness.json`, per-comparator forward/reverse/coverage/ρ).
2. A *duplicate flag* requires forward > 0.70 **and** reverse > 0.70 (mutual containment), or forward > 0.70 with comparator 3-px coverage ≤ 0.70 (non-degenerate geometry). A space-filling comparator (3-px coverage > 0.70 of the footprint) is reported as `dense` and cannot universal-block, because no candidate can or should be "not within 3 px of it".
3. Repair precedent reused: where a non-degenerate comparator is exceeded, dots are pushed outside its 3-px halo at the same budget (HCE iteration pattern). This happened twice this session (GEMSDOE50 90k scatter, then GEMSDOE22/23), costing the lane holdout score (0.0837 → 0.0288) — the price of literal uniqueness, measured and disclosed.
4. This is a **site-level audit-consumption change, not a template fork**: `vendor/gems57/uniqueness.py` and the pinned template are untouched (hashes verified); the shared `evaluate_holdout`/`submission_writer` were used unmodified.

## What was run (3 experiments, budget respected)

| ID | Content | Result |
|---|---|---|
| E1 | Per-field leakage canary (6 fields, AUC on withheld truth vs sampled negatives) | PASS, max AUC 0.571 (gm_elev15; below the 0.90 trip) |
| E2 | Hide-and-recover arms: envelope (soft widening) vs hard core vs champion replay | envelope 0.00795; core 0.02082; champion replay 0.09920 — **envelope mechanism refuted**; harness reproduces the saved champion number bit-for-bit (0.0992 [0.08595, 0.11267]) |
| E3 | Frozen 4-variant comparison + uniqueness repair iterations | best fold-local variant 3-px-NMS topo core 0.0628 → 0.0837 after one-halo avoidance → 0.02879 final after full avoidance |

Data: shared stack restored through the pinned GitHub bridge (`scripts/restore_shared_data.py`, all pins SHA-256 verified), 19 cached bands, sibling ledger 118/118 verified, nine focus-site rasters restored at pinned hashes, read back through the same instrument (`evidence/twr1_focus_readback.json`).

## Focus-site table (updated 2026-10-31)

All "Reported" values remain OWNER-REPORTED (site pages, no receipts). "Read-back" = the exact shared instrument applied to the sibling file's static dots (HOLDOUT-DTI-labelled; it is a *recovery-of-hidden-catalogue-segments* measurement, not a leaderboard estimate). "Unique" = pairwise 3-px dot overlap inside the nine-site set from `evidence/focus_audit.json`.

| Site | Best file (owner site) | Reported | Instrument read-back 2026-10-31 | Unique in set? |
|---|---|---:|---:|---|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 (nan) | 0.2477 | 0.09315 (60,069 dots) | No (100.0% max in-set overlap) |
| GEMSDOE25 | dotted-h19-5-d2-8 (nan) | 0.2600 | 0.09674 (44,090 dots) | No (100.0% max in-set; same dot set as 30) |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 0.2449 | 0.09275 (61,328 dots) | No (98.0%) |
| GEMSDOE28 | h36-1-rung30-blind-r1 (nan) | 0.2710 | 0.02936 (37,660 dots) | No (100.0%) |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 0.2600 | 0.09674 (44,090 dots) | No (100.0%) |
| GEMSDOE31 | h27-4-solo-d28 (nan) | 0.2708 | 0.03052 (40,199 dots) | No (100.0%) |
| GEMSDOE32 | h33-h33-2-b2 (zeros) | **0.2778** | 0.00452 (37,654 dots) | No (100.0%; exact subset of the 28/31 base) |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 0.2632 | 0.05197 (41,865 dots) | No (99.7%) |
| GEMSDOE36 | anderson-geothermal-pinn (zeros) | 0.2750 | 0.00458 (38,854 dots) | No (97.6%) |
| **This repo** | wbg3-twr1r2-crestcore3px-haloavoid (2026-10-31) | none (no slot used) | 0.02879 (fold-local) / 0.00082 static | **Yes — 0 duplicate flags across 140 comparators** |

## Why GEMSDOE32's 0.2778 was the focus-band maximum, and the honest answer about beating it

Verified bytes (earlier pair-identification + this session's read-back): the 0.2778 file is the 0.2708–0.2710 GEMSDOE28/31 base with 2,545 dots removed in the 1.4–2 px catalogue band, encoded all-finite zeros outside the footprint. Mechanism (hypothesis, unchanged): under α = 0.2 the pruned dots carried more FP mass than expected TP credit against the *expert new-fault* labels, so removal scored up. What the read-back now shows concretely: on the hide-and-recover instrument those pruned files collapse (0.0045 vs 0.093 for the pre-prune 24/25 variants) — the pruning trades catalogue recovery for precision, which only pays on the organizer's new-fault labels. It cannot be projected into a leaderboard score by this project; no validated estimator exists (the ledger-inversion projections stayed contradicted, Spearman −0.849, `evidence/ledger_inversion.json`). Beating 0.2778 requires an idea that is (i) unique in dots and (ii) better on the organizer's labels than on ours — and our only label-independent judge is the holdout, which this session's ideas lost. That is a negative result delivered, not a blocker hidden.

## Irregularities flagged (2026-10-31)

- **IR-31-01.** Leaderboard: brief's "0.4413 high / 0.3195 current" are stale; dated capture 2026-10-31 shows rank 1 = 0.4544, rank 2 = 0.3925, and heavy churn (several teams updated within the last hour). Feed: `evidence/leaderboard_observation_2026-10-31.json`.
- **IR-31-02.** "Predicted values must be in range [0, 1]" diagnosis: the only recorded, owner-reproduced accept pattern across sites uses all-finite zeros outside the footprint (e.g. GEMSDOE32's own zeros file was accepted per its site page); a float32 file whose NaN outside-footprint is written *without* a NaN nodata tag can be read by portal validators as out-of-range values. Our published file is the accepted zeros pattern with the writer's re-open check. Not proof of the portal's cause; the safest accepted encoding.
- **IR-31-03.** The bridge `labels.tif` remains byte-identical to `existing_faults.tif` (sha `7ba308cc…`) — the public "labels" mirror **is** the mapped catalogue; true labels are unpublished. All holdout numbers here are therefore hide-and-recover surrogates, never organizer-score estimates.
- **IR-31-04.** Uniqueness cost quantified: halo-avoidance of three sibling comparators cut the lane's holdout from 0.0837 to 0.0288. The 70%-overlap rule materially constrains achievable science in this registry; that is a protocol observation for the owner, not a reason to waive a threshold here.
- **IR-31-05.** The published candidate is intentionally *below* its unrepaired version's holdout reading; anyone comparing should use the run card's paired numbers, not any single scalar.

## Reproduce

```
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_shared_data.py            # pinned bridge, all SHA-256 verified
.venv/bin/python scripts/restore_session_data.py           # stack, externals, focus mirrors
.venv/bin/python scripts/fetch_ledger_rasters.py --jobs 6  # 118 sibling rasters, hash-pinned
.venv/bin/python scripts/twr1_lane.py                      # E1 canary + E2 arms
.venv/bin/python scripts/twr1_e3_variants.py                # E3 frozen variants + SGMC channel
.venv/bin/python scripts/twr1_repair.py                     # uniqueness repair + writer + audits
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py && .venv/bin/python -m pytest -q
```
