"""Independent objective checks; submitted example Python is read only as text."""

import json
from itertools import product
from pathlib import Path

import pytest

from app.compiler.generation import generate_source
from app.experiments.optimization.maxcut import maxcut_to_qubo
from app.quantum import qaoa
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import OptimizationResult, QAOAResult
from scripts import benchmark_stress_examples as stress

PROGRAMS = Path(__file__).resolve().parents[3] / "examples/compiler/programs"
CUT_EDGES = [
    (0, 1, 2),
    (0, 2, 4),
    (0, 3, 3),
    (0, 4, 9),
    (0, 5, 5),
    (1, 2, 2),
    (1, 3, 9),
    (1, 4, 9),
    (1, 5, 1),
    (2, 3, 7),
    (2, 4, 5),
    (2, 5, 9),
    (3, 4, 5),
    (3, 5, 6),
    (4, 5, 1),
]
CONFLICT_EDGES = [(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5), (0, 3), (1, 4), (2, 5)]


def independent_cost(name, bits):
    if name == "maxcut":
        return -sum(weight for i, j, weight in CUT_EDGES if bits[i] != bits[j])
    if name == "partition":
        load = sum(weight * bit for weight, bit in zip([7, 11, 13, 17, 19, 23], bits, strict=True))
        return (load - 45) ** 2 + 25 * (sum(bits) - 3) ** 2
    reward = sum(weight * bit for weight, bit in zip([7, 6, 5, 4, 3, 2], bits, strict=True))
    return 11 * sum(bits[i] * bits[j] for i, j in CONFLICT_EDGES) - reward


@pytest.mark.parametrize(
    "name,optimum,first,pairs",
    [
        ("maxcut", -57, "000111", 15),
        ("partition", 4, "010110", 15),
        ("conflicts", -10, "010100", 9),
    ],
)
def test_compiler_stress_objectives_match_independent_arithmetic(name, optimum, first, pairs):
    result = generate_source((PROGRAMS / f"stress_{name}_6.py").read_text(), p=8)
    assert result.status == "supported", result.diagnostics
    assert result.qubo.num_variables == result.circuit.num_qubits == 6
    assert len(result.qubo.quadratic) == pairs
    assert result.artifact.executed is result.circuit.executed is False
    rows = []
    for bits in product((0, 1), repeat=6):
        bitstring = "".join(map(str, bits))
        expected = independent_cost(name, bits)
        assert evaluate_qubo(result.qubo, bitstring) == expected
        rows.append((expected, bitstring))
    assert min(rows) == (optimum, first)


def test_larger_graph_family_extends_the_compiler_maxcut_instance():
    compiled = generate_source((PROGRAMS / "stress_maxcut_6.py").read_text()).qubo
    graph = stress.build_stress_graph(6)
    assert [(edge.i, edge.j, edge.coefficient) for edge in graph.edges] == CUT_EDGES
    qubo = maxcut_to_qubo(graph)
    for bits in product((0, 1), repeat=6):
        bitstring = "".join(map(str, bits))
        assert evaluate_qubo(qubo, bitstring) == evaluate_qubo(compiled, bitstring)


@pytest.mark.parametrize("width", [6, 8, 12, 16])
@pytest.mark.parametrize("shape", ["dense", "sparse"])
def test_scaling_family_has_expected_connectivity_and_consistent_cut_cost(width, shape):
    graph = stress.build_stress_graph(width, shape)
    assert graph == stress.build_stress_graph(width, shape)
    assert len(graph.edges) == (width * (width - 1) // 2 if shape == "dense" else 2 * width - 2)
    qubo = maxcut_to_qubo(graph)
    for bits in ["0" * width, "1" * width, "01" * (width // 2), "0" * 3 + "1" * (width - 3)]:
        cut = sum(edge.coefficient for edge in graph.edges if bits[edge.i] != bits[edge.j])
        assert evaluate_qubo(qubo, bits) == -cut


@pytest.mark.parametrize("width,shape", [(7, "dense"), (32, "dense"), (6, "unknown")])
def test_graph_generator_respects_existing_width_and_shape_limits(width, shape):
    with pytest.raises(ValueError):
        stress.build_stress_graph(width, shape)


def test_cli_saves_raw_comparison_and_heuristic_without_running_source(monkeypatch, tmp_path):
    def fake_quantum(qubo, config):
        return QAOAResult(
            objective=evaluate_qubo(qubo, "0" * qubo.num_variables),
            best_bitstring="0" * qubo.num_variables,
            elapsed_ms=1,
            timing={
                "includes_queue": False,
                "includes_transpilation": True,
                "includes_optimizer": True,
                "includes_sampling": True,
            },
            metrics={"num_qubits": qubo.num_variables, "shots": config.shots},
        )

    monkeypatch.setattr(qaoa, "run_qaoa", fake_quantum)
    output = tmp_path / "record.json"
    source = PROGRAMS / "stress_maxcut_6.py"
    assert stress.main(["--source", str(source), "--output", str(output)]) == 0
    record = json.loads(output.read_text())
    comparison = OptimizationResult.model_validate(record["comparison"])
    assert comparison.classical.objective == -57
    assert comparison.metrics.optimality_gap == 57  # Synthetic all-zero QAOA candidate.
    assert record["simulated"] is True
    assert record["input"]["source"] == source.read_text()
    assert record["heuristic_optimality_gap"] >= 0
    assert record["request"]["config"]["max_iterations"] == 20
    with pytest.raises(SystemExit):
        stress.main(["--output", str(output)])
    assert json.loads(output.read_text()) == record


def test_cli_preserves_timeout_as_failure_without_fabricating_a_result(monkeypatch, tmp_path):
    def timeout(request):
        raise TimeoutError("local budget exhausted")

    monkeypatch.setattr(stress, "run_optimization", timeout)
    output = tmp_path / "record.json"
    with pytest.raises(SystemExit, match="1"):
        stress.main(["--qubits", "16", "--output", str(output)])
    assert not output.exists()
