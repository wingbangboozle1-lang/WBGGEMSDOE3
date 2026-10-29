# Session review — 2026-10-29 · the dense-witness stop is a definition artifact

Branch `arena/b0600e4e-wbggemsdoe3`, based on `main` at `85f9ce9`.

## Decision

**Governing decision unchanged: DO-NOT-SUBMIT.** No candidate TIFF was generated, no holdout was run,
no weekly slot was used, and no file is cleared for download or upload. Every TIFF in `docs/downloads/`
remains research archive only.

Why no candidate was built: the release gate (`docs/data/release_gate.json`) says *"Do not build a
candidate, run a holdout, or select a slot unless a documented evidence-based correction resolves the
stop. Never waive the threshold or silently exempt the dense witness."* This session tested whether such
a correction exists. It found a real definitional problem, but the fix changes the protocol, so the owner
must approve it. This session does not approve it.

## What was verified (measured, reproducible)

Script: `scripts/check_witness_definition.py` → `evidence/witness_definition_check_2026-10-29.json`

| Check | Result | Source |
|---|---|---|
| Witness bytes | sha256 `ab0a0a62…3872be` matches registry and the pinned commit | <https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif> (fetched via codeload archive) |
| Grid | EPSG:32611, 3730×3292, 100 m, transform (100, 0, 243350, 0, −100, 4508550) | same file |
| Finite cells | 5,167,373 finite; 7,111,787 NaN outside | same file |
| Value range | 0.000463 to 0.984116 (soft probability) | same file |
| Literal "dots" (value > 0) | 5,167,373 = **100.0%** of finite cells | repo rule `scripts/session2_registry.py` |
| Probability > 0.5 | 728,137 cells (14.1%) | same file |
| Probability > 0.9 | 14,054 cells (0.27%) | same file |
| Top-37,654 cells | threshold 0.8438 | same file |
| Registry recount | `n_dots` 5,167,373 matches `registry/registry_session2.json` | same file |

The embedded per-file JSON (`17GEMSDOE_E-proba-multiscale_20260930T044527Z.json`, same commit) describes it as
`soft probability output`, `NaN outside footprint`, `value_range` 0.00046 to 0.98. That is a probability surface.

## Irregularities for review

1. **Code contradicts gate.** `scripts/session2_registry.py` line 83 says *"Space-filling continuous fields
   (e.g. the 17GEMSDOE witness) are not 'dots'"* and labels it `comparator_class: dense`. The same
   registry then uses "value > 0" as dots for every raster, so the dense witness becomes a universal
   blocker. The code comment and the gate disagree.
2. **Lattice blocker is independent of the witness.** `evidence/uniqueness_gate_full_2026-10-28.json`: the
   invdesign candidate has 3-px directed overlap 0.9944 with the 13GEMSDOE r13 lattice (free fraction of
   footprint 0.14%), 0.8166 with GEMSDOE23 h30 habitat, and 0.7178 with GEMSDOE46 r11f. Three comparators
   exceed 70%. Fixing the witness alone would not clear any candidate.
3. **Leaderboard figures in the brief do not match the saved observation.** The brief says top is 0.4413 and
   the highest is 0.3195. `evidence/leaderboard_observation_2026-10-28.json` records rank 1 = 0.4544
   (xiaofanhu), rank 2 = 0.3916 (team not captured), rank 25 = 0.3217, rank 26 = 0.3195 (kpomazi). **Could not re-check today:**
   `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/` returned HTTP 000 from this
   sandbox (outside the allowed hosts).
4. **Outside-footprint encoding.** The DrivenData format text says null or NaN outside bounds. The local
   zero-outside policy in older run cards is not compliant with that text. `knowledge/session-review-2026-10-28-uniqueness.md` and
   `evidence/session_7393d521_run_card.json` already flag this. Unresolved.
5. **Deadline conflict** (unchanged): homepage 2026-12-03 23:59 UTC vs rules Appendix A.1 5:00 p.m. ET.
6. **Access.** `drivendata.org` returned HTTP 000; `raw.githubusercontent.com` is outside the allowlist, so the
   witness was fetched through `codeload.github.com` instead. The DrivenData submission and data pages cannot be
   read from this sandbox, so the account quota, the file upload format, and any receipt remain unknown.

## Options for the owner (decision needed before any candidate)

- **A. Keep the literal rule.** Result: no file is ever cleared under the current registry. Honest, but no
  submission is possible.
- **B. Fix only the witness definition** (dots of a continuous surface = top-N or ≥0.5 cells). The lattice
  (0.99) and two other comparators (0.82, 0.72) still block the invdesign candidate under the literal
  70% rule. Result: still no clearance.
- **C. Exclude dense and lattice comparators** (the earlier 2026-10-28 convention, with the stated reason).
  Result: a candidate could pass the uniqueness gate, but still needs a shared-tool holdout with
  HOLDOUT-DTI, a CI, and the outside-encoding decision (item 4) before any upload.

This session recommends **B followed by a fresh uniqueness audit with the lattice class reported
separately** (not silently dropped). Whichever option is chosen, the owner must record it in the protocol.
The user's own rule (>70% of final dots within 3 px) stays in force.

## Not done in this session (honest limits)

- No candidate, holdout, validator run, or slot selection.
- No organizer receipt. Owner-reported scores (24: 0.2477; 25: 0.2600; 27: 0.2449; 28: 0.2710; 30: 0.2600;
  31: 0.2708; 32: 0.2778; 33: 0.2632; 36: 0.2750) remain OWNER-REPORTED / UNVERIFIED.
- No estimate is written as a score. The executive summary keeps "Not estimable" for every site.
- The 0.2778 explanation (`content/why-0.2778.md`) is unchanged; it remains a mechanism hypothesis.
- No new hypothesis was added. The five preregistered hypotheses (H1–H5) are still untested.
