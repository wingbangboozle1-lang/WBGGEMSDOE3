# Review and irregularities — RFL session addendum, 2026-10-27 (`arena/bd44f94b`)

Continues IR-01…IR-19 (2026-10-26/27 files stay in force). Numbering continues IR-20.

### IR-20 — Skarpline uniqueness gate fails on the full rebuilt registry (CORRECTED)
- **Observed.** `wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif` has 73.52% of dots
  within 3 px of `GEMSDOE23 h30-arrangement-matched-habitat` (91,533 ref dots, null 0.411,
  ρ +0.42) and 72.40% within 3 px of `GEMSDOE50 h59-sharpened-scarp-scatter-90k` (90,000 dots,
  null 0.276, ρ +0.74), ex-self, vs the 151-file/120-mask rebuilt registry. Its published audit
  compared 20 files and reported max within-3px 29.3% (sparse comparators).
- **Evidence.** `evidence/rfl_selector_analysis.json` → `uniqueness_reaudit.skarpline_union_saved`.
- **Impact.** The repository-wide "CURRENT DECISION: SUBMIT … cleared by every automated gate"
  was false under the project's own gate at full-registry scope.
- **Action taken.** Decision superseded: README top block, `scripts/rfl_banner.py` banner on all
  root pages, generated downloads page relabelled, `docs/rfl/index.html` carries the corrected
  table. The skarpline lane's own run card is untouched (lane history preserved).

### IR-21 — Leaderboard estimate model violates its own physics for dense files
- **Observed.** `gemsdoe.validation.score_from_profile` assumes SGMC hit-rate h transfers at any
  mass. Implied capture h·mass/|G|: HCE-1 1.43, lattice-s5 1.49, skarpline 0.96 — the first two
  exceed 100% of all hidden faults; HCE-1's point estimate 0.4393 exceeds the model's own cap
  |G|/(|G|+0.2·mass) = 0.316. The lattice file (in-sample residual +0.309) was excluded by the
  robust trimmed fit, hiding the failure mode; LOO RMS is ±0.096.
- **Impact.** Published point estimates (0.428 skarpline; any HCE value from this model) are
  optimistic extrapolations, not ±0.02-accurate forecasts.
- **Action.** Estimates now published with physical cap + implied capture + LOO RMS on
  `docs/rfl/index.html`. No code in `src/gemsdoe/` was silently edited.

### IR-22 — Holdout anti-correlation claim does not reproduce at n=118
- **Observed.** `src/gemsdoe/validation.py` states catalogue holdout Spearman −0.15 vs reported
  scores (11 files). Measured here across 118 byte-verified owner-scored ledger rasters under a
  specified static protocol (`GEMSDOE32-HIDE-RECOVER-v3.0` on saved bytes): **+0.172**.
  SGMC-family metrics rank better (+0.34…+0.45) but none is strong.
- **Impact.** "Holdout is an anti-proxy" is not generally true; static holdout is, however,
  structurally biased against full-catalogue-pruned files (mechanism in session review).
- **Action.** Flagged; reconciling the original 11-file protocol is listed as next work.

### IR-23 — Legacy "-nan" filename contains no NaN bytes
- **Observed.** `docs/downloads/wb-gems-doe-3-stepover-damagezone-…-nan.tif`: nodata metadata is
  NaN but the array holds 0 NaN cells (values {0,1}, "mixed" outside-footprint encoding).
- **Impact.** Filename-based assumptions about outside-footprint encoding (IR-15) are unsafe;
  it remains research-only/DO-NOT-SUBMIT.
- **Action.** Recorded in E0 audit; no bytes changed.

### IR-24 — RFL lane self-assigned; preregistration Amendment 1 on the uniqueness operationalisation
- **Observed.** No external lane paragraph was supplied again; RFL was self-assigned and
  preregistered before modelling. After E1, the surface-stage stop rule was amended (rank-
  correlation on surface; 70% on placed dots; lattice-like refs by excess-over-null), matching
  both prior lanes' published gates. Amendment is dated and in the preregistration; the original
  probe numbers (0.7016/0.7033) are preserved in `evidence/rfl_uniqueness.json`. The placed dots
  then failed anyway (0.709) and the lane stopped without repair, as the amendment required.
- **Action.** None further; future lanes should adopt the same explicit two-stage wording.

### IR-25 — Registry coverage remains partial
- Rebuilt registry = 151 files / 120 unique masks vs committed index 522 files / 296 masks
  (`.cache/sites` trees not rebuilt; `registry/cspes_registry_index.json` regenerated this
  session from 149→151 files because newer lane artifacts exist). Every uniqueness statement
  this session carries this scope. A "pass" is not proven against the unrebuilt remainder.
