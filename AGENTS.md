# Working agreement

At the start of every session, read the **Standing user brief and operating constraints**
in `README.md`, then read `PROJECT_PROMPT.md`, this file, `knowledge/protocol.md`,
`knowledge/hypotheses.md`, the latest review in `knowledge/review-c1e656ce.md`, its run card
in `evidence/session_c1e656ce_run_card.json`, and `docs/data/release_gate.json`. Review
historical lane cards only when relevant; a lane's local `promote` label never authorizes a
repository-wide release.

The current repository decision is **DO-NOT-SUBMIT**. The checked-in authority/candidate
cards evaluate to the negative `gems-release-gate-v1` gate. The positive v2 site files and
claiming builders were stale and have been retired; the root site must be rebuilt with
`scripts/build_site.py` and checked with `scripts/check_site.py`. Never weaken the release
gate or restore a positive page to satisfy a download request.

Preserve the literal stop: if pre-placement surface rank correlation with any registry
raster exceeds 0.90, or more than 70% of final dots lie within 3 px of any one registry
raster, record a duplicate and stop. No dense-raster/content-aware exemption is authorized.
The currently recorded mirrored witness is conditional evidence, not a complete or
organizer-authenticated registry audit; disclose both facts without waiving the stop.

Use the template's cached feature stack, shared `evaluate_holdout.py`, and
`submission_writer.py`; do not maintain a private evaluator/writer fork. Holdout must hide
whole buffered fault segments, derive catalogue features from visible faults only, mask
visible faults pixel-exactly, and score pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
Test each feature alone for leakage; AUC >0.90 is a warning until resolved. Label score
values only as `HOLDOUT-DTI` with evaluator version, withheld-positive count and 95% CI,
or `ORGANIZER-CONFIRMED` with a receipt. Historical claims are `OWNER-REPORTED`;
projections are never scores.

End a run with one JSON card containing the requested hypothesis, mechanism, named
non-fault mimic, holdout/CI, registry comparisons, raster hash, exact-byte validator
output, submission name/note (≤140 chars), and `promote` or `negative` verdict. Record
missing results as null/`NOT RUN`. Negative is a valid deliverable. Stop after 3
experiments or 2 hours, do not select or spend a competition slot, and let the separate
selector check the live weekly cap. No upload or automated DrivenData access is claimed;
credentials and the competition data cache are absent.

The stored mirrored feature stack, labels, sample file and cache are not present in this
checkout (only `data/template_grid.tif` is tracked). Hash-pinned GitHub mirrors are not
authenticated organizer downloads. The assigned method paragraph is not identifiable.
Do not run a model, invent a candidate, or claim a holdout while these blockers remain.
Keep large data in ignored caches. Review current generated HTML/data together with its
source cards; do not trust a stale page merely because it exists in `docs/`.

Keep **Maximize P(Win)** and **Own the Outcome** central: act autonomously where safe,
weigh evidence and risk, and report blockers rather than fabricating a route around them.
The user requested multiple review passes, a pull request, and a merge. Stay on the fixed
Arena branch; open a PR from it and follow the explicit merge controls if the changes are
ready. The branch name is fixed and must not be changed.
