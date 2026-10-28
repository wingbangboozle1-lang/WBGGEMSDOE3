# Repository review — 2026-10-28 UTC

## Outcome

This was a review and verification pass, not a new modeling lane. No experiment,
submission slot, or organizer submission was used. The repository's current
release decision remains **DO NOT SUBMIT**. No new TIFF is cleared for download
or upload. The highest owner-reported GEMSDOE32 number (0.2778) is not an
organizer-confirmed receipt in this checkout, and it must not be represented as
a current-score estimate.

## Pass 1 — inspect implementation and evidence

- Confirmed branch `arena/979ea466-wbggemsdoe3`, initially clean.
- Read the README, reconstructed standing brief, run cards, active-lane
  irregularities, and the submission inventory.
- Confirmed the release gate at `docs/data/release_gate.json` says
  `DO-NOT-SUBMIT`; the current top-level run card is negative and records no
  candidate, no score, and zero slots used.
- Confirmed existing historical and lane TIFs are not implicitly eligible just
  because local format checks passed. The registry witness blocks the literal
  uniqueness rule; prior lanes also have experiment budgets exhausted.

## Pass 2 — run checks and inspect likely failure paths

- `python scripts/build_site.py` completed successfully.
- `python scripts/check_site.py` passed after the build, including the negative
  gate, source hashes, witness, research bytes, status consistency and local
  links.
- Initial `python -m pytest -q` could not start because system Python does not
  have pytest installed. Direct system-wide installation was correctly
  rejected by PEP 668; no system packages were changed.
- Created the ignored project virtual environment and installed the declared
  `requirements.txt`. Full suite result: **223 passed, 4 skipped** in 8.20 s.
  Rasterio emitted 72 `PendingDeprecationWarning`s from the installed library;
  no test failed.
- Site build regenerated no tracked changes. `.venv/` remains ignored.

## Pass 3 — compare against the standing request and constraints

- The nine-site executive table exists in `README.md` and the site page. It
  treats submitted values as owner-reported, leaves a new-score estimate
  unestimated, identifies historical overlap, and explicitly says not to
  submit. This is more defensible than fabricating scores or claiming an
  organizer receipt.
- The research-only download links and submission instructions remain
  distinguishable from an approved submission. No candidate is promoted.
- The requested geological hypothesis experiments cannot ethically be run in
  this review: the current branch records the literal duplicate-stop and prior
  lane budgets are spent. The current turn did not identify a valid remaining
  method paragraph/lane. Starting a new model would violate the stated lane
  protocol.
- Pull request/merge was not attempted. There are no implementation changes to
  propose or merge; the active branch must not be switched, and a no-op PR
  would not improve the project.

## Reproduction

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

## Open blockers / next safe work

1. Resolve the conflicting interpretation of registry overlap and footprint
   support in the shared protocol. Do not weaken the duplicate rule silently.
2. Obtain authenticated competition data / submission receipt access if
   needed; mirrored public data can verify bytes but not organizer provenance.
3. Reconcile outside-footprint encoding with the authoritative submission
   specification and an actual organizer response.
4. Have the independent selector authorize a fresh lane and budget before
   preregistering any new experiments. Require a leakage canary, spatially
   blocked hide-and-recover, registry-wide uniqueness checks before and after
   placement, and byte-level validator evidence before any upload.
5. Refresh the live leaderboard and site feed only through the documented
   read-only updater; treat leaderboard entries as observations, not local
   model estimates.
