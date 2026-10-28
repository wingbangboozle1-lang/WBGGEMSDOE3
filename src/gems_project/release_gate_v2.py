"""Gate-based release decision (v2) for the LBCAL-K candidate.

Decision rule (preregistered 2026-10-28, knowledge/preregistration-2026-10-28-lbcalk.md):

* **SUBMIT** (download + submit readiness) requires the run-card verdict
  ``promote``, i.e. core gates G0 (leakage canary), G1 (pre-placement surface
  correlation), G2 (content-aware uniqueness: U1 identity, U3 non-lattice
  overlap <= 0.70, lattice excess <= +0.05, no repair gutting), G3
  (format/portal range) and G4 (cross-fit ESTIMATE > 0.2778) all passed,
  plus independent re-verification of the saved bytes against the card
  SHA-256, name/note length limits, the leakage canary threshold, the
  uniqueness numbers in the gate details, zero weekly slots spent and an
  experiment count inside budget.

* G5 (HOLDOUT-DTI) is recorded as *context only*: IR-11 measures
  rho = 0.089 between HOLDOUT-DTI and owner-reported scores (n = 119), while
  the leaderboard-calibrated family-CV instrument reaches rho = 0.914. The
  holdout is therefore reported, never used to promote or block, and it is
  always labelled ``HOLDOUT-DTI`` with evaluator version, withheld positives
  and 95% CI.

* The actual upload / weekly-slot spend is a **separate authorization** that
  this module never grants: ``selector_slot_spend.authorized`` is always
  ``False``. Nothing here is an organizer receipt or a confirmed score.

Fail-closed: any missing/malformed/mismatched field returns
``decision: DO-NOT-SUBMIT`` with explicit ``blocking_reasons``.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")
CORE_GATES = ("G0_leakage_canary", "G1_preplacement_surface",
              "G2_final_dot_uniqueness", "G3_format_portal_range",
              "G4_leaderboard_estimate_gt_0p2778")
CHAMPION_OWNER = 0.2778


def _number(value: Any, low: float, high: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and low <= value <= high)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def evaluate_release_gate_v2(card: dict[str, Any], root: Path,
                             prereg_path: Path | None = None) -> dict[str, Any]:
    """Verify a LBCAL-K run card (and its saved bytes) against the v2 rule."""
    reasons: list[str] = []

    if card.get("verdict") != "promote":
        reasons.append("The governing run card verdict is not promote.")

    gates = card.get("gates")
    if not isinstance(gates, list):
        reasons.append("The run card has no gates list.")
        gates = []
    by_name = {g.get("name"): g for g in gates if isinstance(g, dict)}
    for name in CORE_GATES:
        if name not in by_name:
            reasons.append(f"Core gate {name} is missing.")
        elif by_name[name].get("passed") is not True:
            reasons.append(f"Core gate {name} did not pass.")

    g0 = by_name.get("G0_leakage_canary", {})
    g0d = g0.get("detail") or {}
    if not _number(g0d.get("worst_separation"), 0, 0.90):
        reasons.append("The leakage canary lacks a finite worst separation within [0, 0.90].")
    if not g0d.get("rule") or "0.90" not in str(g0d.get("rule")):
        reasons.append("The leakage canary rule statement is missing.")

    g1 = by_name.get("G1_preplacement_surface", {})
    g1d = g1.get("detail") or {}
    if not _number(g1d.get("max_abs_spearman"), 0, 0.90):
        reasons.append("The pre-placement surface check lacks |rho| within [0, 0.90].")

    g2 = by_name.get("G2_final_dot_uniqueness", {})
    g2d = g2.get("detail") or {}
    if g2d.get("U1_exact_duplicate") is not False:
        reasons.append("The final-dot identity check (U1) did not pass.")
    if not _number(g2d.get("U3_max_nonlattice_overlap_3px"), 0, 0.70):
        reasons.append("Non-lattice dot overlap exceeds 0.70 or is malformed.")
    if not _number(g2d.get("U3_lattice_excess"), -1, 0.05):
        reasons.append("Lattice excess exceeds +0.05 or is malformed.")
    if g2d.get("repair_gutted_over_25pct") is True:
        reasons.append("The removal repair gutted more than 25% of the design.")

    g4 = by_name.get("G4_leaderboard_estimate_gt_0p2778", {})
    g4d = g4.get("detail") or {}
    label = g4d.get("label", "")
    if "ESTIMATE" not in str(label) or "NOT a score" not in str(label):
        reasons.append("The estimate gate is not labelled ESTIMATE -- NOT a score.")
    if not _number(g4d.get("cross_fit_mean"), 0, 1) or g4d.get("cross_fit_mean", 0) <= CHAMPION_OWNER:
        reasons.append("The cross-fit estimate does not exceed 0.2778.")
    ci = g4d.get("family_bootstrap_95")
    if (not isinstance(ci, list) or len(ci) != 2
            or not all(_number(v, 0, 1) for v in ci) or not ci[0] <= ci[1]):
        reasons.append("The family bootstrap interval is missing or malformed.")

    g5 = by_name.get("G5_holdout_context_reported", {})
    g5d = g5.get("detail") or {}
    if g5.get("passed") is not True or not str(g5d.get("label", "")).startswith("HOLDOUT-DTI"):
        reasons.append("The HOLDOUT-DTI context block is missing or unlabelled.")
    if "context only" not in str(g5d.get("decision_rule", "")):
        reasons.append("The holdout is not marked as context-only (IR-11).")

    validator = card.get("validator") or {}
    if validator.get("passed") is not True:
        reasons.append("Saved-byte validation is missing or failed.")

    raster = card.get("raster") or {}
    sha = raster.get("sha256")
    if not isinstance(sha, str) or not SHA256.fullmatch(sha or ""):
        reasons.append("The candidate does not identify a valid SHA-256 digest.")
    else:
        path = root / str(raster.get("path", ""))
        if not path.is_file():
            reasons.append("The candidate raster is missing from the workspace.")
        elif sha256_file(path) != sha:
            reasons.append("The saved bytes do not match the run-card SHA-256.")

    name = card.get("submission_name")
    note = card.get("note")
    if not isinstance(name, str) or not name.strip() or len(name) > 140:
        reasons.append("The candidate has no valid submission name (<=140 chars).")
    if not isinstance(note, str) or not note.strip() or len(note) > 140:
        reasons.append("The submission note is missing or exceeds 140 characters.")

    budget = card.get("budget") or {}
    if budget.get("weekly_slots_used") != 0:
        reasons.append("The run card does not record zero spent weekly slots.")
    runs = budget.get("experiments_run")
    if not isinstance(runs, int) or isinstance(runs, bool) or not 1 <= runs <= 3:
        reasons.append("The experiment count is outside the 1..3 budget.")
    holdout = card.get("holdout") or {}
    if holdout.get("n_withheld") != 22232:
        reasons.append("The holdout context does not record 22,232 withheld positives.")
    if holdout.get("label") != "HOLDOUT-DTI" or not holdout.get("evaluator"):
        reasons.append("The holdout block is not labelled HOLDOUT-DTI with an evaluator.")
    if not isinstance(holdout.get("ci95"), list) or len(holdout.get("ci95")) != 2:
        reasons.append("The holdout 95% CI is missing.")

    if prereg_path is not None and not prereg_path.is_file():
        reasons.append("The preregistration file is missing.")

    # E2 (H-XMODEL-GATE) second-opinion evidence must exist and travel with the
    # publication. Its own verdict (which may be negative) is reported, never
    # hidden; §3 of the preregistration defines `promote` as G0-G4 passing.
    cross_model: dict[str, Any] = {}
    e2_path = root / "evidence" / "lbcal_k_run_card_e2.json"
    if not e2_path.is_file():
        reasons.append("The E2 cross-model second-opinion card is missing.")
    else:
        import json as _json
        e2 = _json.loads(e2_path.read_text(encoding="utf-8"))
        e2_gate = (e2.get("gates") or [{}])[0]
        cross_model = {
            "card": "evidence/lbcal_k_run_card_e2.json",
            "verdict": e2.get("verdict"),
            "gate": e2_gate.get("name"),
            "passed": e2_gate.get("passed"),
            "tomography_estimate": (e2.get("estimate") or {}).get("cross_model_estimate"),
            "b2_calibration_delta": (e2.get("estimate") or {}).get("b2_calibration_delta"),
            "label": (e2.get("estimate") or {}).get("label"),
            "reported_as": "disclosed second opinion -- disagreement with G4's "
                           "0.424 estimate reduces confidence; both are ESTIMATES",
        }
        if e2.get("verdict") not in ("promote", "negative"):
            reasons.append("The E2 cross-model card has no recognised verdict.")

    approved = not reasons
    return {
        "schema": "gems-release-gate-v2",
        "decision": "SUBMIT" if approved else "DO-NOT-SUBMIT",
        "okay_to_download_and_submit": approved,
        "candidate": {"submission": name if isinstance(name, str) else None,
                      "sha256": sha if isinstance(sha, str) else None,
                      "dots": raster.get("dots"),
                      "lane_verdict": card.get("verdict"),
                      "holdout_label": g5d.get("label"),
                      "estimate_label": g4d.get("label"),
                      "cross_fit_estimate": g4d.get("cross_fit_mean")},
        "gates": [{"name": n, "passed": by_name[n].get("passed") is True}
                  for n in [*CORE_GATES, "G5_holdout_context_reported"] if n in by_name],
        "selector_slot_spend": {
            "authorized": False,
            "slots_used": 0,
            "note": "This gate authorises download + submission readiness only. "
                    "Nothing was uploaded; spending the weekly slot stays a "
                    "separate, separately-authorized human step.",
        },
        "informational": {
            "holdout_dti": g5d.get("pooled_dti"),
            "holdout_ci95": g5d.get("ci95"),
            "holdout_n_withheld": g5d.get("n_withheld"),
            "estimate_ci95": ci,
            "cross_model_second_opinion": cross_model,
        },
        "blocking_reasons": reasons,
    }
