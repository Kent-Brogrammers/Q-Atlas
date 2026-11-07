"""Analytical gate-phase checks only: no statevector, simulator, or quantum jobs."""

import cmath
import itertools
import math

import pytest
from pydantic import ValidationError

from app.compiler.analysis import analyze_source
from app.quantum.circuits import build_qaoa_preview
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, CircuitGate, CircuitPreview


@pytest.mark.parametrize("p", [1, 3])
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_cost_gate_phases_equal_objective_phase_with_constant(p, sense):
    source = (
        f'@qatlas.objective(num_bits=3, sense="{sense}")\n'
        "def cost(x): return 5 - 2*x[0] + 0.5*x[2] + 3*x[0]*x[1] - x[1]*x[2]"
    )
    qubo = analyze_source(source).qubo
    preview = build_qaoa_preview(qubo, p)
    for layer in range(p):
        parameter = f"gamma_{layer}"
        gamma = -0.37 + layer * 0.29
        for bits in itertools.product((0, 1), repeat=3):
            # Compare diagonal gate formulas, without evolving a state or sampling.
            phase = gamma * sum(
                angle.coefficient for angle in preview.global_phase if angle.parameter == parameter
            )
            for gate in preview.gates:
                if gate.angle is None or gate.angle.parameter != parameter:
                    continue
                angle = gamma * gate.angle.coefficient
                if gate.name == "rz":
                    phase += angle * (bits[gate.qubits[0]] - 0.5)
                else:
                    assert gate.name == "cp"
                    phase += angle * bits[gate.qubits[0]] * bits[gate.qubits[1]]
            objective = evaluate_qubo(qubo, "".join(map(str, bits)))
            assert cmath.exp(1j * phase) == pytest.approx(cmath.exp(-1j * gamma * objective))


def test_preview_has_preparation_mixer_and_only_logical_depth():
    preview = build_qaoa_preview(QUBO(num_variables=3, constant=7, linear=[0, 0, 0]), p=2)
    assert preview.executed is False and preview.depth is None
    assert preview.logical_depth == 3  # H, then two parallel RX layers.
    assert preview.parameters == ["gamma_0", "beta_0", "gamma_1", "beta_1"]
    assert [gate.name for gate in preview.gates[:3]] == ["h"] * 3
    assert len(preview.gates) == 9
    assert all(gate.name == "rx" and gate.angle.coefficient == 2 for gate in preview.gates[3:])
    assert [angle.coefficient for angle in preview.global_phase] == [-7, -7]
    assert CircuitPreview.model_validate_json(preview.model_dump_json()) == preview


@pytest.mark.parametrize("bitstring", ["1", "1000", "10a", "1 0", "١00"])
def test_evaluator_rejects_invalid_width_and_nonbinary_bits(bitstring):
    with pytest.raises(ValueError):
        evaluate_qubo(QUBO(num_variables=3, constant=5, linear=[-2, 1, 3]), bitstring)


def test_evaluator_preserves_leading_zeros_api_order_and_offset():
    qubo = QUBO(num_variables=3, constant=5, linear=[-2, 1, 3])
    assert evaluate_qubo(qubo, "100") == 3
    assert evaluate_qubo(qubo, "001") == 8


@pytest.mark.parametrize("p", [0, 9, True, 1.5])
def test_preview_rejects_invalid_layer_counts(p):
    with pytest.raises(ValueError):
        build_qaoa_preview(QUBO(num_variables=1, linear=[1]), p)


def test_preview_schema_rejects_bad_gates_and_unbound_references():
    with pytest.raises(ValidationError):
        CircuitGate(name="cp", qubits=[0, 0], angle={"parameter": "gamma_0", "coefficient": 1})
    preview = build_qaoa_preview(QUBO(num_variables=1, linear=[1])).model_dump()
    preview["gates"][1]["angle"]["parameter"] = "gamma_1"
    with pytest.raises(ValidationError):
        CircuitPreview.model_validate(preview)


def test_shared_preview_rejects_overflow_in_global_phase():
    with pytest.raises(ValueError, match="global phase"):
        build_qaoa_preview(QUBO(num_variables=2, constant=1e308, linear=[1e308, 1e308]))
    assert math.isfinite(
        build_qaoa_preview(QUBO(num_variables=1, linear=[1e308])).global_phase[0].coefficient
    )
