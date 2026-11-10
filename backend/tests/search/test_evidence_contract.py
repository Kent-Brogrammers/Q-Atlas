"""Optional evidence fields preserve old responses and reject inconsistent records."""

import pytest
from pydantic import ValidationError

from app.schemas.contracts import SearchMetrics


def test_legacy_search_metrics_remain_valid_without_evidence():
    metrics = SearchMetrics(shots=16, success_probability=0.5, quantum_oracle_queries=2)
    assert metrics.successful_shots is None
    assert metrics.classical_observed_queries is None
    assert metrics.quantum_total_oracle_queries is None


@pytest.mark.parametrize("successes", [0, 8, 16])
@pytest.mark.parametrize("queries", [0, 2])
def test_zero_partial_and_perfect_success_and_zero_oracle_calls(successes, queries):
    metrics = SearchMetrics(
        num_qubits=3,
        shots=16,
        success_probability=successes / 16,
        successful_shots=successes,
        classical_observed_queries=2,
        classical_worst_case_queries=8,
        quantum_oracle_queries=queries,
        quantum_total_oracle_queries=queries * 16,
    )
    assert SearchMetrics.model_validate_json(metrics.model_dump_json()) == metrics


@pytest.mark.parametrize(
    "fields",
    [
        {"successful_shots": 0},
        {"shots": 16, "successful_shots": 17},
        {"shots": 16, "successful_shots": 8, "success_probability": 0.75},
        {"shots": 16, "successful_shots": -1},
        {"shots": 16, "successful_shots": 1.5},
        {"shots": 16, "successful_shots": True},
        {"quantum_total_oracle_queries": 0},
        {"shots": 16, "quantum_total_oracle_queries": 0},
        {"shots": 16, "quantum_oracle_queries": 2, "quantum_total_oracle_queries": 31},
        {"shots": 16, "quantum_oracle_queries": 0, "quantum_total_oracle_queries": False},
        {"classical_observed_queries": 0},
        {"classical_observed_queries": True},
        {"num_qubits": 3, "classical_observed_queries": 9},
        {"classical_worst_case_queries": 7, "classical_observed_queries": 8},
    ],
)
def test_invalid_or_inconsistent_evidence_is_rejected(fields):
    with pytest.raises(ValidationError):
        SearchMetrics(**fields)
