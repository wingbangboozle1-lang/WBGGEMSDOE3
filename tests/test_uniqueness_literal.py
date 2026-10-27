from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("uniq", ROOT / "src/gemsw/uniq.py")
uniq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uniq)


def test_literal_overlap_requires_every_reference_at_or_below_threshold():
    assert uniq.literal_overlap_pass([{"overlap": 0.70}, {"overlap": 0.2}], 0.70)
    assert not uniq.literal_overlap_pass([{"overlap": 0.70001}, {"overlap": 0.2}], 0.70)


def test_lattice_null_cannot_exempt_literal_overlap():
    # Lattice diagnostics are deliberately absent from this decision function.
    assert not uniq.literal_overlap_pass([{"overlap": 0.95, "excess": 0.0}], 0.70)


def test_unknown_registry_scope_fails_closed_even_with_zero_observed_overlap():
    assert not uniq.literal_overlap_pass([], 0.70, scope_complete=False)


def test_uniqueness_requires_a_measured_rank_gate():
    gates = dict(
        candidate_nonempty=True,
        exact_duplicate_pass=True,
        rank_correlation_pass=False,
        nonlattice_overlap_pass=True,
        lattice_diagnostic_pass=True,
        registry_scope_complete=True,
        literal_overlap_passed=True,
    )
    assert not uniq.uniqueness_gates_pass(**gates)


def test_lattice_diagnostic_cannot_replace_literal_gate():
    gates = dict(
        candidate_nonempty=True,
        exact_duplicate_pass=True,
        rank_correlation_pass=True,
        nonlattice_overlap_pass=True,
        lattice_diagnostic_pass=True,
        registry_scope_complete=True,
        literal_overlap_passed=False,
    )
    assert not uniq.uniqueness_gates_pass(**gates)
