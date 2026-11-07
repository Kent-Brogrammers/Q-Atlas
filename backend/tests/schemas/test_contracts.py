import pytest
from pydantic import ValidationError

from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkResult,
    MaterialsResult,
    OptimizationResult,
    SearchResult,
    SolverResult,
)


def test_qubo_normalizes_duplicate_pairs_and_orders_them(qubo_payload):
    qubo_payload["quadratic"] = [
        {"i": 1, "j": 2, "coefficient": 3},
        {"i": 0, "j": 1, "coefficient": 5},
        {"i": 0, "j": 1, "coefficient": -2},
        {"i": 0, "j": 2, "coefficient": 0},
    ]
    qubo = QUBO.model_validate(qubo_payload)
    assert [term.model_dump() for term in qubo.quadratic] == [
        {"i": 0, "j": 1, "coefficient": 3},
        {"i": 1, "j": 2, "coefficient": 3},
    ]
    assert QUBO.model_validate_json(qubo.model_dump_json()) == qubo


@pytest.mark.parametrize(
    "patch",
    [
        {"linear": [1]},
        {"sense": "maximize"},
        {"num_variables": 17},
        {"constant": float("inf")},
        {"linear": [1, float("nan"), 0]},
        {"quadratic": [{"i": 1, "j": 1, "coefficient": 1}]},
        {"quadratic": [{"i": 2, "j": 1, "coefficient": 1}]},
        {"quadratic": [{"i": 0, "j": 3, "coefficient": 1}]},
        {"quadratic": [{"i": 0, "j": 1, "coefficient": float("inf")}]},
        {"quadratic": [{"i": 0, "j": 1, "coefficient": 1e308}] * 2},
        {"unknown": 123},
    ],
)
def test_qubo_rejects_noncanonical_or_unbounded_values(qubo_payload, patch):
    with pytest.raises(ValidationError):
        QUBO.model_validate(qubo_payload | patch)


def test_measured_solver_requires_explicit_timer_inclusions():
    with pytest.raises(ValidationError):
        SolverResult(algorithm="fixture", elapsed_ms=0, timing={})


@pytest.mark.parametrize(
    ("model", "experiment", "metrics", "extra"),
    [
        (CompilerBenchmarkResult, "compiler", {"optimality_gap": None}, "optimization"),
        (OptimizationResult, "optimization", {"optimizer_evaluations": None}, "optimization"),
        (SearchResult, "search", {"success_probability": None}, "search"),
        (MaterialsResult, "materials", {"absolute_error": None}, "materials"),
    ],
)
def test_result_envelopes_round_trip_nullable_measurements(
    qubo_payload,
    model,
    experiment,
    metrics,
    extra,
):
    # Synthetic contract fixture, never exposed as measured experimental evidence.
    metadata = {"seed": 42, "timing_scope": "end_to_end", "simulation_method": "statevector"}
    if extra == "optimization":
        metadata |= {"qubo": qubo_payload, "config": {}}
    elif extra == "search":
        metadata |= {
            "parameters": {"num_qubits": 3, "marked_states": ["100"]},
            "oracle_assumptions": "Fixture only",
        }
    else:
        metadata |= {
            "parameters": {},
            "hamiltonian_convention": "Fixture only",
            "energy_unit": "J",
            "observable_unit": "J",
        }
    result = model.model_validate(
        {
            "experiment": experiment,
            "problem_id": "contract-fixture",
            "backend": "aer_simulator",
            "classical": None,
            "quantum": None,
            "metrics": metrics,
            "metadata": metadata,
        }
    )
    assert model.model_validate_json(result.model_dump_json()) == result
    assert result.metadata.simulated is True
