# Review — 2026-10-29 session (arena/c3775ee9-wbggemsdoe3)

## Decision: NOT OK to download or submit. No TIFF was generated.

- **Download a TIFF from this project today?** No. Every file in `docs/downloads/` is research-only and labelled DO NOT SUBMIT.
- **Why no new TIFF?** The user's own parallel-run rule says to stop if more than 70% of a candidate's dots fall within 3 px of any registry raster. The registered dense witness (below) is positive in every in-bounds cell, so under the literal definition of "dot", every candidate fails. The rule says to stop and log, so I did not build a file that would be blocked by the stop.
- **What would unblock it?** Two decisions from you (below). I cannot make them without a protocol change.

### Decisions needed from you

**Q1 — What counts as a "dot" when comparing rasters?**
- (a) **Literal (current):** any cell with value > 0 is a dot. The witness has 5,167,373 of 5,167,373 in-bounds positive cells, so every candidate fails. Result: no file can be cleared; the project stays DO NOT SUBMIT.
- (b) **Top-N:** each raster's dots are its own N highest-value cells, where N is that raster's dot count. This is my recommended reading, but it changes the rule, so it needs your approval and a preregistration before any candidate is tested. The witness's top-37,654 cells start at value 0.8438; top-44,090 at 0.8305; top-60,069 at 0.8011 (`evidence/witness_independent_stats_2026-10-29.json`).
- (c) **Fixed-threshold binary:** dot = value ≥ a cutoff you set in advance (for example 0.5). Still needs a preregistered cutoff.
- (d) Something else you specify.

**Q2 — Does the binary lattice count as a registry raster?**
The repo reports that a 13GEMSDOE binary lattice raster is within 3 px of 99.86% of the footprint, which would block almost any candidate under the 70% rule regardless of Q1. Per the repo's notes, I have **not** re-measured this lattice this session. Options:
- (a) Yes, it counts (literal).
- (b) No. Exclude dense or lattice rasters from the comparator set, following the earlier 2026-10-28 convention.
- (c) Count only rasters with fewer than a set number of dots.

Any answer should be recorded in `knowledge/protocol.md` before a candidate is generated. The decision is yours, so this review does not assume an answer.

## Answer to "why did GEMSDOE32 score 0.2778, and can we beat it?"

Full analysis: [`content/why-0.2778.md`](../content/why-0.2778.md). Summary, all owner-reported and unverified:

1. **What the bytes show (verified from pinned rasters in earlier sessions):** GEMSDOE32's B2 file has 37,654 dots and is an exact subset of GEMSDOE28's H27-4 base (40,199 dots). It removes 2,545 cells that lie 1.4–2 px from the mirrored catalogue.
2. **Mechanism (hypothesis):** under the official distance-weighted Tversky metric, removing redundant or catalogue-adjacent dots can reduce false-positive mass more than it loses true-positive credit. Whether that happened here needs the hidden labels and a receipt, which are unavailable.
3. **Uniqueness:** the repo's own audit found every GEMSDOE32 dot within 3 px of a dot in GEMSDOE24, 25, 27, 30, 31 and 36 (overlap 1.000 each). So 0.2778 is **not unique** under your rule.
4. **Can we beat 0.2778?** Unknown. The repo's matched-holdout check ranks the near-catalogue family low, and the ledger-inversion projections that rank it high are contradicted by that holdout (Spearman −0.849). Pruning alone cannot go higher; beating it needs new geology that the family does not already cover.

## Estimated score for each focus file

The executive summary shows **"Not estimable"** on purpose. The two available estimators disagree:
- Ledger-inversion projections (0.33–0.36 in `docs/data/nine_site_table.json`) are contradicted by the matched holdout (Spearman −0.849, Pearson −0.886) and must not be used.
- Matched-holdout results in the repo are not sufficiently validated to be called a competition estimate.

So: no estimate is given as a score. The table in the executive summary lists each file, its owner-reported score, and its uniqueness result. Those are the honest numbers.

## Passes

**Pass 1 — measure and verify.**
- Re-ran the registry witness recheck from pinned public bytes. Both SHA-256 values matched the pins (witness `ab0a0a62…`, sample `2176d08e…`).
- Re-measured the witness independently with `scripts/verify_witness_independent.py` (no project audit code): 5,167,373 positive cells inside the footprint; values 0.00046–0.98412; zero exact-zero cells. The result matches the saved card.
- Fetched official sources (table in `evidence/official_source_check_2026-10-29.json`) and the public leaderboard (`evidence/leaderboard_observation_2026-10-29.json`).
- Ran the project's own venv (`requirements.txt`), so the checks used the pinned stack.

