# Working agreement

**Latest (2026-10-31):** read `knowledge/review-2026-10-31-session.md`, `evidence/twr1_run_card.json`, and the 2026-10-31 protocol revision in `knowledge/protocol.md` first. A unique, validated, uniqueness-passing candidate TIFF is published for research but FAILS the holdout promotion bar — still DO NOT SUBMIT / no slot. Prior: 2026-10-29 gate recheck (`knowledge/review-2026-10-29-session.md`).

At the start of every session read `README.md`, `PROJECT_PROMPT.md`, the latest
`knowledge/review-2026-10-28-session.md` and
`evidence/session_7393d521_run_card.json`, `knowledge/preregistration-2026-10-28.md`,
`evidence/preregistration_2026-10-28.json`, `evidence/official_source_check_2026-10-28.json`,
`knowledge/protocol.md`, the earlier preregistrations/reviews listed below, and the
pinned source/lane cards required by the repository history. The repo is the source of truth.

## Current project-wide decision

**DO NOT SUBMIT. No file is cleared; this review generated no candidate.** GitHub `main`
advanced while this branch was in progress with PR #53, which added a 15,000-dot blind-basin
TIFF under `docs/downloads/`. This review did not generate or use it as a candidate, and did not
assess scientific or format eligibility; its bytes were only matched to the upstream-reported
SHA-256 for archive identity. It is quarantined as a pre-existing research artifact and is not
cleared. The 2026-10-28 evidence-first
review recorded a literal-registry stop: a registered, hash-pinned owner-mirrored raster is
positive on all 5,167,373 cells of the mirrored
sample footprint. Under the committed finite-and-positive support definition, every
nonempty in-footprint dot map would have 100% directed overlap at distance zero, above
the user's 70%/3-pixel stop. This is a conditional owner-mirror measurement—not proof
of organizer provenance or complete portal-registry coverage—but it must be honored
under the current literal protocol. Do not build a candidate, run a holdout, or select a
slot unless a documented evidence-based correction resolves the stop. Never waive the
threshold or silently exempt the dense witness.

Do not present owner reports, projections, holdout results, raster measurements, or
format checks as organizer-confirmed scores. An `ORGANIZER-CONFIRMED` score requires an
actual verified submission receipt. Do not upload files or select a weekly slot from a
research lane. The separate selector owns any real final-slot decision.

## Scientific and release protocol

- Remain in the assigned single method lane. Before placement, check surface rank-correlation; stop if absolute rank correlation exceeds 0.90. After placement, stop/log a duplicate if more than 70% of final dots fall within 3 px of any registry raster.
- Reuse the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not fork shared tools. The pinned template bootstrap is in `src/gems_project/template.py`. The shared cache/runtime is not present in this checkout until restored and verified.
- Hold out whole fault segments with a buffer; derive catalogue-based features only from visible faults; pixel-exactly mask visible faults; use pooled DTI (α=0.2, β=0.8, 300 m triangular kernel). Test each feature alone for leakage; AUC >0.90 is leakage until proven otherwise.
- Label every actual score `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` only from a receipt. A projection is never a score.
- End a research run with one JSON card containing hypothesis/mechanism/non-fault mimic, holdout and CI, surface correlation/final overlap, raster SHA-256, validator results, submission name/note (≤140 characters), and `promote` or `negative`. A negative result is a complete deliverable; null fields must remain null when no run occurred.
- Maximum three geological experiments or two hours, whichever comes first. Do not select a real submission slot. Promotion is a separate selector step subject to the official three-per-week limit and one-final-submission rule.
- Retain the user values **Maximize P(Win)** and **Own the Outcome**. Be autonomous on safe evidence and engineering work; do not let urgency override the duplicate, provenance, or experiment safeguards.

## Site/build contract

`scripts/build_site.py` is the only active project-level site generator and always publishes a
hash-bound negative decision for the current review. `scripts/check_site.py` must fail closed
against positive/stale approval. `scripts/build_site_v3.py`, `scripts/build_release_gate_v2.py`,
and `scripts/build_evidence_page.py` are blocked retired positive paths; do not revive them.
The FCHD and AMDC renderers may only update their scoped negative archive pages. Do not copy
historical TIFFs as new submissions. All files in `docs/downloads/` are research archive only;
the top-level downloads index intentionally provides no direct TIFF link.

The official DrivenData format page says outside-bounds cells must be null or NaN. Do not
claim finite-zero outside is compliant. The current official homepage and September 2026
rules PDF disagree on the effective deadline; see `evidence/official_source_check_2026-10-28.json`.
The unauthenticated submission/data pages redirect to login, so account quota, organizer data
access, and receipts are unknown. Hash-pinned mirrors prove byte identity, not organizer origin.
Keep large datasets in ignored caches.

## Required historical reads

Read `knowledge/repo-review-followup-2026-10-28.md` and `evidence/repo_review_followup_2026-10-28.json` as an earlier 2026-10-28 release audit; it is historical and is superseded by the current review where they differ. Also read `knowledge/preregistration-2026-10-28-blind-basin.md` as an untested historical idea, not a selected lane. Read `knowledge/session-review-9b794637.md`,
`evidence/session_9b794637_run_card.json`,
`evidence/registry_witness_recheck_2026-10-27.json`,
`knowledge/preregistration-2026-10-27-9b794637.md`,
`knowledge/protocol.md`, `knowledge/preregistration-2026-10-27.md`,
`knowledge/review-passes-2026-10-27.md`, `knowledge/preregistration-2026-10-26.md`,
`knowledge/review-and-irregularities-2026-10-26.md`, `research/REVIEW.md`,
`evidence/session2_run_card.json`, and `evidence/run_card.json` before changing
historical interpretations. For the LBCAL lane also read
`knowledge/lbcal-findings-2026-10-27.md` and `evidence/lbcal_lane_decision.json`.
