"""Known instances and exhaustive small-space query accounting."""

from itertools import combinations

import pytest

from app.experiments.search import classical
from app.experiments.search.classical import query_bounds, run_classical_search
from app.schemas.contracts import SearchRequest


@pytest.mark.parametrize(("target", "queries"), [("000", 1), ("100", 5), ("111", 8)])
def test_fixed_instance_stops_at_first_marked_candidate(target, queries):
    request = SearchRequest(num_qubits=3, marked_states=[target])
    before = request.model_dump()
    result = run_classical_search(request)
    assert result.found_state == target
    assert result.oracle_queries == queries
    assert result.expected_queries == 4.5
    assert result.worst_case_queries == 8
    assert result.elapsed_ms >= 0
    assert request.model_dump() == before


def test_multiple_targets_stop_at_first_in_checking_order_not_input_order():
    result = run_classical_search(SearchRequest(num_qubits=3, marked_states=["111", "001"]))
    assert result.found_state == "001"
    assert result.oracle_queries == 2
    assert result.expected_queries == 3
    assert result.worst_case_queries == 7


@pytest.mark.parametrize("marked_count", [1, 2, 3, 4])
def test_query_formulas_match_every_placement_in_four_candidate_space(marked_count):
    observations = []
    states = ["00", "01", "10", "11"]
    for marked in combinations(states, marked_count):
        result = run_classical_search(SearchRequest(num_qubits=2, marked_states=list(marked)))
        observations.append(result.oracle_queries)
    expected, worst = query_bounds(4, marked_count)
    assert sum(observations) / len(observations) == pytest.approx(expected)
    assert max(observations) == worst


@pytest.mark.parametrize(("candidates", "marked"), [(0, 0), (4, 0), (4, 5), (4, -1), (4, True)])
def test_invalid_query_counts_are_rejected(candidates, marked):
    with pytest.raises(ValueError):
        query_bounds(candidates, marked)


def test_timeout_is_enforced_before_search(monkeypatch):
    clock = iter([0, 2_000_000_000])
    monkeypatch.setattr(classical, "perf_counter_ns", lambda: next(clock))
    request = SearchRequest(num_qubits=2, marked_states=["00"], config={"timeout_seconds": 1})
    with pytest.raises(TimeoutError):
        run_classical_search(request)


def test_timeout_is_enforced_after_final_query(monkeypatch):
    clock = iter([0, 0, 2_000_000_000])
    monkeypatch.setattr(classical, "perf_counter_ns", lambda: next(clock))
    request = SearchRequest(num_qubits=2, marked_states=["00"], config={"timeout_seconds": 1})
    with pytest.raises(TimeoutError):
        run_classical_search(request)