**Pass 2 — adversarial review.** I checked my own outputs and found three errors, which I fixed:
- An evidence file first quoted a staff clarification that I had not re-verified this session. It now sits under "not verified in this session".
- An ECOSTRESS description said "70 m products"; the page says "70 m" imagery in its examples. Corrected.
- A sentence in the leaderboard JSON was garbled. Rewritten.

**Pass 3 — reconcile with the request.** See "Requested vs delivered" below.

## Irregularities for review

| ID | Irregularity | Evidence | Status |
|---|---|---|---|
| IR-29-01 | The brief cites 0.4413 as the leaderboard high and 0.3195 as "the highest score right now". Neither is true on the live page: rank 1 is **0.4544**. 0.4413 is not visible at all. | leaderboard_observation_2026-10-29.json | Flagged. Use 0.4544 as the dated public high. |
| IR-29-02 | Rank 26 changed from 0.3195 (2026-10-28) to 0.3328 (2026-10-29). The board moves, so any rank claim must carry a date. | both leaderboard JSON files | Explained, not a contradiction. |
| IR-29-03 | Deadline conflict. Homepage: 2026-12-03 23:59 UTC. Rules A.1: 5:00 p.m. ET on the deadline date. **Now verified from the rules text.** | official_source_check_2026-10-29.json | Use **2026-12-03 22:00 UTC** as the effective cutoff unless the organizer confirms otherwise. |
| IR-29-04 | Outside-bounds convention. Official format: outside cells must be **null or NaN**. Several GEMSDOE "-zeros" files (including the 0.2778 file) use zeros outside. Whether the portal accepted those, and how its score was computed, is unknown. | official page; repo file names | Open. Any file we generate must use NaN outside. |
| IR-29-05 | The "Predicted values must be in range [0, 1]" rejection. Official spec: float32, 0 to 1. The cause for that user file cannot be reproduced without the file itself. Likely causes: NaN/nodata handling, or values above 1. | user report; official page | Open. Need the failing file to diagnose. |
| IR-29-06 | No validated score estimate exists. The ledger projections conflict with the holdout. | content/why-0.2778.md | Flagged. Shown as "Not estimable". |
| IR-29-07 | The highest focus-site file (GEMSDOE32, 0.2778) is not unique under the user's rule. | evidence/nine_site_table.json | Flagged. |
| IR-29-08 | The dense witness makes the literal 70% rule degenerate for any continuous-score registry raster. | evidence/witness_independent_stats_2026-10-29.json | Decision needed (Q1). |
| IR-29-09 | All competition inputs in the repo are owner mirrors, hash-pinned but not organizer downloads. The DrivenData data tab requires login and was not accessed. | registry/data_manifest.json | Open. Needs your data access. |
| IR-29-10 | Rules A.5(1) requires an original work with no undisclosed third-party content. Rule 3.2 requires disclosing any generative-AI use in the narrative. Copying another team's file would be third-party content, so the "do not copy" instruction matches the rules. | official rules PDF | Noted for the submission narrative. |
| IR-29-11 | Public score is not the final score. Rule 3.2/3.6 uses private and re-labelled sets, and one final submission must be chosen without knowing private results. | official rules PDF | Noted. |
| IR-29-12 | The EarthScope magnetotelluric URL returned "Page not found". No official MT source was verified. | official_source_check_2026-10-29.json | H8-MT blocked. |

## Candidate hypotheses (3, untested, ranked)

These are not a replacement for the five preregistered H1–H5 (`knowledge/preregistration-2026-10-28.md`). Grep counts in `src/`, `scripts/`, `knowledge/`, `content/`, `docs/data/` checked for overlap. "focal" in the repo means focal relief, not focal mechanisms, so the earthquake-mechanism idea is new.

