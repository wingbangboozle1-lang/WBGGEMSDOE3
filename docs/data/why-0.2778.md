# What can explain GEMSDOE32's reported 0.2778?

**Bottom line:** 0.2778 is an owner-reported historical claim, not an organizer-confirmed result. The public repository bytes support a plausible pruning mechanism, but they do not establish that it caused the reported score. No hidden labels or receipt linking the score to the exact file are available.

## What was measured in the public mirror

The SHA-pinned byte audit reports that GEMSDOE32's B2 file contains **37,654 positive cells** and is an exact subset of a **40,199-cell H27-4 base**. The removed **2,545 cells** fall near the mirrored fault catalogue; the saved pair-identification card reports all removed dots within 3 px and a median catalogue distance of 2 px. These are measurements of owner-mirrored raster bytes, not organizer labels or score components. The H27-4 base is a separate historical artifact from the GEMSDOE28 H36 file shown as the focus site's highest file in the comparison table.

Evidence: [`focus_files_verification_2026-10-29.json`](../evidence/focus_files_verification_2026-10-29.json), [`pair_identification.json`](../evidence/pair_identification.json), and [`focus_audit.json`](../evidence/focus_audit.json). The upstream file identities are pinned, but the mirrors are not authenticated organizer downloads.

## Why pruning could help — and why this is not proven

The [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) specifies a distance-weighted Tversky score with α=0.2, β=0.8, and a 300 m triangular kernel. Removing predictions can reduce false-positive mass, but it can also discard true-positive credit. DrivenData staff state that known-fault pixels are masked from scoring; that does **not** imply all pixels near those faults are masked. Thus the removed near-catalogue cells might have low score value under the pruning rule, but their exact contribution depends on hidden faults and the evaluated raster.

A plausible mechanism is that B2 pruned redundant or low-credit cells while preserving enough nearby kernel support. The repository cannot separate this explanation from other causes, confirm the owner-reported score, or calculate a causal +0.0070 effect from public bytes alone. It would be incorrect to describe the mechanism as established.

## Scoped holdout evidence for a related pruning test

A prior experiment, H6-1, is reported as **HOLDOUT-DTI** using evaluator `gems57-pooled-hide-v2`, **11,321 withheld positives**, and a spatial-cluster bootstrap 95% CI:

| Arm | HOLDOUT-DTI | 95% CI |
|---|---:|---:|
| Unpruned | 0.13520 | [0.11846, 0.15306] |
| Within-2-px proximity prune | 0.13526 | [0.11849, 0.15310] |

The paired change versus unpruned was **+0.000054 [0.000027, 0.000089] HOLDOUT-DTI**. Against equal-count random pruning the paired change was **+0.000108 [−0.0000008, 0.000235] HOLDOUT-DTI**, including zero; the experiment verdict was negative. This proxy's own scope note says no withheld truth lay within 3 px of visible catalogue context, so it cannot resolve the near-catalogue new-fault regime that motivates B2. It neither validates nor disproves the owner-reported 0.2778.

Source record: [`h6_1_proximity_pruning_holdout.json`](../evidence/h6_1_proximity_pruning_holdout.json). This is a historical shared-template result, not a new experiment in the current review.

## Current comparison and whether a better file is demonstrated

The 2026-10-31 official public leaderboard capture shows **0.4544 at rank 1**, **0.3925 at rank 2**, and **0.3195 at rank 50**. These are other participants' public scores. They show that public leaderboard entries exceed 0.2778; they do not estimate or predict a score for this repository.

No new candidate was generated or validated. The literal uniqueness stop remains active on the hash-pinned owner-mirrored registry witness; the required method-lane paragraph is missing; and the shared cached feature/runtime was not restored or verified. There is no current file safe to download or submit, no HOLDOUT-DTI for a candidate, and no slot was used. See the [current negative run card](../evidence/session_2026-10-31_run_card.json), [current site](../docs/index.html), and [current source/leaderboard audit](../evidence/official_source_check_2026-10-31.json).
