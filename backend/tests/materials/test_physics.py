import numpy as np
import pytest
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from app.experiments.materials.circuits import build_trotter_circuit, simulate_statevector
from app.experiments.materials.physics import (
    X,
    Z,
    build_hamiltonian,
    evolve_exact,
    initial_state,
    spin_operator,
    state_observables,
)


@pytest.mark.parametrize("n", [2, 3, 4])
def test_hamiltonian_dimension_hermiticity_and_zero_time(n):
    hamiltonian = build_hamiltonian(n, 1.2, -0.7)
    assert hamiltonian.shape == (2**n, 2**n)
    np.testing.assert_allclose(hamiltonian, hamiltonian.conj().T, atol=1e-14)
    np.testing.assert_allclose(evolve_exact(hamiltonian, 0), initial_state(n), atol=1e-14)
    observed = state_observables(initial_state(n), n, 1.2, -0.7)
    assert observed.magnetization_z == pytest.approx(1)
    assert observed.zz_correlations == pytest.approx([1] * (n - 1))
    assert observed.energy == pytest.approx(-1.2 * (n - 1))


def test_two_spin_hamiltonian_matches_independent_explicit_matrix():
    j, h = 1.3, -0.4
    expected = np.array(
        [
            [-j, -h, -h, 0],
            [-h, j, 0, -h],
            [-h, 0, j, -h],
            [0, -h, -h, -j],
        ]
    )
    np.testing.assert_allclose(build_hamiltonian(2, j, h), expected, atol=1e-14)
    # At zero field the two-spin spectrum is {-J,-J,+J,+J}.
    np.testing.assert_allclose(np.linalg.eigvalsh(build_hamiltonian(2, j, 0)), [-j, -j, j, j])


def test_kronecker_order_maps_spin_zero_to_least_significant_bit():
    np.testing.assert_array_equal(spin_operator(2, {0: Z}), np.kron(np.eye(2), Z))
    np.testing.assert_array_equal(spin_operator(2, {1: X}), np.kron(X, np.eye(2)))
    state = np.array([0, 1, 0, 0], dtype=complex)  # Qiskit |q1 q0> = |01>
    assert state_observables(state, 2, 0, 0).per_spin_z == [-1, 1]


@pytest.mark.parametrize("n", [2, 3, 4])
@pytest.mark.parametrize(("j", "h"), [(0, 0.7), (-1.2, 0), (0, 0)])
def test_commuting_limits_are_exact_even_with_one_trotter_step(n, j, h):
    t = 0.43
    exact = evolve_exact(build_hamiltonian(n, j, h), t)
    circuit = build_trotter_circuit(n, j, h, t, 1)
    ideal = simulate_statevector(circuit)
    np.testing.assert_allclose(ideal, exact, atol=2e-14)
    observed = state_observables(exact, n, j, h)
    assert observed.state_norm == pytest.approx(1, abs=2e-14)
    if j == 0:
        expected_z = np.cos(2 * h * t)
        assert observed.magnetization_z == pytest.approx(expected_z, abs=2e-14)
        assert observed.zz_correlations == pytest.approx([expected_z**2] * (n - 1))
    if h == 0:
        assert observed.magnetization_z == pytest.approx(1)
        assert observed.energy == pytest.approx(-j * (n - 1))


def test_gate_angles_and_matrix_signs_for_one_strang_step():
    j, h, t = 1.2, 0.7, 0.3
    circuit = build_trotter_circuit(2, j, h, t, 1)
    assert [item.operation.name for item in circuit.data] == ["rzz", "rx", "rx", "rzz"]
    assert [float(item.operation.params[0]) for item in circuit.data] == pytest.approx(
        [-j * t, -2 * h * t, -2 * h * t, -j * t]
    )
    zz = np.kron(Z, Z)
    x_sum = np.kron(X, np.eye(2)) + np.kron(np.eye(2), X)
    zz_half = expm(1j * j * t * zz / 2)
    expected = zz_half @ expm(1j * h * t * x_sum) @ zz_half
    np.testing.assert_allclose(Operator(circuit).data, expected, atol=1e-14)


@pytest.mark.parametrize("n", [2, 3, 4])
def test_trotter_converges_to_independent_reference_and_preserves_norm(n):
    j, h, t = 1.0, 0.7, 0.8
    hamiltonian = build_hamiltonian(n, j, h)
    exact = evolve_exact(hamiltonian, t)
    errors = []
    for steps in (4, 8, 16, 32):
        ideal = simulate_statevector(build_trotter_circuit(n, j, h, t, steps))
        assert np.linalg.norm(ideal) == pytest.approx(1, abs=2e-13)
        errors.append(np.linalg.norm(ideal - exact))
    # Second-order global error scales as O(1/r^2) for fixed N,J,h,t.
    assert all(fine < coarse / 3.5 for coarse, fine in zip(errors, errors[1:], strict=False))
    assert errors[-1] < 5e-4
    assert state_observables(exact, n, j, h).energy == pytest.approx(-j * (n - 1), abs=1e-13)


def test_zero_time_circuit_is_identity():
    circuit = build_trotter_circuit(2, 1, 0.5, 0, 20)
    assert len(circuit.data) == 0
    np.testing.assert_allclose(simulate_statevector(circuit), initial_state(2), atol=1e-14)
