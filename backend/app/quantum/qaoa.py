"""Shared synchronous QAOA interface with bounded local Aer execution."""

from time import perf_counter_ns

from app.quantum._execution import run_with_deadline
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, OptimizationMetrics, QAOAConfig, QAOAResult, TimingBreakdown


def _best_sample(qubo: QUBO, counts: dict[str, int], shots: int) -> tuple[float, str]:
    """Validate observed counts and select minimum cost, then API bitstring on ties."""
    if not counts:
        raise RuntimeError("Aer returned empty measurement counts")
    for bitstring, count in counts.items():
        if (
            not isinstance(bitstring, str)
            or len(bitstring) != qubo.num_variables
            or set(bitstring) - {"0", "1"}
            or type(count) is not int
            or count <= 0
        ):
            raise RuntimeError("Aer returned invalid measurement counts")
    if sum(counts.values()) != shots:
        raise RuntimeError("Aer measurement counts do not match requested shots")
    return min((evaluate_qubo(qubo, raw[::-1]), raw[::-1]) for raw in counts)


def _sampled_run(qubo: QUBO, config: QAOAConfig) -> QAOAResult:
    """Worker-side search and final sampling using one shared deadline boundary.

    Report depth after level-1 all-to-all transpilation to rz/sx/x/cx, including
    the final measurement layer. Transpilation timing covers that compilation.
    Sampling timing covers the final Aer call and extraction of raw counts.
    """
    started_ns = perf_counter_ns()
    from qiskit import ClassicalRegister, transpile
    from qiskit_aer import AerSimulator

    from app.quantum.qaoa_circuit import build_qaoa_circuit
    from app.quantum.qaoa_optimization import _search_angles

    optimized = _search_angles(qubo, config)
    circuit, parameters = build_qaoa_circuit(qubo, p=config.p)
    circuit = circuit.assign_parameters(
        dict(zip(parameters, optimized.angles, strict=True)), strict=False
    )
    circuit.add_register(ClassicalRegister(qubo.num_variables, "meas"))
    circuit.measure(range(qubo.num_variables), range(qubo.num_variables))
    transpilation_started_ns = perf_counter_ns()
    compiled = transpile(
        circuit,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=1,
        seed_transpiler=config.seed,
    )
    transpilation_ms = (perf_counter_ns() - transpilation_started_ns) / 1_000_000
    simulator = AerSimulator(
        method="statevector",
        device="CPU",
        precision="double",
        max_parallel_threads=1,
        max_parallel_experiments=1,
    )
    sampling_started_ns = perf_counter_ns()
    sampled = simulator.run(compiled, shots=config.shots, seed_simulator=config.seed).result()
    if not sampled.success:
        raise RuntimeError("Aer final sampling failed")
    counts = sampled.get_counts(0)
    sampling_ms = (perf_counter_ns() - sampling_started_ns) / 1_000_000
    objective, bitstring = _best_sample(qubo, counts, config.shots)
    return QAOAResult(
        backend=config.backend,
        objective=objective,
        best_bitstring=bitstring,
        elapsed_ms=(perf_counter_ns() - started_ns) / 1_000_000,
        timing=TimingBreakdown(
            includes_queue=False,
            includes_transpilation=True,
            includes_optimizer=True,
            includes_sampling=True,
            transpilation_ms=transpilation_ms,
            optimizer_ms=optimized.optimizer_ms,
            sampling_ms=sampling_ms,
        ),
        metrics=OptimizationMetrics(
            num_qubits=qubo.num_variables,
            circuit_depth=compiled.depth(),
            shots=sum(counts.values()),
            optimizer_evaluations=optimized.evaluations,
        ),
    )


def run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult:
    """Optimize mean cost, then return the best assignment observed in final shots.

    API bitstrings put x[0] first and objectives include the QUBO constant. Equal
    sampled costs select the lexicographically smallest API string. The full local
    computation runs in one disposable worker within config.timeout_seconds.
    Raise TimeoutError on expiry and ImportError for missing optional packages.
    Elapsed time includes worker startup, all preparation, execution, and cleanup.
    """
    started_ns = perf_counter_ns()
    payload, _ = run_with_deadline(qubo, config, _sampled_run, task_name="QAOA run")
    if not isinstance(payload, QAOAResult):
        raise RuntimeError("QAOA worker returned an invalid result")
    result = QAOAResult.model_validate(payload.model_dump(mode="python"))
    elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000
    if elapsed_ms >= config.timeout_seconds * 1000:
        raise TimeoutError("QAOA run exceeded timeout_seconds")
    result.elapsed_ms = elapsed_ms
    return result
