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

## Verification addendum — 2026-10-29 (mechanism, verified bytes; score still unproven)

Sources: [`evidence/focus_files_verification_2026-10-29.json`](../evidence/focus_files_verification_2026-10-29.json)
(script `scripts/verify_focus_files.py`), and the organizer statements in
[`evidence/official_source_check_2026-10-29.json`](../evidence/official_source_check_2026-10-29.json).

1. **Exact construction, verified.** GEMSDOE32's 37,654 positive cells are a subset of the 40,199
   positive cells of the GEMSDOE28 H27-4 base, and the removed set is exactly the base cells within
   2.0 px of a catalogue fault. Rule "base AND distance > 2.0 px" reproduces GEMSDOE32 with **0
   mismatches** over the 12.28 M-cell grid. GEMSDOE31's dot set is identical to the base. So the
   owner-reported pair GEMSDOE31 (0.2708) → GEMSDOE32 (0.2778) differs **only** by this exclusion.
   Owner-reported difference: +0.0070 (not a receipt).
2. **Organizer masking rule, verified (forum staff reply).** DrivenData staff say pixels "corresponding to
   known USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards
   penalty terms." The reply does not say that neighbouring pixels are masked. A prediction 1.4–2 px
   from a catalogue fault therefore keeps its false-positive weight, unless the hidden test faults lie
   within 300 m of it. That is the mechanism proposed here: removing low-credit cells near the catalogue
   lowers FP mass. Whether the 300 m kernel gives back enough TP credit is **unknown**.
3. **Pattern across the nine owner-reported scores (descriptive, n = 9).** The two top files (GEMSDOE32
   0.2778, GEMSDOE36 0.2750) are the only two with **0.0%** of dots within 2 px of the catalogue; the
   other seven have 6.2%–14.6%. Dot count vs owner score: Spearman ρ = −0.983. Catalogue-ring fraction vs
   owner score: ρ = −0.895. These are correlations over nine self-reported numbers from different authors.
   They are not evidence of causation.
4. **Counter-evidence from the only holdout test of the same idea.** The historical H6-1 proxy
   (`evidence/h6_1_proximity_pruning_holdout.json`, HOLDOUT-DTI, evaluator gems57-pooled-hide-v2) pruned
   ≤2 px cells and changed DTI from 0.13520 to 0.13526 (paired Δ +0.000054, CI [+0.000027, +0.000089]).
   Its FP mass fell by about 32 units out of 32,206 (0.1%), and TP was unchanged. The proxy's scope
   excludes the near-catalogue new-fault regime, and it did not score GEMSDOE32's file. So it neither
   confirms nor refutes a +0.007 owner-reported gain, but the owner gain is about 130× larger than the
   proxy gain. This discrepancy is recorded as an irregularity to review, not as an explanation.
5. **Why this does not give a new TIF.** Any variant that changes only the exclusion radius, or applies
   the same rule to another focus file, lands at more than 0.97 directed 3-px overlap with the focus set
   and fails the literal uniqueness rule. A new candidate needs a different evidence source (see the
   preregistered H1–H5 and the session review), and none has been validated. No holdout was run here.

## Addendum 2026-10-31 — the question re-measured on a common truth

Everything above predates a candidate that exists. This addendum supersedes the
"no new TIF / not demonstrated" conclusions in §"Can a new TIF beat it?" and
addendum item 5 of 2026-10-29. It does **not** upgrade the owner-reported 0.2778
to a receipt: the number is still what GEMSDOE32 published, not what an organizer
returned to this project.

**1. The nine files and this release, scored against one truth.** Hidden labels are
unavailable, so every file was scored with the official formula (α = 0.2, β = 0.8,
300 m triangular kernel, catalogue masked, NaN outside the footprint) against USGS
State Geologic Map Compilation faults that lie more than 300 m from the competition
catalogue — 62,649 cells, an independent mapping lineage
(`evidence/release/truth_b.json`). This is a generalisation proxy, not truth, and it
contains non-Quaternary bedrock structure.

