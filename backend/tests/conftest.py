import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def qubo_payload():
    return {
        "num_variables": 3,
        "constant": 0.0,
        "linear": [10.0, 20.0, 0.0],
        "quadratic": [{"i": 0, "j": 1, "coefficient": 15.0}],
        "sense": "minimize",
    }
