# Session review — 2026-10-29 (branch arena/bec1b1b6-wbggemsdoe3)

**Decision: DO NOT SUBMIT (unchanged).** This session generated no candidate TIFF, ran no holdout,
selected no slot and uploaded nothing. Repository-measured facts are labelled as measurements,
organizer text is labelled as official-source text, and nothing here is an organizer score.

## 1. What was done
- Created `scripts/verify_focus_files.py` and ran it end to end. It downloads pinned codeload
  tarballs, checks SHA-256 against `evidence/focus_audit.json`, and writes
  `evidence/focus_files_verification_2026-10-29.json` (no hidden labels; no network beyond the pinned
  codeload archives).
- Re-checked official sources on 2026-10-29 with exact quotes:
  `evidence/official_source_check_2026-10-29_focus.json`.
- Updated `scripts/build_site.py` (single active generator) to render the nine-site table, the
  "verified 2026-10-29" block, the direct answer, and the portal-error diagnosis from those JSON files.
  It fails closed if the verification or source check is missing or inconsistent.
- Added `tests/test_focus_verification.py` (13 tests). Full suite: 249 passed, 4 skipped.

## 2. Line-by-line claim check
| # | Claim | Status | Source |
|---|---|---|---|
| 1 | Competition end: Dec. 3, 2026, 11:59 p.m. UTC | Verified | competition homepage (fetch 2026-10-29) |
| 2 | Rules Appendix A.1: 5:00 p.m. ET on the deadline date | Verified; **conflicts with #1**. In December ET is UTC−5, so 5:00 p.m. ET = 22:00 UTC on Dec. 3, 2026; use that as the conservative cutoff | NLR rules PDF, Sept 2026 |
| 3 | Up to three submissions per week; one final submission | Verified | NLR rules §3.2, §3.4 |
| 4 | Out-of-bounds data is null or NaN; values in [0,1]; float32; EPSG:32611; 100 m | Verified | problem description page 967 |
| 5 | α=0.2, β=0.8, R=300 m | Verified | problem description page 967 |
| 6 | Public leaderboard rank 1 = 0.4544 | Verified (2026-10-29 fetch, chunks 0–1) | leaderboard page |
| 7 | User's 0.4413 is the top score | **Not supported** (0.4544 is rank 1) | leaderboard page |
| 8 | 0.3195 is the top score | **Not supported**. It was rank 26 in the 2026-10-28 capture; today rank 26 is newway at 0.3328 and 0.3195 does not appear in ranks 1–46 | `evidence/leaderboard_observation_2026-10-28.json`; live page 2026-10-29 |
| 9 | Pixels on known catalogue faults are masked from scoring | Verified (staff forum reply, Sep 16) | community.drivendata.org #11516 |
| 10 | GEMSDOE32 = GEMSDOE28 H27-4 base minus cells within 2 px of catalogue | Verified, 0 mismatches | repository measurement (pinned SHA-256) |
| 11 | GEMSDOE32's score 0.2778 is due to this exclusion | **Unproven** (owner-reported; H6-1 proxy gain was +0.000054) | `content/why-0.2778.md` |
| 12 | GEMSDOE25 and GEMSDOE30 have identical dot sets | Verified (phi 1.0; overlap 1.0) | repository measurement |
| 13 | Every focus file fails the 70%/3-px rule against another focus file | Verified (max overlap 0.980–1.000) | repository measurement |
| 14 | Sample submission predicts total absence | **Contradicted by the owner-mirrored file**: 60,988 positive cells identical to the training labels | repository measurement + official text |
| 15 | `data/template_grid.tif` is the official footprint | **Not supported**: fully finite zeros; the official-sample footprint is 5,167,373 cells | repository measurement |
| 16 | Portal error "Predicted values must be in range [0, 1]" | **Not reproduced** for any of the nine files (finite values all in [0,1]) | repository measurement |
| 17 | Ledger-inversion values (0.33–0.36) | **Projection only**, circular (fit on the same owner reports), not a score | `docs/data/nine_site_table.json` |

## 3. Irregularities for review
- IR-01 Deadline conflict (homepage 11:59 p.m. UTC vs Appendix A.1 5:00 p.m. ET = 22:00 UTC). Use 22:00 UTC on Dec. 3, 2026.
- IR-02 Leaderboard values in the brief (0.4413 "top"; 0.3195 "top") do not match the live page: rank 1 is 0.4544, rank 26 is 0.3328, and 0.3195 is not in ranks 1–46 today.
- IR-03 Owner-mirrored `sample_submission.tif` has 60,988 positive cells identical to the training labels. This conflicts with "predicts total fault absence". Do not use it as a null baseline.
- IR-04 Two output encodings (NaN outside the footprint in 5 files; zero-filled everywhere in 4). The official text says null/NaN outside bounds, so the zero-filled encoding is a risk to be checked, not a finding of failure.
- IR-05 GEMSDOE25 and GEMSDOE30 are the same dot set under two owner names, both reported at 0.2600.
- IR-06 The +0.0070 owner gain from the exclusion is about 130× the H6-1 proxy gain (+0.000054). The proxy scope does not cover the regime, so the discrepancy is unexplained.
- IR-07 `data/template_grid.tif` (sha 6a1dde6f…) is not the official sample grid (sha 2176d08e…). Its finite cell count (12,279,160) does not match the sample's footprint (5,167,373).

