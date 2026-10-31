# Session review — 2026-10-31 · DO NOT DOWNLOAD, DO NOT SUBMIT (gate unchanged)

Branch `arena/33eb077e-wbggemsdoe3`, based on `main` at `b245a32`.
Companion files: [`docs/data/release_gate.json`](../docs/data/release_gate.json) (gate, unchanged) ·
[`evidence/session_2026-10-31_run_card.json`](../evidence/session_2026-10-31_run_card.json) (negative run card) ·
[`knowledge/executive-summary-2026-10-29.md`](executive-summary-2026-10-29.md) (nine-site table, prior session).

## 1. Bottom line (read this first)

- **No TIFF is cleared for download or submission.** This session generated no candidate, ran no holdout,
  and used no weekly slot. The project-wide gate is still `DO-NOT-SUBMIT`.
- **Why no new TIFF was generated.** Two blockers in the repository's own protocol are not resolved, and
  one of them cannot be resolved by engineering alone:
  1. **Uniqueness rule is unsatisfiable as written.** The 457 sibling submissions cover 100% of the
     5,167,373-cell footprint within 3 px, and the binding comparator (the 13GEMSDOE r13 lattice,
     206,895 dots) leaves only 0.14% of the footprint free. Under the literal per-raster 70% rule, every
     candidate with dots in the footprint fails. Measured in
     [`evidence/uniqueness_coverage_2026-10-28.json`](../evidence/uniqueness_coverage_2026-10-28.json)
     (`footprint_share_within_3px_of_any_submission: 1.0`, `zero_overlap_complement_exists: false`).
  2. **Dense-witness definition.** The registered soft-probability raster is positive on 100% of its
     finite cells under the literal "value > 0" rule. Measured in
     [`evidence/witness_definition_check_2026-10-29.json`](../evidence/witness_definition_check_2026-10-29.json).
     The repo's own code comment calls this surface "not dots", so the gate and the code disagree.
- **Labels and holdout tooling are not in this sandbox.** The DrivenData data page is login-walled and the
  Dropbox links are unreachable from this sandbox (HTTP 000). The local `data/` directory contains only
  `template_grid.tif`. A DTI holdout cannot be run, so **no HOLDOUT-DTI number exists** and **no estimate
  can be written for any file.**
- **The decision the owner must make** is in §6. Engineering cannot pick it: changing either rule changes
  what the user's protocol means.

## 2. Official sources checked this session (fetched 2026-10-31)