| Rank | ID | Layer(s) | Signature targeted | Why it could catch an uncatalogued fault | Repo difference (grep) | Named non-fault mimic | Source status | Cost | Expected DTI gain |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **H7-FM** | USGS ComCat earthquakes with focal mechanisms (nodal planes) | Clustering of nodal-plane strikes along a trend, consistent with the regional stress field | Microseismicity on unmapped faults; mechanisms give orientation the catalogue lacks | "moment tensor" 0 hits; the repo uses earthquake density only (`QEPI-FOCAL`, "density of earthquakes") | Quarry blasts; induced seismicity from fluid operations | **Verified:** USGS FDSN event API documentation (`earthquake.usgs.gov/fdsnws/event/1/`). Regional mechanism coverage **not verified**. | Low | Unknown; sparse in Nevada, so likely low–medium |
| 2 | **H6-ECO** | NASA ECOSTRESS 70 m land-surface temperature (nighttime) | Coherent nighttime thermal anomaly along a structural trend | Hydrothermal permeability may warm the surface at night, even under no mapped scarp | "ECOSTRESS" 0 hits; H3/H5 use other thermal and Landsat sources | Irrigation or vegetation; playa or albedo contrast; sampling gaps | **Verified:** NASA JPL site describes 70 m imagery and a data link. **Earthdata login not verified** and may need a manual account step. | Medium | Unknown; sampling is sparse in time |
| 3 | **H8-MT** | Magnetotelluric resistivity | Conductive zone along a structural boundary | Fluid-bearing fault zones are conductive | "magnetotell" 0 hits | Clay alteration; conductive sediment | **BLOCKED:** no official source verified | High | Not estimable |

**Validation status of all three:** none is tested. The top-ranked idea (H7-FM) cannot be validated until the stop is resolved (Q1, Q2), and then only after the holdout protocol (buffered whole-segment withholding, pooled DTI, leakage canary) has been run on the shared tooling. Under the user's rule, nothing is put in a submission slot before it beats the current holdout best.

## Requested vs delivered

| Requested | Status this session |
|---|---|
| Review the repo; explain GEMSDOE32's 0.2778 | Done (content/why-0.2778.md, verified against the pinned bytes). |
| Executive summary per focus site with a table: file, estimated score, unique? | Already in the site. Updated the leaderboard panel. Estimates remain "Not estimable" for stated reasons. |
| Unique TIFF that is obviously OK to download and submit | **Not delivered.** Blocked by the stop (Q1, Q2). The site says plainly: not OK. |
| Fix "Predicted values must be in range [0, 1]" | Diagnosis needs the rejected file (IR-29-05). The format is re-verified from source. |
| 3–5 new hypotheses, ranked, with sources | Done: 3 listed; obtainability checked; H8-MT blocked. |
| Holdout validation before any slot | **Not run**; blocked by the stop and by the missing shared cache (`data/` holds only the template grid). |
| Official sources with links; flag irregularities | Done (official_source_check_2026-10-29.json; irregularities table). |
| Put the prompt into the README; read it every session | Done in README (verbatim capture, see README). |
| PR and merge to main | Planned (see final step in the session). |
| Three review passes | Done (above). |
| Leaderboard high and "0.3195 is highest" | Corrected: rank 1 is 0.4544 (IR-29-01). |

## Limits of this review

- Fetch tool only: page-text observations with no exact timestamps. Nothing here is an organizer receipt.
- No DrivenData login; the data tab and the submission page were not accessed.
- No holdout was run, so no HOLDOUT-DTI value, CI, or evaluator version exists. No score is claimed for any file.
- The witness "dense" finding rests on the registry's pinned public mirror, not on organizer-provided data.

## Pointers

- Run card: [`evidence/session_2026-10-29_run_card.json`](../evidence/session_2026-10-29_run_card.json)
- Independent witness measurement: [`evidence/witness_independent_stats_2026-10-29.json`](../evidence/witness_independent_stats_2026-10-29.json) · [`scripts/verify_witness_independent.py`](../scripts/verify_witness_independent.py)
- Recheck (pins verified): [`evidence/registry_witness_recheck_2026-10-29.json`](../evidence/registry_witness_recheck_2026-10-29.json)
- Official sources: [`evidence/official_source_check_2026-10-29.json`](../evidence/official_source_check_2026-10-29.json)
- Leaderboard capture: [`evidence/leaderboard_observation_2026-10-29.json`](../evidence/leaderboard_observation_2026-10-29.json)
- Official pages: [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [official rules PDF](https://www.nlr.gov/docs/fy26osti/96647.pdf)
