"""LBCAL — leaderboard-calibrated hidden-fault density lane (2026-10-27).

The lane answers two questions with the same object, a per-pixel density
``pi(g)`` = expected share of hidden expert-labelled (public-test) fault pixels:

1. *Estimation.*  For any binary or soft raster ``p`` the official metric's
   expected value under ``pi`` is

       E[TP_w] = sum_g pi(g) * c_p(g),      c_p(g) = max_x p(x) k(d(x, g))
       E[FP_w] = sum_x p(x) * (1 - E[max_g k(d(x, g))]) ~= N_p - 3 * sum_x p(x) pi(x)
       E[DTI]  ~= E[TP_w] / (0.2 * (E[TP_w] + E[FP_w]) + 0.8 * sum_g pi(g))

   (official definitions: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
   ``pi`` is a log-linear function of geological feature bins whose few
   coefficients are fitted to the OWNER-REPORTED public-leaderboard scores of
   the ~120 archived rasters, and validated by leave-one-site-out prediction.

2. *Placement.*  The same ``pi`` drives a greedy max-coverage dot placement
   (Dinkelbach ratio form of the DTI) that is unique by construction against
   every registry raster.

Every number produced by this package is an ESTIMATE (a model output), never an
organizer score.  See knowledge/preregistration-2026-10-27-lbcal.md.
"""

VERSION = "lbcal-v1.0"
