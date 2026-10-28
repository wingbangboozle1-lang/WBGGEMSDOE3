# Session review — 2026-10-28 · uniqueness audit and HOLD decision

Branch `arena/0d17f7d5-wbggemsdoe3`, base `main` at `0549e93`.

## Lane method paragraph

This session did not build a new design. It re-measured the single candidate and two alternatives
against the full registry of real sibling submissions, using the shared 3-px kernel
(`gemsw.exact.kernel_credit_field`, `RADIUS_PX = 3.0`) and the repo's existing audit tooling
(`scripts/check_uniqueness.py`, extended to take a candidate path and to classify
`submission` vs `input_feature` rows). Every number was measured from bytes pinned by sha256.
The 3-px test is the directed overlap: the share of a candidate's dots within 3 px of any dot of a comparator.

## Decision

**HOLD. No file is cleared to submit.** The 2026-10-28 SUBMIT for
`docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif` is withdrawn.

Reason: under the user's literal rule (≤ 70% of dots within 3 px of any registry raster), the
candidate reaches **0.9944** against `13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`
(206,895 dots, owner-reported score 0.0904). Also above 0.70: GEMSDOE23 h30 (0.8165) and GEMSDOE46 r11f (0.7177).

## Measurements (all from `evidence/`)

| Artifact | Comparators | Max directed 3-px overlap | Binding comparator | Max abs Spearman | Literal unique |
|---|---|---|---|---|---|
| invdesign candidate (`uniqueness_gate_full_2026-10-28.json`) | 457 submissions | **0.9944** | 13GEMSDOE r13 lattice | 0.0507 | no |
| KHD (`uniqueness_khd_full_2026-10-28.json`) | 457 | **0.9991** | 13GEMSDOE r13 lattice | 0.2019 | no |
| FCHD-NCM (`uniqueness_fchd_full_2026-10-28.json`) | 458 | **0.9996** | 13GEMSDOE r13 lattice | 0.6232 | no |
| TDE30k (`uniqueness_tde30k_full_2026-10-28.json`) | 457 | **0.9895** | 13GEMSDOE r13 lattice | 0.0400 | no |

Earlier 58-raster pass (`evidence/uniqueness_gate.json`, max 0.6874): **superseded**. It was a subset of the registry.

Structural measurements (`scripts/uniqueness_coverage.py` → `evidence/uniqueness_coverage_2026-10-28.json`):
- Union of all 457 submissions' dots (3,964,929 cells): the 3-px footprint covers **100%** of the 5,167,373-cell footprint. A zero-overlap-with-everything design does not exist.
- The 13GEMSDOE lattice leaves **7,103 footprint cells (0.14%)** that are ≥ 3 px from it. Under the literal rule, ≥ 30% of any design's dots must sit there.
- Input and witness rasters were excluded from the sibling count: `acquisition_block_id_100m` (1.0), `tiger_road_distance_m` (0.9998), `blm_closed_claim_distance_m`, and the dense witness `17GEMSDOE_E-proba-multiscale` (100% footprint, sha `ab0a0a62…`).

## Corrections made in this session

1. **Decision.** SUBMIT → HOLD in `docs/data/release_gate.json`, `docs/data/decision.json`, the meta tags of
   index / executive-summary / how-to-submit / evidence / method, and the README header. `evidence/run_card_v3.json`
   verdict is marked SUPERSEDED (original kept in `superseded_verdict_2026-10-28`).
2. **Gate source.** The gate now binds `evidence/uniqueness_gate_full_2026-10-28.json` (457 comparators), not the 58-raster card.
3. **Checker.** `scripts/check_site.py` reads the decision from the gate and accepts `HOLD` only when the uniqueness failure is recorded. It rejects SUBMIT wording on HOLD pages. It passes in HOLD mode.
4. **Site KPIs showed 0.000.** `scripts/build_site_v3.py` read a git-ignored `data/work/inversion98b.json`. Fixed to read the tracked `evidence/ledger_inversion.json`: in-sample ρ **0.989**, site-grouped CV ρ **0.946**, CV MAE **0.037**, all n = 118 probes.
   **The builder is now disabled** (it exits at start) because its template still declares SUBMIT and would revert this HOLD.
