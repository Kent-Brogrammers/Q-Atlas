import numpy as np
import pytest
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from app.experiments.neutrinos.circuit import build_circuit
from app.experiments.neutrinos.experiment import run
from app.experiments.neutrinos.model import Experiment, Layer, Parameters
from app.experiments.neutrinos.physics import hamiltonian, numerical


def test_ordered_layers_match_independent_matrix_product():
    p = Parameters(theta=0.4)
    layers = [Layer(distance=0.8, potential=0.1), Layer(distance=1.1, potential=1.4)]
    experiment = Experiment(parameters=p, layers=layers)
    first = expm(-1j * hamiltonian(p, 0.1) * 0.8)
    second = expm(-1j * hamiltonian(p, 1.4) * 1.1)
    expected = second @ first
    np.testing.assert_allclose(Operator(build_circuit(experiment)).data, expected, atol=1e-13)
    np.testing.assert_allclose(numerical(experiment), expected[:, 0], atol=1e-13)
    assert np.linalg.norm(expected[:, 0] - (first @ second)[:, 0]) > 0.1
    result = run(experiment)
    assert result["analytical"] is None
    assert result["numerics"]["state_error_l2"] < 1e-13
    assert result["numerics"]["subdivision_check"]["state_change_l2"] < 1e-13
    assert result["absolute_errors"]["sampling"]["other"] < 3 / np.sqrt(experiment.shots)


@pytest.mark.parametrize("potential", [0, 0.9, 2])
@pytest.mark.parametrize("pieces", [1, 2, 8, 64])
def test_constant_profile_subdivision_invariance(potential, pieces):
    single = Experiment(layers=[Layer(distance=2, potential=potential)])
    divided = Experiment(layers=[Layer(distance=2 / pieces, potential=potential)] * pieces)
    np.testing.assert_allclose(numerical(single), numerical(divided), atol=1e-12)
    np.testing.assert_allclose(
        numerical(single, subdivisions=pieces), numerical(divided), atol=1e-12
    )
    np.testing.assert_allclose(
        Operator(build_circuit(single)).data, Operator(build_circuit(divided)).data, atol=1e-12
    )


def test_empty_layers_and_oversized_profiles_rejected():
    with pytest.raises(ValueError):
        Experiment(layers=[])
    with pytest.raises(ValueError):
        Experiment(layers=[Layer(distance=1)] * 65)


def test_zero_length_layer_does_not_change_state():
    a = Experiment(layers=[Layer(distance=1)])
    b = Experiment(layers=[Layer(distance=0, potential=4), *a.layers])
    np.testing.assert_allclose(numerical(a), numerical(b), atol=1e-14)
