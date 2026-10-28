# Release protocol and limitations

1. Read README and the user's task requirements first. Confirm the method lane
   exists; do not infer it from a generic request for novel methods.
2. Restore a provenance-checked template, footprint, catalogue, cached features,
   physical channel dictionary, whole-segment identifiers, buffered spatial
   folds and a complete registry of rasters including calibration/null entries.
   Hashes prove integrity against a mirror, not official authenticity.
3. Before placement, compare the candidate surface to **every** registry raster
   using Spearman rank correlation on the common footprint. The request states
   signed correlation >0.90 or directed dot overlap >70% within 3 pixels; it
   does not explicitly specify absolute correlation. This project additionally
   applies the more conservative |correlation| >0.90 check. No exemption for a
   dense lattice is authorized. A threshold failure is a
   duplicate stop, not a parameter-tuning opportunity.
4. For hide-and-recover, withhold whole segments plus a buffer, remove them from
   every catalogue-derived feature and fitting input, and reconstruct all such
   features using visible faults only. Pixel-mask visible traces in evaluation.
   Keep footprints/regions identical for every arm. Check kernel-boundary
   effects and component tails. A static prediction from full-catalogue
   exclusions is not a compliant holdout result.
5. Run each feature alone on the same holdout. AUC >0.90 is a leakage canary
   until explained; record positives, negatives, masks, folds and CI. Below
   threshold does not prove absence of leakage.
6. Use shared `gems57-pooled-hide-v2` evaluator; pool metric components first.
   Report HOLDOUT-DTI, evaluator hashes, withheld positive count and spatial
   cluster bootstrap 95% CI. Compare paired to the incumbent on identical folds.
   Required promotion policy: candidate beats the current comparable holdout
   best and paired improvement's lower CI bound is positive. This conservative
   gate does not turn a surrogate into a hidden-test estimate.
7. After placement, repeat all-registry correlation/overlap, hash exact TIFF
   bytes, run finite/range/single-band/CRS/shape/transform checks and verify
   outside-footprint encoding against the latest official instructions. Never
   silently clip or fill invalid model output. A parallel independent review
   interprets the outside rule as requiring null/NaN; this session could not
   independently re-read that page or test either encoding on the portal.
   A valid TIFF can still score poorly or be a duplicate.
8. A separate selector approves a weekly slot only after reading the actual
   current submission-page cap and usage. Neither is available here. No upload
   automation or submission credentials are included.
9. Stop after three experiments or two hours. Negative results are retained.
   No geological experiment was run in this session; no data-free score exists.

## Shared-tool irregularity

Peers do not all use the same template. GEMSDOE36 pins GEMSDOE24; GEMSDOE31
pins 57GEMSDOE. This checkout restores the latter byte-for-byte at commit
822a0ce5546c7b6749cdd82eb145b6b3e616603d, using GEMSDOE31's hash manifest.
No new shared-code fix or private fork was made in this session. A flawed historical
local holdout wrapper is now disabled rather than substituted for the template.
This restoration is an auditable API base,
not evidence that a lane was assigned or that the cache was recovered. A real
run must reconcile which instrument the parallel lanes share before comparison.

## Access limits

Outbound network hosts are limited to GitHub and Python/npm package registries.
DrivenData, Dropbox, USGS, GDR and PDF hosts are not directly accessible here.
There are no authenticated competition feature stack, labels or saved folds in
this checkout; the excluded cache holds only audited mirrors and shared code. An upstream
GEMSDOE32 manifest identifies a 418,912,844-byte numerical-stack owner mirror
on GitHub, so data are not universally unobtainable; it is not downloaded
without the missing lane and cache contract. Labels/template mirrors are also
listed there. Cached stack paths in upstream receipts refer to that repo's
local filesystem, not files available here. No verified full registry inventory
or organizer score receipts were restored. Compute requirements cannot be
established before a method is selected; the official reference supports CPU.

## Prospective selector schema (not a release)

`src/gems_project/release_gate.py` is a fail-closed **schema check**, not an
independent measurement or a replacement for a selector. Its caller must replay
and authenticate the evidence, verify source/registry completeness and bind all
measurements to exact saved bytes. Synthetic test fixtures are not candidate
approvals. A future candidate needs:

- Authority: `verdict: "promote"`, `selector_approval: true`, and an exact
  lowercase `raster_sha256` matching the candidate.
- Candidate: `verdict: "promote"`, `submission_name`, `submission_note` (nonblank,
  ≤140 characters) and the same 64-hex `raster_sha256`.
- `holdout_dti`: `label: "HOLDOUT-DTI"`, `evaluator_version`, positive integer
  `withheld_positives`, numeric `value`, ordered `ci95` containing it,
  `fold_local_catalogue_features: true`, `matched_incumbent_folds: true`,
  `matched_baseline_dti` lower than `value`, and `paired_delta_ci95` with a
  strictly positive lower bound. Independently verify folds, buffers and hashes.
- `canary`: true `all_features_tested`, positive integer `n_features` and matching
  `n_features_tested`, `max_auc` ≤0.90. Record each feature result separately.
- `uniqueness`: true `literal_pass` and `complete_registry`, equal positive
  integer counts `registry_expected` and `registry_checked`, plus `surface` and
  `final` maps each containing `passed: true`, `max_abs_spearman` ≤0.90 and
  `max_dot_overlap` ≤0.70. The absolute-rank condition is the project's extra
  conservative convention, not explicit in the user's signed wording. Counts
  alone cannot prove registry coverage; attach the complete per-file audit.
- `validator`: true `passed`, `single_band`, `dtype_float32`, `no_inf`,
  `no_nan_inside_footprint`, `values_in_0_1`, `crs_shape_transform_match`,
  `outside_footprint_compliant` and `saved_bytes_equal_audited_dots`; name the
  nonblank `outside_footprint_policy`, bind the reference with
  `reference_footprint_sha256`, include a positive integer
  `positive_cells_inside_footprint`, and set `sha256` to the candidate digest.
  `values_in_0_1` must cover every finite prediction as specified by the current
  portal, and inside values must all be finite. Prove the outside policy from the
  current official source; do not treat a local boolean as proof.

Anything missing, malformed, non-finite or unsupported blocks promotion. The
current site builder intentionally publishes only a negative decision; replacing
that with a positive publication requires a separately reviewed release path.
