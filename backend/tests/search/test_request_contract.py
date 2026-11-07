import pytest
from pydantic import ValidationError

from app.schemas.contracts import SearchRequest


@pytest.mark.parametrize("states", [["1"], ["102"], ["100", "100"], []])
def test_marked_states_are_unique_binary_strings_of_declared_width(states):
    with pytest.raises(ValidationError):
        SearchRequest(num_qubits=3, marked_states=states)


def test_marked_state_preserves_leading_zero_and_wire_order():
    request = SearchRequest(num_qubits=3, marked_states=["001"])
    assert request.marked_states == ["001"]
    assert request.iterations is None  # owner chooses a documented iteration rule later
