# Executive summary — the 9 focus sites, the 0.2778 champion, and submission status

> **CURRENT REVIEW OVERRIDES THE HISTORICAL ROUND-6 PROMOTION BELOW: DO NOT SUBMIT THE R6-1 TIFF.** Strict format/grid validation passes against a hash-pinned owner mirror, but the TIFF is not unique under the literal registry rule: 97.82% of final dots lie within 3 px of the registered calibration lattice (70% stop threshold). The earlier 41.36% result omitted that lattice. In addition, the B=2 mask used full-catalogue geometry before holdout evaluation, and fold-local hide-and-recover evidence is not established. It is audit-only. See [`protocol-review-20261026.md`](protocol-review-20261026.md), [`repo-review-20261026.md`](repo-review-20261026.md), and [`evidence/current_release_review.json`](../../evidence/current_release_review.json).

**Date:** 2026-10-26 · **Round:** 6 · **Competition:** DOE GEMS Prize (DrivenData #306)
**Evidence classes (used on every number):** `[OWNER-REPORT]` = recorded from a
DrivenData submission screen; **this repository holds no organizer receipt linking
any group file's bytes to its score** (IR-32-SCORE-01), so the label
ORGANIZER-CONFIRMED is *not* used for any group score, including 0.2778.
`[HOLDOUT-DTI]` = local instrument (evaluator, withheld positives, 95 % CI stated).
`[MODEL]` = algebra on the published metric. `[measured-here]` = computed from
bytes on disk in this session (reproduce: `scripts/run_round6.py`).

---

## 1. Per-site verdicts (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)

| Site | Its highest-scoring submission | Score `[OWNER-REPORT]` | What it actually is `[measured-here]` | Submit it today? |
|---|---|---:|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-…-989f59505db1` (60,069 dots) | 0.2477 | H19-5 field thinned at 1.5 px. A *parent* of the champion lineage. Later lane `gems24-gvc1` scored 0.0859. | **No** — superseded by its sparser descendants |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-…-e56ea318af89` (44,090) | 0.2600 | Same field at 2.8 px. Direct parent of solo and champion. Later lane scored 0.0742. | **No** — superseded |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-…-5512495c6bd1` | 0.2449 | d1.5 **plus** gap-closure mass — scored *below* d1.5 (0.2477): a controlled demonstration that adding low-credit mass hurts. Later lane 0.2190. | **No** |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-…-b531dae0a36f` | **0.2710** | Best of a four-file ~0.27 cluster (solo 0.2708, h38-1 0.2707, h32-1 0.2649). The cluster is one family at slightly different prunes, not four independent methods. | **No** — already scored; family exhausted |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-…-91eae1ca` | 0.2600 | **Dot-for-dot identical to GEMSDOE25's d2.8** (same 44,090 dots, same score — a free determinism check on the scorer, IR-32-FAM-02). Later lane 0.1462. | **No** — exact duplicate of GEMSDOE25 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-…-8acb75e1` (40,199) | 0.2708 | The B=1 solo file — same `8acb75e1` lineage as GEMSDOE28's solo. | **No** — duplicate lineage, already scored |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-…-e5eb6e7e-zeros` (37,654) | **0.2778 — group best** | Solo minus its 2,545 dots within 200 m of the catalogue (B=2). End of the subtraction ladder (§2). | **No** — historical entry; do not resubmit. R6-1 also fails the current literal uniqueness and holdout gates (§4). |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-…-cb490425926e` (41,865) | 0.2632 | Fault-tip/step-over analog lane. Genuinely different geometry, but below the champion. | **No** — already scored lower |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-…-9b9ea4e6-zeros` (38,854) | 0.2750 | **Contains all 37,654 champion dots + 1,200 extras** (champion ⊂ Anderson exactly, IR-32-FAM-01). The extras cost −0.0028. The "PINN" framing adds no independent discovery over the champion. | **No** — champion superset, already scored lower |

**The pattern across all nine sites:** there is exactly **one** discovery lineage
(H19-5 multiline corroboration) and every top score is a pruning of it. No
"consensus of independent top methods" exists to ensemble — GEMSDOE30 duplicates
25, GEMSDOE31 duplicates 28, GEMSDOE36 contains 32. Any future gain must come
from a *different field*, which is what Round 6 builds (§4).

## 2. Why `h33-2-b2` got 0.2778 (PhD-level forensic, verified from bytes)

**The metric is a budget.** Official DTI (α=0.2, β=0.8, triangular kernel
k(d)=1−d/300 m) reduces exactly to `DTI = T / (0.2(T+S−M) + 0.8|G|)`
(`knowledge/01`, verified vs brute force in `tests/test_metric.py`).
Differentiating: **a dot raises DTI iff its realised credit k > 0.2·DTI** —
0.0520 at 0.26, 0.0556 at 0.2778, 0.0652 at the 0.3262-era leader. `[MODEL]`

**The ladder** `[measured-here, re-verified 2026-10-26]`:
H19-5 solid (121,131 dots, 0.1922) ⊃ d2.8 (44,090, 0.2600) ⊃ solo/B=1 (40,199,
0.2708) ⊃ **champion/B=2 (37,654, 0.2778)** ⊂ Anderson (38,854, 0.2750).
Champion ⊂ d2.8 exactly (37,654/37,654 dots, sha256 `c55bafc4…`). Each step
*removed* dots whose credit sat below the bar:

- **Thinning** (121k→44k): adjacent ridge pixels' 300 m kernel disks overlap
  63.6 %; the thin kept 75.9 % of kernel integral with 36.4 % of the mass.
- **B=1** (−3,891 dots ≤100 m from catalogue): known faults are masked in
  scoring, so these earned ≈0 but each paid 0.2. Gain +0.0108.
- **B=2** (−2,545 more at 100–200 m, implied credit ≈0.006–0.016/dot ≪ bar
  0.0556): first file with *zero* dots inside 200 m. Gain +0.0070 → 0.2778.
- **Anderson's +1,200** ran the same arithmetic backwards (−0.0028), and
  GEMSDOE27's gap-closure did too (0.2449 < 0.2477). Subtraction pays;
  addition of sub-bar mass costs. Three independent confirmations.

**Can we beat 0.2778?** `[MODEL]` At the same 37,654 dots, +8 % mean credit ⇒
≈0.30; the current public #1 (0.4413, owner-stated, unverified here) needs
≈+59 % mean credit. Emission tricks on the same field are exhausted (B=3's
expected Δ straddles zero and, as a strict subset, it is a duplicate lane).
The only remaining lever is a **better-ordered field** — dots placed where
H19-5 never looked. That is a detector problem, and no public catalogue solves
it (the newest compilation is already inside the given catalogue: 59,064 of
59,065 px within 300 m).

## 3. Five ranked hypotheses (full text: `hypotheses-round6.md`)

1. **R6-1 Step-profile scarp detector** — historical artifact only (§4). `det_elev`
   step-vs-ramp profile geometry. Existing run is invalidated by full-catalogue B=2 construction and literal lattice overlap; do not promote.
2. **R6-2 Cross-gradient phase pairing** (mag×gravity gradient angle). Research hypothesis only; not currently testable without the feature stack.
3. **R6-3 Nuisance-residualised conductivity ridge**. Research hypothesis only; not currently testable without the feature stack.
4. **R6-4 Relocated microseismicity lineaments** — free official USGS FDSN
   source named; **blocked in this sandbox** (allowlist), fetcher ready.
5. **R6-5 1 m LiDAR scarplet chains** — free official USGS 3DEP source named;
   **blocked in this sandbox**. Neither blocked idea is claimed viable here.

## 4. Historical R6-1 artifact — format PASS, submission NOT authorized

- **Artifact:** [`gemsdoe32-r6-stepprofile-b2-37654-20261026T002502Z-23fbbb51-zeros.tif`](../downloads/gemsdoe32-r6-stepprofile-b2-37654-20261026T002502Z-23fbbb51-zeros.tif) · SHA-256 `c7f094c1f4d00f2dd9a056dc80fecc94bf1d636363acd020c9da3659eae56547`.
- **Strict format/grid audit:** one float32 band, EPSG:32611, 3730×3292, exact transform, all 12,279,160 cells finite and in [0,1], nodata unset, 37,654 positive cells. Strict validator passes against the sample template restored from a SHA-256-pinned owner mirror; that mirror is not organizer-authenticated.
- **Current verdict: DO NOT SUBMIT.** The B=2 exclusion was generated from the full catalogue (`distance_transform_edt(~labels)`) before hide-and-recover evaluation. The required fold-local re-emission using only visible catalogue faults was not established. Separately, 36,832/37,654 final dots (97.82%) are within 3 px of the registered calibration lattice (70% stop threshold), and pre-placement surface correlation against every registry raster is incomplete.
- **Historical result only — [HOLDOUT-DTI, `gems32.holdout` draws 20/21, 4 quadrants × 2 draws, pooled across 8 cells, 22,232 withheld positives, 95% cluster-bootstrap CI]:** candidate 0.00338 [0.00251, 0.00453] vs incumbent 0.00452 [0.00394, 0.00525]. Because the candidate was built with the full-label buffer, these numbers are not accepted as compliant promotion evidence.
- The previous run's primary comparison was against SGMC off-catalogue truth, not the mandated fold-local hide-and-recover gate. No organizer score exists for the R6 artifact. No weekly slot was used.
- The historical comparison against 29 detector rasters recorded max surface Spearman 0.3401 and max final-dot within-3-pixel fraction 41.36%, but omitted the registered calibration lattice. Direct audit against that lattice is 97.82% within 3 px. No pre-placement correlation against every registry raster is recorded; the older numbers do not pass the current all-registry uniqueness gate.
- **Next step:** obtain the explicit lane/slot authorization; restore the missing training features, labels and cache; run the shared fold-isolated evaluator with all catalogue-derived steps recomputed from visible faults only; measure pre-placement surface correlation against every registry raster; then check final-dot overlap and validate the emitted TIFF. Do not spend a slot before a separate selector approves it.

## 5. Irregularities flagged this round

- **IR-R6-01:** 0.2778 (and every group score) was labelled
  "ORGANIZER-CONFIRMED" in places without any receipt. Downgraded to
  OWNER-REPORT everywhere this round.
- **IR-R6-02:** Former primary `geo-conduit` was bannered "OK TO SUBMIT"
  while failing the ≤70 % gate (70.24 % vs h28) and trailing the champion on
  SGMC-cal (0.0462 vs 0.0641); the site also showed contradictory red/green
  banners. Demoted; single-verdict banner installed.
- **IR-R6-03:** The literal ≤70 % gate vs the calibration lattice is
  mathematically unsatisfiable (99.87 % footprint coverage; champion itself
  99.92 %). Gate applied to detector rasters; lattice reported as diagnostic.
- **IR-R6-04:** Along-strike (N–S) shifted null retains SGMC signal (0.121);
  across-strike collapses (0.089). Consistent with N–S structural grain;
  documented in `evidence/round6_pass2_controls.json`, not gated.

## 6. Limitations & next steps

- Data are hash-pinned **owner mirrors**, not organizer-authenticated
  (DrivenData login wall). Leaderboard #1 (0.4413) is owner-stated, unread here.
- R6-1's catalogue AUC (0.525) shows step geometry barely ranks *mapped*
  faults — its SGMC strength may reflect range-front steps SGMC also traces.
  The live test is the only arbiter; spend at most one slot on it.
- Next levers if R6-1 scores poorly live: R6-2/R6-3 (viable now); R6-4
  seismicity + R6-5 1 m LiDAR need an unrestricted machine; probes S2/S3
  (value-semantics identification) remain the cheapest structural unlock.
- No GPU here (2 vCPU / 3.9 GB): the U-Net route to +59 % credit needs
  external compute. The official reference solution supports CPU training
  (slower), so GPU is a speed limit, not a hard blocker.

**Official sources for manual review:** [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) ·
[problem & metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[rules PDF 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[INGENIOUS](https://gbcge.org/current-projects/ingenious/) ·
[GDR 1391](https://gdr.openei.org/submissions/1391) ·
[EPSG:32611](https://epsg.io/32611) ·
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index) ·
[USGS FDSN](https://earthquake.usgs.gov/fdsnws/event/1/) ·
[USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
