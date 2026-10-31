"""GEMS release pipeline: catalogue-independent structural fault detection.

Design contract (verified against official sources; see ``SOURCES`` in
``gems_release.shared``):

1. Every scored pixel is either *catalogue-masked* or active
   (DrivenData staff, forum topic 11516, post 2: "Pixels corresponding to known
   USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not
   count towards penalty terms.").
2. The public leaderboard is a single pooled distance-weighted Tversky index
   over the public subset (staff, forum topic 11550, post 2).
3. No feature used for scoring is derived from the fault catalogue. The
   catalogue is used only (a) as supervised training labels under spatial
   blocking and (b) as the masking/collar geometry that the official scorer
   applies. This keeps the holdout honest: the model cannot learn "predict
   near a known fault".
"""
