# Repository review — 2026-10-27 UTC

## Decision: negative / no submission cleared

The repository contains several incompatible generations of status artifacts. The current governing `evidence/run_card.json` is a **negative prerequisite stop**: it reports that the literal registry witness is positive on every allowed footprint cell, implying 100% directed 3-pixel overlap for any nonempty candidate. Per the standing protocol, this is a duplicate stop. It records zero experiments, no candidate raster, no canary, no holdout, and no validator result for a new candidate. No weekly slot was used.

That current stop conflicts with:

- `README.md`, which opens with “CURRENT DECISION: SUBMIT,” a 0.428 estimated leaderboard value, and download directions;
- `docs/index.html` and `docs/executive-summary.html`, which advertise the legacy skarpline file as cleared;
- `docs/data/run_card.json`, `docs/data/gemsdoe_run_card.json`, and `evidence/gemsdoe_run_card.json`, which preserve earlier positive decisions;
- the HCE-1 lane, which applies a content-aware interpretation of the uniqueness gate and reports a positive holdout result, while the literal protocol still fails.

The point estimate 0.428 is not an organizer-confirmed score. The historical score claims lack a submission-page receipt tied to the exact TIFF bytes. Earlier positive verdicts do not override the current negative card or the user's literal threshold. Existing TIFs remain historical/research artifacts; this review does not approve them for download-and-submit.

## Requested focus-site comparison

The user-provided leaderboard figures can be recorded as **unverified owner-reported claims**, not as organizer-confirmed values. Within the nine requested sites, the supplied maxima are GEMSDOE24 0.2477, GEMSDOE25 0.2600, GEMSDOE27 0.2449 (but later entries report 0.2250 and 0.2190), GEMSDOE28 0.2710, GEMSDOE30 0.2600, GEMSDOE31 0.2708, GEMSDOE32 0.2778, GEMSDOE33 0.2632, and GEMSDOE36 0.2750. The most repeated support pattern is a closely related dotted mask; the repo's pinned raster audits report near-total 3-px overlap among key 31/32/36 submissions. These observations explain why a minor re-trim can alter measured competition results without evidencing a new geological detector, but do not establish causal scoring effects.

No reliable expected leaderboard score is estimable from the repo evidence: historical entries are repeated/dependent placements, the score provenance is incomplete, and the requested compliant holdout was not run for the current lane. Do not promote 0.428 or any earlier estimate as a score. Per site, the existing historical files are available as research artifacts, but none is approved as a new unique submission under the unmodified rule.

## Hypotheses and execution constraints

The candidate hypotheses are already ranked in `knowledge/preregistration-2026-10-27.md` (CSPES lane) and `knowledge/hypotheses.md`. CSPES did run in a prior parallel lane and was negative (HOLDOUT-DTI 0.02565, 95% CI 0.01937–0.03192, evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives); the paired difference against its matched incumbent was −0.07355 (95% CI −0.08832 to −0.05866). It should not be represented as a path to a high-score submission. Current run-card evidence says the present session did not run a geological experiment.

A requested new TIFF cannot responsibly be produced while the unchanged user protocol mandates stopping on the universal witness, forbids choosing a slot, and requires pre-placement comparison. Creating a TIF that violates this gate, silently redefining the comparator set, or changing a filename is not an acceptable substitute. The scientific data/metadata provenance and exact shared evaluator/cache contract also require reconciliation before another run.

## Verification performed

- `git status --short --branch`: clean at review start; branch is `arena/d8f258ff-wbggemsdoe3`.
- Read the repository working agreement, protocol, preregistrations, current run cards, README and generated landing/summary pages.
- `python -m pytest -q`: could not run because pytest is not installed in the sandbox (`No module named pytest`). No dependency installation or test pass is claimed.
- No network source was fetched in this review; no external assertions are newly verified.
- No files or scores were generated, no weekly slot was used, and no organizer submission was made.

## Next work, in order

1. Resolve the universal-raster overlap conflict by an explicit authorized protocol amendment; do not treat the rule as vacuous/exempt unilaterally.
2. Reconcile current `evidence/run_card.json`, historical `docs/data/*run_card.json`, HCE lane status and the README/site so a single decision is shown everywhere.
3. Confirm data/channel provenance and one shared evaluator/version/cache, with genuinely fold-local feature reconstruction and a paired comparable incumbent.
4. Only after the protocol permits proceeding: use at most three experiments/two hours; canary each feature; run whole-segment buffered holdout; test surface and final dots against the entire agreed registry; validate saved TIFF bytes.
5. A separate selector must check current portal cap and usage. No uploader or account access is available here.

Official references for manual review (not fetched in this review):

- Competition overview/rules: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN data release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
