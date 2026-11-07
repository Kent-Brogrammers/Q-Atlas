import pytest

from app.experiments.optimization.solvers import run_classical
from app.quantum.qaoa import run_qaoa
from app.schemas.contracts import QUBO, GraphInput, QAOAConfig


@pytest.mark.parametrize("runner", [run_qaoa, run_classical])
def test_shared_runners_remain_explicit_stubs(runner, qubo_payload):
    with pytest.raises(NotImplementedError, match="Developer 3"):
        runner(QUBO.model_validate(qubo_payload), QAOAConfig())


@pytest.mark.parametrize(
    "edges",
    [
        [{"i": 0, "j": 1, "coefficient": 1}] * 2,
        [{"i": 0, "j": 0, "coefficient": 1}],
        [{"i": 0, "j": 2, "coefficient": 1}],
    ],
)
def test_graph_rejects_duplicate_self_and_out_of_range_edges(edges):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GraphInput(kind="graph", num_vertices=2, edges=edges)
