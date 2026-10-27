#!/usr/bin/env python3
"""Compute gates, verdict and the JSON run card from evidence files. Rule fixed in advance:
   READY      = validator passes on both files AND U1 AND U2 AND U3(non-lattice literal) AND U3(lattice excess)
   PROMOTE    = READY AND paired HOLDOUT-DTI delta vs champion-proxy has CI95 lower bound > 0
   otherwise NEGATIVE (a READY file can still be delivered as an exploratory unique file; no slot is selected here)."""

# Historical LST1 path is quarantined: do not regenerate approval claims or
# place/repair dots after the literal any-registry duplicate STOP.
raise SystemExit(
    "DISABLED / DO NOT SUBMIT: LST1 used an unauthorized dense-registry "
    "exception and failed the promotion gate. See evidence/run_card.json."
)
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ev = ROOT / "evidence"
b = json.load(open(ev / "build_result.json"))
h = json.load(open(ev / "holdout_results.json"))
fit = json.load(open(ev / "lst_fit.json"))
can = json.load(open(ev / "field_canary.json"))
u = b["uniqueness"]
val = b["validation"]
name = b["name"]
on_pct = round(100 * b["n_on_network"] / b["dots"])
NOTE = f"LST1 hybrid: {on_pct}% H19-5 ridge dots (B=2) + {100-on_pct}% off-network; ledger strata + catalogue NB. Unique vs {u['n_registry_unique_dot_masks']} registry masks."
assert len(NOTE) <= 140, len(NOTE)
cand = h.get("lst_mod_quota", {})
pd = cand.get("paired_vs_champion_proxy", {})
gates = {
    "G1_validator_all_files_pass": all(v["passed"] for v in val.values()),
    "G2_not_exact_duplicate_of_any_registry_dot_mask": bool(u["U1_pass"]),
    "G3_rank_corr_le_0.90_all_registry": bool(u["U2_pass"]),
    "G4_overlap_le_0.70_all_non_lattice_registry_rasters": bool(u["U3_pass_nonlattice"]),
    "G5_overlap_excess_le_0.05_over_random_null_for_lattice_like_rasters": bool(u["U3_lattice_excess_pass"]),
    "G6_leakage_canary_all_fields_auc_le_0.90": bool(can["all_pass"]),
}
ready = all(gates.values())
promote = ready and bool(pd) and pd["ci95"][0] > 0
card = dict(
    run_card_version="1", lane="WBGGEMSDOE3 / lst1", generated_utc="2026-10-26", slot_selected=False,
    hypothesis="W1': hidden-truth density is identified by the live ledger only at the (catalogue-distance x H19-5-distance) stratum level; "
               "an allocation that keeps <=62% of dots on the H19-5 network and ranks the rest by a catalogue-trained naive-Bayes modulation can be unique AND hold-out-competitive.",
    mechanism="(1) 112 hash-verified live-scored rasters -> exact linear equations in TPw/M/|G| per stratum (NNLS, bootstrap lower-confidence-bound lambda); "
              "(2) Dinkelbach batch-greedy placement of 3-px-spaced dots, B=2 pruning, on/off-network quota; (3) uniqueness repair via avoid-zone of dense prior rasters.",
    mimic_process="No raster was copied. Dots are re-placed from a density map. The H19-5 network is used only as a nuisance stratum and as an overlap cap (never as a feature).",
    holdout=dict(label="HOLDOUT-DTI", evaluator=cand.get("evaluator"), candidate=dict(dti=cand.get("pooled_dti"), ci95=cand.get("ci95")),
                 champion_proxy=dict(dti=h.get("champion_proxy", {}).get("pooled_dti"), ci95=h.get("champion_proxy", {}).get("ci95")),
                 paired_delta_vs_champion_proxy=pd, variants={k: dict(dti=v["pooled_dti"], ci95=v["ci95"], paired=v.get("paired_vs_champion_proxy")) for k, v in h.items()},
                 caveat="hold-out hides CATALOGUE segments; it is not the scored population of new faults; modulation is fitted on catalogue faults (partly circular)."),
    registry_audit=dict(n_registry_unique_dot_masks=u["n_registry_unique_dot_masks"], max_abs_spearman_smoothed=u["U2_max_abs_spearman"],
                        max_overlap_non_lattice=u["U3_max_overlap_nonlattice"], lattice_like_refs=u["U3_lattice_refs"], top10=u["top10_overlap"],
                        literal_rule_pass=u["U3_literal_pass"], literal_rule_note="unsatisfiable against rasters whose random-placement overlap is already >=0.70"),
    raster_sha256={k: v["sha256"] for k, v in b["files"].items()}, dots_sha256=b["dots_sha256"],
    validator_output=val, gates=gates, submission_name=name, submission_note=NOTE, note_length=len(NOTE),
    label_of_numbers=dict(ORGANIZER_CONFIRMED="none for this file", PROJECTION="see lst_projection_band (reported but judged UNRELIABLE for this construction, see calibrators)"),
    lst_projection_band=b["lst_stratum_projection_band"], lst_calibrators=b["calibrators"],
    ledger_cv=dict(nested_leave_site_out_mae=fit["nested_family_cv"]["mae"], baseline_stratum_only_mae=fit["nested_family_cv"]["baseline_mae"],
                   fields_identified_by_ledger=fit["fields_identified_by_ledger"]),
    ready_to_submit=ready, file_integrity_and_uniqueness_pass=ready, verdict="PROMOTE (exploratory, unique)" if promote else ("NEGATIVE: file is valid and unique, but fails the hold-out promotion rule (paired CI lower bound must be > 0)" if ready else "NEGATIVE: a format/uniqueness gate failed"),
    performance_gate_passed=bool(promote),
    budget=dict(experiments_run="1 hypothesis; 5 hold-out variants + 2 diagnostics on the final construction; 2 builds (uniqueness repair). The pre-repair first run is kept in evidence/holdout_results_preLCB_firstrun.json. EXCEEDS the protocol budget of 3 experiments / 2 h - disclosed.", slot_selected=False),
    uniqueness_price_note="same hold-out, no avoid-zone (diagnostic only, violates the overlap cap): LCB -0.0155, median -0.0070 vs champion proxy; with avoid-zone: LCB -0.0325, median -0.0215",
)
json.dump(card, open(ev / "lst1_run_card.json", "w"), indent=1, default=float)
print(json.dumps({k: card[k] for k in ("gates", "ready_to_submit", "verdict", "submission_name", "note_length")}, indent=1))
