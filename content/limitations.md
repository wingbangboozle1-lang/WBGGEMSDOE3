# Limitations and next steps

- **No eligible TIF.** Under the literal finite-positive, within-3-pixel rule, a pinned
  registered probability raster is positive at all 5,167,373 mirrored footprint cells.
  Any nonempty in-footprint candidate overlaps at 100% and must stop. The two historical
  LST1 TIFFs actually measure 100% overlap. Do not introduce an exemption without an
  explicit protocol revision. [Proof and audit](../evidence/focus_audit.json).
- **No confirmed competition score.** The nine site values are historical owner/user
  claims without receipts linking uploaded bytes. The repositories have advanced, so
  their current best files and scores are unverified. Public leaderboard standings are
  dated observations of other participants, not a score for this project.
- **No validated holdout this session.** Historical LST1 results used fixed historical
  rasters plus full-catalogue-derived bins/canaries, so a truly fold-local evaluation is
  unproven. Its projection is not a score and must not be used for promotion.
- **Format ambiguity.** One-band float32, matching sample grid and [0,1] values are
  necessary. The organizer says outside bounds null/NaN while the shared writer emits
  unmasked zeros outside the mirrored finite footprint; the meaning of bounds and portal
  behavior are unresolved. Do not claim to know why the earlier range error occurred.
- **Data provenance.** The sample, labels and cached bands are hash-verified public
  mirrors, not authenticated organizer downloads. The public official data tab requires
  login. GeoDAWN and 3DEP/GDR source descriptions were checked, but the necessary raw
  AOI downloads and band semantics still require verification.
- **Process.** Reconcile the shared tool upstream, freeze a single lane and full current
  registry, rebuild catalogue-derived features within hidden-segment buffered folds,
  run per-feature AUC canaries, matched-baseline shared holdout and literal final gates,
  then leave any slot selection to a separate step with current quota.