| Claim | Source | What it says (verified text) |
|---|---|---|
| Metric | [problem and metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Distance-weighted Tversky index, α=0.2, β=0.8, triangular kernel with R = 300 m (3 px at 100 m). Prediction p(x) ∈ [0,1]. FP_w sums over **all x with p(x) > 0**, weighted by p(x)·[1 − max k]. |
| Format | same page, "Submission format" | Single layer, float32, values between 0 and 1, EPSG 32611, 100 m, same bounds as training data, **data outside the bounds is null or nan.** |
| Leaderboard | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | #1 xiaofanhu **0.4544**; #2 cfld__ **0.3925**; #3 Batik Shirt Brothers **0.3917** (public DW-Tversky). |
| Data access | [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Redirects to login from this sandbox (verified in prior sessions; not re-downloadable here). |
| Rules | [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not re-read line by line this session. Prior-session deadline conflict is still open. |

**Irregularity:** the brief gives "0.4413" as the high and "0.3195" as the current top. The official
leaderboard fetched today shows top **0.4544**. 0.3195 does not appear among the top three. The repo's
2026-10-28 capture also shows rank 26 = 0.3195, so 0.3195 is a rank-26 figure, not the top.

## 3. Focus sites — best file and estimate

All scores below are **OWNER-REPORTED / UNVERIFIED** (no organizer receipt). Estimates are **not estimable**
because no holdout can be run here. Uniqueness is from the prior nine-site audit (max 3-px overlap 97.6%
within the nine-site set) in [`knowledge/executive-summary-2026-10-29.md`](executive-summary-2026-10-29.md).

| Site | Best reported file (research reference only) | Owner-reported score | Estimate | Unique? | Download / submit |
|---|---|---:|---|---|---|
| GEMSDOE24 | gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif | 0.2477 | Not estimable | No | **NO** |
| GEMSDOE25 | gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif | 0.2600 | Not estimable | No | **NO** |
| GEMSDOE27 | gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif | 0.2449 | Not estimable | No | **NO** |
| GEMSDOE28 | gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif | 0.2710 | Not estimable | No | **NO** |
| GEMSDOE30 | gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif | 0.2600 | Not estimable | No | **NO** |
| GEMSDOE31 | gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif | 0.2708 | Not estimable | No | **NO** |
| **GEMSDOE32** (highest focus-site report) | gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif | **0.2778** | Not estimable | No | **NO** |
| GEMSDOE33 | GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif | 0.2632 | Not estimable | No | **NO** |
| GEMSDOE36 | gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif | 0.2750 | Not estimable | No | **NO** |

**Pinned download links** for these files are in [`registry/focus_sites.json`](../registry/focus_sites.json)
and the [executive summary](../docs/executive-summary.html). They are for reproducibility, not upload.

Against the official leaderboard, the highest focus-site report (0.2778) sits below #3 (0.3917) and below
the 0.3195 figure in the brief. Even if the 0.2778 report were accurate, it would not place top-3 on the
2026-10-31 public board.

## 4. Why GEMSDOE32 reports 0.2778 — what is verified and what is not

Source: [`content/why-0.2778.md`](../content/why-0.2778.md) and
[`evidence/pair_identification.json`](../evidence/pair_identification.json) (prior session, re-read this session).

**Verified byte-level facts (repo measurement, from pinned owner mirrors):**
- GEMSDOE32 B2 has **37,654** positive cells.
- It is an **exact subset** of GEMSDOE28 H27-4 (40,199 positive cells). **2,545** cells were removed and none added.
- All removed cells lie 1.414–2 px from the mirrored fault catalogue (`removed_within_3px_of_catalogue_frac: 1.0`).

**Arithmetic identification (labelled as such in the repo, not a score):** treating dots as unit
probabilities, the two owner-reported scores (0.2708 and 0.2778) imply a hidden-truth coverage
M ≈ 15,200 and T ≈ 5,470. This relies on a simplified model (unit dots, not the distance-weighted sum),
so the coverage figure should be treated as an order-of-magnitude artifact, not a measurement.

**Mechanism (hypothesis, unproven):** pruning 2,545 near-catalogue dots lowers the false-positive mass
at a cost in true-positive credit. Which effect dominates requires the hidden labels and the exact evaluated
bytes, neither of which is available here. The repo's historical H6-1 proximity-pruning holdout was
**negative** (paired Δ +0.000054, CI includes zero for the random-pruning comparison); that experiment's
own caveat says it cannot test the near-catalogue regime that motivates B2.

**Metric reasoning (verified from the official text):** FP_w sums p(x)·[1 − max k] over **every** cell with
p(x) > 0. Dense low-probability surfaces therefore carry false-positive cost on every nonzero cell. That is
why sparse, well-placed predictions are the scoring-relevant design, and why the witness-definition question
in §1 matters for the gate.

**Can a new TIFF beat 0.2778?** Unknown. It cannot be tested without labels or a valid holdout, and the
gate currently blocks any candidate. The public top is 0.4544 (verified today), so the competitive target
is well above 0.2778 regardless.

## 5. Irregularities flagged for review

| ID | Irregularity | Status this session |
|---|---|---|
| IR-31-01 | `docs/downloads/` contained **three TIFFs absent from the do-not-submit inventory**: `WB-GEMS-DOE-3-STEP-OVER-DAMAGE-ZONE-30000D-20261029T202958Z-37C53EB9-zeros.tif`, `wbg-gems-offnet-conduit-19520d-20261029T203307Z-zeros.tif`, and the symlink `wbg-gems-offnet-conduit-latest.tif`. `scripts/check_site.py` failed (exit 1) on this. | **Fixed.** Added to `LEGACY-DO-NOT-SUBMIT.txt` as uncleared. Files were not deleted. `check_site.py` now exits 0. |
| IR-31-02 | The committed site (before rebuild) showed a row "WB-GEMS-DOE-3 (generated) … NOT CLEARED" with "1 generated" and "Unique vs 23 local rasters … max overlap 0.5899". The README says "No TIFF was generated on 2026-10-29", yet `WB-GEMS-DOE-3-STEP-OVER-…-20261029T202958Z` exists in the repo. The 0.5899 figure is against 23 local rasters, not the full 457-comparator registry. | **Flagged; site rebuilt from `scripts/build_site.py`**, which now reports 0 candidates. The TIFF remains in the archive, uncleared. Provenance of that file is unexplained and needs owner review. |
| IR-31-03 | Two tests fail on the rebuilt site: `test_published_index_states_not_ok_to_submit` (expects the wording "Not OK to download or submit"; the page says "DO NOT SUBMIT — no file is cleared") and `test_latest_upstream_identity_feed_is_published_and_never_implies_approval` (expects a "Focus-site source freshness" heading the builder no longer emits). Both are wording/heading drift, not a negative-decision regression. | **Open.** Not changed: tests vs builder wording is an owner choice. 257 pass, 2 fail. |
| IR-31-04 | Leaderboard figures in the brief (0.4413 high, 0.3195 top) do not match the official page (0.4544 top). | **Open.** Recorded in §2. |
| IR-31-05 | Literal uniqueness rule is unsatisfiable against the full registry (§1). | **Open; owner decision (§6).** |
| IR-31-06 | Dense-witness definition contradicts the repo's own code comment (§1). | **Open; owner decision (§6).** |
| IR-31-07 | Deadline conflict: homepage 2026-12-03 23:59 UTC vs rules Appendix A.1 "5:00 p.m. ET" (prior session). | **Open; not re-verified this session.** |
| IR-31-08 | Outside-footprint encoding: the official format text says null or NaN; older run cards used zero outside. | **Open.** Relevant to any future candidate. |

## 6. Decision needed from the owner (blocks any TIFF)

The repository's gate says: *"Do not build a candidate, run a holdout, or select a slot unless a documented
evidence-based correction resolves the stop."* This session tested the options and did not make the call.
The options are the ones already recorded in
[`knowledge/session-review-2026-10-29-witness.md`](session-review-2026-10-29-witness.md):

- **A. Keep the literal rules.** Result: no candidate can ever be cleared. Honest, but no submission is possible.
- **B. Redefine dots for continuous surfaces (top-N or ≥0.5).** Fixes the witness only. The 13GEMSDOE lattice
  (0.99 overlap) still blocks any broad candidate under the literal per-raster rule.
- **C. Score uniqueness against non-lattice, non-dense comparators, with the exclusion stated and the lattice
  class reported separately.** This is the only option that can pass in practice. It changes the user's
  70% rule, so the owner must approve it in writing.

**Engineering recommendation (not a decision):** choose C, record the exclusion and its reason in the protocol,
then run the shared holdout with HOLDOUT-DTI labels and the outside-encoding fix (IR-31-08) before any upload.
Until then, **no TIFF should be downloaded or submitted.**

## 7. Passes and checks

- **Pass 1 (implement and verify):** fetched the official metric/format text, leaderboard, and data page; ran
  `pytest` and `check_site.py`; read the saved uniqueness, witness, and pair-identification artifacts.
- **Pass 2 (review for bugs):** found IR-31-01 (inventory gap, check failing) and fixed it; found IR-31-02 (stale
  generated-candidate claim on the committed site) and rebuilt; found the stash-pop conflict during verification
  (its content was identical, so it was resolved with no loss, and `git stash list` is now empty).
- **Pass 3 (re-check against request):** all nine focus sites are covered with a file, owner-reported score,
  "Not estimable" estimate, and uniqueness verdict; no number is written as a score; the gate and both blockers are
  restated; the decision is isolated for the owner.

**Test status:** `pytest` 257 passed, 4 skipped, 2 failed (IR-31-03). `scripts/check_site.py`: PASS.

## 8. Not done (honest limits)

- No holdout, no candidate raster, no slot selection. No HOLDOUT-DTI or ORGANIZER-CONFIRMED number exists.
- No DrivenData receipt, no account quota, no submission-page check (login-walled; not reachable).
- Did not re-verify the staff clarification on known-fault masking cited in `content/why-0.2778.md`.
- Did not re-read the full rules PDF this session.
- The five preregistered hypotheses (H1–H5) in the README remain **untested**.
