import pytest
from pydantic import ValidationError

from app.schemas.contracts import MaterialsRequest, RunConfig


@pytest.mark.parametrize(
    "patch",
    [
        {"num_spins": 1},
        {"num_spins": 9},
        {"coupling": float("nan")},
        {"field": float("inf")},
        {"boundary": "unknown"},
        {"config": {"timeout_seconds": 61}},
    ],
)
def test_spin_request_is_small_finite_and_bounded(patch):
    with pytest.raises(ValidationError):
        MaterialsRequest.model_validate(patch)


def test_original_shared_run_config_instance_remains_accepted():
    original = RunConfig(shots=4096, seed=7)
    request = MaterialsRequest(config=original)
    assert request.config.model_dump() == original.model_dump()
    assert request.evolution_time == 1
    assert request.time_samples == 1


def test_null_seed_extension_is_confined_to_materials():
    assert MaterialsRequest(config={"seed": None}).config.seed is None
    with pytest.raises(ValidationError):
        RunConfig(seed=None)
