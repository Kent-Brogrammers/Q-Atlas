"""Second-order Suzuki–Trotter TFIM circuits on the noiseless local Aer simulator."""

from math import isfinite

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.library import SaveStatevector

from app.experiments.materials.physics import ComplexArray, Observables, validate_model


def build_trotter_circuit(
    num_spins: int,
    coupling: float,
    field: float,
    evolution_time: float,
    trotter_steps: int,
) -> QuantumCircuit:
    """Each step applies ZZ half-step, X full-step, ZZ half-step to |0...0>.

    RX(theta)=exp(-i theta X/2), RZZ(theta)=exp(-i theta ZZ/2).
    Thus RX(-2 h dt) and half-step RZZ(-J dt) implement the negative TFIM terms.
    """
    validate_model(num_spins, coupling, field)
    if not isfinite(evolution_time) or not 0 <= evolution_time <= 10:
        raise ValueError("evolution_time must be finite and within [0, 10]")
    if (
        isinstance(trotter_steps, bool)
        or not isinstance(trotter_steps, int)
        or not 1 <= trotter_steps <= 256
    ):
        raise ValueError("trotter_steps must be an integer within [1, 256]")
    circuit = QuantumCircuit(num_spins, name="tfim_strang")
    if evolution_time == 0:
        return circuit
    dt = evolution_time / trotter_steps
    for _ in range(trotter_steps):
        if coupling != 0:
            for i in range(num_spins - 1):
                circuit.rzz(-coupling * dt, i, i + 1)
        if field != 0:
            circuit.rx(-2 * field * dt, range(num_spins))
        if coupling != 0:
            for i in range(num_spins - 1):
                circuit.rzz(-coupling * dt, i, i + 1)
    return circuit


def make_simulator() -> AerSimulator:
    # Small problems do not benefit from many OpenMP threads; limit per-request resources.
    return AerSimulator(
        method="statevector",
        device="CPU",
        precision="double",
        max_parallel_threads=1,
        max_parallel_experiments=1,
    )


def simulate_statevector(
    circuit: QuantumCircuit,
    simulator: AerSimulator | None = None,
) -> ComplexArray:
    saved = circuit.copy()
    saved.append(SaveStatevector(circuit.num_qubits), range(circuit.num_qubits))
    result = (simulator or make_simulator()).run(saved, shots=1).result()
    if not result.success:
        raise RuntimeError("Aer statevector simulation failed")
    return np.asarray(result.get_statevector(0), dtype=complex)


def measurement_circuits(circuit: QuantumCircuit) -> tuple[QuantumCircuit, QuantumCircuit]:
    """Measure all Z terms together; H before measurement gives all X terms."""
    z_circuit = circuit.copy()
    z_circuit.measure_all()
    x_circuit = circuit.copy()
    x_circuit.h(range(circuit.num_qubits))
    x_circuit.measure_all()
    return z_circuit, x_circuit


def count_expectations(counts: dict[str, int], num_spins: int) -> tuple[list[float], list[float]]:
    """Decode Aer q_(N-1)...q_0 strings into spin 0 first; preserve leading zeros."""
    shots = sum(counts.values())
    if shots <= 0:
        raise ValueError("measurement counts must contain shots")
    means = np.zeros(num_spins)
    correlations = np.zeros(num_spins - 1)
    for bitstring, count in counts.items():
        if len(bitstring) != num_spins or set(bitstring) - {"0", "1"} or count < 0:
            raise ValueError("invalid measurement counts")
        spins = np.array([1 if bit == "0" else -1 for bit in reversed(bitstring)])
        means += count * spins
        correlations += count * spins[:-1] * spins[1:]
    return (means / shots).tolist(), (correlations / shots).tolist()


def measured_observables(
    z_counts: dict[str, int],
    x_counts: dict[str, int],
    num_spins: int,
    coupling: float,
    field: float,
) -> Observables:
    """Energy uses both settings: -J sum <ZZ>_Z - h sum <X>_X."""
    z_values, correlations = count_expectations(z_counts, num_spins)
    x_values, _ = count_expectations(x_counts, num_spins)
    return Observables(
        per_spin_z=z_values,
        per_spin_x=x_values,
        magnetization_z=float(np.mean(z_values)),
        zz_correlations=correlations,
        energy=-coupling * sum(correlations) - field * sum(x_values),
        state_norm=None,  # finite-shot samples do not measure the statevector norm
    )
