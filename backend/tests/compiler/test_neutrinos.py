"""Scientific compiler tests. Sources are parsed as data; no uploaded Python executes."""

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest
from qiskit import qasm2
from qiskit.quantum_info import Statevector

from app.compiler.analysis import Rejected
from app.compiler.neutrinos import _literal, compile_neutrino, parse_neutrino
from app.experiments.neutrinos.physics import numerical
from app.experiments.neutrinos.web import curve_points
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse

SOURCE = (
    Path(__file__).resolve().parents[3] / "examples/compiler/programs/neutrino_simulation.py"
).read_text()


def declaration(payload):
    return f"@qatlas.neutrino\ndef propagation():\n    return {payload!r}\n"


def test_exported_circuits_and_reference_use_exactly_the_same_curve_inputs():
    compiled = compile_neutrino(SOURCE)
    tree = ast.parse(compiled.artifact.source)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign))
    exported = _literal(assignment.value)
    assert len(exported) == compiled.request.samples == 9
    assert compiled.artifact.executed is False
    assert compiled.artifact.entrypoint == "compare_neutrinos"
    for record, (coordinate, experiment) in zip(
        exported, curve_points(compiled.request), strict=True
    ):
        assert record["coordinate"] == coordinate
        assert record["experiment"] == experiment.model_dump(mode="json")
        state = Statevector.from_instruction(qasm2.loads(record["qasm"]))
        assert abs(abs(state[1]) ** 2 - abs(numerical(experiment)[1]) ** 2) < 1e-13
    assert (
        abs(abs(Statevector.from_instruction(qasm2.loads(exported[4]["qasm"]))[1]) ** 2 - 1) < 1e-13
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"experiment": {"layers": [{"distance": 0}]}, "samples": 2},
        {
            "experiment": {
                "layers": [{"distance": 1, "potential": 0.3}, {"distance": 2, "potential": 1.2}],
                "seed": 4294967295,
            },
            "samples": 5,
        },
        {
            "experiment": {
                "parameters": {"particle": "antineutrino", "delta_m2": -1},
                "layers": [{"distance": 2}],
            },
            "samples": 3,
        },
    ],
)
def test_layered_zero_distance_and_antineutrino_exports(payload):
    compiled = compile_neutrino(declaration(payload))
    points = curve_points(compiled.request)
    assert points[-1][1].layers == compiled.request.experiment.layers
    for _, experiment in points:
        assert 0 <= experiment.seed < 2**32
    ast.parse(compiled.artifact.source)


@pytest.mark.parametrize(
    "source",
    [
        "import os\n@qatlas.neutrino\ndef f(): return {}",
        "@qatlas.neutrino()\ndef f(): return {}",
        "@qatlas.neutrino\nasync def f(): return {}",
        "@qatlas.neutrino\ndef f(x=print('bad')): return {}",
        "@qatlas.neutrino\ndef f() -> int: return {}",
        "@qatlas.neutrino\ndef f(): return {'experiment': dict()}",
        "@qatlas.neutrino\ndef f(): return {'experiment': {**{'layers':[]}}}",
        "@qatlas.neutrino\ndef f(): return {'experiment': {}, 'experiment': {}}",
        "@qatlas.neutrino\ndef f(): return {'experiment': [x for x in [1]]}",
        "@qatlas.neutrino\ndef f():\n x=1\n return {}",
        "@qatlas.neutrino\ndef f(): return "
        "{'experiment': {'layers':[{'distance':1}]}, 'samples':42}",
        "@qatlas.neutrino\ndef f(): return {'experiment': {'layers':[{'distance':101}]}}",
        "@qatlas.neutrino\ndef f(): return "
        "{'experiment': {'layers':[{'distance':1}], 'shots':100000}, 'samples':41}",
    ],
)
def test_nonliteral_code_invalid_parameters_and_excessive_work_are_rejected(source):
    with pytest.raises(Rejected):
        parse_neutrino(source)


def test_malicious_call_is_never_executed(tmp_path):
    sentinel = tmp_path / "must-not-exist"
    source = (
        f"@qatlas.neutrino\ndef f(): return __import__('pathlib').Path({str(sentinel)!r}).touch()"
    )
    with pytest.raises(Rejected):
        compile_neutrino(source)
    assert not sentinel.exists()


def test_science_compiler_api_runs_real_same_instance_reference_and_aer(client):
    response = client.post("/api/compiler/neutrinos/generate", json={"source": SOURCE})
    assert response.status_code == 200, response.text
    request = NeutrinoRequest.model_validate(response.json()["request"])
    response = client.post("/api/compiler/neutrinos/benchmark", json={"source": SOURCE})
    assert response.status_code == 200, response.text
    result = NeutrinoResponse.model_validate(response.json())
    assert result.axis == request.axis
    assert len(result.results) == 9
    assert result.results[4].numerical.other == pytest.approx(1)
    assert all(
        r.simulated and r.absolute_errors.ideal_vs_numerical.other < 1e-13 for r in result.results
    )
    assert all(sum(r.counts.values()) == request.experiment.shots for r in result.results)
    assert sum(r.timing_ms.classical for r in result.results) > 0
    assert sum(r.timing_ms.circuit_end_to_end for r in result.results) > 0


def test_invalid_science_source_never_reaches_execution(client, monkeypatch):
    from app.api import compiler_neutrinos

    runner = Mock()
    monkeypatch.setattr(compiler_neutrinos, "run", runner)
    response = client.post(
        "/api/compiler/neutrinos/benchmark", json={"source": "raise RuntimeError()"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["diagnostics"]
    runner.assert_not_called()
