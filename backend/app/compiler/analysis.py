"""Restricted Python -> binary polynomial -> canonical QUBO, without execution."""

import ast
import itertools
import math
from dataclasses import dataclass
from typing import NoReturn

from app.compiler.lowering import LoweringError, lower_body
from app.quantum.circuits import build_qaoa_preview
from app.schemas.contracts import (
    QUBO,
    CompilerAnalyzeResult,
    Diagnostic,
    QuadraticTerm,
)

MAX_SOURCE_LENGTH = 20_000
MAX_AST_NODES = 2048
MAX_AST_DEPTH = 64
MAX_COMPILER_BITS = 6
MAX_VECTOR_LENGTH = 64
Polynomial = dict[tuple[int, ...], float]
SymbolicBindings = dict[str, Polynomial | tuple[float, ...]]
NumericBindings = dict[str, float | tuple[float, ...]]


@dataclass(frozen=True)
class BinaryInputs:
    vector: str | None = None
    scalars: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        return (self.vector,) if self.vector is not None else self.scalars


class Rejected(Exception):
    def __init__(self, code: str, message: str, node: ast.AST | None = None):
        self.diagnostic = Diagnostic(
            code=code,
            message=message,
            severity="error",
            line=getattr(node, "lineno", None),
            column=(node.col_offset + 1) if hasattr(node, "col_offset") else None,
        )


def _reject(message: str, node: ast.AST, code: str = "UNSUPPORTED_SYNTAX") -> NoReturn:
    raise Rejected(code, message, node)


def _check_tree(tree: ast.AST) -> None:
    pending = [(tree, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_AST_NODES or depth > MAX_AST_DEPTH:
            _reject("Source exceeds the AST node or depth limit.", node, "SOURCE_LIMIT")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))


def parse_source(source: str) -> ast.Module:
    """Parse bounded source as data; callers decide which nodes may be translated."""
    if not 1 <= len(source) <= MAX_SOURCE_LENGTH:
        raise Rejected("SOURCE_LIMIT", "Source must contain 1 to 20,000 characters.")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        failure = Rejected("SYNTAX_ERROR", "Source is not valid Python syntax.")
        if isinstance(exc, SyntaxError):
            failure.diagnostic.line = max(1, exc.lineno or 1)
            failure.diagnostic.column = max(1, exc.offset or 1)
        raise failure from None
    _check_tree(tree)
    return tree


def _infer_width(function: ast.FunctionDef, body: list[ast.stmt], names: tuple[str, ...]) -> int:
    if len(names) != 1:
        return len(names)
    try:
        assignments, expression = lower_body(body[:-1], body[-1].value, names)
    except LoweringError as exc:
        _reject(exc.message, exc.node, exc.code)
    indices = [
        node.slice
        for statement in [*assignments, expression]
        for node in ast.walk(statement)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == names[0]
    ]
    if any(
        not isinstance(index, ast.Constant) or type(index.value) is not int or index.value < 0
        for index in indices
    ):
        _reject(
            "Cannot infer vector width from a dynamic or invalid index.", function, "INVALID_INDEX"
        )
    return max((index.value + 1 for index in indices), default=1)


