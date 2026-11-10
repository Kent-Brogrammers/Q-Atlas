"""Analytic scores, basis ordering, reusable binding, and simulator failure checks."""

import math
from unittest.mock import Mock

import pytest

pytest.importorskip("numpy", reason="Install the optional quantum extra")
pytest.importorskip("qiskit", reason="Install the optional quantum extra")
pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Statevector

from app.experiments.optimization.solvers import run_classical
from app.quantum import qaoa_expectation
from app.quantum.qaoa_circuit import build_qaoa_circuit
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, QAOAConfig


@pytest.mark.parametrize("gamma,beta", [(0, 0), (0.31, -0.47), (math.pi / 2, -math.pi / 4)])
@pytest.mark.parametrize("coefficient,constant", [(1, 0), (-3, 2)])
def test_single_variable_matches_analytic_expectation(gamma, beta, coefficient, constant):
    qubo = QUBO(num_variables=1, constant=constant, linear=[coefficient])
    score = qaoa_expectation.QAOAExpectation(qubo)
    expected = constant + coefficient * (1 + math.sin(coefficient * gamma) * math.sin(2 * beta)) / 2
    assert score([gamma, beta]) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("beta,expected", [(-math.pi / 8, -1), (math.pi / 8, 0), (0, -0.5)])
def test_single_edge_maxcut_has_known_optimal_and_worst_angle_scores(beta, expected):
    qubo = QUBO(
        num_variables=2,
        linear=[-1, -1],
        quadratic=[{"i": 0, "j": 1, "coefficient": 2}],
    )
    assert qaoa_expectation.QAOAExpectation(qubo)([math.pi / 2, beta]) == pytest.approx(
        expected, abs=1e-12
    )


@pytest.mark.parametrize("p", [1, 2, 3])
def test_multiple_layers_match_independent_statevector_and_shared_costs(mixed_qubo, p):
    qubo = QUBO.model_validate(mixed_qubo)
    values = [0.13, -0.41, 0.67, 0.22, -0.3, 0.7][: 2 * p]
    circuit, parameters = build_qaoa_circuit(qubo, p)
    bound = circuit.assign_parameters(dict(zip(parameters, values, strict=True)), strict=False)
    probabilities = Statevector.from_instruction(bound).probabilities_dict()
    expected = math.fsum(
        probability * evaluate_qubo(qubo, bitstring[::-1])
        for bitstring, probability in probabilities.items()
    )
    score = qaoa_expectation.QAOAExpectation(qubo, p)
    assert score.num_parameters == 2 * p
    assert score(values) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("constant", [-2.5, 0, 7.25])
def test_constant_only_objectives_include_the_offset_at_any_angles(constant):
    score = qaoa_expectation.QAOAExpectation(
        QUBO(num_variables=2, constant=constant, linear=[0, 0]), p=2
    )
    assert score.num_parameters == 4
    assert score([0.3, -0.7, 1.2, 0.4]) == pytest.approx(constant, abs=1e-12)


@pytest.mark.parametrize("bitstring,expected", [("000", 2), ("001", -1), ("100", 1), ("111", 4)])
def test_statevector_indices_match_x0_first_costs(monkeypatch, bitstring, expected):
    qubo = QUBO(
        num_variables=3,
        constant=2,
        linear=[-1, 2, -3],
        quadratic=[{"i": 0, "j": 2, "coefficient": 4}],
    )
    circuit = QuantumCircuit(3)
    for qubit, bit in enumerate(bitstring):
        if bit == "1":
            circuit.x(qubit)
    parameters = (Parameter("gamma_0"), Parameter("beta_0"))
    monkeypatch.setattr(
        qaoa_expectation, "build_qaoa_circuit", Mock(return_value=(circuit, parameters))
    )
    assert qaoa_expectation.QAOAExpectation(qubo)([0, 0]) == pytest.approx(expected, abs=1e-12)


def test_expectation_is_a_distribution_average_and_reuses_preparation():
    qubo = QUBO(num_variables=1, linear=[1])
    before = qubo.model_dump()
    values = [0.0, 0.0]
    score = qaoa_expectation.QAOAExpectation(qubo)
    assert score(values) == pytest.approx(0.5, abs=1e-12)
    assert run_classical(qubo, QAOAConfig()).objective == 0
    assert score([math.pi / 2, -math.pi / 4]) == pytest.approx(0, abs=1e-12)
    assert score(values) == pytest.approx(0.5, abs=1e-12)
    assert qubo.model_dump() == before
    assert values == [0.0, 0.0]
    qubo.linear[0] = -100  # Preparation owns its data independently of later caller edits.
    assert score(values) == pytest.approx(0.5, abs=1e-12)


def test_canonical_maximization_cost_keeps_its_supplied_sign():
    qubo = QUBO(num_variables=1, linear=[-2], original_sense="maximize")
    score = qaoa_expectation.QAOAExpectation(qubo)
    assert score(np.array([0, 0])) == pytest.approx(-1, abs=1e-12)


def test_maximum_width_and_layers_score_the_uniform_distribution():
    score = qaoa_expectation.QAOAExpectation(QUBO(num_variables=16, linear=[1] * 16), p=8)
    assert score.num_parameters == 16
    assert score([0] * 16) == pytest.approx(8, abs=1e-10)


@pytest.fixture
def fake_simulator(monkeypatch):
    simulator = Mock()
    monkeypatch.setattr(qaoa_expectation, "AerSimulator", Mock(return_value=simulator))
    return simulator


@pytest.mark.parametrize(
    "angles",
    [
        [],
        [0],
        [0, 0, 0],
        [np.nan, 0],
        [0, np.inf],
        [-np.inf, 0],
        [[0], [0]],
        ["invalid", 0],
        [10**400, 0],
        np.array([1 + 1j, 0]),
    ],
)
def test_invalid_angles_are_rejected_before_simulation(fake_simulator, angles):
    score = qaoa_expectation.QAOAExpectation(QUBO(num_variables=1, linear=[1]))
    with pytest.raises(ValueError, match="angles"):
        score(angles)
    fake_simulator.run.assert_not_called()


def test_weighted_angle_overflow_is_rejected_before_simulation(fake_simulator):
    score = qaoa_expectation.QAOAExpectation(QUBO(num_variables=1, linear=[1e308]))
    with pytest.raises(ValueError, match="rotations"):
        score([1e308, 0])
    fake_simulator.run.assert_not_called()


def test_cost_overflow_is_rejected_during_preparation(fake_simulator):
    with pytest.raises(ValueError, match="overflow"):
        qaoa_expectation.QAOAExpectation(QUBO(num_variables=2, linear=[1e308, 1e308]))
    fake_simulator.run.assert_not_called()


def test_failed_simulator_result_is_explicit(fake_simulator):
    fake_simulator.run.return_value.result.return_value.success = False
    score = qaoa_expectation.QAOAExpectation(QUBO(num_variables=1, linear=[1]))
    with pytest.raises(RuntimeError, match="evaluation failed"):
        score([0, 0])


@pytest.mark.parametrize("state", [[1], [np.nan, 0], [0, 0], [1, 1]])
def test_invalid_or_unnormalized_statevector_is_rejected(fake_simulator, state):
    result = fake_simulator.run.return_value.result.return_value
    result.success = True
    result.get_statevector.return_value = state
    score = qaoa_expectation.QAOAExpectation(QUBO(num_variables=1, linear=[1]))
    with pytest.raises(RuntimeError, match="statevector"):
        score([0, 0])
