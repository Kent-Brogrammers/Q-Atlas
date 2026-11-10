"""Verify oracle phases, amplification, and the shared bitstring convention."""

from math import asin, sin, sqrt

import numpy as np
import pytest

pytest.importorskip("qiskit", reason="Install the optional quantum extra")
from qiskit import transpile
from qiskit.quantum_info import Operator, Statevector

from app.experiments.search.circuits import build_grover_circuit, build_phase_oracle


@pytest.mark.parametrize("marked", ["0", "1", "01", "001", "1010"])
def test_oracle_flips_only_target_phase(marked):
    expected = np.ones(2 ** len(marked))
    expected[int(marked[::-1], 2)] = -1
    np.testing.assert_allclose(
        Operator(build_phase_oracle(marked)).data, np.diag(expected), atol=1e-12
    )


@pytest.mark.parametrize("marked", ["01", "001", "1010"])
@pytest.mark.parametrize("iterations", [0, 1, 2, 3, 4, 5])
def test_amplification_matches_theory_including_overshoot(marked, iterations):
    state = Statevector.from_instruction(build_grover_circuit(marked, iterations, measure=False))
    theta = asin(1 / sqrt(2 ** len(marked)))
    actual = state.probabilities()[int(marked[::-1], 2)]
    assert actual == pytest.approx(sin((2 * iterations + 1) * theta) ** 2, abs=1e-12)


def test_aer_counts_convert_to_shared_wire_order():
    aer = pytest.importorskip("qiskit_aer")
    simulator = aer.AerSimulator()
    circuit = transpile(build_grover_circuit("001", 2), simulator, seed_transpiler=42)
    raw = simulator.run(circuit, shots=2048, seed_simulator=42).result().get_counts()
    counts = {key[::-1]: value for key, value in raw.items()}
    assert sum(counts.values()) == 2048
    assert counts.get("001", 0) / 2048 == pytest.approx(0.9453125, abs=0.04)


@pytest.mark.parametrize("marked", ["", "102", "0000000", 3, None])
def test_invalid_targets_are_rejected(marked):
    with pytest.raises(ValueError):
        build_phase_oracle(marked)


@pytest.mark.parametrize("iterations", [-1, 33, True, 1.5])
def test_invalid_iterations_are_rejected(iterations):
    with pytest.raises(ValueError):
        build_grover_circuit("001", iterations)


@pytest.mark.parametrize("targets", [["001", "110"], ["00", "01", "10", "11"]])
@pytest.mark.parametrize("iterations", [0, 1, 2, 3])
def test_multiple_target_circuits_match_exact_amplification(targets, iterations):
    state = Statevector.from_instruction(build_grover_circuit(targets, iterations, measure=False))
    probability = sum(state.probabilities()[int(target[::-1], 2)] for target in targets)
    theta = asin(sqrt(len(targets) / (2 ** len(targets[0]))))
    assert probability == pytest.approx(sin((2 * iterations + 1) * theta) ** 2, abs=1e-12)


@pytest.mark.parametrize("targets", [[], ["001", "001"], ["00", "001"], None])
def test_invalid_target_collections_are_rejected(targets):
    with pytest.raises(ValueError):
        build_grover_circuit(targets, 1)
