"""Independent dense TFIM reference. No Qiskit objects or gate-derived matrices.

H = -J sum Z_i Z_(i+1) - h sum X_i, open chain, hbar = 1.
Array index bits are |q_(N-1)...q_0>; spin i is qubit i (least-significant bit i).
"""

from dataclasses import dataclass
from functools import reduce
from math import isfinite

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm

ComplexArray = NDArray[np.complex128]
IDENTITY = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)


def validate_model(num_spins: int, coupling: float, field: float) -> None:
    if isinstance(num_spins, bool) or not isinstance(num_spins, int) or not 2 <= num_spins <= 4:
        raise ValueError("materials supports 2–4 spins")
    if any(not isfinite(value) or abs(value) > 10 for value in (coupling, field)):
        raise ValueError("coupling and field must be finite and within [-10, 10]")


def spin_operator(num_spins: int, factors: dict[int, ComplexArray]) -> ComplexArray:
    """Kronecker product ordered highest qubit first, independently of Qiskit."""
    return reduce(np.kron, [factors.get(i, IDENTITY) for i in reversed(range(num_spins))])


def build_hamiltonian(num_spins: int, coupling: float, field: float) -> ComplexArray:
    validate_model(num_spins, coupling, field)
    hamiltonian = np.zeros((2**num_spins, 2**num_spins), dtype=complex)
    for i in range(num_spins - 1):
        hamiltonian -= coupling * spin_operator(num_spins, {i: Z, i + 1: Z})
    for i in range(num_spins):
        hamiltonian -= field * spin_operator(num_spins, {i: X})
    return hamiltonian


def initial_state(num_spins: int) -> ComplexArray:
    state = np.zeros(2**num_spins, dtype=complex)
    state[0] = 1
    return state


def evolve_exact(hamiltonian: ComplexArray, evolution_time: float) -> ComplexArray:
    """Dense matrix exponential; exact evolution up to floating-point error, no Trotter split."""
    if not isfinite(evolution_time) or not 0 <= evolution_time <= 10:
        raise ValueError("evolution_time must be finite and within [0, 10]")
    state = np.zeros(hamiltonian.shape[0], dtype=complex)
    state[0] = 1
    return expm(-1j * hamiltonian * evolution_time) @ state


@dataclass(frozen=True)
class Observables:
    per_spin_z: list[float]
    per_spin_x: list[float]
    magnetization_z: float
    zz_correlations: list[float]
    energy: float
    state_norm: float | None


def state_observables(
    state: ComplexArray,
    num_spins: int,
    coupling: float,
    field: float,
) -> Observables:
    """Matrix expectations: Mz is mean Pauli Z per spin; energy is total, not per spin."""
    validate_model(num_spins, coupling, field)
    if state.shape != (2**num_spins,):
        raise ValueError("state dimension does not match num_spins")
    norm = float(np.linalg.norm(state))
    if not np.isfinite(state).all() or not np.isclose(norm, 1, atol=1e-9, rtol=0):
        raise ValueError("state must be finite and normalized")

    def expectation(operator: ComplexArray) -> float:
        return float(np.vdot(state, operator @ state).real)

    z_values = [expectation(spin_operator(num_spins, {i: Z})) for i in range(num_spins)]
    x_values = [expectation(spin_operator(num_spins, {i: X})) for i in range(num_spins)]
    correlations = [
        expectation(spin_operator(num_spins, {i: Z, i + 1: Z})) for i in range(num_spins - 1)
    ]
    return Observables(
        per_spin_z=z_values,
        per_spin_x=x_values,
        magnetization_z=float(np.mean(z_values)),
        zz_correlations=correlations,
        energy=expectation(build_hamiltonian(num_spins, coupling, field)),
        state_norm=norm,
    )
