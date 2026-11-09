"""Restricted Python -> binary polynomial -> canonical QUBO, without execution."""

import ast
import itertools
import math
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
Polynomial = dict[tuple[int, ...], float]


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


def _objective(tree: ast.Module) -> tuple[list[ast.stmt], ast.expr, str, int, str]:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        _reject(
            "Provide exactly one marked function; imports and top-level code are unsupported.",
            tree.body[0] if tree.body else tree,
        )
    function = tree.body[0]
    args = function.args
    if (
        len(args.args) != 1
        or args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or args.defaults
        or args.kw_defaults
        or args.args[0].annotation
        or function.returns
        or function.type_comment
        or getattr(function, "type_params", [])
    ):
        _reject("Use one unannotated binary-vector parameter with no defaults.", function)
    if len(function.decorator_list) != 1:
        _reject("Mark the function with @qatlas.objective(num_bits=N).", function, "INVALID_MARKER")
    marker = function.decorator_list[0]
    if not (
        isinstance(marker, ast.Call)
        and isinstance(marker.func, ast.Attribute)
        and isinstance(marker.func.value, ast.Name)
        and marker.func.value.id == "qatlas"
        and marker.func.attr == "objective"
        and not marker.args
    ):
        _reject("Expected @qatlas.objective(num_bits=N).", marker, "INVALID_MARKER")
    keywords = {item.arg: item.value for item in marker.keywords}
    if (
        len(keywords) != len(marker.keywords)
        or set(keywords) - {"num_bits", "sense"}
        or "num_bits" not in keywords
    ):
        _reject("Marker accepts num_bits and optional sense only.", marker, "INVALID_MARKER")
    bits = keywords["num_bits"]
    if not (
        isinstance(bits, ast.Constant)
        and type(bits.value) is int
        and 1 <= bits.value <= MAX_COMPILER_BITS
    ):
        _reject("num_bits must be an integer literal from 1 to 6.", bits, "INVALID_MARKER")
    sense_node = keywords.get("sense")
    sense = "minimize"
    if sense_node is not None:
        if not (
            isinstance(sense_node, ast.Constant) and sense_node.value in ("minimize", "maximize")
        ):
            _reject("sense must be 'minimize' or 'maximize'.", sense_node, "INVALID_MARKER")
        sense = sense_node.value
    body = function.body
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and type(body[0].value.value) is str
    ):
        body = body[1:]
    if not body or not isinstance(body[-1], ast.Return) or body[-1].value is None:
        _reject("End the function with one return expression.", body[-1] if body else function)
    return body[:-1], body[-1].value, args.args[0].arg, bits.value, sense


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


def _extract(
    node: ast.expr, parameter: str, num_bits: int, bindings: dict[str, Polynomial]
) -> Polynomial:
    if isinstance(node, ast.Name):
        if node.id == parameter:
            _reject("Index the binary-vector parameter with a literal integer.", node)
        if node.id not in bindings:
            _reject("Local name must be assigned before use.", node, "UNDEFINED_NAME")
        return bindings[node.id].copy()
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        try:
            value = _finite(float(node.value), node)
        except OverflowError:
            _reject("Numeric literal is too large.", node, "NONFINITE_COEFFICIENT")
        return {(): value} if value else {}
    if isinstance(node, ast.Subscript):
        index = node.slice
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


def _interpret(node: ast.expr, assignment: tuple[int, ...], bindings: dict[str, float]) -> float:
    """Independent interpreter, called only on an already validated expression."""
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return bindings[node.id]
    if isinstance(node, ast.Subscript):
        return float(assignment[int(_interpret(node.slice, assignment, bindings))])
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
    statements: list[ast.stmt], assignment: tuple[int, ...], bindings: dict[str, float]
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
        statements, expression, parameter, num_bits, sense = _objective(tree)
        try:
            assignments, lowered_expression = lower_body(statements, expression, parameter)
        except LoweringError as exc:
            _reject(exc.message, exc.node, exc.code)
        symbolic_bindings: dict[str, Polynomial] = {}
        for statement in assignments:
            symbolic_bindings[statement.targets[0].id] = _extract(
                statement.value, parameter, num_bits, symbolic_bindings
            )
        polynomial = _extract(lowered_expression, parameter, num_bits, symbolic_bindings)
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
            numeric_bindings: dict[str, float] = {}
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
                )
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