## 3a. Relation to the parallel 2026-10-29 session on `main`
Main carries a separate 2026-10-29 review (witness definition, executive summary, source-identity feed). It
reaches the same DO NOT SUBMIT decision and the same leaderboard and deadline corrections. This branch adds the
focus-site byte verification, the GEMSDOE32 mechanism, the sample-file irregularity, and the portal-error
diagnosis. Its canonical source check is kept as `evidence/official_source_check_2026-10-29_focus.json`, so the
main-branch file `evidence/official_source_check_2026-10-29.json` is left unchanged. Main's ledger projections
are not used here; this review and the site show "Not estimable".

## 4. Candidate hypotheses (ranked; none validated)
Ranked by expected value of information per unit cost. Expected DTI gain is **not estimable**: no
holdout labels, no validated feature stack, and the uniqueness stop is active.
1. **H1-RMIX** (preregistered): local K-Th-U closure residual at concealed structures. Layers: GeoDAWN K, Th, U, total count, potential-field edges. Non-fault mimic: lithologic/weathering contact. Cost low–medium. Data: owner mirror, not re-downloaded. Differs from the repository's raw ratios (HCE, THCS, FCHD).
2. **H3-ANISO-THERM**: anisotropic, sampling-corrected shallow-thermal evidence. Layers: DOE GDR 1391 (page verified), wells, springs. Mimic: sampling bias around hot springs. Cost medium.
3. **H2-XCATCH**: cross-catchment channel-profile discontinuity. Layers: 3DEP DEM, flow network. Mimic: resistant lithologic contact. Cost medium–high; AOI coverage unverified.
4. **H4-XOVER**: acquisition-crossing repeatability of airborne anomalies. Layers: GeoDAWN flight lines and tie lines. Mimic: flight-line leveling noise. Cost high.
5. **H5-LANDSAT**: surface-alteration texture conditioned on independent structure. Layers: Landsat C2 SR, season and cloud masks. Mimic: soil, vegetation, mine disturbance. Cost high.

The top candidate (H1) cannot be validated on the holdout yet. The shared feature cache and holdout
tooling are not restored in this checkout, and the literal uniqueness stop applies.

## 5. Three review passes
1. **Code correctness.** Re-ran the verifier end to end. Unit tests cover directed overlap and phi on synthetic arrays, and the phi edge case for constant arrays. Fixed one earlier error in my draft (an unsupported A.14/A.15 reference) by checking the rules text.
2. **Claims against sources.** Compared every number in the README, the site, and this review with the evidence JSON and the quoted official text. Downgraded the GEMSDOE32 explanation from "plausible" to "mechanism proposed; unproven" after reading the H6-1 proxy. Corrected the template-mismatch finding: the audit's "template" is the official sample, not the repo template.
3. **Adversarial and safety.** Checked that no page or file gives a candidate download as a submission, that no projection is labelled as a score, and that the fail-closed guards in `build_site.py` trip on tampered evidence. `check_site.py` passes.

## 6. Decision needed from you (not blocking the stop)
- **Uniqueness definition (main's Q1/Q2).** Under the literal rule, any dense registry raster that covers the footprint within 3 px blocks every candidate. Choose one before any candidate exists (Q1 = what counts as a dot; Q2 = whether the 13GEMSDOE lattice counts):
  (a) keep the literal rule (no candidate can pass; the project stays at DO NOT SUBMIT);
  (b) pre-register an amendment that excludes dense/lattice rasters, applied to all registry files and written down before generation;
  (c) compare only against sparse top-K dot sets, with K fixed in advance.
  My recommendation is (b) or (c), decided and recorded before any candidate is generated. This is your call.
- **Which 0.4413?** Do you have a source for 0.4413? The live page shows 0.4544 at rank 1.
- **Portal error.** Which exact file was uploaded (name and SHA-256)? We can classify it with the checks in this session.

## 7. Remaining work and limitations
- Competition data (training features, labels, sample submission) is login-gated on DrivenData; it cannot be downloaded automatically. The repository's sample is an owner mirror, not an organizer file.
- No holdout, no candidate, no organizer receipt, no portal quota check (login required).
- Official pages not re-fetched today: page 968, the GeoDAWN page, GBCGE INGENIOUS, epsg.io, and the Tversky reference. See the source check's "not checked" list.
- Dropbox files named in the brief (example submission, existing faults) were not reachable.
- The ledger projections (0.33–0.36) are circular and must not be read as scores.
- Merge to main and the final review are recorded in the PR for this branch.
