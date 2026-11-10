"""Rewrite explicitly marked source spans using the shared symbolic circuit plan.

Surrounding Python is opaque text. It is preserved, never imported or executed.
Only the objective is interpreted, through the existing restricted analyzer.
"""

import ast
import io
import re
import tokenize

from app.compiler.analysis import Rejected, analyze_source, parse_source
from app.quantum.circuits import build_qaoa_preview
from app.schemas.contracts import (
    CircuitAngle,
    CircuitPreview,
    CompilerGenerateResult,
    Diagnostic,
    GeneratedPythonArtifact,
)


def _marker(node: ast.AST, name: str) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    return (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "qatlas"
        and target.attr == name
    )


def _marked_function(tree: ast.Module, name: str, required: bool) -> ast.FunctionDef | None:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and any(_marker(item, name) for item in node.decorator_list)
    ]
    if len(matches) > 1 or (required and not matches):
        raise Rejected(
            "INVALID_MARKER",
            f"Provide {'exactly one' if required else 'at most one'} @qatlas.{name} function.",
            matches[-1] if matches else None,
        )
    if not matches:
        return None
    function = matches[0]
    if not isinstance(function, ast.FunctionDef) or function not in tree.body:
        raise Rejected(
            "INVALID_MARKER", f"@qatlas.{name} requires a top-level synchronous function.", function
        )
    return function


def _validate_replacement(function: ast.FunctionDef) -> None:
    args = function.args
    if (
        len(function.decorator_list) != 1
        or not isinstance(function.decorator_list[0], ast.Attribute)
        or args.posonlyargs
        or args.args
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or function.returns
        or getattr(function, "type_params", [])
    ):
        raise Rejected(
            "INVALID_CIRCUIT_MARKER",
            "Use @qatlas.circuit on a function with no parameters, annotations,"
            " or other decorators."
            " The replacement returns an unbound QuantumCircuit.",
            function,
        )


def _angle(angle: CircuitAngle) -> str:
    return f"{angle.coefficient!r} * _qatlas_parameters[{angle.parameter!r}]"


def _decorator_spans(source: str) -> list[tuple[int, int]]:
    """Physical line spans include parentheses outside a decorator's AST expression."""
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    spans = []
    start = None
    for token in tokenize.generate_tokens(io.StringIO(normalized).readline):
        if (
            start is None
            and token.type == tokenize.OP
            and token.string == "@"
            and not token.line[: token.start[1]].strip()
        ):
            start = token.start[0]
        elif start is not None and token.type == tokenize.NEWLINE:
            spans.append((start, token.end[0]))
            start = None
    return spans


def render_circuit(plan: CircuitPreview, name: str) -> str:
    """Serialize trusted gate models to Python; no QUBO formulas or execution engine."""
    lines = [
        f"def {name}():",
        '    """Build an unbound QAOA circuit; no sampling or optimization is performed.',
        f"    Parameter order: {', '.join(plan.parameters)}.",
        "    x[i] maps to qubit i. No measurements are included.",
        '    """',
        "    from qiskit import QuantumCircuit as _qatlas_QuantumCircuit",
        "    from qiskit.circuit import Parameter as _qatlas_Parameter",
        "",
        "    _qatlas_parameters = {",
        *[
            f"        {parameter!r}: _qatlas_Parameter({parameter!r}),"
            for parameter in plan.parameters
        ],
        "    }",
        f"    _qatlas_circuit = _qatlas_QuantumCircuit({plan.num_qubits})",
    ]
    for gate in plan.gates:
        arguments = [] if gate.angle is None else [_angle(gate.angle)]
        arguments.extend(str(qubit) for qubit in gate.qubits)
        lines.append(f"    _qatlas_circuit.{gate.name}({', '.join(arguments)})")
    lines.extend(
        f"    _qatlas_circuit.global_phase += {_angle(phase)}" for phase in plan.global_phase
    )
    lines.extend(["    return _qatlas_circuit", ""])
    return "\n".join(lines)


def generate_source(source: str, p: int = 1) -> CompilerGenerateResult:
    """Preserve a script and replace its explicitly marked circuit factory, if any."""
    try:
        tree = parse_source(source)
        objective = _marked_function(tree, "objective", required=True)
        replacement = _marked_function(tree, "circuit", required=False)
        if replacement is objective:
            raise Rejected("INVALID_MARKER", "Objective and circuit must be separate functions.")
        if replacement is not None:
            _validate_replacement(replacement)
        # Only Python newline sequences count as AST lines; Unicode separators inside
        # strings must not corrupt spans. Keep CRLF and all untouched source verbatim.
        offsets = [0, *[match.end() for match in re.finditer(r"\r\n|\r|\n", source)], len(source)]
        decorator_spans = _decorator_spans(source)

        def span(marker: ast.expr) -> tuple[int, int]:
            return next(pair for pair in decorator_spans if pair[0] <= marker.lineno <= pair[1])

        first = min(span(item)[0] for item in objective.decorator_list)
        objective_source = (
            "\n" * (first - 1) + source[offsets[first - 1] : offsets[objective.end_lineno]]
        )
        analysis = analyze_source(objective_source)
        if analysis.status == "rejected":
            return CompilerGenerateResult(**analysis.model_dump())
        plan = build_qaoa_preview(analysis.qubo, p=p)
        names = {
            node.id if isinstance(node, ast.Name) else node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Name, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        names.update(
            alias.asname or alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        )
        entrypoint = replacement.name if replacement is not None else "build_qatlas_circuit"
        if replacement is None:
            suffix = 2
            while entrypoint in names:
                entrypoint = f"build_qatlas_circuit_{suffix}"
                suffix += 1
        generated = render_circuit(plan, entrypoint)
        first_marker, last_marker = span(objective.decorator_list[0])
        edits = [(offsets[first_marker - 1], offsets[last_marker], "")]
        if replacement is not None:
            start = span(replacement.decorator_list[0])[0]
            edits.append((offsets[start - 1], offsets[replacement.end_lineno], generated))
        newline = (
            "\r\n" if "\r\n" in source else "\r" if "\r" in source and "\n" not in source else "\n"
        )
        output = source
        for start, end, text in sorted(edits, reverse=True):
            output = output[:start] + text.replace("\n", newline) + output[end:]
        if replacement is None:
            output += newline * 2 + generated.replace("\n", newline)
        # Verify the rewritten file is syntactically valid, without compiling/executing it.
        ast.parse(output)
        return CompilerGenerateResult(
            status="supported",
            qubo=analysis.qubo,
            circuit=plan,
            diagnostics=[
                *analysis.diagnostics,
                Diagnostic(
                    code="SCRIPT_GENERATED",
                    message=f"Generated {entrypoint}(). Surrounding Python was preserved as text;"
                    " no source, circuit, or solver was executed.",
                    severity="info",
                ),
            ],
            artifact=GeneratedPythonArtifact(
                source=output,
                entrypoint=entrypoint,
                replaced_function=replacement.name if replacement is not None else None,
            ),
        )
    except Rejected as exc:
        return CompilerGenerateResult(status="rejected", diagnostics=[exc.diagnostic])
    except (RecursionError, MemoryError):
        return CompilerGenerateResult(
            status="rejected",
            diagnostics=[
                Diagnostic(
                    code="SOURCE_LIMIT", message="Source exceeds parser limits.", severity="error"
                )
            ],
        )
