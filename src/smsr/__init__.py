"""SMSR -- Seismogeodetic Missing-Shear Ridge lane.

Hypothesis (preregistered, see knowledge/preregistration-2026-10-28-smsr.md):
Walker Lane GPS geodesy records dextral/oblique shear-strain rates that are
not fully matched by the mapped Quaternary fault slip budget (Bormann et al.
2016, *Geology* 44:535 -- "missing shear" across the central Walker Lane).
Where the training stack's geodetic strain-rate second invariant
(``geod_2ndinv``) forms an *elongated, anisotropic* ridge -- not an isotropic
bullseye, which is the signature of a fluid-production/injection bowl rather
than a tectonic structure -- and where instrumental seismicity
(``deq_n100a15``, ``ieq_n100a15``) independently corroborates it, the
catalogue-masked gap is a candidate site for an unmapped structure.

This lane only adds three new geophysical planes to the shared, pinned
``gems57`` fault-zone-anatomy pipeline (``cell_geometry`` / ``fit_model`` /
``canary`` / ``run_cell`` / ``evaluate_holdout``). It does not fork any shared
evaluator, holdout, writer or metric file.
"""
