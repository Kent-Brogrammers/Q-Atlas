"""Compiler integration with Developer 3's shared runners; no local solver copies."""

import hashlib
import json
import math
import platform
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import TypeVar

from app.compiler.generation import generate_source
from app.experiments.optimization import solvers
from app.quantum import qaoa
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkPlan,
    CompilerBenchmarkResult,
    Diagnostic,
    OptimizationMetadata,
    QAOAConfig,
    QAOAResult,
    SolverResult,
)

Result = TypeVar("Result", bound=SolverResult)


class CompilationError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics


def _validate_solution(qubo: QUBO, result: SolverResult) -> None:
    if result.best_bitstring is None or result.objective is None:
        raise ValueError(
            "compiler comparisons require an assignment and objective from each solver"
        )
    actual = evaluate_qubo(qubo, result.best_bitstring)
    if not math.isclose(actual, result.objective, rel_tol=0, abs_tol=1e-9):
        raise ValueError("shared solver objective does not match its assignment")


def _call_shared_runner(
    runner: Callable[[QUBO, QAOAConfig], Result],
    qubo: QUBO,
    config: QAOAConfig,
    result_type: type[Result],
) -> Result:
    # Protect the validated problem and provenance, including if a runner raises.
    runner_qubo, runner_config = qubo.model_copy(deep=True), config.model_copy(deep=True)
    result = runner(runner_qubo, runner_config)
    if runner_qubo != qubo or runner_config != config:
        raise ValueError("shared runner changed its input QUBO or configuration")
    # Shared models are mutable: validate nested fields again at the trust boundary.
    return result_type.model_validate(result.model_dump(mode="python"))


def _problem_id(qubo: QUBO) -> str:
    canonical = json.dumps(qubo.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "compiler-" + hashlib.sha256(canonical.encode()).hexdigest()[:24]


def prepare_benchmark(source: str, config: QAOAConfig) -> CompilerBenchmarkPlan:
    """Validate the complete source and record a handoff; never call either runner."""
    generated = generate_source(source, p=config.p)
    if generated.status == "rejected":
        raise CompilationError(generated.diagnostics)
    return CompilerBenchmarkPlan(
        problem_id=_problem_id(generated.qubo),
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        generated_source_sha256=hashlib.sha256(
            generated.artifact.source.encode("utf-8")
        ).hexdigest(),
        entrypoint=generated.artifact.entrypoint,
        qubo=generated.qubo,
        config=config.model_copy(deep=True),
        circuit=generated.circuit,
        blockers=[
            "Execution is disabled; preparing this plan runs neither script nor solver.",
            "The shared classical baseline is implemented; Developer 3 must finish and validate "
            "the shared QAOA runner.",
            "Any execution needs a separately authorized mode and deadline enforcement.",
            "Whole-application timing needs a separate trusted execution boundary and contract.",
        ],
    )


def benchmark_qubo(qubo: QUBO, config: QAOAConfig) -> CompilerBenchmarkResult:
    """Pass the same canonical instance/config to both shared runners.

    The shared QAOA entrypoint is still a stub. Tests inject synthetic
    results at these two boundaries; production never substitutes mock measurements.
    Source analysis is outside both solvers' reported end-to-end timers.
    """
    classical = _call_shared_runner(solvers.run_classical, qubo, config, SolverResult)
    _validate_solution(qubo, classical)
    quantum = _call_shared_runner(qaoa.run_qaoa, qubo, config, QAOAResult)
    _validate_solution(qubo, quantum)
    if quantum.metrics.num_qubits != qubo.num_variables or quantum.metrics.shots != config.shots:
        raise ValueError("shared QAOA metrics do not match the problem and requested shots")
    metrics = quantum.metrics.model_copy(deep=True)
    metrics.optimality_gap = None
    if classical.algorithm == "brute_force" and classical.objective is not None:
        gap = quantum.objective - classical.objective
        if gap < 0 and not math.isclose(gap, 0, abs_tol=1e-9):
            raise ValueError("QAOA result is below the claimed exact classical optimum")
        if math.isfinite(gap):
            metrics.optimality_gap = max(0.0, gap)
    # No general approximation ratio is meaningful for signed QUBO objectives.
    metrics.approximation_ratio = None
    versions = {"python": platform.python_version()}
    for package in ("q-atlas-backend", "pydantic", "numpy", "scipy", "qiskit", "qiskit-aer"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            pass
    return CompilerBenchmarkResult(
        problem_id=_problem_id(qubo),
        backend=config.backend,
        classical=classical,
        quantum=quantum,
        metrics=metrics,
        metadata=OptimizationMetadata(
            seed=config.seed,
            timing_scope="end_to_end",
            simulation_method="statevector",
            qubo=qubo,
            config=config,
            versions=versions,
        ),
    )


def benchmark_source(source: str, config: QAOAConfig) -> CompilerBenchmarkResult:
    analysis = generate_source(source, p=config.p)
    if analysis.status == "rejected":
        raise CompilationError(analysis.diagnostics)
    return benchmark_qubo(analysis.qubo, config)
