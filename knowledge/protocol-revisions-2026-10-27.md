# Protocol revisions, 2026-10-27

Two binding clauses of the parallel-run protocol were amended after measurement. Both changes are
weakening *of a test*, never of an outcome, and both are applied by code in this repository, not by prose.

## R1 — the uniqueness rule was unsatisfiable as written

**Original text (clause 1):** stop if more than 70% of final dots are within 3 px of *one registry raster*.

**Measurement.** `17GEMSDOE`'s probability raster is finite-positive on all 5,167,373 footprint cells
(`evidence/concurrent_audit.json`, verified by re-reading the file). Under the template's definition of a
"dot" (finite and > 0), every nonempty submission is 100% within 3 px of it. The rule therefore forbids all
submissions, including the nine archived files that the organizer scored.

**Revision.** The 70%-within-3-px rule is applied to every *sparse, submission-like* comparator. It is
treated as vacuous only for comparators whose own 3-px coverage of the footprint is ≥ 90% — currently exactly
one, a spacing-5 lattice at 99.87%. Each comparator records `comparator_3px_coverage`,
`space_filling_comparator` and `reasons` in `docs/data/uniqueness.json`; the exclusion is never silent.

**Second defect in the same clause.** "Rank correlation > 0.90" on raw binary masks is degenerate: two
disjoint masks have ρ ≈ −0.99 on their union, so the rule blocked *every* comparison, including comparisons
between files that share no dots. Rank correlation is now computed on 2 km density fields (Gaussian σ = 20 px)
inside the footprint, which is what "is this the same map" actually means. Both statistics are reported.

## R2 — the catalogue holdout is anti-correlated with the competition metric

**Original text (clause 2):** holdout = withhold whole catalogue fault segments with a buffer; score pooled
DTI on the withheld segments.

**Measurement.** Implemented with four spatial folds, whole connected segments, a 3-px buffer, exact
catalogue masking and pooled false-positive accounting. Ranking the eleven archived submissions by that
holdout gives Spearman **−0.146** against their organizer-reported scores. The 0.2778 champion ranks **last**
(DTI 0.0048) and a 0.1563 file ranks first (0.2673). The holdout rewards predicting catalogue faults; the
competition's ground truth is faults *not* in the catalogue. It measures the opposite skill.

**Revision.** The validation target is the external-catalogue proxy in `src/gemsdoe/validation.py`:
USGS SGMC faults more than 300 m from every catalogue fault (62,122 positives). On it, the eleven archived
files reproduce their reported ordering at Spearman 0.55 and their reported values at a median absolute
residual of 0.014 once one constant (|G| = 15,672 px) is fitted; a spacing-5 lattice is a rejected outlier.
Every number derived from it is labelled PROXY-DTI with evaluator version, positive count and 95% CI, and the
leaderboard value is labelled ESTIMATE. The old holdout code is retained and its negative result is published
(`docs/research.html` §3) rather than deleted.

## What was *not* changed

- α = 0.2, β = 0.8, R = 300 m, the triangular kernel and the pooled evaluation are untouched.
- The shared writer's semantics (binary 1.0 on support, 0.0 outside) are untouched; no clipping was added.
- No registry raster was edited, no threshold was tuned to make a candidate pass, and the evaluator used for
  every published number is the one verified against brute force on the official 512×512 fixture.
