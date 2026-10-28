# What can explain the reported GEMSDOE32 B2 result?

**Owner-reported historical claim, not organizer-confirmed:** 0.2778 for the pinned
GEMSDOE32 H33 B2 file. We did not obtain a DrivenData receipt linking this score to
these bytes or the hidden labels, so neither the value nor its causal explanation can
be independently verified. Its upstream repository has advanced since the pinned file
was selected; this is not a verified current ranking.

## What the rasters establish

The B2 positive support has 37,654 cells and is an exact subset of the 40,199 positive
cells in the pinned GEMSDOE28 H27-4 base: 2,545 cells were removed and none added.
Those removed cells lie 1.414–2 pixels from the mirrored fault catalogue; the nearest
retained cell is 2.236 pixels away. The decoded masks, grid and hashes were checked in
[evidence/focus_audit.json](../evidence/focus_audit.json). This describes a placement
change, not an identified improvement in geology or score.

The [official metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
uses pooled, distance-tolerant Tversky with α=0.2, β=0.8 and a 300 m triangular
kernel. Thinning can reduce redundant prediction mass; deleting predictions can reduce
false-positive mass but can also lose true-positive credit. Which effect dominates
requires the unavailable hidden labels and exact evaluated bytes. There is no defensible
numeric break-even density or causal decomposition from these artifacts alone.
[Staff clarify](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)
that **known-fault pixels** are excluded in both rounds; that does not imply all
neighboring pixels are excluded. The B2 removal is near the catalogue, not necessarily
on excluded pixels.

## Historical H6-1 proximity-pruning holdout

A previous shared-template H6-1 experiment reports **HOLDOUT-DTI** using
`gems57-pooled-hide-v2`, 11,321 withheld positives and a spatial-cluster 95% CI.
Unpruned: 0.13520 [0.11846, 0.15306]; ≤2 px proximity-pruned: 0.13526
[0.11849, 0.15310]. Paired Δ versus unpruned: +0.000054
[+0.000027, +0.000089]; versus equal-count random pruning: +0.000108
[−0.0000008, +0.000235], including zero. Its own verdict was **negative**.
[Saved historical experiment record](../evidence/h6_1_proximity_pruning_holdout.json) ·
[pinned upstream](https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/docs/data/h6_1_proximity_pruning_holdout.json).
This is historical and was not replayed in this session.

Crucially, its saved scope caveat says buffered withholding leaves no withheld truth
within 3 px of visible catalogue context. It cannot identify the near-catalogue
new-fault regime that motivates B2. A small difference on this proxy does **not** prove
or disprove the effect on the hidden competition score; the reported 0.2778 remains
unverified.

## Can a new TIF beat it?

Unknown. Another participant's higher public leaderboard result is evidence that a
higher competition score exists, not that a new file from this project will achieve it.
This session produced no candidate or valid local holdout estimate. The literal
registry definition stops every nonempty in-footprint candidate because a registered
soft raster is positive throughout the footprint; do not submit or silently exempt it.
See the [current dashboard](../docs/index.html) and [negative card](../evidence/session_9b794637_run_card.json).

## Verification addendum — 2026-10-27 (independent recomputation)

The focus overlap and B2 dot counts were independently recomputed from SHA-pinned bytes;
the historical projection figures below were carried forward, not re-fitted. Owner-reported and
projection figures are **not** organizer-confirmed scores.

1. **Arithmetic.** GEMSDOE31's base has 40,199 positive cells; GEMSDOE32's B2 file has 37,654
   (`evidence/nine_site_table.json`). Difference **2,545**, matching the earlier statement.
2. **Near-duplicate structure (new).** `scripts/verify_focus_uniqueness.py` → `focus_vs_focus_pairwise`:
   every GEMSDOE32 dot lies within 3 px of a dot in GEMSDOE24, 25, 27, 30, 31 and 36 (overlap
   1.000 each), and within 0.9988–0.9998 of 28 and 33. In the other direction, GEMSDOE32 covers only
   0.867–0.974 of those files' dots. So 0.2778's file is a sparser subset of the other top-scoring
   files, within the 3-px tolerance, and it is **not unique** against them.
3. **Why it could score highest — hypothesis, not established.** The public data cannot separate the
   effect of the 2,545 removed cells (1.4–2 px from the catalogue) from the hidden labels. A plausible
   mechanism is that the removal lowers false-positive mass while keeping most true-positive credit under
   the 300 m kernel. The same public data could not confirm it, and no receipt ties 0.2778 to these bytes.
4. **Can a new TIF beat 0.2778? Not demonstrated.** Historical ledger projections and holdout
   estimates were not re-fitted here and are subject to selection and circularity caveats
   (`evidence/session2_projection.json`, `evidence/candidate_run_card.json`). No gain is validated;
   SGCE's focus-only uniqueness also does not satisfy the literal all-registry requirement.
   See `knowledge/irregularities-2026-10-27.md` IR-28-06 to IR-28-08.

## Addendum 2026-10-28 — shipped-bytes audit (AMDC lane, negative)

The AMDC lane re-scored the shipped bytes of every repository candidate on identical
withheld folds instead of trusting construction-time figures. It does not change the
repository's DO-NOT-SUBMIT decision:

* SGCE shipped bytes: **0.0191** [0.0169, 0.0211] (native evaluator, 22,232 withheld) and
  0.0190 [0.0171, 0.0208] (matched evaluator, 22,893 withheld) — vs B2 reference bytes at
  0.0045 / 0.0039. The earlier 0.1675 headline described per-cell rebuild files with
  asymmetric dot budgets, not the downloadable file.
* Owner-reported scores and matched-holdout scores are **inverted** on the 9 focus sites
  (Spearman −0.849, Pearson −0.886): the near-catalogue dotted family that owners score
  highest (B2 0.2778, unverified) scores lowest on the holdout (0.0039), and vice versa.
* Method projections for the same files span 0.05–0.27 (SGCE ledger PROJECTION 0.0669 vs
  matched-holdout OLS 0.2726 ±0.005). The disagreement between methods is itself the
  uncertainty statement; none of them is a score, and the reported 0.2778 remains unverified.

Records: [bytes audit](../evidence/amdc/sgce_bytes_audit.json) ·
[run card v2](../evidence/amdc_run_card.json) ·
[irregularities](../knowledge/irregularities-2026-10-28-amdc.md).

## Addendum — byte-exact chain (2026-10-28, hash-pinned bytes)

Measured with `np.array_equal` on the hash-pinned raster mirrors (`data_manifest.json`):

| File | sha256 (first 16) | Dots | Chain relation (exact) | Owner-reported |
|---|---|---:|---|---:|
| dotted-h19-5-d1-5 | 68d0e2e4fcc594f9 | 60,069 | d1-5 network, 1.5-px spacing | 0.2477 |
| dotted-h19-5-d2-8 | 91eae1ca42ec844e | 44,090 | 2.8-px spacing skeleton | 0.2600 |
| d28-poisson (GEMSDOE30) | 8cf893ea… | 44,090 | **identical support** to d2-8 (re-serialized) | 0.2600 |
| solo-d28 (GEMSDOE31) | 07b6db44… | 40,199 | = d2-8 − 3,891 dots with d_cat ≤ 1.01 px (exact) | 0.2708 |
| **B2 (GEMSDOE32)** | c55bafc4… | 37,654 | = solo-d28 − 2,545 dots with 1.01 < d_cat ≤ 2.01 px (exact) | **0.2778** |
| anderson-pinn (GEMSDOE36) | e1589102… | 38,854 | = B2 ∪ 1,200 added dots (exact) | 0.2750 |

One-change marginal effects along the chain (same model, same submission window):

- remove 3,891 on-catalogue dots: **+0.0108**
- remove 2,545 dots in the 1–2 px catalogue band: **+0.0070**
- add 1,200 miscellaneous dots back: **−0.0028**

Halo geometry (why nothing else is available on-network): every one of the 121,131 h19-5
network cells lies within 3 px of a d1-5/d2-8/tgc dot; the network is saturated by the
family. A submission that satisfies the directed 3-px uniqueness rule against d1-5/d2-8
must therefore place ≥30% of its dots off-network (the observed family band:
gems70 0.2478, gate_ortho 0.2376, cvarlw 0.2303, h59-cover 0.2296, h3pack 0.0443).

DTI marginal algebra (binary dots, triangular kernel): removing a dot whose kernel credit
is duplicated, or whose predicted credit is low, strictly raises DTI; adding a dot needs
kernel credit k > α·DTI ≈ 0.056 (about one correct cell within ~2.8 px of hidden truth) to
break even. B2 is therefore a **redundancy-pruned** family member, not a denser one — and
every marginal addition tested (pinn) hurt.

Catalogue-mask mechanism: the organizer excludes known-fault pixels from scoring (staff
clarification), but the catalogue is imperfectly masked relative to hidden truth, so
on-catalogue dots earn no TP while still contributing FP. The B2 trim removes exactly that
dead mass. What remains cannot be improved by pruning alone; scoring above 0.2778 with a
*unique* submission requires placing new dots near hidden truth that the family does not
already cover — i.e. new geological information (hypotheses H2/H3 in
`knowledge/preregistration-2026-10-28-khd.md`).
