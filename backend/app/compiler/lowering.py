"""Bounded AST lowering for numeric accumulation and literal range loops.

This module produces ordinary assignments for symbolic extraction. Verification
interprets original source control flow separately. Submitted functions are never run.
"""

import ast
import copy

MAX_SOURCE_ASSIGNMENTS = 64
MAX_EXPANDED_ASSIGNMENTS = 256
MAX_EXPANDED_NODES = 8192
MAX_RANGE_BOUND = 64
MAX_LOOP_ITERATIONS = 64
MAX_LOOP_DEPTH = 2


class LoweringError(Exception):
    def __init__(self, code: str, message: str, node: ast.AST):
        self.code, self.message, self.node = code, message, node


def _integer(node: ast.AST, *, offsets: bool = False) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        value = node.value
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _integer(node.operand, offsets=offsets)
        if isinstance(node.op, ast.USub):
            value = -value
    elif offsets and isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left, right = _integer(node.left, offsets=True), _integer(node.right, offsets=True)
        value = left + right if isinstance(node.op, ast.Add) else left - right
    else:
        raise ValueError("not a supported static integer")
    if abs(value) > MAX_RANGE_BOUND:
        raise ValueError("static integer outside the supported bounds")
    return value


class _SubstituteIndices(ast.NodeTransformer):
    def __init__(self, values: dict[str, int]):
        self.values = values

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.values:
            return ast.copy_location(ast.Constant(value=self.values[node.id]), node)
        return node

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        has_index = any(
            isinstance(part, ast.Name) and part.id in self.values for part in ast.walk(node.slice)
        )
        self.generic_visit(node)
        if has_index:
            try:
                value = _integer(node.slice, offsets=True)
            except ValueError:
                pass  # The expression validator will reject this dynamic/unsupported index.
            else:
                node.slice = ast.copy_location(ast.Constant(value=value), node.slice)
        return node


def lower_body(
    statements: list[ast.stmt], expression: ast.expr, parameter: str | tuple[str, ...]
) -> tuple[list[ast.Assign], ast.expr]:
    """Flatten a bounded statement sequence, preserving source diagnostic locations."""
    parameters = {parameter} if isinstance(parameter, str) else set(parameter)
    source_assignments = [
        node
        for statement in statements
        for node in ast.walk(statement)
        if isinstance(node, (ast.Assign, ast.AugAssign))
    ]
    if len(source_assignments) > MAX_SOURCE_ASSIGNMENTS:
        raise LoweringError(
            "SOURCE_LIMIT", "At most 64 source assignments are supported.", source_assignments[64]
        )
    assigned_names = {
        target.id
        for statement in source_assignments
        for target in (
            statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        )
        if isinstance(target, ast.Name)
    }
    loop_names = {
        node.target.id
        for statement in statements
        for node in ast.walk(statement)
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name)
    }
    range_shadowed = "range" in assigned_names | loop_names | parameters
    values: dict[str, int] = {}
    result: list[ast.Assign] = []
    expanded_nodes = 0

    def substitute(node: ast.expr) -> ast.expr:
        return _SubstituteIndices(values).visit(copy.deepcopy(node))

    def append(statement: ast.Assign) -> None:
        nonlocal expanded_nodes
        expanded_nodes += sum(1 for _ in ast.walk(statement))
        if len(result) >= MAX_EXPANDED_ASSIGNMENTS or expanded_nodes > MAX_EXPANDED_NODES:
            raise LoweringError(
                "SOURCE_LIMIT", "Loop expansion exceeds compiler limits.", statement
            )
        result.append(statement)

    def walk(block: list[ast.stmt], active: tuple[str, ...] = ()) -> None:
        for statement in block:
            if isinstance(statement, ast.For):
                iterator = statement.iter
                if (
                    len(active) >= MAX_LOOP_DEPTH
                    or statement.orelse
                    or not isinstance(statement.target, ast.Name)
                    or statement.target.id in parameters
                    or statement.target.id in active
                    or statement.target.id in assigned_names
                    or range_shadowed
                    or not isinstance(iterator, ast.Call)
                    or not isinstance(iterator.func, ast.Name)
                    or iterator.func.id != "range"
                    or iterator.keywords
                    or not 1 <= len(iterator.args) <= 3
                ):
                    raise LoweringError(
                        "INVALID_LOOP",
                        "Use an unshadowed literal range with a distinct index and no else; "
                        "nesting is limited to two.",
                        statement,
                    )
                try:
                    # Only compiler-owned range is called, on validated literal integers.
                    iterations = range(*[_integer(arg) for arg in iterator.args])
                except ValueError as exc:
                    raise LoweringError(
                        "INVALID_LOOP",
                        "range requires bounded integer literals and a nonzero step.",
                        iterator,
                    ) from exc
                if not 1 <= len(iterations) <= MAX_LOOP_ITERATIONS:
                    raise LoweringError(
                        "INVALID_LOOP",
                        "range must contain 1 to 64 values; empty ranges are unsupported.",
                        iterator,
                    )
                for value in iterations:
                    values[statement.target.id] = value
                    walk(statement.body, (*active, statement.target.id))
                continue
            if isinstance(statement, ast.Assign):
                targets = statement.targets
                value = statement.value
            elif isinstance(statement, ast.AugAssign) and isinstance(
                statement.op, (ast.Add, ast.Sub, ast.Mult)
            ):
                targets = [statement.target]
                value = statement.value
            else:
                raise LoweringError(
                    "UNSUPPORTED_SYNTAX",
                    "Use local assignments, bounded range loops, and one final return.",
                    statement,
                )
            if (
                len(targets) != 1
                or not isinstance(targets[0], ast.Name)
                or targets[0].id in parameters
            ):
                raise LoweringError(
                    "INVALID_ASSIGNMENT",
                    "Assign to one plain local name; do not rebind a binary input parameter.",
                    statement,
                )
            if isinstance(statement, ast.AugAssign):
                load = ast.copy_location(ast.Name(id=targets[0].id, ctx=ast.Load()), targets[0])
                value = ast.copy_location(
                    ast.BinOp(left=load, op=statement.op, right=value), statement
                )
            append(
                ast.copy_location(
                    ast.Assign(targets=copy.deepcopy(targets), value=substitute(value)), statement
                )
            )

    walk(statements)
    lowered_expression = substitute(expression)
    expanded_nodes += sum(1 for _ in ast.walk(lowered_expression))
    if expanded_nodes > MAX_EXPANDED_NODES:
        raise LoweringError("SOURCE_LIMIT", "Loop expansion exceeds compiler limits.", expression)
    return result, lowered_expression
