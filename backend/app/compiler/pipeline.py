"""Compiler integration with Developer 3's shared runners; no local solver copies."""

import hashlib
import json
import math
import platform
from importlib.metadata import PackageNotFoundError, version

from app.compiler.analysis import analyze_source
from app.experiments.optimization import solvers
from app.quantum import qaoa
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkResult,
    Diagnostic,
    OptimizationMetadata,
    QAOAConfig,
)


class CompilationError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics


def benchmark_qubo(qubo: QUBO, config: QAOAConfig) -> CompilerBenchmarkResult:
    """Pass the same canonical instance/config to both shared runners.

    The current shared implementations are explicit stubs. Tests inject synthetic
    results at these two boundaries; production never substitutes mock measurements.
    Source analysis is outside both solvers' reported end-to-end timers.
    """
    classical = solvers.run_classical(qubo, config)
    quantum = qaoa.run_qaoa(qubo, config)
    metrics = quantum.metrics.model_copy(deep=True)
    metrics.optimality_gap = None
    if classical.algorithm == "brute_force" and classical.objective is not None:
        gap = quantum.objective - classical.objective
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
    canonical = json.dumps(qubo.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return CompilerBenchmarkResult(
        problem_id="compiler-" + hashlib.sha256(canonical.encode()).hexdigest()[:24],
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
    analysis = analyze_source(source)
    if analysis.status == "rejected":
        raise CompilationError(analysis.diagnostics)
    return benchmark_qubo(analysis.qubo, config)
