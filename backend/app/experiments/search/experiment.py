"""Assemble a measured local Grover/classical comparison in the shared envelope."""

from hashlib import sha256
from importlib.metadata import version
from time import perf_counter

from qiskit import transpile
from qiskit_aer import AerSimulator

from app.experiments.search.circuits import build_grover_circuit
from app.experiments.search.classical import run_classical_search
from app.experiments.search.settings import (
    request_diagnostics,
    suggested_iterations,
    theoretical_probability,
)
from app.schemas.contracts import (
    SearchMetadata,
    SearchMetrics,
    SearchRequest,
    SearchResult,
    SolverResult,
    TimingBreakdown,
)


def run_experiment(request: SearchRequest) -> SearchResult:
    """Worker entry point; use run_search to enforce cancellation of native work.

    Each solver timer excludes worker startup/imports, HTTP and serialization.
    Quantum elapsed time includes construction through measurement extraction.
    """
    if diagnostics := request_diagnostics(request):
        raise ValueError("; ".join(item.message for item in diagnostics))
    # Copy instead of mutating the caller; record the effective iteration choice.
    iterations = request.iterations
    if iterations is None:
        iterations = suggested_iterations(1 << request.num_qubits, len(request.marked_states))
    effective = request.model_copy(update={"iterations": iterations})
    classical = run_classical_search(effective)

    started = perf_counter()
    circuit = build_grover_circuit(sorted(request.marked_states), iterations)
    simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    transpilation_started = perf_counter()
    compiled = transpile(
        circuit, simulator, seed_transpiler=request.config.seed, optimization_level=1
    )
    transpilation_ms = (perf_counter() - transpilation_started) * 1000
    sampling_started = perf_counter()
    execution = simulator.run(
        compiled, shots=request.config.shots, seed_simulator=request.config.seed
    ).result()
    sampling_ms = (perf_counter() - sampling_started) * 1000
    if not execution.success:
        raise RuntimeError("Aer search simulation failed")
    counts = {bits[::-1]: count for bits, count in execution.get_counts().items()}
    if sum(counts.values()) != request.config.shots:
        raise RuntimeError("Aer returned an unexpected shot count")
    successful_shots = sum(counts.get(state, 0) for state in request.marked_states)
    success = successful_shots / request.config.shots
    # Most frequent observed string, not a promise of success or a hidden postselection.
    most_frequent = min(counts, key=lambda state: (-counts[state], state))
    quantum_ms = (perf_counter() - started) * 1000
    instance = f"{request.num_qubits}:" + ",".join(sorted(request.marked_states))
    return SearchResult(
        problem_id="search-" + sha256(instance.encode()).hexdigest()[:16],
        backend=request.config.backend,
        classical=SolverResult(
            algorithm="lexicographic_search_without_replacement",
            elapsed_ms=classical.elapsed_ms,
            best_bitstring=classical.found_state,
            timing=TimingBreakdown(
                includes_queue=False,
                includes_transpilation=False,
                includes_optimizer=False,
                includes_sampling=False,
            ),
        ),
        quantum=SolverResult(
            algorithm="grover",
            elapsed_ms=quantum_ms,
            best_bitstring=most_frequent,
            timing=TimingBreakdown(
                includes_queue=False,
                includes_transpilation=True,
                includes_optimizer=False,
                includes_sampling=True,
                transpilation_ms=transpilation_ms,
                sampling_ms=sampling_ms,
            ),
        ),
        metrics=SearchMetrics(
            num_qubits=request.num_qubits,
            circuit_depth=compiled.depth(),
            shots=request.config.shots,
            success_probability=success,
            theoretical_success_probability=theoretical_probability(
                1 << request.num_qubits, len(request.marked_states), iterations
            ),
            quantum_oracle_queries=iterations,
            classical_expected_queries=classical.expected_queries,
            classical_worst_case_queries=classical.worst_case_queries,
            successful_shots=successful_shots,
            classical_observed_queries=classical.oracle_queries,
            quantum_total_oracle_queries=iterations * request.config.shots,
        ),
        metadata=SearchMetadata(
            seed=request.config.seed,
            timing_scope="end_to_end",
            simulation_method="statevector",
            versions={name: version(name) for name in ("qiskit", "qiskit-aer", "numpy")},
            parameters=effective,
            oracle_assumptions=(
                "Targets are explicitly known to construct the combined phase oracle. "
                "One Grover iteration uses one combined oracle query per shot, not one gate. "
                f"The sampling batch uses {iterations * request.config.shots} oracle calls. "
                f"Classical lexicographic search made {classical.oracle_queries} predicate checks. "
                "Classical expected queries assume uniformly distributed marked positions; "
                "worst case is without replacement, stopping at first success. "
                "Display order is qubit 0 first; Qiskit counts are reversed. "
                "Quantum best_bitstring is the most frequent observation and may be unmarked. "
                "Depth is after transpilation to Aer, not physical hardware. Solver timers "
                "include each solver's preparation and extraction, exclude worker startup, "
                "imports, result-envelope assembly, serialization and HTTP. Single ideal "
                "simulator run; query complexity does not establish runtime speedup."
            ),
        ),
    )
