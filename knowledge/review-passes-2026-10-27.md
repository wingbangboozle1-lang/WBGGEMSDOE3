# Three review passes — session 2026-10-27 (SGCE)

Every number below is either HOLDOUT-DTI (evaluator, positives, CI), a measured file property, or
an explicitly labelled PROJECTION / owner claim. No organizer receipt exists. Official links are
provided for manual verification.

## Pass 1 — implement and verify

1. **Official sources re-read live** (not from memory):
   - [Problem, DTI metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — α=0.2, β=0.8, R=300 m, `max`-kernel TP, FP = Σp(1−max k), one float32 band in [0,1].
   - [Known-fault masking clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) — organiser staff answer.
   - [Pooled scoring clarification](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2).
   - [Expert labels / Phase-2 expansion](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) — organisers decline to disclose labelling sources.
   - [Official rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — three submissions/week, one selected final GeoTIFF, generative-AI disclosure.
   - [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — magnetics = subsurface structure, radiometrics = surface materials, variable terrain clearance, CC0 1.0.
   - [GDR 1391](https://gdr.openei.org/submissions/1391) — INGENIOUS compilation, CC BY 4.0.
   - [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — leader 0.4544 observed 2026-10-27 (timestamped public observation, not our score).
2. **Data restored and hash-verified**: 26 core/external/scored mirrors (`scripts/fetch_mirrors.sh`), 118 live-ledger rasters (`scripts/fetch_ledger_rasters.py`), nine pinned focus-site repositories, the 17GEMSDOE dense witness (SHA `ab0a0a62…`), and the pinned shared 57GEMSDOE template with its 19 cached bands. All large files live in ignored `data/` and `.cache/`.
3. **Preregistered** five new hypotheses and one lane before modelling: `knowledge/preregistration-2026-10-27.md`.
4. **Leakage canary** on the same holdout: max single-field AUC 0.748 (`GEOM_d_vis_neg`), composite density 0.787; both below 0.90.
5. **Three preregistered arms** on the unchanged vendored evaluator: E1 0.1489 (CI 0.1369–0.1610), E2 0.1464, E3 0.1489; champion proxy 0.0992 (CI 0.0860–0.1127); E1 paired Δ +0.0497 (CI 0.0353–0.0645).
6. **Uniqueness repair** (documented, post-hoc within one repair family), final k=6 construction: 102,208 dots; HOLDOUT-DTI 0.1675 (CI 0.1524–0.1820); paired Δ +0.0683 (CI 0.0517–0.0855). Official content-aware audit: |ρ|max 0.345, max non-lattice 3-px overlap 0.690, no exact duplicate, lattice excess PASS; literal reading FAIL (dense witness) — flagged.
7. **TIFF written and re-read**: `wbggems3-sgce-20261027-f52d35d8-zeros.tif`, SHA-256 `0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09`; validator PASS for zeros and NaN variants plus ZIP.
8. **Site generated deterministically**, one-click download at the top, nine-site table, step-by-step submission guide, gates, sources; `scripts/check_site.py` PASS; 81 pytest tests PASS.

## Pass 2 — bug / assumption / edge-case review (fixes applied)

| Finding | Fix |
|---|---|
| `sgce.geometry` scanned the full label array once per component (78 s/cell). | Replaced with `ndi.find_objects` bounding boxes → 1.8 s/cell. |
| Fixed-μ allocation produced only ~6k dots; the DTI fixed point was not reached. | Added Dinkelbach μ←model-DTI iteration (3 passes), matching the shared `alloc.py` semantics. |
| First registry audit used a per-comparator EDT + dilation (~4 min/audit). | Replaced with `binary_dilation(DISC)` for the literal 3-px rule and a Gaussian-smoothed surface for Spearman (~1 min/audit). No shared evaluator was forked. |
| `"continuous"` classification wrongly exempted sparse soft-probability submissions from the literal overlap rule (two rasters at excess 0.077). | Reclassified: >15 % footprint support = `dense`; sparse soft rasters = `soft-sparse` and judged by the 0.70 overlap rule. Registry rebuilt and audits re-run. |
| First repair (union of 10 dilations) covered 98 % of the footprint and collapsed HOLDOUT-DTI to 0.0026. | Retained as a measured **negative** result; replaced by a graded contrarian-coverage prior. |
| Run card initially quoted the un-repaired E1 holdout for a repaired file. | Added `scripts/session2_repair_holdout.py` to re-measure every repair; the final card is bound to the exact released dot mask (`released_dots_match_saved_tiff: True`). |
| The projection model predicted 0.0669 while holdout said 0.1675. | Kept both, labelled PROJECTION, and documented the ledger-collinearity reason; a dot-cap scan showed capping does not rescue the projection. |
| Old site generator was hard-wired to a negative fail-closed card. | Replaced with `scripts/session2_site.py` (deterministic from evidence) + `check_site.py` hash/validator/uniqueness checks; kept `build_site.build()` for CI and tests. |
| Stale "DO NOT SUBMIT" banners on archived `site/` and LST1 pages. | Reworded to point to the current decision; LST1 lane labelled as a separate negative experiment. |
| Note exceeded the 140-character portal limit (151). | Shortened to 134 characters; asserted in code and tested. |

## Pass 3 — re-check against the original request

- **Unique TIF**: yes — new dot mask (`f52d35d8…`), new file SHA, new method; not a copy, rename, nodata swap or perturbation. Historical nine-site rasters remain research-only with measured duplicate percentages in the table.
- **Obvious download/submit decision**: the green banner and download button are the first content on both the overview and the executive-summary subpage; the directory index also offers the file. The decision is "YES, after the portal slot check".
- **Estimated score table**: nine sites with pinned file link, owner claim, calibrated PROJECTION (clearly not a score), uniqueness and a clear action; plus the new candidate row with its HOLDOUT-DTI and projection.
- **Unique name + note ≤140 chars**: `wbggems3-sgce-20261027-f52d35d8` and a 132-character note, printed on the site.
- **Range error**: primary file is all-finite, [0,1], no NaN/sentinel/nodata; a NaN-outside variant is supplied for the official "null/NaN outside bounds" wording. Both validated by re-reading saved bytes.
- **No human inspection**: canary, holdout, uniqueness, format and hash checks are code; the only manual action is the portal login/quota.
- **Executive-summary subpage**: `docs/executive-summary.html` contains the exact five-step portal procedure.
- **Hypotheses before implementation**: five ranked ideas with layers, signature, off-catalogue rationale, mimic, cost and official sources; only H1 run.
- **Top candidate validated before a slot**: yes, on the spatially blocked whole-segment holdout; zero slots used.
- **Run card**: `evidence/session2_run_card.json` with hypothesis, mechanism, named mimic, HOLDOUT-DTI + CI, correlation/overlap, SHA-256, validator output, name, note, verdict.
- **Three passes, PR and merge**: this document, the test suite, and the PR/merge complete the loop.

## Irregularities flagged for review

1. **Literal vs content-aware registry rule.** The dense 17GEMSDOE witness is positive on all 5,167,373 footprint cells, so literal positive-support overlap is 100 % for any nonempty candidate. The preregistered interpretation is disclosed everywhere; user ratification is still required.
2. **Holdout vs projection disagreement.** The projection is unreliable for a deliberately unique construction because all high-scoring ledger rasters overlap the H19-5 network. Do not read 0.0669 as a score or 0.1675 as a leaderboard forecast.
3. **Post-hoc k selection and budget overrun.** k=2…6 was scanned after the first draft failed the registry gate; wall time exceeded the 2 h guideline. Disclosed in the run card, not hidden.
4. **Mirror provenance.** Hash-pinned public GitHub mirrors, not an authenticated organizer download. `tc` band semantics remain unauthenticated.
5. **Outside-bounds convention.** Official text says null/NaN outside bounds; the shared writer's primary emits finite zeros. Both encodings are supplied; portal acceptance is unverified.
6. **Leaderboard staleness.** 0.4544 was observed on 2026-10-27; the site marks the snapshot stale after 12 h. It is not our score.
7. **Weekly quota and selector.** Neither the account quota nor the separate selector step is accessible here; `selector_approval: false`, `slots_spent: 0`.