5. **Reverse-overlap claim.** The site said "≤ 0.174". Measured focus → candidate max is **0.2044** (GEMSDOE36). Corrected to 0.204.
6. **Release note.** "14k dots; DTI est 0.31 [0.24,0.40]" was wrong (20,000 dots; ESTIMATE 0.470). Removed from the gate; the gate's `note` is null.
7. **"ORGANIZER-CONFIRMED" zeros claim** (how-to-submit). Withdrawn. Both encodings are unconfirmed. NaN-named owner files also have owner-reported scores: 24 0.2477, 25 0.2600, 28 0.2710, 31 0.2708.
8. **0.2778 chain wording.** The 2,545 removed dots (GEMSDOE31 → GEMSDOE32) lie at √2 px (1,201) and 2.0 px (1,344), not "1.01–2.01 px". The 3,891 dots removed from GEMSDOE25 → GEMSDOE31 are at 1.0 px (adjacent), not on the catalogue. "Zero credit" and "pure false positive" are premises, not verified (`evidence/chain_0_2778_verify_2026-10-28.json`).
9. **Headline M sensitivity.** The 0.47 estimate assumes M = 15,200. Other repo lanes use M = 27,110 (`evidence/ledger_inversion.json`) and M = 9,150 (KHD). With T fixed, M = 27,110 gives DTI ≈ 0.30. This is a sensitivity bound, not a new estimate.
10. **Contradictory fit counts.** The site text said "98 probes, ρ 0.823". The tracked fit is n = 118 with CV ρ 0.946. The 98-probe numbers cannot be reproduced from tracked files. They are not used now.

## Irregularities (flagged, not resolved)

- The lanes' lattice exclusion conflicts with the user's rule ("any registry raster"). The FCHD and ADJDIS run cards claim "gate 3 pass" under that exclusion (`sparse_nonlattice_masks_compared`).
- The earlier "[0, 1]" portal rejection has no known cause. The rejected bytes and receipt are not available.
- The candidate writes zeros outside the footprint (no NaN). The official format says "null or nan outside bounds". Every NaN-bearing owner file declares `nodata=nan`. Encoding decision still open; changing it changes the sha256 and requires regenerating the gate, run card, README header, and pages.
- The official `sample_submission.tif` (sha `2176d08e…`) is pixel-identical to `labels.tif`, so it is not the all-zero "total absence" sample the how-to-submit page describes.
- `pindrop-v4-discovery` and `pindrop-v4-nodes` (155,021 dots each; sha `37f9d5b8…`, `f347b70d…`) are in the registry index but their bytes are not in the cache. They were measured through `.cache/registry/` (fetched 461 rasters). Their upstream repo/ref is still unlocated (`registry/upstream_live_ledger_rasters.json`).
- Verifier vs run-card Spearman: 0.03 (::6 subsample) vs 0.0469. The subsampling choice is the likely cause; not confirmed.
- `docs/method.html` line "correlating the 98 sibling scores…" and "Design-predictor calibration R² (n = 41)" use counts I could not reproduce; the R² is from `evidence/design_calibration.json` (n = 41).
- `knowledge/preregistration-2026-10-28-khd.md` writes "1.01–2.01 px". Left unchanged because it is a frozen preregistration. The measured values are in this review.
- Owner-reported scores (24 0.2477, 25 0.2600, 28 0.2710, 31 0.2708, 32 0.2778, 33 0.2632, 36 0.2750, 30 0.2600, 27 0.2449) are research only. None is an organizer receipt.
- Leaderboard: dated observation #1 = **0.4544** (`registry/leaderboard.json`). The brief's 0.4413 and 0.3195 are older references.
- The catalogue hide-and-recover holdout is anti-correlated with owner-reported scores (rho ≈ −0.85). Not used to promote or reject anything.

## Remaining work (ordered)

1. **Choose the uniqueness reading** (the user's decision, see README header):
   (a) lane convention: exclude lattice-class rasters from the 3-px test and disclose the lattice excess. The candidates then pass the content-aware test; or
   (b) literal: build a registry-aware constrained allocator (per-raster cap count_r ≤ 0.60·N, 7,103-cell lattice-free pool) using `scripts/design_inv.py`. Blocked: it needs `data/external/*_u8.tif` (GEMSDOE24 mirror ref `07345ea0…`), `data/work/rho_blocks.npy` (from `scripts/invert_ledger.py`, which needs `data/work/probes_f4.npz`), and `data/work/champion_ref.tif`. None are present in the checkout. Credit cost of the constraint is unknown.
2. Decide the outside-footprint encoding (zeros vs NaN). Do not change it without a decision.
3. Locate the pindrop-v4 upstream raster and its ref.
4. Rewrite the `build_site_v3.py` template for HOLD (or retire it), then re-enable it.
5. Resolve the 98 vs 118 probe-count discrepancy by re-running the inversion from tracked inputs.

## Limitations

- No new design lane was built or run in this session. Zero design experiments were spent; four audits were run.
- No organizer receipt, portal result, or holdout result exists in this sandbox for any file. Every number is labelled ESTIMATE, HOLDOUT-DTI, or owner-reported. None is an organizer-confirmed score.
- The DrivenData portal and data pages are login-walled from this sandbox.

## Additional irregularity found while re-reading the README

- The README's "Start every session here" section links `evidence/review-2026-10-28.json`, which is not in the repository (dangling link, pre-existing). It was not created here. The matching `knowledge/review-2026-10-28.md` exists.