def _objective(tree: ast.Module) -> tuple[list[ast.stmt], ast.expr, BinaryInputs, int, str]:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        _reject(
            "Provide exactly one marked function; imports and top-level code are unsupported.",
            tree.body[0] if tree.body else tree,
        )
    function = tree.body[0]
    args = function.args
    if (
        not args.args
        or args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or args.defaults
        or args.kw_defaults
        or any(argument.annotation for argument in args.args)
        or function.returns
        or function.type_comment
        or getattr(function, "type_params", [])
    ):
        _reject(
            "Use unannotated positional binary inputs with no defaults or variadic arguments.",
            function,
        )
    if len(function.decorator_list) != 1:
        _reject("Put one @qatlas.objective marker on the function.", function, "INVALID_MARKER")
    marker = function.decorator_list[0]
    target = marker.func if isinstance(marker, ast.Call) else marker
    if not (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "qatlas"
        and target.attr == "objective"
        and (not isinstance(marker, ast.Call) or not marker.args)
    ):
        _reject(
            "Expected @qatlas.objective, optionally with num_bits and sense.",
            marker,
            "INVALID_MARKER",
        )
    arguments = marker.keywords if isinstance(marker, ast.Call) else []
    keywords = {item.arg: item.value for item in arguments}
    if len(keywords) != len(arguments) or set(keywords) - {"num_bits", "sense"}:
        _reject("Marker accepts optional num_bits and sense only.", marker, "INVALID_MARKER")
    body = function.body
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and type(body[0].value.value) is str
    ):
        body = body[1:]
    if not body or not isinstance(body[-1], ast.Return) or body[-1].value is None:
        _reject("End the function with one return expression.", body[-1] if body else function)
    bits = keywords.get("num_bits")
    if bits is not None and not (
        isinstance(bits, ast.Constant)
        and type(bits.value) is int
        and 1 <= bits.value <= MAX_COMPILER_BITS
    ):
        _reject("num_bits must be an integer literal from 1 to 6.", bits, "INVALID_MARKER")
    names = tuple(argument.arg for argument in args.args)
    # Inference is bounded AST lowering, not a call to the user's function.
    if bits is None:
        num_bits = _infer_width(function, body, names)
    else:
        num_bits = bits.value
    if not 1 <= num_bits <= MAX_COMPILER_BITS:
        _reject(
            "The inferred objective width must be from 1 to 6 bits.", function, "INVALID_MARKER"
        )
    sense_node = keywords.get("sense")
    sense = "minimize"
    if sense_node is not None:
        if not (
            isinstance(sense_node, ast.Constant) and sense_node.value in ("minimize", "maximize")
        ):
            _reject("sense must be 'minimize' or 'maximize'.", sense_node, "INVALID_MARKER")
        sense = sense_node.value
    if len(set(names)) != len(names) or len(names) not in (1, num_bits):
        _reject(
            "Use one vector parameter or exactly num_bits distinct scalar parameters.",
            function,
            "INVALID_SIGNATURE",
        )
    indexed = len(names) == 1 and any(
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == names[0]
        for statement in function.body
        for node in ast.walk(statement)
    )
    inputs = (
        BinaryInputs(vector=names[0])
        if len(names) == 1 and (num_bits > 1 or indexed)
        else BinaryInputs(scalars=names)
    )
    return body[:-1], body[-1].value, inputs, num_bits, sense


def _finite(value: float, node: ast.AST) -> float:
    if not math.isfinite(value):
        _reject(
            "Coefficients and intermediate values must be finite.", node, "NONFINITE_COEFFICIENT"
        )
    return value


def _add_term(result: Polynomial, key: tuple[int, ...], value: float, node: ast.AST) -> None:
    result[key] = _finite(result.get(key, 0.0) + value, node)
    if result[key] == 0:
        del result[key]


def _multiply(left: Polynomial, right: Polynomial, node: ast.AST) -> Polynomial:
    result: Polynomial = {}
    for first, a in left.items():
        for second, b in right.items():
            key = tuple(sorted(set(first) | set(second)))
            if len(key) > 2:
                _reject("Products may involve at most two distinct bits.", node, "HIGHER_ORDER")
            _add_term(result, key, _finite(a * b, node), node)
    return result


def _vector_literal(node: ast.List | ast.Tuple) -> tuple[float, ...]:
    if not 1 <= len(node.elts) <= MAX_VECTOR_LENGTH:
        _reject("Numeric vectors require 1 to 64 literal elements.", node, "INVALID_VECTOR")

    def number(item: ast.expr) -> float:
        if isinstance(item, ast.UnaryOp) and isinstance(item.op, (ast.UAdd, ast.USub)):
            value = number(item.operand)
            return -value if isinstance(item.op, ast.USub) else value
        if not isinstance(item, ast.Constant) or type(item.value) not in (int, float):
            _reject("Vector elements must be signed numeric literals.", item, "INVALID_VECTOR")
        try:
            return _finite(float(item.value), item)
        except OverflowError:
            _reject("Numeric literal is too large.", item, "NONFINITE_COEFFICIENT")

    return tuple(number(item) for item in node.elts)


