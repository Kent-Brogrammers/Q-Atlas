import json
from pathlib import Path

import numpy as np
import pytest

from app.experiments.materials.experiment import run_experiment
from app.experiments.materials.runner import request_diagnostics
from app.schemas.contracts import MaterialsRequest, MaterialsResult


def test_small_sweep_has_independent_evolutions_and_terminal_summary():
    request = MaterialsRequest(
        num_spins=3,
        evolution_time=1,
        time_samples=5,
        trotter_steps=32,
        observable="magnetization",
        config={"seed": 42, "shots": 128},
    )
    result = run_experiment(request)
    points = result.metrics.time_series
    assert [point.time for point in points] == pytest.approx([0, 0.25, 0.5, 0.75, 1])
    assert points[0].exact.magnetization_z == pytest.approx(1)
    assert points[0].ideal.magnetization_z == pytest.approx(1)
    assert points[0].measured.magnetization_z == 1
    assert result.metrics.classical_observable == points[-1].exact.magnetization_z
    assert result.metrics.ideal_observable == points[-1].ideal.magnetization_z
    assert result.metrics.quantum_observable == points[-1].measured.magnetization_z
    assert result.metrics.total_shots == 2 * 5 * 128
    assert result.metrics.circuit_depth == max(point.circuit_depth for point in points)
    assert result.metadata.repetitions == 1  # a time grid is not repeated independent trials
    for point in points:
        assert point.exact.energy == pytest.approx(-2, abs=1e-12)
        assert point.exact.state_norm == pytest.approx(1, abs=1e-12)
        assert point.ideal.state_norm == pytest.approx(1, abs=1e-12)
    terminal = run_experiment(request.model_copy(update={"time_samples": 1})).metrics.time_series[0]
    assert points[-1].exact == terminal.exact
    assert points[-1].ideal == terminal.ideal


def test_sweep_seed_policy_handles_unsigned_wraparound_and_null():
    for seed in (2**32 - 1, None):
        request = MaterialsRequest(time_samples=3, config={"seed": seed, "shots": 64})
        result = run_experiment(request)
        assert result.metadata.seed == seed
        assert len(result.metrics.time_series) == 3
        if seed is not None:
            repeated = run_experiment(request)
            assert repeated.metrics.time_series == result.metrics.time_series


def test_instance_id_does_not_depend_on_seed_shots_or_trotter_resolution():
    first = run_experiment(MaterialsRequest(config={"shots": 64, "seed": 1}))
    second = run_experiment(MaterialsRequest(trotter_steps=8, config={"shots": 128, "seed": 2}))
    assert first.problem_id == second.problem_id


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"time_samples": 0}, "time_samples"),
        ({"time_samples": 22}, "time_samples"),
        ({"time_samples": 9, "trotter_steps": 256}, "trotter_steps"),
        ({"time_samples": 6, "config": {"shots": 100_000}}, "shots"),
        ({"time_samples": 3, "evolution_time": 0}, "evolution_time"),
    ],
)
def test_api_rejects_oversized_or_degenerate_sweeps(client, payload, field):
    response = client.post("/api/materials/run", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert any(field in item["message"] for item in response.json()["error"]["diagnostics"])


def test_runtime_limits_accept_their_boundaries():
    assert (
        request_diagnostics(
            MaterialsRequest(
                num_spins=4,
                coupling=-10,
                field=10,
                evolution_time=10,
                time_samples=8,
                trotter_steps=256,
            )
        )
        == []
    )
    assert request_diagnostics(MaterialsRequest(time_samples=5, config={"shots": 100_000})) == []


def test_documented_sweep_runs_through_api(client):
    example = Path(__file__).resolve().parents[2] / "examples" / "materials_request.json"
    payload = json.loads(example.read_text())
    response = client.post("/api/materials/run", json=payload)
    assert response.status_code == 200, response.text
    result = MaterialsResult.model_validate(response.json())
    assert len(result.metrics.time_series) == payload["time_samples"]
    assert np.isfinite(result.metrics.quantum_observable)
