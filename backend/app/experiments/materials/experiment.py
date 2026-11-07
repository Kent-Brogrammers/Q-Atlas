"""Assemble exact/Trotter/shot comparisons using the shared benchmark envelope."""

from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from time import perf_counter

import numpy as np
from qiskit import transpile

from app.experiments.materials.circuits import (
    build_trotter_circuit,
    make_simulator,
    measured_observables,
    measurement_circuits,
    simulate_statevector,
)
from app.experiments.materials.physics import (
    build_hamiltonian,
    evolve_exact,
    state_observables,
)
from app.schemas.contracts import (
    MaterialsMetadata,
    MaterialsMetrics,
    MaterialsObservableErrors,
    MaterialsObservables,
    MaterialsRequest,
    MaterialsResult,
    MaterialsTimePoint,
    SolverResult,
    TimingBreakdown,
)

BASIS_GATES = ["rx", "rzz", "h"]


def observable_errors(
    observed: MaterialsObservables,
    reference: MaterialsObservables,
) -> MaterialsObservableErrors:
    return MaterialsObservableErrors(
        magnetization_z=abs(observed.magnetization_z - reference.magnetization_z),
        zz_correlations=[
            abs(a - b)
            for a, b in zip(observed.zz_correlations, reference.zz_correlations, strict=True)
        ],
        energy=abs(observed.energy - reference.energy),
    )


def run_experiment(request: MaterialsRequest) -> MaterialsResult:
    """Worker entry point. Timings exclude process startup, HTTP, and serialization."""
    n, j, h = request.num_spins, request.coupling, request.field
    times = (
        [request.evolution_time]
        if request.time_samples == 1
        else np.linspace(0, request.evolution_time, request.time_samples).tolist()
    )
    start = perf_counter()
    hamiltonian = build_hamiltonian(n, j, h)
    exact_states = [evolve_exact(hamiltonian, t) for t in times]
    references = [
        MaterialsObservables(**asdict(state_observables(state, n, j, h))) for state in exact_states
    ]
    classical_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    simulator = make_simulator()
    transpilation_ms = ideal_ms = sampling_ms = 0.0
    points = []
    for index, (t, exact_state, exact) in enumerate(
        zip(times, exact_states, references, strict=True)
    ):
        circuit = build_trotter_circuit(n, j, h, t, request.trotter_steps)
        z_circuit, x_circuit = measurement_circuits(circuit)
        transpilation_start = perf_counter()
        # Explicit ideal-simulator basis; no hardware durations or noise model to override.
        compiled, compiled_z, compiled_x = transpile(
            [circuit, z_circuit, x_circuit],
            basis_gates=BASIS_GATES,
            optimization_level=0,
            seed_transpiler=request.config.seed,
            num_processes=1,
        )
        transpilation_ms += (perf_counter() - transpilation_start) * 1000
        ideal_start = perf_counter()
        ideal_state = simulate_statevector(compiled, simulator)
        ideal_ms += (perf_counter() - ideal_start) * 1000
        ideal = MaterialsObservables(**asdict(state_observables(ideal_state, n, j, h)))
        sampling_start = perf_counter()
        point_seed = None if request.config.seed is None else (request.config.seed + index) % 2**32
        sampled = simulator.run(
            [compiled_z, compiled_x],
            shots=request.config.shots,
            seed_simulator=point_seed,
        ).result()
        if not sampled.success:
            raise RuntimeError("Aer measurement simulation failed")
        z_counts, x_counts = sampled.get_counts(0), sampled.get_counts(1)
        sampling_ms += (perf_counter() - sampling_start) * 1000
        measured = MaterialsObservables(**asdict(measured_observables(z_counts, x_counts, n, j, h)))
        points.append(
            MaterialsTimePoint(
                time=t,
                exact=exact,
                ideal=ideal,
                measured=measured,
                trotter_error=observable_errors(ideal, exact),
                sampling_error=observable_errors(measured, ideal),
                total_error=observable_errors(measured, exact),
                state_fidelity=float(np.clip(abs(np.vdot(exact_state, ideal_state)) ** 2, 0, 1)),
                circuit_depth=max(compiled_z.depth(), compiled_x.depth()),
                shots_per_basis=request.config.shots,
            )
        )
    quantum_ms = (perf_counter() - start) * 1000
    point = points[-1]  # Existing scalar metrics summarize the requested terminal time.
    selected = "energy" if request.observable == "energy" else "magnetization_z"
    # Execution settings do not change the mathematical instance identifier.
    identity = request.model_dump_json(exclude={"config", "trotter_steps"})
    return MaterialsResult(
        problem_id=f"tfim-{sha256(identity.encode()).hexdigest()[:16]}",
        backend="aer_simulator",
        classical=SolverResult(
            algorithm="scipy_expm",
            elapsed_ms=classical_ms,
            timing=TimingBreakdown(
                includes_queue=False,
                includes_transpilation=False,
                includes_optimizer=False,
                includes_sampling=False,
            ),
        ),
        quantum=SolverResult(
            algorithm="suzuki_trotter_2_aer_statevector_and_shots",
            elapsed_ms=quantum_ms,
            timing=TimingBreakdown(
                includes_queue=False,
                includes_transpilation=True,
                includes_optimizer=False,
                includes_sampling=True,
                transpilation_ms=transpilation_ms,
                sampling_ms=sampling_ms,
            ),
        ),
        metrics=MaterialsMetrics(
            num_qubits=n,
            circuit_depth=max(item.circuit_depth for item in points),
            shots=request.config.shots,
            classical_observable=getattr(point.exact, selected),
            quantum_observable=getattr(point.measured, selected),
            ideal_observable=getattr(point.ideal, selected),
            absolute_error=getattr(point.total_error, selected),
            trotter_absolute_error=getattr(point.trotter_error, selected),
            sampling_absolute_error=getattr(point.sampling_error, selected),
            total_shots=2 * len(points) * request.config.shots,
            time_series=points,
        ),
        metadata=MaterialsMetadata(
            parameters=request,
            seed=request.config.seed,
            timing_scope="end_to_end",
            simulated=True,
            simulation_method="statevector",
            versions={p: version(p) for p in ("numpy", "scipy", "qiskit", "qiskit-aer")},
            hamiltonian_convention=(
                "H = -J sum(i=0..N-2) Z_i Z_(i+1) - h sum(i=0..N-1) X_i; open; hbar=1"
            ),
            energy_unit="dimensionless",
            observable_unit="dimensionless",
            initial_state="0" * n,
            execution_methods=["scipy_expm", "aer_statevector", "aer_shots"],
            measurement_bases=["Z", "X"],
            transpilation_basis=BASIS_GATES,
            circuit_depth_scope=(
                "max Z/X measured circuit depth after transpilation, "
                "including basis changes and measurements"
            ),
            ideal_elapsed_ms=ideal_ms,
            sampling_seed_policy=(
                "seed_simulator = (seed + time_index) modulo 2**32; "
                "null seed uses nondeterministic sampling"
            ),
        ),
    )