def _extract(
    node: ast.expr, parameter: str | None, num_bits: int, bindings: SymbolicBindings
) -> Polynomial:
    if isinstance(node, ast.Name):
        if node.id == parameter:
            _reject("Index the binary-vector parameter with a literal integer.", node)
        if node.id not in bindings:
            _reject("Local name must be assigned before use.", node, "UNDEFINED_NAME")
        value = bindings[node.id]
        if isinstance(value, tuple):
            _reject("Index a numeric vector; whole-vector operations are unsupported.", node)
        return value.copy()
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        try:
            value = _finite(float(node.value), node)
        except OverflowError:
            _reject("Numeric literal is too large.", node, "NONFINITE_COEFFICIENT")
        return {(): value} if value else {}
    if isinstance(node, ast.Subscript):
        index = node.slice
        if isinstance(node.value, ast.Name) and node.value.id != parameter:
            vector = bindings.get(node.value.id)
            if (
                isinstance(vector, tuple)
                and isinstance(index, ast.Constant)
                and type(index.value) is int
                and 0 <= index.value < len(vector)
            ):
                value = vector[index.value]
                return {(): value} if value else {}
            _reject(
                "Use a declared numeric vector with a literal index in range.",
                node,
                "INVALID_INDEX",
            )
        if not (
            isinstance(node.value, ast.Name)
            and node.value.id == parameter
            and isinstance(index, ast.Constant)
            and type(index.value) is int
            and 0 <= index.value < num_bits
        ):
            _reject(
                "Use the binary parameter with a literal index in range.", node, "INVALID_INDEX"
            )
        return {(index.value,): 1.0}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        sign = -1 if isinstance(node.op, ast.USub) else 1
        return {
            key: sign * value
            for key, value in _extract(node.operand, parameter, num_bits, bindings).items()
        }
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            if not (
                isinstance(node.right, ast.Constant)
                and type(node.right.value) is int
                and node.right.value == 2
            ):
                _reject("Only squares with exponent literal 2 are supported for powers.", node)
            base = _extract(node.left, parameter, num_bits, bindings)
            return _multiply(base, base, node)
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            _reject("Only addition, subtraction, and multiplication are supported.", node)
        left = _extract(node.left, parameter, num_bits, bindings)
        right = _extract(node.right, parameter, num_bits, bindings)
        if isinstance(node.op, ast.Mult):
            return _multiply(left, right, node)
        result = left.copy()
        sign = -1 if isinstance(node.op, ast.Sub) else 1
        for key, value in right.items():
            _add_term(result, key, sign * value, node)
        return result
    _reject("Unsupported expression; calls and attributes are forbidden.", node)


def _interpret(node: ast.expr, assignment: tuple[int, ...], bindings: NumericBindings) -> float:
    """Independent interpreter, called only on an already validated expression."""
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        value = bindings[node.id]
        if isinstance(value, tuple):
            _reject("Index a numeric vector before using its value.", node)
        return value
    if isinstance(node, ast.Subscript):
        vector = bindings.get(node.value.id, assignment)
        return float(vector[int(_interpret(node.slice, assignment, bindings))])
    if isinstance(node, ast.UnaryOp):
        value = _interpret(node.operand, assignment, bindings)
        return -value if isinstance(node.op, ast.USub) else value
    left = _interpret(node.left, assignment, bindings)
    right = _interpret(node.right, assignment, bindings)
    if isinstance(node.op, ast.Add):
        return left + right
    if isinstance(node.op, ast.Sub):
        return left - right
    if isinstance(node.op, ast.Mult):
        return left * right
    try:
        return left**right
    except OverflowError:
        _reject(
            "Squared expression overflows; rescale the coefficients.", node, "NONFINITE_COEFFICIENT"
        )


