"""Tiny circuit-matrix checks for construction, phases, and explicit binding order."""

import cmath
import math
from unittest.mock import Mock

import pytest

pytest.importorskip("numpy", reason="Install the optional quantum extra")
pytest.importorskip("qiskit", reason="Install the optional quantum extra")
import numpy as np
from qiskit.quantum_info import Operator

from app.quantum import qaoa_circuit
from app.quantum.circuits import build_qaoa_preview
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO


def reference_matrix(qubo, angles):
    """Independent dense H, diagonal objective, and analytic mixer matrices."""
    size = 1 << qubo.num_variables
    hadamard = np.array(
        [[(-1) ** (row & column).bit_count() for column in range(size)] for row in range(size)]
    ) / math.sqrt(size)
    # Qiskit matrix indices place qubit 0 at the least-significant position.
    costs = np.array(
        [
            evaluate_qubo(
                qubo, "".join(str((index >> qubit) & 1) for qubit in range(qubo.num_variables))
            )
            for index in range(size)
        ]
    )
    result = hadamard
    for gamma, beta in angles:
        rotation = np.array(
            [[math.cos(beta), -1j * math.sin(beta)], [-1j * math.sin(beta), math.cos(beta)]]
        )
        mixer = np.ones((1, 1), dtype=complex)
        for _ in range(qubo.num_variables):
            mixer = np.kron(mixer, rotation)
        result = mixer @ np.diag(np.exp(-1j * gamma * costs)) @ result
    return result


@pytest.mark.parametrize("p", [1, 2, 3])
@pytest.mark.parametrize("original_sense", ["minimize", "maximize"])
def test_full_circuit_matches_independent_cost_and_mixer_matrices(mixed_qubo, p, original_sense):
    qubo = QUBO.model_validate({**mixed_qubo, "original_sense": original_sense})
    angles = [(-0.37, 0.19), (0.23, -0.51), (1.2, 0.28)][:p]
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo, p)
    assert [parameter.name for parameter in parameters] == [
        name for layer in range(p) for name in (f"gamma_{layer}", f"beta_{layer}")
    ]
    values = [value for layer in angles for value in layer]
    bound = circuit.assign_parameters(dict(zip(parameters, values, strict=True)), strict=False)
    assert bound.num_parameters == 0
    assert circuit.num_parameters == 2 * p
    np.testing.assert_allclose(
        Operator(bound).data, reference_matrix(qubo, angles), rtol=0, atol=1e-12
    )


@pytest.mark.parametrize("gamma", [-0.37, 0, 0.73])
def test_zero_mixer_preserves_exact_objective_phases_and_qubit_mapping(gamma):
    qubo = QUBO(
        num_variables=3,
        constant=2,
        linear=[-1, 2, -3],
        quadratic=[{"i": 0, "j": 2, "coefficient": 4}],
    )
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo)
    bound = circuit.assign_parameters(dict(zip(parameters, [gamma, 0], strict=True)))
    amplitudes = Operator(bound).data[:, 0]
    # Hand-calculated costs ordered by Qiskit's |q2 q1 q0> matrix basis.
    costs = [2, 1, 4, 3, -1, 2, 1, 4]
    expected = [cmath.exp(-1j * gamma * cost) / math.sqrt(8) for cost in costs]
    np.testing.assert_allclose(amplitudes, expected, rtol=0, atol=1e-12)
    assert abs(amplitudes[4] - cmath.exp(1j * gamma) / math.sqrt(8)) < 1e-12


@pytest.mark.parametrize("constant", [0, 7.25, -2])
def test_constant_only_costs_keep_layer_order_and_global_phase(constant):
    qubo = QUBO(num_variables=2, constant=constant, linear=[0, 0])
    angles = [(0.43, -0.17), (-0.29, 0.31)]
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo, p=2)
    assert [parameter.name for parameter in parameters] == [
        "gamma_0",
        "beta_0",
        "gamma_1",
        "beta_1",
    ]
    bound = circuit.assign_parameters(
        dict(zip(parameters, [value for layer in angles for value in layer], strict=True)),
        strict=False,
    )
    assert bound.num_parameters == 0
    np.testing.assert_allclose(
        Operator(bound).data, reference_matrix(qubo, angles), rtol=0, atol=1e-12
    )


def test_binding_uses_explicit_order_instead_of_alphabetical_sdk_order():
    qubo = QUBO(num_variables=1, constant=0.25, linear=[-1])
    angles = [(0.13, -0.41), (0.67, 0.22)]
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo, p=2)
    assert [parameter.name for parameter in circuit.parameters] != [
        parameter.name for parameter in parameters
    ]
    bound = circuit.assign_parameters(dict(zip(parameters, [0.13, -0.41, 0.67, 0.22], strict=True)))
    np.testing.assert_allclose(
        Operator(bound).data, reference_matrix(qubo, angles), rtol=0, atol=1e-12
    )


def test_adapter_consumes_shared_gate_angles_and_phase_without_changing_inputs(monkeypatch):
    qubo = QUBO(num_variables=1, constant=0, linear=[1])
    plan = build_qaoa_preview(qubo)
    # Change a trusted plan to catch an adapter that independently rebuilds formulas.
    plan.gates[1].angle.coefficient = -2
    plan.global_phase[0].coefficient = 0.75
    before_qubo, before_plan = qubo.model_dump(), plan.model_dump()
    shared_builder = Mock(return_value=plan)
    monkeypatch.setattr(qaoa_circuit, "build_qaoa_preview", shared_builder)
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo)
    bound = circuit.assign_parameters(dict(zip(parameters, [0.3, 0], strict=True)))
    expected = np.diag([cmath.exp(1j * 0.525), cmath.exp(-1j * 0.075)]) @ (
        np.array([[1, 1], [1, -1]]) / math.sqrt(2)
    )
    np.testing.assert_allclose(Operator(bound).data, expected, rtol=0, atol=1e-12)
    shared_builder.assert_called_once_with(qubo, p=1)
    assert qubo.model_dump() == before_qubo
    assert plan.model_dump() == before_plan


def test_maximum_width_and_layers_construct_and_bind():
    qubo = QUBO(num_variables=16, linear=[1] * 16)
    circuit, parameters = qaoa_circuit.build_qaoa_circuit(qubo, p=8)
    assert len(parameters) == 16
    assert circuit.num_qubits == 16
    assert circuit.num_clbits == 0
    assert "measure" not in circuit.count_ops()
    bound = circuit.assign_parameters(dict.fromkeys(parameters, 0.0))
    assert bound.num_parameters == 0


@pytest.mark.parametrize("p", [0, 9, True, 1.5])
def test_invalid_layers_follow_the_shared_plan_validation(p):
    with pytest.raises(ValueError, match="p must be an integer"):
        qaoa_circuit.build_qaoa_circuit(QUBO(num_variables=1, linear=[1]), p)


def test_global_phase_overflow_uses_the_shared_validation():
    qubo = QUBO(num_variables=2, constant=1e308, linear=[1e308, 1e308])
    with pytest.raises(ValueError, match="global phase"):
        qaoa_circuit.build_qaoa_circuit(qubo)