| File | Dots | Axis-B DTI | Recall | Hit rate ≤3 px |
|---|---:|---:|---:|---:|
| this release (CIFS CAT, 139,957 dots) | 139,957 | **0.2251** | 0.288 | 0.117 |
| GEMSDOE27 | 61,328 | 0.1015 | 0.102 | 0.122 |
| GEMSDOE24 | 60,069 | 0.1002 | 0.100 | 0.122 |
| GEMSDOE36 | 38,854 | 0.0961 | 0.090 | 0.130 |
| GEMSDOE33 | 41,865 | 0.0956 | 0.090 | 0.127 |
| GEMSDOE31 | 40,199 | 0.0951 | 0.089 | 0.129 |
| GEMSDOE32 (0.2778) | 37,654 | 0.0947 | 0.088 | 0.131 |
| GEMSDOE30 | 44,090 | 0.0944 | 0.090 | 0.122 |
| GEMSDOE25 | 44,090 | 0.0944 | 0.090 | 0.122 |
| GEMSDOE28 | 37,660 | 0.0931 | 0.087 | 0.129 |

The family's dots are *slightly better placed* than ours (hit rate 0.122–0.131 vs
0.117) and its recall is *three times worse* (0.087–0.102 vs 0.288). The axis-B lead
is therefore a coverage effect, not a ranking effect — an earlier density ablation of
our own candidate makes the same point: at the family's ~40,000-dot budget we scored
0.0860, *below* every sibling (`evidence/release/density_ablation.json`).

**2. What the algebra now forces.** With a binary dot field,
`TP_w + FN_w = |G|` exactly, so `DTI = TP_w / (0.2·TP_w + 0.8·|G| + 0.2·FP_w)`.
With `FP_w = 0`, DTI ≤ R/0.8, hence a score of 0.2778 *requires* recall ≥ 0.222 and
a hit rate ≥ 0.056. Inverting at a stated hit rate h bounds the hidden truth
(|G| ≈ 7,531 at h = 0.10; 16,001 at 0.15; 32,940 at 0.25) — the same table as before,
now with a measured h to anchor it (ours 0.117, theirs 0.122–0.131 on axis B).

**3. The correlations, stated with their fragility.** Across the nine files,
ρ(owner score, dots) = −0.983 and ρ(owner score, ≤3 px near-catalogue fraction) =
−0.983, with the two predictors collinear in this sample (n = 9, self-reported
scores from different authors). The 2026-10-29 addendum quoted −0.895 for the *≤2 px*
band; the statistic moves with the band width, which is exactly why it is supporting
evidence and not proof. The mechanism it supports is organizer-confirmed: known-fault
pixels are masked in both rounds, so a dot on the mask earns nothing, and a dot
1–3 px off it is an active cell that pays false-positive weight unless a hidden new
fault happens to lie within 300 m.

**4. Can a new TIF beat 0.2778?** On the only truth where both can be measured, yes:
0.2251 vs 0.0947, a factor of 2.4, with a 3 px collar rather than the family's 2 px
and 3.7× more dots. Whether that transfers to the hidden label set is **not
identified**: the projection `DTI = h·(n/|G|)/(0.8 + 0.2·n/|G|)` runs from 0.167 to
0.418 across |G| = 15,000–90,000, and it assumes our per-dot credit on axis B carries
over unchanged. That is a projection with a named assumption, not a score. The one
number that is neither conditional nor owner-reported is the holdout DTI of the
fold-fitted recipe: **0.2292 [0.2145, 0.2440]** on 60,692 withheld catalogue pixels
(`evidence/release/density_sweep.json`). The released bytes are a refit on all four
quadrants, so no uncontaminated axis-A number exists for them and none is claimed.

Records: `evidence/release/{truth_b,density_ablation,why_02778,density_sweep,experiments}.json`
· live decision `docs/index.html`.
