import numpy as np
import pytest
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from app.experiments.neutrinos.circuit import build_circuit
from app.experiments.neutrinos.experiment import density_sweep, run
from app.experiments.neutrinos.model import Experiment, Layer, Parameters
from app.experiments.neutrinos.physics import analytical, hamiltonian, numerical, probabilities


@pytest.mark.parametrize("particle", ["neutrino", "antineutrino"])
@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("potential", [0, 0.4, 2])
def test_constant_density_reference_and_gate_matrix(particle, delta, potential):
    p = Parameters(particle=particle, delta_m2=delta)
    layer = Layer(distance=0.7, potential=potential)
    experiment = Experiment(parameters=p, layers=[layer])
    matrix = hamiltonian(p, potential)
    np.testing.assert_allclose(matrix, matrix.conj().T)
    np.testing.assert_allclose(
        Operator(build_circuit(experiment)).data, expm(-1j * matrix * layer.distance), atol=1e-13
    )
    assert probabilities(numerical(experiment))["other"] == pytest.approx(
        analytical(p, layer)["other"], abs=1e-13
    )


@pytest.mark.parametrize(("particle", "delta"), [("neutrino", 1), ("antineutrino", -1)])
def test_resonance_and_distinct_conversion_maximum(particle, delta):
    p = Parameters(particle=particle, delta_m2=delta)
    resonance = np.cos(2 * p.theta)
    for offset in [-0.2, 0, 0.2]:
        a = analytical(p, Layer(distance=0.7, potential=resonance + offset))
        assert a["mixing_strength"] == pytest.approx(1) if offset == 0 else a["mixing_strength"] < 1
    short = analytical(p, Layer(distance=0.7, potential=resonance))
    assert short["other"] < 0.1
    optimum = Layer(distance=np.pi / (2 * np.sin(2 * p.theta)), potential=resonance)
    result = run(Experiment(parameters=p, layers=[optimum], shots=256))
    assert result["ideal"]["other"] == pytest.approx(1, abs=1e-13)
    assert result["measured"]["other"] == 1


def test_wrong_particle_sign_does_not_resonate_at_positive_potential():
    p = Parameters(particle="antineutrino")
    assert analytical(p, Layer(distance=1, potential=np.cos(2 * p.theta)))["mixing_strength"] < 0.1


def test_zero_mixing_in_matter_and_degenerate_hamiltonian():
    p = Parameters(theta=0)
    for potential in (0, 1, 2):
        result = analytical(p, Layer(distance=4, potential=potential))
        assert result["other"] == 0
        if potential == 1:
            assert result["mixing_strength"] is None


def test_density_sweep_includes_resonance_and_reports_both_flavors():
    e = Experiment(layers=[Layer(distance=0.7)], shots=128)
    results = density_sweep(e, [0, float(np.cos(0.4)), 2])
    assert results[1]["analytical"]["mixing_strength"] == pytest.approx(1)
    for r in results:
        assert sum(r["ideal"].values()) == pytest.approx(1)
        assert r["absolute_errors"]["ideal_vs_numerical"]["other"] < 1e-13
    with pytest.raises(ValueError):
        density_sweep(e, [-1])
