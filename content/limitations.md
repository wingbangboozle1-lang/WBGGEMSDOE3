# Current limitations, irregularities and blocked work

## Current decision (2026-10-27)

- **DO NOT SUBMIT any historical artifact.** The current audit records a registry witness with positive support across the full mirrored sample footprint. Under the binding literal `>70% within 3 px` stop, every nonempty in-footprint candidate fails. The mirror is hash-pinned, not organizer-authenticated; that provenance limit does not authorize bypassing the stop.
- **No candidate, holdout run, or experiment was created in this review.** There is no new-file score and no leaderboard estimate. A real submission slot remains a separate selector decision and none was selected.
- User/owner score figures, including the GEMSDOE32 B2 report, are unverified without an organizer receipt tied to exact bytes. The public leaderboard snapshot last observed on 2026-10-26 is stale for this review; conflicting values are not reconciled without a fresh attributable observation.
- The `restore_shared_data.sh` wrapper previously targeted a missing Python script. It is now repaired to call the pinned template's own `prepare_data.py`. The public mirror bridge is not an authenticated organizer download, and no training stack was fetched in this review.

## Historical LST1 record — superseded, not current approval

The old LST1 run used evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, with 22,232 withheld positives. For example, its `lst_mod_quota` candidate pooled DTI was 0.06668 (95% CI 0.05688–0.07655); the champion proxy was 0.09920 (95% CI 0.08595–0.11267); paired delta −0.03252 (95% CI −0.04103 to −0.02372). These are archived **HOLDOUT-DTI** diagnostics, not results from the currently prescribed `gems57-pooled-hide-v2`, not a leaderboard estimate, and not an organizer-confirmed score.

The historical finalizer omitted the literal overlap result from its readiness decision; its LST1 card could say `ready_to_submit=true` even though `literal_rule_pass=false`. It also used a lattice-excess exception. This contradiction is corrected in the reclassified run card: literal gate fails; unknown registry scope fails closed; selector approval is false. `scripts/build_submission.py` is disabled and writes no TIFF. Old `ready_to_submit`, “unique,” “valid,” exploratory-upload, or projection wording must not be treated as current approval.

The ledger-model projection is retained only in archived evidence for reproducibility and is marked `NOT_A_SCORE`; current-facing summaries suppress it. No estimate is published because there is no validated mapping from the legacy holdout to the hidden leaderboard.

## Technical and provenance limits

- The local preflight applies the required two-sided `abs(Spearman) > 0.90` stop. The vendored/shared uniqueness helper still has a one-sided rank gate; no private fork was made. That upstream defect needs maintainer resolution.
- The local historical uniqueness audit excludes registry entries it cannot classify under its processing guard; those entries now make `U3_literal_scope_complete=false` and cannot pass. The literal rule must not silently ignore large/continuous rasters or rely on a lattice/null exemption.
- Some historical shared data came from a peer-maintained GitHub mirror. Pinned hashes establish byte consistency, not organizer origin, completeness, official-grid conventions, or current-label leakage clearance.
- The official competition pages, rules, submission portal, and current public leaderboard were not re-fetched in this review. Account quota, portal field names, and organizer acceptance are unknown.
- Old LST1 work exceeded its stated three-experiment/two-hour budget. This is historical disclosure only; it does not grant a new budget or permission to cross the current stop.
- Repository hypotheses are proposed options, not an assigned method lane. Anonymous `band01`–`band19` identifiers do not establish geophysical semantics; no new-feature experiment is justified by the current evidence.

## Protocol-owner / upstream actions required

1. Resolve explicitly whether the literal registry stop applies to every positive pixel in continuous/dense registry rasters, how the witness should be classified, and what registry is authoritative. Any exception or support definition must be approved and preregistered; do not infer one from a failed candidate.
2. Correct the shared uniqueness package's signed-correlation check and clarify how registry raster roles are represented. This repository did not patch or fork shared code.
3. Only after the stop is lifted may an authorized lane use the unchanged shared feature stack, hide whole fault segments with a buffer, derive catalog features from visible faults only, run feature-only leakage canaries, evaluate pooled DTI under `gems57-pooled-hide-v2`, and use the shared writer.
4. Report performance only as `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` with an organizer receipt. Keep slot selection separate.

## Reproducible safe checks

```bash
.venv/bin/python -m pytest -q
python scripts/build_site.py && python scripts/check_site.py
bash scripts/restore_shared_data.sh --template-only
bash scripts/restore_shared_data.sh --dry-run
```

Do not invoke `scripts/build_submission.py`, old holdout scripts, `scripts/finalize.py` to create a new run, or any slot selector until the blocker is explicitly resolved. The old evidence is preserved for audit; it is not a current candidate.
