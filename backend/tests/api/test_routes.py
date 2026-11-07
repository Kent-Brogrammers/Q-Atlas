import pytest

from app.schemas.contracts import ErrorResponse, HealthResponse

REQUESTS = [
    (
        "/api/compiler/analyze",
        {"source": "@qatlas.objective(num_bits=1)\ndef cost(x): return x[0]"},
    ),
    ("/api/compiler/benchmark", {"source": "raise RuntimeError('must never execute')"}),
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
    ("/api/search/run", {"num_qubits": 3, "marked_states": ["100"]}),
    ("/api/materials/run", {}),
]


def test_health_is_api_readiness_only(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    health = HealthResponse.model_validate(response.json())
    assert health.status == "ok"
    assert health.backend == "aer_simulator"
    assert health.experiments_ready is False


@pytest.mark.parametrize(("path", "payload"), REQUESTS[2:])
def test_validated_stubs_have_no_measurements(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 501
    error = ErrorResponse.model_validate(response.json())
    assert error.error.code == "NOT_IMPLEMENTED"
    assert set(response.json()) == {"status", "error"}


def test_qubo_request_is_accepted_before_stub(client, qubo_payload):
    response = client.post(
        "/api/optimization/run",
        json={
            "problem": {"kind": "qubo", "qubo": qubo_payload},
        },
    )
    assert response.status_code == 501


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/compiler/analyze", {"source": "x" * 20001}),
        ("/api/compiler/benchmark", {"source": "x", "config": {"shots": 0}}),
        ("/api/optimization/run", {"problem": {"kind": "graph", "num_vertices": 2, "edges": []}}),
        ("/api/search/run", {"num_qubits": 2, "marked_states": ["100"]}),
        ("/api/materials/run", {"num_spins": 100}),
    ],
)
def test_invalid_requests_are_rejected_before_stub(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 422
    assert ErrorResponse.model_validate(response.json()).error.code == "VALIDATION_ERROR"


def test_validation_errors_do_not_echo_source(client):
    source = "private user source that should not appear in validation responses"
    response = client.post("/api/compiler/analyze", json={"source": source, "unexpected": source})
    assert response.status_code == 422
    assert source not in response.text
    assert "input" not in response.json()["error"]


def test_cors_allows_local_frontend_and_rejects_other_origins(client):
    headers = {"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"}
    response = client.options("/api/search/run", headers=headers)
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    headers["Origin"] = "https://unrelated.example"
    response = client.options("/api/search/run", headers=headers)
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [
        ("GET", "/missing", 404, "NOT_FOUND"),
        ("POST", "/api/health", 405, "METHOD_NOT_ALLOWED"),
    ],
)
def test_http_errors_share_the_envelope(client, method, path, status, code):
    response = client.request(method, path)
    assert response.status_code == status
    assert ErrorResponse.model_validate(response.json()).error.code == code


def test_openapi_documents_success_validation_and_not_implemented(client):
    document = client.get("/openapi.json").json()
    for path, _ in REQUESTS:
        responses = document["paths"][path]["post"]["responses"]
        assert {"200", "422", "501"} <= responses.keys()
        assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ErrorResponse"
        )
