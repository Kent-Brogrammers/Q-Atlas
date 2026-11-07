import numpy as np
import pytest
from qiskit import QuantumCircuit

from app.experiments.materials.circuits import (
    count_expectations,
    make_simulator,
    measured_observables,
    measurement_circuits,
)
from app.experiments.materials.experiment import run_experiment
from app.schemas.contracts import MaterialsRequest


def test_counts_decode_asymmetric_state_into_spin_zero_first():
    means, correlations = count_expectations({"001": 7, "011": 3}, 3)
    assert means == pytest.approx([-1, 0.4, 1])
    assert correlations == pytest.approx([-0.4, 0.4])


@pytest.mark.parametrize("counts", [{}, {"2": 1}, {"00": -1}, {"001": 1}])
def test_invalid_counts_are_rejected(counts):
    with pytest.raises(ValueError):
        count_expectations(counts, 2)


def test_x_basis_rotation_measures_plus_and_minus_eigenstates():
    circuit = QuantumCircuit(2)
    circuit.x(1)
    circuit.h([0, 1])  # q0 = |+>, q1 = |->
    z_circuit, x_circuit = measurement_circuits(circuit)
    sampled = make_simulator().run([z_circuit, x_circuit], shots=256, seed_simulator=42).result()
    assert sampled.get_counts(1) == {"10": 256}
    observed = measured_observables(sampled.get_counts(0), sampled.get_counts(1), 2, 0, 1)
    assert observed.per_spin_x == [1, -1]
    assert observed.energy == 0
    assert observed.state_norm is None


def test_shot_energy_uses_x_terms_as_well_as_zz_terms():
    observed = measured_observables({"00": 100}, {"10": 100}, 2, 1.5, 0.7)
    assert observed.energy == pytest.approx(-1.5)  # +1 and -1 X contributions cancel
    observed = measured_observables({"00": 100}, {"00": 100}, 2, 1.5, 0.7)
    assert observed.energy == pytest.approx(-1.5 - 2 * 0.7)


@pytest.mark.parametrize("n", [2, 3, 4])
def test_seeded_sampling_matches_ideal_with_statistical_tolerances(n):
    shots, j, h = 8192, 0.9, 0.6
    result = run_experiment(
        MaterialsRequest(
            num_spins=n,
            coupling=j,
            field=h,
            evolution_time=0.6,
            trotter_steps=32,
            config={"shots": shots, "seed": 120},
        )
    )
    point = result.metrics.time_series[0]
    tolerance = 6 / np.sqrt(shots)  # worst-case standard error of a bounded +/-1 observable
    for measured, ideal in [
        (point.measured.per_spin_z, point.ideal.per_spin_z),
        (point.measured.per_spin_x, point.ideal.per_spin_x),
        (point.measured.zz_correlations, point.ideal.zz_correlations),
    ]:
        np.testing.assert_allclose(measured, ideal, atol=tolerance)
    energy_tolerance = 6 * np.hypot(j * (n - 1), h * n) / np.sqrt(shots)
    assert abs(point.measured.energy - point.ideal.energy) < energy_tolerance
    assert point.trotter_error.magnetization_z < 5e-4
    assert point.exact.state_norm == pytest.approx(1, abs=1e-12)
    assert point.ideal.state_norm == pytest.approx(1, abs=1e-12)
    assert result.metrics.total_shots == 2 * shots
    assert result.quantum.timing.includes_sampling is True
    assert result.quantum.timing.includes_transpilation is True
    assert result.metadata.execution_methods == ["scipy_expm", "aer_statevector", "aer_shots"]


def test_same_seed_reproduces_shot_observables_and_reports_error_components():
    request = MaterialsRequest(observable="magnetization", config={"shots": 512, "seed": 42})
    first, second = run_experiment(request), run_experiment(request)
    assert first.problem_id == second.problem_id
    assert first.metrics.time_series == second.metrics.time_series
    point = first.metrics.time_series[0]
    assert first.metrics.classical_observable == point.exact.magnetization_z
    assert first.metrics.quantum_observable == point.measured.magnetization_z
    assert first.metrics.ideal_observable == point.ideal.magnetization_z
    assert point.total_error.magnetization_z == pytest.approx(
        abs(point.measured.magnetization_z - point.exact.magnetization_z)
    )
    assert point.sampling_error.magnetization_z == pytest.approx(
        abs(point.measured.magnetization_z - point.ideal.magnetization_z)
    )
    assert point.trotter_error.magnetization_z == pytest.approx(
        abs(point.ideal.magnetization_z - point.exact.magnetization_z)
    )
