# Three-Pass Verification Record — Lane `THCS-OOF` (2026-10-27 UTC)

**Branch:** `arena/f226cee3-wbggemsdoe3`  
**Primary Artifact:** `submission/wbggems3-thcs-oof-celf-46000d-20261027T200639Z-21256a7e-zeros.tif`  
**SHA-256:** `025cbc8f67902895154ef50b6088a3047e4f99b88db534955bf66e56e57b5b92`

---

## Pass 1 — Implementation & Empirical Verification
1. **Verified Competition & External Data Stack:** Restored and SHA-256 verified all 26 official/public datasets in `data/raw/` and `data/raw/external/`, all 118 live-scored ledger GeoTIFFs in `data/ledger/`, and 12 peer GeoTIFFs in `data/peer_extra/` (`17GEMSDOE`, `KANLERGEMSDOE2/3`, `WBGGEMSDOE1/2`, `GEMSDOE27/28/33/36` Oct 26). Confirmed `EUGGEMSDOE1..3` and `GINNYGEMSDOE1..3` publish 0 candidate GeoTIFFs.
2. **Resolved `IR-20` (Band 6 `tc` Physical Identity):** Proved across `5,164,300` valid overlap cells that `training_features.tif` Band 6 (`tc`) correlates at `Spearman ρ = 0.999953` with USGS GeoDAWN airborne gamma-ray Total Radiometric Count (contradicting the embedded GeoTIFF tag *"Tilt angle or total curvature"*).
3. **Fixed Shared Tools Upstream (Protocol Rule 2):**
   - Fixed `IR-21` in `src/gemsdoe/validation.py` so `score_from_profile` scales proxy capture by `n_truth / n_proxy` and enforces `0 <= TP_w <= |G|`;
   - Expanded `src/hce/uniqueness.py` to scan all peer/comparator/ledger directories deduplicated by SHA-256 and check two-way raw + smoothed Spearman correlations.
4. **Preregistered 5 Hypotheses & Executed Gate 0 + 3-Experiment Budget (`E1–E3`):**
   - Gate 0 Leakage Canary: `48/48` zero-catalogue features passed (`max directional AUC = 0.59602 <= 0.90`);
   - `E1` (38 geophysical/LiDAR/radiometric ch): `HOLDOUT-DTI = 0.08167 [0.06845, 0.09535]`;
   - `E2` (+10 DOE GDR #1391 2m temperature probes `F2mDAB`, paleo-sinter/travertine/tufa, thermal well silica/cation geothermometry, volcanic vents): `HOLDOUT-DTI = 0.09184 [0.07705, 0.10676]` (`+12.4%` controlled ablation gain);
   - `E3` (Dual-capacity OOF HGB ensemble + medial-crest boost + CELF `46,000` dots): `HOLDOUT-DTI = 0.09573 [0.08044, 0.11041]` (#1 among all 5 lanes in `WBGGEMSDOE3`).
5. **Calibrated 120-Run Leave-One-Site-Out Estimator:** Fitted out-of-site across 120 live-scored rasters (`Spearman = +0.8821, RMSE = 0.0330, MAE = 0.0240`), confirming `THCS-OOF` (`0.1455 [0.086, 0.205]`) leads all 5 repo lanes and exposing `skarpline-union`'s prior `0.4284` as `0.0697`.

---

## Pass 2 — Review, Bug Fixes, Edge Cases, & Test Audit
1. **Hash-Bound Legacy Audit Fixture Preserved:** Restored `evidence/run_card.json` (hash-bound historical fixture tested by `tests/test_audit.py` and `tests/test_preflight.py`) and isolated `THCS-OOF`'s run card cleanly in `evidence/thcs_run_card.json` and `docs/data/run_card.json`.
2. **Eliminated Conflicting Dual Banners (`IR-23`) & Upgraded `submission.html`:** Removed `HCE_BANNER` injection from `scripts/build_executive.py`, replaced the redirect stub at `docs/submission.html` with a full How-to-Submit & Portal `[0, 1]` Error Prevention page, and preserved archive reachability to `cspes/` and `hce/`.
3. **Caught & Fixed Submodular Curve Edge Case:** Unit testing in `tests/test_thcs_and_ir_fixes.py` caught `cum_tp > expected_n_truth` in `optimal_dti_budget_from_gain_curve` on synthetic gain arrays exceeding `expected_n_truth`; bounded `cum_tp <= expected_n_truth` in `src/thcs/celf.py`.
4. **Verified Staleness Feed Handling:** Simulated `scripts/refresh_feed.py` offline failure + rebuild + restore, confirming clean fallback and deterministic byte-identical HTML generation (`test_site_is_reproducible` PASS).

---

## Pass 3 — Full Prompt & Protocol Re-Check
- [x] **Unique `.tif` generated & validated automatically without human inspection:** `wbggems3-thcs-oof-celf-46000d-20261027T200639Z-21256a7e-zeros.tif` (`13/13` byte checks PASS, `float32`, `[0, 1]`, `0` NaN, `43.0%` 3-px overlap vs `GEMSDOE32`, `<= 66.5%` across all `<80k`-dot sparse submissions, `max |Spearman| = 0.544 <= 0.90`).
- [x] **Obvious OK-to-submit vs DO-NOT-SUBMIT status:** Unified `DO-NOT-SUBMIT` (`verdict: negative`) slot-protection governance across all 5 HTML pages and `README.md`, clearly distinguishing `13/13` technical format PASS from weekly slot hold (`0.09573` vs `0.09920`).
- [x] **Focus-9 (`GEMSDOE24..36`) & Peer (`KANLERGEMSDOE1..3`, `EUGGEMSDOE1..3`, `WBGGEMSDOE1..3`, `GINNYGEMSDOE1..3`) comparison table + PhD explanation of `0.2778`:** Published in `docs/executive-summary.html` and `evidence/focus_and_lane_comparison.json`.
- [x] **3–5 novel geological hypotheses ranked prior to implementation with verified free official external data:** 5 hypotheses (`H1..H5`) preregistered in `knowledge/preregistration-2026-10-27-thcs.md` and `docs/research.html`.
- [x] **Strict score labeling (`HOLDOUT-DTI`, `ORGANIZER-CONFIRMED`, `LOSO-MODEL-ESTIMATE`):** Verified across all pages and JSONs; regex audit in `tests/test_site.py` PASS.
- [x] **Preserved project prompt in `README.md` + Executive Summary at front + How-to-Submit subpage + Verified Official Sources table + Limitations & Next-Session Roadmap:** All verified (`124 passed, 4 skipped` in `pytest`; `check_site.py` PASS).
