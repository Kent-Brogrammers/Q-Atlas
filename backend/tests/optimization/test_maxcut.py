"""Independent cut-weight checks, known optima, and real shared-solver integration."""

from itertools import product

import pytest

pytest.importorskip("networkx", reason="Install the optional quantum extra")
import networkx as nx

from app.experiments.optimization.maxcut import maxcut_to_qubo
from app.experiments.optimization.solvers import run_classical
from app.quantum.qaoa import run_qaoa
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import GraphInput, QAOAConfig


def graph_input(graph):
    return GraphInput(
        kind="graph",
        num_vertices=graph.number_of_nodes(),
        edges=[
            {"i": min(i, j), "j": max(i, j), "coefficient": data.get("weight", 1)}
            for i, j, data in graph.edges(data=True)
        ],
    )


@pytest.mark.parametrize(
    "graph",
    [
        nx.path_graph(2),
        nx.cycle_graph(3),
        nx.cycle_graph(4),
        nx.complete_graph(4),
        nx.Graph([(0, 1, {"weight": 0.25}), (1, 2, {"weight": -1.5})]),
        nx.Graph([(0, 1, {"weight": 0}), (1, 2, {"weight": 2})]),
    ],
)
def test_qubo_cost_matches_negative_networkx_cut_for_every_assignment(graph):
    problem = graph_input(graph)
    before = problem.model_dump()
    qubo = maxcut_to_qubo(problem)
    assert qubo.num_variables == graph.number_of_nodes()
    assert qubo.sense == "minimize"
    assert qubo.original_sense == "maximize"
    assert qubo.constant == 0
    for bits in product((0, 1), repeat=qubo.num_variables):
        partition = [vertex for vertex, bit in enumerate(bits) if bit]
        expected = -nx.cut_size(graph, partition, weight="weight")
        assert evaluate_qubo(qubo, "".join(map(str, bits))) == pytest.approx(expected, abs=1e-12)
    assert problem.model_dump() == before


def test_single_edge_has_the_expected_coefficients():
    qubo = maxcut_to_qubo(graph_input(nx.path_graph(2)))
    assert qubo.linear == [-1, -1]
    assert qubo.model_dump()["quadratic"] == [{"i": 0, "j": 1, "coefficient": 2}]


def test_isolated_vertices_and_api_bit_positions_are_preserved():
    graph = nx.Graph()
    graph.add_nodes_from(range(5))
    graph.add_edge(1, 4, weight=3)
    qubo = maxcut_to_qubo(graph_input(graph))
    assert qubo.linear == [0, -3, 0, 0, -3]
    assert qubo.model_dump()["quadratic"] == [{"i": 1, "j": 4, "coefficient": 6}]
    assert evaluate_qubo(qubo, "00001") == -3
    assert evaluate_qubo(qubo, "10000") == 0
    result = run_classical(qubo, QAOAConfig())
    assert result.best_bitstring == "00001"


@pytest.mark.parametrize(
    "graph,optimum",
    [
        (nx.path_graph(2), 1),
        (nx.cycle_graph(3), 2),
        (nx.cycle_graph(4), 4),
        (nx.complete_graph(4), 4),
        (nx.cycle_graph(8), 8),
        (nx.Graph([(0, 1, {"weight": -3})]), 0),
        (nx.Graph([(0, 1, {"weight": 0})]), 0),
        (nx.Graph([(0, 1, {"weight": 0.5}), (1, 2, {"weight": 2})]), 2.5),
    ],
)
def test_classical_solver_matches_known_cut_optima(graph, optimum):
    qubo = maxcut_to_qubo(graph_input(graph))
    result = run_classical(qubo, QAOAConfig())
    assert result.objective == -optimum
    partition = [vertex for vertex, bit in enumerate(result.best_bitstring) if bit == "1"]
    assert nx.cut_size(graph, partition, weight="weight") == optimum


def test_input_edge_order_does_not_change_the_canonical_problem():
    problem = graph_input(nx.complete_graph(4))
    reordered = problem.model_copy(update={"edges": list(reversed(problem.edges))})
    assert maxcut_to_qubo(problem) == maxcut_to_qubo(reordered)


def test_maximum_graph_width_and_edge_count_are_supported():
    graph = nx.complete_graph(16)
    qubo = maxcut_to_qubo(graph_input(graph))
    assert qubo.num_variables == 16
    assert qubo.linear == [-15] * 16
    assert len(qubo.quadratic) == 120
    assert evaluate_qubo(qubo, "0000000011111111") == -64


@pytest.mark.parametrize(
    "edges",
    [
        [(0, 1, 1e308)],
        [(0, 1, 8e307), (0, 2, 8e307), (0, 3, 8e307)],
    ],
)
def test_derived_coefficient_overflow_requires_rescaling(edges):
    problem = GraphInput(
        kind="graph",
        num_vertices=4,
        edges=[{"i": i, "j": j, "coefficient": weight} for i, j, weight in edges],
    )
    with pytest.raises(ValueError, match="overflow; rescale edge weights"):
        maxcut_to_qubo(problem)


@pytest.mark.parametrize("vertices", [4, 8])
def test_real_qaoa_and_classical_solvers_run_the_same_maxcut_instance(vertices):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    graph = nx.cycle_graph(vertices)
    qubo = maxcut_to_qubo(graph_input(graph))
    config = QAOAConfig(seed=42, shots=256, max_iterations=60)
    before = qubo.model_dump(), config.model_dump()
    classical = run_classical(qubo, config)
    quantum = run_qaoa(qubo, config)
    partition = [vertex for vertex, bit in enumerate(quantum.best_bitstring) if bit == "1"]
    assert classical.objective == -vertices
    assert quantum.objective == -nx.cut_size(graph, partition, weight="weight")
    assert classical.objective <= quantum.objective <= 0
    assert quantum.metrics.num_qubits == vertices
    assert quantum.metrics.shots == config.shots
    assert 1 <= quantum.metrics.optimizer_evaluations <= config.max_iterations
    assert (qubo.model_dump(), config.model_dump()) == before