def _interpret_statements(
    statements: list[ast.stmt], assignment: tuple[int, ...], bindings: NumericBindings
) -> None:
    """Interpret validated source control flow, independently of AST loop lowering."""
    for statement in statements:
        if isinstance(statement, ast.For):
            # The syntax validator permits only unshadowed range with bounded literals.
            arguments = [int(_interpret(arg, assignment, bindings)) for arg in statement.iter.args]
            for value in range(*arguments):
                bindings[statement.target.id] = value
                _interpret_statements(statement.body, assignment, bindings)
        elif isinstance(statement, ast.Assign):
            if isinstance(statement.value, (ast.List, ast.Tuple)):
                # Interpret the original literal elements independently of symbolic extraction.
                bindings[statement.targets[0].id] = tuple(
                    _finite(_interpret(item, assignment, bindings), item)
                    for item in statement.value.elts
                )
            else:
                bindings[statement.targets[0].id] = _finite(
                    _interpret(statement.value, assignment, bindings), statement.value
                )
        else:  # Validated numeric +=, -=, or *=; no user object mutation.
            left = bindings[statement.target.id]
            right = _interpret(statement.value, assignment, bindings)
            if isinstance(statement.op, ast.Add):
                value = left + right
            elif isinstance(statement.op, ast.Sub):
                value = left - right
            else:
                value = left * right
            bindings[statement.target.id] = _finite(value, statement)


def analyze_source(source: str) -> CompilerAnalyzeResult:
    """Exhaustively verify every accepted 1–6-bit objective against its QUBO."""
    try:
        tree = parse_source(source)
        statements, expression, inputs, num_bits, sense = _objective(tree)
        try:
            assignments, lowered_expression = lower_body(statements, expression, inputs.names)
        except LoweringError as exc:
            _reject(exc.message, exc.node, exc.code)
        symbolic_bindings: SymbolicBindings = {
            name: {(i,): 1.0} for i, name in enumerate(inputs.scalars)
        }
        for statement in assignments:
            symbolic_bindings[statement.targets[0].id] = (
                _vector_literal(statement.value)
                if isinstance(statement.value, (ast.List, ast.Tuple))
                else _extract(statement.value, inputs.vector, num_bits, symbolic_bindings)
            )
        polynomial = _extract(lowered_expression, inputs.vector, num_bits, symbolic_bindings)
        sign = -1 if sense == "maximize" else 1
        # The IR stores only nonzero terms. Apply sense before filling absent terms
        # so their canonical JSON values remain +0.0, including under maximization.
        polynomial = {key: sign * value for key, value in polynomial.items()}
        qubo = QUBO(
            num_variables=num_bits,
            constant=polynomial.get((), 0.0),
            linear=[polynomial.get((i,), 0.0) for i in range(num_bits)],
            quadratic=[
                QuadraticTerm(i=key[0], j=key[1], coefficient=value)
                for key, value in sorted(polynomial.items())
                if len(key) == 2
            ],
            original_sense=sense,
        )
        for assignment in itertools.product((0, 1), repeat=num_bits):
            numeric_bindings: NumericBindings = {
                name: float(assignment[i]) for i, name in enumerate(inputs.scalars)
            }
            _interpret_statements(statements, assignment, numeric_bindings)
            expected = _finite(
                sign * _interpret(expression, assignment, numeric_bindings), expression
            )
            actual = _finite(
                qubo.constant
                + sum(a * x for a, x in zip(qubo.linear, assignment, strict=True))
                + sum(
                    term.coefficient * assignment[term.i] * assignment[term.j]
                    for term in qubo.quadratic
                ),
                expression,
            )
            if not math.isclose(expected, actual, rel_tol=0, abs_tol=1e-9):
                _reject(
                    "Floating-point normalization changed objective values; rescale coefficients.",
                    expression,
                    "VERIFICATION_FAILED",
                )
        return CompilerAnalyzeResult(
            status="supported",
            qubo=qubo,
            circuit=build_qaoa_preview(qubo),
            diagnostics=[
                Diagnostic(
                    code="VERIFIED",
                    message=f"Verified the objective on all {2**num_bits} binary assignments.",
                    severity="info",
                ),
                Diagnostic(
                    code="INPUT_MAPPING",
                    message=(
                        f"Vector {inputs.vector}[i] maps to canonical bit i."
                        if inputs.vector is not None
                        else "Declared input order: "
                        + "; ".join(f"{name} -> bit {i}" for i, name in enumerate(inputs.scalars))
                    ),
                    severity="info",
                ),
            ],
        )
    except Rejected as exc:
        return CompilerAnalyzeResult(status="rejected", diagnostics=[exc.diagnostic])
    except (RecursionError, MemoryError):
        return CompilerAnalyzeResult(
            status="rejected",
            diagnostics=[
                Diagnostic(
                    code="SOURCE_LIMIT", message="Source exceeds parser limits.", severity="error"
                )
            ],
        )
