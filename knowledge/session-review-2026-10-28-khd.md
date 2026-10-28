# Session review — KHD lane (2026-10-28)

Scope: explain GEMSDOE32 B2's 0.2778 with a byte-exact chain; generate a brand-new
unique TIF with an obvious ready-to-submit status; executive summary for the nine
focus sites; run card; PR + merge. Branch `arena/7702e9ff-wbggemsdoe3`.

## What ran (3 experiments + 2 shared-tool fixes, within the 2-hour budget)

| ID | Design | Result |
|---|---|---|
| E1 | `scripts/khd_emit.py --scan` coverage-gain greedy on ρ̂ (LST NNLS × tri-domain concordance), caps 0.64 | **negative (instrument):** allocated 0 at 34k/37,654/41k. Two root causes, both reproduced on synthetic probes |
| E1-A1 | same emission + disclosed 25% hedge mass outside the 4 identified strata (amendment A1, prereg) | **positive (construction):** budgets fill at all three sizes; LEDGER-PROJECTION 0.364–0.366 (in-sample optimistic); uniqueness gates pass |
| E2 | paired hide-and-recover, identical folds: KHD vs byte-exact B2 vs strata-shuffled control | **negative (preregistered gate):** HOLDOUT-DTI KHD 0.00006 [1.7e-5, 1.1e-4] vs B2 0.00452 [0.00382, 0.00526]; paired Δ −0.00446 [−0.00522, −0.00375]; control 0.00001 (KHD = 6× control) |
| E3 | budget sensitivity | bundled in E1-A1; flat (0.3652 / 0.3655 / 0.3641) |

Shared tools fixed once (no forks):
1. `src/fchd/registry_full.py` post-guard: multi-violator cascade deletion replaced by a
   ≤50% removal floor + `residual_cap_violation` disclosure (irregularity IR-KHD-02).
2. `scripts/fetch_peer_prompt_rasters.py`: disclose-and-continue on missing pins
   (irregularity IR-KHD-01 — two GEMSDOE92 files 404 at the pinned commit).

## The scientific finding of this session

The 112-probe ledger identifies hidden-truth mass Ê|G| ≈ 9,150 cells concentrated in
strata **far from the mapped catalogue** (bins 32/43/48/56 of catalogue-distance ×
network-distance; only bin 43 carries off-network mass). Every fold-legal local holdout
constructs its withheld truth from catalogue segments — i.e. exactly the zones where
the family's dots live and where the ledger says the hidden truth is NOT. This
explains, mechanically, the measured anti-correlation between catalogue-holdout DTI and
owner-reported scores for this family (Spearman −0.146 family-level / −0.849 AMDC
bytes-level): **the holdout cannot rank this family, only detect leaks.** KHD's near-zero
holdout score alongside a projection at or above B2 is the predicted signature of a
far-from-catalogue placement, not evidence the file is bad — nor proof it is good.

## Honest score statement

- LEDGER-PROJECTION 0.3655 — ESTIMATE, in-sample optimistic (the candidate was allocated
  against the model's own support). Upper anchor only.
- Class anchor (owner-reported uniqueness-constrained designs): 0.2296–0.2478.
- **Headline ESTIMATE: 0.275, band 0.23–0.31** — straddles B2's 0.2778. No organizer
  receipt exists; nothing here is a score.
- The preregistered promotion gate (holdout beat + positive paired CI) is **negative**;
  run-card verdict `negative`. The file is nonetheless released as the lane's unique
  deliverable per the user brief; slot promotion is the selector's call.

## Limitations and remaining work (next session)

1. **Instruments cannot rank placements for this family.** Build a fold-legal placement
   instrument whose withheld truth is off-catalogue (e.g. synthetic fault injection into
   geological-plausible ridge segments), or accept ranked uncertainty bands.
2. **Strata identification is confounded** by the family's own placement correlation
   (probes live at h_code 0/1 by construction). Independent strata probes (H2/H3 designs)
   would de-confound the LST.
3. **H2 (tip-linkage relay corridors)** and **H3 (radiometric alteration-cap vent
   habitat)** remain untested. They target off-catalogue truth directly and are the only
   plausible routes to >0.2778 for a unique submission.
4. **Evidence gaps:** no DrivenData auth (mirror provenance, IR-06); two peer pins gone
   (IR-KHD-01); leaderboard snapshots conflict (0.3195 / 0.4413 / 0.4544 — IR-KHD-04).
5. **Do not resubmit** SGCE bytes (dense-witness flag, 100% overlap at 0 px) or any
   `-nan`-encoded file (portal rejects values outside [0,1]).
6. Web research was limited by sandbox egress (GitHub + package registries only);
   geological priors in the hypotheses come from the archived sources in
   `knowledge/deep-research-2026-10-27.md`, not fresh browse.
