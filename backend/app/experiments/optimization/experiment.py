"""Max-Cut and QUBO comparisons through the existing shared solver handoff."""

from hashlib import sha256
from importlib.metadata import version

from app.compiler.pipeline import benchmark_qubo
from app.experiments.optimization.maxcut import maxcut_to_qubo
from app.schemas.contracts import GraphInput, OptimizationRequest, OptimizationResult


def run_optimization(request: OptimizationRequest) -> OptimizationResult:
    """Convert graph inputs, then compare both runners on one canonical QUBO.

    Reuse the public validated-QUBO comparison function currently hosted in the
    compiler pipeline. It already validates solver results, computes the exact
    objective gap, and records configuration and versions. Source parsing is
    outside this path. Graph conversion precedes both solver timers, matching
    their existing validated-QUBO timing boundary.
    """
    if isinstance(request.problem, GraphInput):
        qubo = maxcut_to_qubo(request.problem)
    else:
        qubo = request.problem.qubo
    comparison = benchmark_qubo(qubo, request.config)
    result = OptimizationResult(
        **comparison.model_dump(exclude={"experiment", "problem_id"}),
        problem_id="optimization-" + sha256(qubo.model_dump_json().encode()).hexdigest()[:24],
    )
    if isinstance(request.problem, GraphInput):
        result.metadata.versions["networkx"] = version("networkx")
    return result
