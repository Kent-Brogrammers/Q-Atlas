import multiprocessing as mp

import numpy as np
import pytest

from app.experiments.neutrinos.model import Experiment, Layer, Parameters
from app.experiments.neutrinos.physics import numerical, probabilities
from app.experiments.neutrinos.runner import NeutrinoDependencyError
from app.experiments.neutrinos.web import run_curve
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


@pytest.mark.parametrize("potential", [0, 0.9])
def test_real_api_curve(client, potential):
    response = client.post(
        "/api/neutrinos/run",
        json={
            "experiment": {"layers": [{"distance": 2, "potential": potential}], "shots": 128},
            "samples": 3,
        },
    )
    assert response.status_code == 200, response.text
    result = NeutrinoResponse.model_validate(response.json())
    assert result.units == "normalized"
    assert result.coordinates == [0, 1, 2]
    assert result.results[0].measured.electron == 1
    for point in result.results:
        assert point.absolute_errors.ideal_vs_numerical.other < 1e-13
        assert sum(point.counts.values()) == 128


def test_distance_curve_traverses_layers_without_scaling_entire_profile():
    experiment = Experiment(
        parameters=Parameters(theta=0.4),
        layers=[Layer(distance=1, potential=0.1), Layer(distance=1, potential=1.4)],
        shots=128,
    )
    result = run_curve(NeutrinoRequest(experiment=experiment, samples=5))
    midpoint = result.results[2]
    assert midpoint.configuration.layers == [experiment.layers[0]]
    expected = probabilities(
        numerical(Experiment(layers=[experiment.layers[0]], parameters=experiment.parameters))
    )
    assert midpoint.numerical.other == pytest.approx(expected["other"], abs=1e-13)
    assert result.results[-1].configuration.layers == experiment.layers


def test_api_density_sweep_captures_resonance(client):
    resonance = float(np.cos(0.4))
    response = client.post(
        "/api/neutrinos/run",
        json={
            "experiment": {
                "layers": [{"distance": float(np.pi / (2 * np.sin(0.4)))}],
                "shots": 128,
            },
            "axis": "potential",
            "samples": 3,
            "max_potential": 2 * resonance,
        },
    )
    assert response.status_code == 200, response.text
    result = NeutrinoResponse.model_validate(response.json())
    assert result.coordinates[1] == pytest.approx(resonance)
    assert result.results[1].analytical.mixing_strength == pytest.approx(1)
    assert result.results[1].measured.other == 1


def test_zero_distance_and_zero_extent_have_one_real_point():
    request = NeutrinoRequest(experiment=Experiment(layers=[Layer(distance=0)], shots=16))
    result = run_curve(request)
    assert result.coordinates == [0]
    assert result.results[0].measured.electron == 1


@pytest.mark.parametrize(
    "patch",
    [
        {"samples": 42},
        {"samples": 41, "experiment": {"shots": 100000, "layers": [{"distance": 1}]}},
        {"axis": "potential", "experiment": {"layers": [{"distance": 1}, {"distance": 1}]}},
        {"experiment": {"layers": [{"distance": 60}, {"distance": 60}]}},
        {"max_potential": -1},
        {"experiment": {"layers": [{"distance": 1}], "parameters": {"energy": 0}}},
    ],
)
def test_api_validation_rejects_invalid_or_excessive_work(client, patch):
    payload = {"experiment": {"layers": [{"distance": 1}]}, **patch}
    response = client.post("/api/neutrinos/run", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("exception", "status"),
    [
        (NeutrinoDependencyError(), 503),
        (TimeoutError(), 504),
    ],
)
def test_api_reports_dependency_and_timeout_errors(client, monkeypatch, exception, status):
    def fail(_):
        raise exception

    monkeypatch.setattr("app.api.neutrinos.run_neutrinos", fail)
    response = client.post("/api/neutrinos/run", json={"experiment": {"layers": [{"distance": 1}]}})
    assert response.status_code == status
    assert response.json()["status"] == "error"


def test_web_worker_timeout_is_reaped(client):
    before = {process.pid for process in mp.active_children()}
    response = client.post(
        "/api/neutrinos/run",
        json={
            "experiment": {"layers": [{"distance": 1}]},
            "timeout_seconds": 0.01,
        },
    )
    assert response.status_code == 504
    assert {process.pid for process in mp.active_children()} <= before


def test_inspection_data_matches_executed_state_and_rotations():
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    experiment = Experiment(
        layers=[Layer(distance=1, potential=0.2), Layer(distance=1, potential=1.4)], shots=128
    )
    response = run_curve(NeutrinoRequest(experiment=experiment, samples=3))
    assert response.resonance_potential == pytest.approx(np.cos(0.4))
    record = response.results[-1]
    circuit = QuantumCircuit(1)
    for rotation in record.rotations:
        getattr(circuit, rotation.gate)(rotation.angle, 0)
    amplitudes = np.array([complex(*pair) for pair in record.statevector])
    np.testing.assert_allclose(Statevector(circuit).data, amplitudes, atol=1e-13)
    assert abs(amplitudes[1]) ** 2 == pytest.approx(record.ideal.other)
    assert record.ideal.other == pytest.approx(0.4361827, abs=1e-6)
    assert record.circuit_diagram == str(circuit.measure_all(inplace=False).draw("text", fold=-1))


def test_zero_mixing_endpoint_in_cancelling_matter_is_degenerate():
    experiment = Experiment(
        parameters=Parameters(theta=np.pi / 2, particle="antineutrino"),
        layers=[Layer(distance=1, potential=1)],
        shots=32,
    )
    point = run_curve(NeutrinoRequest(experiment=experiment, samples=2)).results[-1]
    assert point.analytical.frequency == 0
    assert point.analytical.mixing_strength is None
    assert point.analytical.theta_m is None
    assert point.ideal.electron == 1
    assert point.rotations == []
