# Session review — RFL lane + selector correction (`arena/bd44f94b-wbggemsdoe3`, 2026-10-27)

Three passes were run as instructed. Pass 1: E0 focus-9 audit + preregistered RFL lane
(E1 canary, E2 holdout). Pass 2: reproduce the skarpline estimate from code, one-calibration
estimates for every candidate, 118-file evaluator-ranking measurement, full-registry
uniqueness re-audit — which found the skarpline uniqueness failure (IR-20) and the estimate
model's physical-cap violations (IR-21). Pass 3: corrections wired durably into the site
generator (banner + downloads page), independent saved-byte validation of the recommended
file, protocol run card, tests, full test suite.

## Headline measured results (all labels per protocol rule 3)

- **Focus-9 are one family.** All 36 pairwise leader comparisons >70% within 3 px both
  directions (min 86.7%); GEMSDOE25 ≡ GEMSDOE30 identical support; 32 ⊂ 31 ⊂ 25/30; 32 ⊂ 36;
  24 ⊂ 27. B2 anatomy re-verified byte-exact (2,545 dots at 1.414–2.0 px from catalogue removed,
  0 added). `evidence/rfl_focus9_audit.json` (closes IR-17).
- **RFL lane: negative.** Canary pass (max AUC 0.594). HOLDOUT-DTI 0.0538 [0.0437–0.0642]
  (`GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld) vs champion proxy 0.0992 [0.0860–0.1127],
  paired Δ −0.0454 [−0.0554–−0.0356]; vs random null +0.0225 [0.0121–0.0331]. Final dots breach
  uniqueness (0.709 vs GEMSDOE22 h23-b; lattice-like excess +0.079 vs pindrop-nodes). E3 not run
  (preregistered reach condition failed). No TIF packaged. `evidence/rfl_run_card.json`.
- **Skarpline estimate reproduces exactly** (0.4284, |G|=15,672.5) **but** its uniqueness claim
  does not survive the full registry (0.735 GEMSDOE23 h30; 0.724 GEMSDOE50 h59) and the model
  implies 96% capture of all hidden faults (LOO RMS ±0.096). Decision superseded in README,
  site banner (`scripts/rfl_banner.py`) and downloads page.
- **HCE-1 is the only fully-gated file:** format PASS on bytes re-read here
  (`evidence/rfl_recommended_validation.json`), 120-mask uniqueness PASS (0.524 / ρ 0.325),
  fold-local HOLDOUT-DTI 0.1292 (lane-run; evaluator replicated bit-for-bit on static files:
  champion 0.0992, CSPES 0.0257, HCE static 0.0931 all match prior run cards).
  Leaderboard expectation unresolved across models (0.082 ridge / 0.104 prevalence-calibrated /
  gemsdoe point 0.439 discarded as >0.316 physical cap).
- **Evaluator trust (n=118 owner-scored, byte-verified):** Spearman vs owner-reported =
  static holdout +0.172, SGMC h +0.341, SGMC proxy DTI +0.453, calibrated estimate +0.419.
  Static holdout is structurally biased against full-catalogue-pruned files (champion-family
  static scores 0.0045–0.0967 track pruning radius, not owner scores).

## Why 0.2778 (answer recorded on the site)

Plausible mechanism: ≤2 px catalogue-halo pruning raises credit-per-mass under the masked-100 m,
300 m-kernel DTI. Not established: +0.0070 has no receipt; H6-1 measures pruning at +0.00005
(±0 vs random). Family spread 0.2449–0.2778 mostly tracks mass/hit-rate. Beating it is possible
in principle (public top 0.4544 observed 2026-10-27) but unproven for any artifact here.

## Limitations / what I could not do (explicit)

- No DrivenData auth: cannot upload, cannot see weekly cap or receipts, cannot fetch organizer
  bytes. All inputs are SHA-pinned owner mirrors (byte identity only, IR-06).
- Outbound network is GitHub/package-registries only: USGS/GDR/DrivenData pages could not be
  re-fetched from bash this session; leaderboard figure used is the repo's 2026-10-27 snapshot.
- 3 GB RAM / 2 CPU sandbox: full 522-file registry rebuild not attempted (151 restorable files /
  120 masks audited; coverage stated everywhere the number is used).
- HCE fold-local holdout (0.1292) is lane-computed, not recomputed from its training code here;
  I verified the shared evaluator and its static-file value bit-for-bit instead.
- Recommendation is a *selector recommendation*, per protocol rule 6 — no slot spent, no upload.

## Suggested next work (priority order)

1. **Human selector:** spend one capped slot on the HCE-1 file to obtain the project's first
   ORGANIZER-CONFIRMED receipt; record it in `registry/`. Every estimate model currently
   disagrees mainly for novel supports — one receipt calibrates them all.
2. Preregister the **piedmont-gated relief** variant (RFL ablation 0.0633, highest holdout of the
   RFL family) or manifestation-alignment lane (#2 in the RFL preregistration) as a fresh lane
   with fold-local placement designed against the 120-mask registry from the start.
3. Rebuild the full 522-file registry (`.cache/sites`) so uniqueness coverage stops at no caveat.
4. Reconcile IR-22 (validation.py −0.15 claim) by re-running that lane's exact holdout protocol.
5. Portal micro-test (IR-14/15): one zeros-outside all-finite upload on an authenticated account
   remains the only way to close the [0,1] error question — item 1 does this for free.
