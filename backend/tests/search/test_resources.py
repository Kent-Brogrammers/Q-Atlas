"""Gate resources describe the simulator circuit, not shot batches or queries."""

import pytest
from pydantic import ValidationError

from app.schemas.contracts import SearchMetrics, SearchRequest


def test_optional_counts_preserve_legacy_metrics_and_empty_circuits():
    assert SearchMetrics().circuit_gate_counts is None
    assert SearchMetrics(circuit_gate_counts={}).circuit_gate_counts == {}
    assert SearchMetrics(circuit_gate_counts={"h": 2, "cx": 1}).model_dump()[
        "circuit_gate_counts"
    ] == {"h": 2, "cx": 1}


@pytest.mark.parametrize("counts", [{"h": -1}, {"h": 0}, {"h": True}, {"h": 1.5}, {"": 1}])
def test_invalid_gate_counts_rejected(counts):
    with pytest.raises(ValidationError):
        SearchMetrics(circuit_gate_counts=counts)


def test_only_gates_are_counted_without_mutation_or_decomposition():
    qiskit = pytest.importorskip("qiskit")
    from app.experiments.search.resources import circuit_gate_counts

    circuit = qiskit.QuantumCircuit(3, 3)
    circuit.h(0)
    circuit.h(1)
    circuit.cx(0, 1)
    circuit.ccx(0, 1, 2)
    circuit.barrier()
    circuit.reset(2)
    circuit.measure(range(3), range(3))
    before = circuit.copy()
    assert circuit_gate_counts(circuit) == {"ccx": 1, "cx": 1, "h": 2}
    assert circuit == before
    assert circuit_gate_counts(qiskit.QuantumCircuit(1)) == {}


def test_counts_describe_executed_circuit_and_do_not_scale_with_shots(monkeypatch):
    pytest.importorskip("qiskit_aer")
    from app.experiments.search import experiment
    from app.experiments.search.resources import circuit_gate_counts

    original = experiment.transpile
    compiled = []

    def capture(*args, **kwargs):
        circuit = original(*args, **kwargs)
        compiled.append(circuit)
        return circuit

    monkeypatch.setattr(experiment, "transpile", capture)
    for iterations in [0, 2]:
        results = [
            experiment.run_experiment(
                SearchRequest(
                    num_qubits=3,
                    marked_states=["001"],
                    iterations=iterations,
                    config={"shots": shots, "seed": 42},
                )
            )
            for shots in [16, 128]
        ]
        assert results[0].metrics.circuit_gate_counts == results[1].metrics.circuit_gate_counts
        for result, circuit in zip(results, compiled[-2:], strict=True):
            assert result.metrics.circuit_gate_counts == circuit_gate_counts(circuit)
            assert "measure" not in result.metrics.circuit_gate_counts
            assert result.metrics.circuit_depth == circuit.depth()
    assert sum(circuit_gate_counts(compiled[0]).values()) < sum(
        circuit_gate_counts(compiled[-1]).values()
    )
