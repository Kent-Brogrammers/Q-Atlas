import pytest
from pydantic import ValidationError

from app.schemas.contracts import MaterialsRequest


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
