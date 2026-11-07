import multiprocessing as mp

import pytest

from app.schemas.contracts import ErrorResponse, MaterialsResult


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "num_spins": 4,
            "coupling": -0.5,
            "field": 0.7,
            "evolution_time": 0.3,
            "trotter_steps": 16,
            "observable": "magnetization",
            "config": {"shots": 256, "seed": 7},
        },
    ],
)
def test_materials_api_returns_real_comparisons(client, payload):
    response = client.post("/api/materials/run", json=payload)
    assert response.status_code == 200, response.text
    result = MaterialsResult.model_validate(response.json())
    assert result.status == "completed"
    assert result.backend == "aer_simulator"
    assert result.metadata.simulated is True
    assert result.classical.algorithm == "scipy_expm"
    assert result.classical.elapsed_ms > 0
    assert result.quantum.elapsed_ms > 0
    assert len(result.metrics.time_series) == 1
    assert result.metrics.absolute_error >= 0
    assert result.metadata.versions["qiskit"]


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"num_spins": 5}, "num_spins"),
        ({"num_spins": 1}, "num_spins"),
        ({"model": "heisenberg"}, "model"),
        ({"boundary": "periodic"}, "boundary"),
        ({"coupling": 11}, "coupling"),
        ({"field": -11}, "field"),
        ({"evolution_time": -0.1}, "evolution_time"),
        ({"evolution_time": 11}, "evolution_time"),
        ({"trotter_steps": 0}, "trotter_steps"),
        ({"trotter_steps": 257}, "trotter_steps"),
        ({"config": {"shots": 0}}, "shots"),
        ({"config": {"shots": 100_001}}, "shots"),
        ({"config": {"seed": -1}}, "seed"),
        ({"unexpected": 0}, "unexpected"),
    ],
)
def test_materials_rejects_invalid_or_unimplemented_options(client, patch, field):
    response = client.post("/api/materials/run", json=patch)
    assert response.status_code == 422
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "VALIDATION_ERROR"
    assert any(field in diagnostic.message for diagnostic in error.error.diagnostics)


def test_runtime_budget_is_enforced_and_worker_is_reaped(client):
    before = {process.pid for process in mp.active_children()}
    response = client.post("/api/materials/run", json={"config": {"timeout_seconds": 0.001}})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "TIMEOUT"
    assert {process.pid for process in mp.active_children()} <= before


def test_other_feature_endpoints_are_still_stubs(client):
    for path, payload in [
        ("/api/compiler/analyze", {"source": "x"}),
        ("/api/compiler/benchmark", {"source": "x"}),
        ("/api/search/run", {"num_qubits": 2, "marked_states": ["00"]}),
        (
            "/api/optimization/run",
            {
                "problem": {
                    "kind": "graph",
                    "num_vertices": 2,
                    "edges": [{"i": 0, "j": 1, "coefficient": 1}],
                }
            },
        ),
    ]:
        response = client.post(path, json=payload)
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"
