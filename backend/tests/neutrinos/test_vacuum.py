import numpy as np
import pytest
from pydantic import ValidationError
from qiskit.quantum_info import Operator, Statevector
from scipy.linalg import expm

from app.experiments.neutrinos.circuit import build_circuit
from app.experiments.neutrinos.model import Experiment, Layer, Parameters
from app.experiments.neutrinos.physics import analytical, hamiltonian, numerical, probabilities


@pytest.mark.parametrize("theta", [0, 0.2, np.pi / 4, np.pi / 2])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_vacuum_three_independent_paths(theta, delta):
    p = Parameters(theta=theta, delta_m2=delta, energy=1.7)
    layer = Layer(distance=2.3)
    experiment = Experiment(parameters=p, layers=[layer])
    expected = np.sin(2 * theta) ** 2 * np.sin(delta * layer.distance / p.energy) ** 2
    reference = numerical(experiment)
    circuit = build_circuit(experiment)
    ideal = Statevector.from_instruction(circuit).data
    assert analytical(p, layer)["other"] == pytest.approx(expected, abs=1e-13)
    assert probabilities(reference)["other"] == pytest.approx(expected, abs=1e-13)
    np.testing.assert_allclose(ideal, reference, atol=1e-13)
    assert np.linalg.norm(ideal) == pytest.approx(1, abs=1e-13)
    np.testing.assert_allclose(
        Operator(circuit).data, expm(-1j * hamiltonian(p, 0) * 2.3), atol=1e-13
    )
    assert circuit.num_qubits == 1
    assert set(circuit.count_ops()) <= {"ry", "rz"}


def test_zero_distance_and_maximal_conversion():
    e = Experiment(parameters=Parameters(theta=np.pi / 4), layers=[Layer(distance=0)])
    np.testing.assert_allclose(numerical(e), [1, 0], atol=1e-14)
    assert build_circuit(e).depth() == 0
    assert analytical(e.parameters, Layer(distance=np.pi / 2))["other"] == pytest.approx(1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"energy": 0},
        {"theta": -1},
        {"theta": 2},
        {"delta_m2": float("nan")},
        {"particle": "unknown"},
    ],
)
def test_invalid_parameters(kwargs):
    with pytest.raises(ValidationError):
        Parameters(**kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"distance": -1}, {"distance": float("inf")}, {"distance": 1, "potential": -1}]
)
def test_invalid_layer(kwargs):
    with pytest.raises(ValidationError):
        Layer(**kwargs)


def test_aer_vacuum_sampling_and_repeatability():
    from app.experiments.neutrinos.experiment import run

    experiment = Experiment(layers=[Layer(distance=1.3)], shots=8192)
    result = run(experiment)
    assert result["ideal"]["other"] == pytest.approx(result["analytical"]["other"], abs=1e-13)
    assert result["absolute_errors"]["sampling"]["other"] < 6 * 0.5 / np.sqrt(experiment.shots)
    assert sum(result["measured"].values()) == pytest.approx(1)
    assert sum(result["counts"].values()) == experiment.shots
    assert result["counts"] == run(experiment)["counts"]
