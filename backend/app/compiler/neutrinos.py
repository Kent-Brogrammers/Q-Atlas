"""Translate a literal scientific declaration. Uploaded Python is never executed."""

import ast

from pydantic import ValidationError

from app.compiler.analysis import Rejected, parse_source
from app.schemas.compiler_neutrinos import CompiledNeutrino
from app.schemas.contracts import GeneratedPythonArtifact
from app.schemas.neutrinos import NeutrinoRequest


def _literal(node):
    if isinstance(node, ast.Constant) and type(node.value) in (str, int, float, bool, type(None)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _literal(node.operand)
        if type(value) not in (int, float):
            raise Rejected("INVALID_NEUTRINO_LITERAL", "Signs require numeric literals.", node)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.List):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        result = {}
        for key, value in zip(node.keys, node.values, strict=True):
            if (
                not isinstance(key, ast.Constant)
                or type(key.value) is not str
                or key.value in result
            ):
                raise Rejected("INVALID_NEUTRINO_LITERAL", "Use unique literal string keys.", node)
            result[key.value] = _literal(value)
        return result
    raise Rejected(
        "INVALID_NEUTRINO_LITERAL",
        "Use literal dictionaries, lists and values; no calls or expressions.",
        node,
    )


def parse_neutrino(source: str) -> NeutrinoRequest:
    tree = parse_source(source)
    statements = [
        n
        for n in tree.body
        if not (
            isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)
        )
    ]
    if len(statements) != 1 or not isinstance(statements[0], ast.FunctionDef):
        raise Rejected(
            "INVALID_NEUTRINO_SOURCE", "Use one @qatlas.neutrino function returning settings."
        )
    function = statements[0]
    decorators = function.decorator_list
    args = function.args
    valid_marker = (
        len(decorators) == 1
        and isinstance(decorators[0], ast.Attribute)
        and isinstance(decorators[0].value, ast.Name)
        and decorators[0].value.id == "qatlas"
        and decorators[0].attr == "neutrino"
    )
    if (
        not valid_marker
        or args.args
        or args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or args.defaults
        or args.kw_defaults
        or function.returns
        or getattr(function, "type_params", [])
    ):
        raise Rejected(
            "INVALID_NEUTRINO_SOURCE",
            "Use @qatlas.neutrino on a function without arguments or annotations.",
            function,
        )
    body = function.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        raise Rejected(
            "INVALID_NEUTRINO_SOURCE",
            "The function must only return literal experiment settings.",
            function,
        )
    try:
        return NeutrinoRequest.model_validate(_literal(body[0].value))
    except ValidationError:
        raise Rejected(
            "INVALID_NEUTRINO_PARAMETERS",
            "Invalid neutrino settings or resource limits; use the Neutrino Lab request structure.",
            function,
        ) from None


_EXPORT = '''"""Generated two-flavor neutrino comparison; local simulation, not QPU timing.
Requires numpy, scipy, qiskit and qiskit-aer. Constants/QASM come from validated
settings and the Neutrino Lab builder. No submitted function is executed.
"""
from time import perf_counter
import json
import numpy as np
from scipy.linalg import expm
from qiskit import qasm2, transpile
from qiskit_aer import AerSimulator

POINTS = __POINTS__

def compare_neutrinos():
    output = []
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Z = np.diag([1, -1])
    for point in POINTS:
        experiment = point["experiment"]
        p = experiment["parameters"]
        started = perf_counter()
        state = np.array([1, 0], dtype=complex)
        kappa = p["delta_m2"] / p["energy"]
        sign = 1 if p["particle"] == "neutrino" else -1
        for layer in experiment["layers"]:
            x = kappa * np.sin(2*p["theta"])
            z = sign*layer["potential"] - kappa*np.cos(2*p["theta"])
            G = x*X + z*Z
            state = expm(-1j*G*layer["distance"]) @ state
        classical_probability = float(abs(state[1])**2)
        classical_ms = (perf_counter()-started)*1000
        started = perf_counter()
        circuit = qasm2.loads(point["qasm"])
        compiled = transpile(circuit, basis_gates=["ry", "rz"],
                             optimization_level=0, num_processes=1)
        backend = AerSimulator(method="statevector", max_parallel_threads=1)
        ideal = compiled.copy()
        ideal.save_statevector()
        sv = backend.run(ideal, shots=1).result().get_statevector()
        ideal_probability = float(abs(sv[1])**2)
        compiled.measure_all()
        sampled = backend.run(compiled, shots=experiment["shots"],
                              seed_simulator=experiment["seed"]).result()
        counts = sampled.get_counts()
        measured_probability = counts.get("1",0)/experiment["shots"]
        circuit_ms = (perf_counter()-started)*1000
        output.append(dict(
            coordinate=point["coordinate"], classical_probability=classical_probability,
            ideal_probability=ideal_probability, measured_probability=measured_probability,
            classical_ms=classical_ms, circuit_end_to_end_ms=circuit_ms,
            counts=counts, simulated=True,
        ))
    return output

if __name__ == "__main__":
    print(json.dumps(compare_neutrinos(), indent=2))
'''


def compile_neutrino(source: str) -> CompiledNeutrino:
    request = parse_neutrino(source)
    from qiskit import qasm2

    from app.experiments.neutrinos.circuit import build_circuit
    from app.experiments.neutrinos.web import curve_points

    points = [
        {
            "coordinate": coordinate,
            "experiment": experiment.model_dump(mode="json"),
            "qasm": qasm2.dumps(build_circuit(experiment)),
        }
        for coordinate, experiment in curve_points(request)
    ]
    return CompiledNeutrino(
        request=request,
        artifact=GeneratedPythonArtifact(
            source=_EXPORT.replace("__POINTS__", repr(points)), entrypoint="compare_neutrinos"
        ),
        circuit_diagram=str(build_circuit(request.experiment).draw(output="text", fold=-1)),
    )
