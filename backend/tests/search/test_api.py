"""Search HTTP integration, including real worker runs and sanitized failures."""

import multiprocessing as mp
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.api import search
from app.experiments.search.runner import SearchDependencyError
from app.main import app
from app.schemas.contracts import ErrorResponse, SearchResult


@pytest.mark.parametrize(
    "payload",
    [
        {"num_qubits": 3, "marked_states": ["001"]},
        {"num_qubits": 3, "marked_states": ["001", "110"], "iterations": 1},
        {"num_qubits": 2, "marked_states": ["00", "01", "10", "11"], "iterations": 0},
    ],
)
def test_real_search_response_matches_shared_contract(client, payload):
    pytest.importorskip("qiskit_aer")
    response = client.post("/api/search/run", json=payload)
    assert response.status_code == 200, response.text
    result = SearchResult.model_validate(response.json())
    assert result.status == "completed"
    assert result.metadata.simulated
    assert result.classical.best_bitstring == min(payload["marked_states"])
    assert result.metrics.success_probability == pytest.approx(
        result.metrics.theoretical_success_probability, abs=0.06
    )
    assert result.quantum.elapsed_ms > 0
    assert result.quantum.objective is None
    assert (
        result.metrics.successful_shots / result.metrics.shots == result.metrics.success_probability
    )
    assert result.metrics.classical_observed_queries == int(min(payload["marked_states"]), 2) + 1
    assert result.metrics.quantum_total_oracle_queries == (
        result.metrics.quantum_oracle_queries * result.metrics.shots
    )
    assert result.metadata.parameters.iterations is not None
    assert result.metrics.circuit_gate_counts
    assert "measure" not in result.metrics.circuit_gate_counts


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"num_qubits": 7, "marked_states": ["0000000"]}, "num_qubits"),
        ({"iterations": 33}, "iterations"),
        ({"config": {"shots": 10001}}, "shots"),
        ({"marked_states": []}, "marked_states"),
        ({"marked_states": ["001", "001"]}, "body"),
        ({"marked_states": ["abc"]}, "marked_states"),
        ({"marked_states": ["01"]}, "body"),
        ({"iterations": -1}, "iterations"),
        ({"config": {"shots": 0}}, "shots"),
        ({"config": {"seed": -1}}, "seed"),
        ({"config": {"timeout_seconds": 0}}, "timeout_seconds"),
        ({"unexpected": "private-value"}, "unexpected"),
    ],
)
def test_invalid_requests_never_reach_the_runner(client, monkeypatch, patch, field):
    def unexpected_run(request):
        pytest.fail("invalid requests must not invoke the runner")

    monkeypatch.setattr(search, "run_search", unexpected_run)
    payload = {"num_qubits": 3, "marked_states": ["001"], **patch}
    response = client.post("/api/search/run", json=payload)
    assert response.status_code == 422
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "VALIDATION_ERROR"
    assert any(field in item.message for item in error.error.diagnostics)
    assert "private-value" not in response.text
    assert "quantum" not in response.json()


@pytest.mark.parametrize(
    ("exception", "status", "code"),
    [
        (TimeoutError("private detail"), 504, "TIMEOUT"),
        (SearchDependencyError("private detail"), 503, "HTTP_ERROR"),
    ],
)
def test_expected_runner_errors_have_sanitized_envelopes(
    client, monkeypatch, exception, status, code
):
    def fail(request):
        raise exception

    monkeypatch.setattr(search, "run_search", fail)
    response = client.post("/api/search/run", json={"num_qubits": 2, "marked_states": ["01"]})
    assert response.status_code == status
    assert ErrorResponse.model_validate(response.json()).error.code == code
    assert "private detail" not in response.text
    assert set(response.json()) == {"status", "error"}


def test_unexpected_worker_failure_uses_shared_500_handler(monkeypatch):
    def fail(request):
        raise RuntimeError("private internal worker details")

    monkeypatch.setattr(search, "run_search", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/search/run", json={"num_qubits": 2, "marked_states": ["01"]})
    assert response.status_code == 500
    assert ErrorResponse.model_validate(response.json()).error.code == "INTERNAL_ERROR"
    assert "private internal" not in response.text


def test_real_api_timeout_reaps_simulator_worker(client):
    before = {child.pid for child in mp.active_children()}
    response = client.post(
        "/api/search/run",
        json={"num_qubits": 3, "marked_states": ["001"], "config": {"timeout_seconds": 0.000001}},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "TIMEOUT"
    assert {child.pid for child in mp.active_children()} == before


def test_search_openapi_includes_dependency_and_timeout_errors(client):
    operation = client.get("/openapi.json").json()["paths"]["/api/search/run"]["post"]
    responses = operation["responses"]
    assert {"200", "422", "500", "503", "504"} <= responses.keys()
    for status in ("422", "503", "504"):
        assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ErrorResponse"
        )


def test_api_starts_without_importing_optional_quantum_packages():
    # A clean interpreter avoids hiding eager imports behind the test suite's cache.
    code = """
import importlib.abc
import sys

class NoQuantum(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'qiskit', 'qiskit_aer', 'numpy', 'scipy'}:
            raise ImportError('optional dependency blocked for startup test')

sys.meta_path.insert(0, NoQuantum())
from app.main import app
assert app.title == 'Q-Atlas API'
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
