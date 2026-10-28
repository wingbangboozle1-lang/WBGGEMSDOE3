# Irregularities Log — Session 4 (`FCHD-NCM`, 2026-10-28 UTC)

This document extends `IR-01`..`IR-23` from earlier lanes with five newly audited irregularities (`IR-24`..`IR-28`), including how each was fixed or disclosed in code.

---

## `IR-24` — Cross-Page & Release-Gate Desynchronization (`SGCE` vs Stale `tde30k` + Uncalled `check_release_gate()`)

- **Discovery:** Line-by-line inspection of `docs/`, `scripts/session2_site.py`, and `scripts/check_site.py` revealed:
  1. `docs/index.html` and `docs/executive-summary.html` promoted `wbggems3-sgce-20261027-f52d35d8-zeros.tif` (`sha256 = 0444c37466fb...`, `HOLDOUT-DTI = 0.16749`), while **`docs/how-to-submit.html`, `docs/data/decision.json`, and `docs/data/release_gate.json`** were stale leftovers from `scripts/build_dossier.py` pointing to the superseded `wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif` (`sha256 = e756a162...`, `HOLDOUT-DTI = 0.07219`)!
  2. In `scripts/check_site.py`, `check_release_gate(errors)` was defined on line 39 and **never invoked** inside `main()`.
- **Fix:**
  - `scripts/session2_site.py` now deterministically generates `docs/how-to-submit.html`, `docs/data/decision.json`, and `docs/data/release_gate.json` directly from `evidence/session2_build.json` and `evidence/session2_run_card.json` (`0444c37466fb...`), while preserving the historical negative `evidence/release_gate.json` and `evidence/run_card.json` untouched.
  - `scripts/check_site.py` now calls `check_release_gate(errors)`, verifies all 5 top-level pages (`index.html`, `executive-summary.html`, `how-to-submit.html`, `research.html`, `evidence.html`) plus `docs/fchd/index.html`, and asserts SHA-256 identity across `docs/data/{run_card,session2_run_card,decision,release_gate}.json`.

---

## `IR-25` — Prior-Lane Audit Findings (`HCE-1` Missing Collar Mask & `THCS-OOF` Full-Registry Overlap)

- **Discovery:**
  1. `scripts/hce_holdout.py` omitted `~collar` when masking visible faults during evaluation (`0.1302` script print vs `0.09313` actual hide-and-recover `HOLDOUT-DTI` of the saved `wbggems3-hce1-...-zeros.tif`).
  2. `THCS-OOF` (`wbggems3-thcs-oof-celf-46000d-...-zeros.tif`, `HOLDOUT-DTI = 0.09573`) passed uniqueness against sparse `< 80k`-dot files (`<= 0.6654`), but had `0.9209` 3-px one-way overlap against the `167,597`-dot ledger blanket `GEMSDOE67__gemsdoe67-ovtr-ml-cover-tau3p0-20261012-nan.tif`.
- **Fix in `FCHD-NCM`:** `src/fchd/model.py` enforces exact `d_visible > 2.0 px` per fold and embeds bit-packed per-comparator knapsack caps across all `149` non-lattice masks (`<= 0.6350` max 3-px overlap across all `195` TIFs, including `167k–516k` ledger blankets and all `17` newly added Oct 27 peer TIFs).

---

## `IR-26` — CELF Background-Quantile Starvation on Concentrated HGB Posteriors

- **Discovery:** Setting `min_gain_frac` via the 68th percentile of footprint posterior probabilities (`0.035`) caused CELF to stop after `1,653 / 38,000` dots (`HOLDOUT-DTI = 0.02521`) on concentrated relief-matched HGB surfaces.
- **Fix & Disclosure:** Replaced arbitrary quantile stopping with exact running-ratio DTI threshold `r(d_x) = TP_w / (0.2 FP_w + 0.8 |G|)` and `min_gain_frac = 1e-4` up to the preregistered `38,000` / `42,000`-dot budget, disclosed in `evidence/fchd_run_card.json` (`budget_disclosure`).

---

## `IR-27` — `training_features.tif` Non-Grouped TIFF-Tag Band-Order Trap (Caught & Fixed in Pass 2)

- **Discovery:** Pass 2 line-by-line inspection against `rasterio.open("data/raw/training_features.tif").descriptions` and `src/lbcal/data.py` caught that `training_features.tif` stores bands in interleaved order (`b2=rtp`, `b4=geod_2ndinv`, `b5=iso_grav_anom_slope`, `b6=tc` radiometric Total Count, `b12=det_elev`, `b13=iso_grav_anom`, `b14=tmi`, `b15=depth_to_base_surf`, `b16=ieq_n100a15`, `b17=cond_surf`, `b18=iso_grav_anom_hg`, `b19=det_elev_slope`), NOT grouped magnetic/gravity/strain order. Reading `b4/b5/b19` as `grav/mag/basement_depth` had turned `basin_ind` into a mountain-slope indicator (`b19 = det_elev_slope`) rather than a sedimentary-basin indicator (`b15 = depth_to_base_surf`).
- **Fix & Scientific Insight:** Fixed `src/fchd/features.py` (`BAND_IDX`), deleted pre-bugfix artefacts, rebuilt `fchd_static_u8.mmap`, and re-ran Gate 0 + `E1/E2/E3`. Restoring true `b15 = depth_to_base_surf` shifted upward-continued basin worms off exposed range-front scarps into flat alluvial valleys: off-catalogue `SGMC-Cal ESTIMATE` **rose** (`0.0494 -> 0.0502`, with `LBCAL-Physics ESTIMATE = 0.0927`, highest of any valid lane in `WBGGEMSDOE3`), while scarp-biased `labels.tif` `HOLDOUT-DTI` moved from `0.10342 / 0.10433` (95% paired CI `[-0.00464, +0.01545]`, already negative) to `0.09702` (`E2`, 95% CI `[0.08726, 0.10652]`, still the #1 ~38k-dot spatially-blocked model in `WBGGEMSDOE3`).

---

## `IR-28` — Post-Collar GeoTIFF Hide-and-Recover Evaluation Trap

- **Discovery:** Exported competition GeoTIFFs (`-zeros.tif`) zero out `d_full_catalogue <= 2.0 px` across all `60,988` `existing_faults.tif` pixels. Because `hide-and-recover` withholds whole segments *from* `existing_faults.tif`, running `evaluate_hide_and_recover` directly on an already-exported `-zeros.tif` measures near-zero (`0.0022–0.0191`, e.g. `0.00452` on `GEMSDOE32.tif`) except on older files (`GEMSDOE25`, `44,090` dots) that never applied the 2-px catalogue collar.
- **Fix:** `scripts/audit_all_sites_and_lanes.py` explicitly separates fold-evaluated hide-and-recover `HOLDOUT-DTI` (where only `d_visible <= 2.0 px` is masked per fold) from post-export `LBCAL-Physics` and `SGMC-Cal` estimates.
