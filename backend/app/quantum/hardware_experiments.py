"""Prepare the established five experiments for physical sampling and decode counts.

No provider access here. QAOA reuses Developer 3's circuit and angle optimizer;
the other experiences reuse their existing circuit builders and independent physics.
"""

from dataclasses import asdict
from hashlib import sha256
from math import isfinite
from time import perf_counter

import numpy as np

from app.compiler.pipeline import prepare_benchmark
from app.experiments.optimization.maxcut import maxcut_to_qubo
from app.experiments.optimization.solvers import run_classical
from app.quantum.qaoa import _best_sample
from app.quantum.qaoa_circuit import build_qaoa_circuit
from app.quantum.qaoa_optimization import optimize_qaoa_angles
from app.schemas.contracts import QUBO, GraphInput, QAOAConfig
from app.schemas.hardware import HardwareJob, HardwareMetric, HardwareRequest


def validate_task(request: HardwareRequest) -> None:
    task, parameters = request.task, request.task.parameters
    if task.kind == "suite":
        if len({t.kind for t in parameters}) != len(parameters):
            raise ValueError("Use each experiment at most once in a QPU suite.")
        for child in parameters:
            validate_task(request.model_copy(update={"task": child}))
        return
    if task.kind in ("compiler", "optimization"):
        if parameters.config.p > 2 or parameters.config.max_iterations > 40:
            raise ValueError("QPU QAOA supports at most 2 layers and 40 local evaluations.")
        if task.kind == "compiler":
            prepare_benchmark(parameters.source, parameters.config)
        else:
            width = (
                parameters.problem.num_vertices
                if isinstance(parameters.problem, GraphInput)
                else parameters.problem.qubo.num_variables
            )
            if width > 8:
                raise ValueError("QPU optimization supports at most 8 variables.")
    elif task.kind == "materials":
        if (
            parameters.model != "ising"
            or parameters.boundary != "open"
            or parameters.num_spins > 4
            or parameters.trotter_steps > 32
            or parameters.time_samples > 5
        ):
            raise ValueError(
                "QPU materials supports open Ising, 2–4 spins, at most 32 steps and 5 times."
            )
        if abs(parameters.coupling) > 10 or abs(parameters.field) > 10:
            raise ValueError("Materials coefficients must be in [-10, 10].")
    elif task.kind == "search":
        if (
            parameters.num_qubits > 6
            or len(parameters.marked_states) > 8
            or (parameters.iterations is not None and parameters.iterations > 8)
        ):
            raise ValueError("QPU search supports at most 6 qubits, 8 targets and 8 iterations.")
    elif task.kind == "neutrinos":
        if parameters.samples > 9 or len(parameters.experiment.layers) > 8:
            raise ValueError("QPU neutrinos supports at most 9 curve points and 8 layers.")


def problem_id(request: HardwareRequest) -> str:
    return sha256(request.task.model_dump_json().encode()).hexdigest()[:24]


def prepare(request: HardwareRequest, record: HardwareJob):
    """Return measured logical circuits and retain independent classical references."""
    from qiskit import ClassicalRegister

    task, p = request.task.kind, request.task.parameters
    start = perf_counter()
    if task == "suite":
        circuits = []
        for child_task in p:
            child_request = request.model_copy(update={"task": child_task})
            child = HardwareJob(
                request_id=record.request_id,
                task=child_task,
                problem_id=problem_id(child_request),
                created_at_utc=record.created_at_utc,
                updated_at_utc=record.updated_at_utc,
                status=record.status,
                shots=record.shots,
                max_execution_seconds=record.max_execution_seconds,
                versions=record.versions,
            )
            built = prepare(child_request, child)
            child.circuit_depths = [c.depth() for c in built]
            circuits.extend(built)
            record.children.append(child)
        record.timings.classical_ms = sum(c.timings.classical_ms or 0 for c in record.children)
        record.timings.local_training_ms = sum(
            c.timings.local_training_ms or 0 for c in record.children
        )
        record.classical_reference = {
            "scope": "One physical job; provider usage belongs to the entire suite."
        }
    elif task in ("compiler", "optimization"):
        config = QAOAConfig(**{**p.config.model_dump(), "shots": request.shots})
        if task == "compiler":
            qubo = prepare_benchmark(p.source, config).qubo
        else:
            qubo = (
                maxcut_to_qubo(p.problem) if isinstance(p.problem, GraphInput) else p.problem.qubo
            )
        exact = run_classical(qubo, config)
        record.timings.classical_ms = exact.elapsed_ms
        record.classical_reference = {
            "qubo": qubo.model_dump(),
            "solver": exact.model_dump(),
            "config": config.model_dump(),
        }
        optimized = optimize_qaoa_angles(qubo, config)
        record.timings.local_training_ms = optimized.elapsed_ms
        record.classical_reference["angles"] = list(optimized.angles)
        circuit, parameters = build_qaoa_circuit(qubo, p=config.p)
        circuit = circuit.assign_parameters(dict(zip(parameters, optimized.angles, strict=True)))
        circuit.add_register(ClassicalRegister(qubo.num_variables, "meas"))
        circuit.measure(range(qubo.num_variables), range(qubo.num_variables))
        circuits = [circuit]
    elif task == "search":
        from app.experiments.search.circuits import build_grover_circuit
        from app.experiments.search.classical import run_classical_search
        from app.experiments.search.settings import suggested_iterations, theoretical_probability

        reference = run_classical_search(p)
        k = (
            p.iterations
            if p.iterations is not None
            else suggested_iterations(1 << p.num_qubits, len(p.marked_states))
        )
        record.timings.classical_ms = reference.elapsed_ms
        record.classical_reference = {
            **asdict(reference),
            "iterations": k,
            "ideal_success": theoretical_probability(1 << p.num_qubits, len(p.marked_states), k),
            "query_note": (
                "Explicit known targets construct the oracle. Expected queries assume "
                "uniform marked positions; observed lexicographic checks are reported separately."
            ),
        }
        circuits = [build_grover_circuit(p.marked_states, k)]
    elif task == "materials":
        from app.experiments.materials.circuits import build_trotter_circuit, measurement_circuits
        from app.experiments.materials.physics import (
            build_hamiltonian,
            evolve_exact,
            state_observables,
        )

        times = (
            [p.evolution_time]
            if p.time_samples == 1
            else np.linspace(0, p.evolution_time, p.time_samples).tolist()
        )
        classical_start = perf_counter()
        hamiltonian = build_hamiltonian(p.num_spins, p.coupling, p.field)
        references = [
            asdict(
                state_observables(evolve_exact(hamiltonian, t), p.num_spins, p.coupling, p.field)
            )
            for t in times
        ]
        record.timings.classical_ms = (perf_counter() - classical_start) * 1000
        record.classical_reference = {
            "coordinates": times,
            "observables": references,
            "unit": "dimensionless, hbar=1",
            "shots_scope": "shots per basis per time; two measurement bases",
        }
        circuits = []
        for t in times:
            circuits.extend(
                measurement_circuits(
                    build_trotter_circuit(p.num_spins, p.coupling, p.field, t, p.trotter_steps)
                )
            )
    else:
        from app.experiments.neutrinos.circuit import build_circuit
        from app.experiments.neutrinos.model import Experiment, Layer
        from app.experiments.neutrinos.physics import numerical, probabilities

        extent = (
            p.max_potential
            if p.axis == "potential"
            else sum(layer.distance for layer in p.experiment.layers)
        )
        grid = np.linspace(0, extent, p.samples).tolist() if extent else [0.0]
        points = []
        for i, coordinate in enumerate(grid):
            if p.axis == "potential":
                layers = [Layer(distance=p.experiment.layers[0].distance, potential=coordinate)]
            else:
                layers, remaining = [], coordinate
                for layer in p.experiment.layers:
                    length = min(remaining, layer.distance)
                    layers.append(Layer(distance=length, potential=layer.potential))
                    remaining = max(0, remaining - length)
                    if remaining == 0:
                        break
                if i == len(grid) - 1:
                    layers = p.experiment.layers
            points.append(
                Experiment(
                    parameters=p.experiment.parameters,
                    layers=layers,
                    shots=request.shots,
                    seed=p.experiment.seed,
                )
            )
        classical_start = perf_counter()
        references = [probabilities(numerical(point)) for point in points]
        record.timings.classical_ms = (perf_counter() - classical_start) * 1000
        record.classical_reference = {
            "coordinates": grid,
            "probabilities": references,
            "axis": p.axis,
            "unit": "normalized",
        }
        circuits = [build_circuit(point) for point in points]
        for circuit in circuits:
            circuit.measure_all()
    record.num_qubits = max(circuit.num_qubits for circuit in circuits)
    record.timings.preparation_ms = (perf_counter() - start) * 1000
    return circuits


def validate_counts(counts, width, expected_shots):
    if (
        not isinstance(counts, dict)
        or not counts
        or any(
            not isinstance(bits, str)
            or len(bits) != width
            or set(bits) - {"0", "1"}
            or type(count) is not int
            or count < 0
            for bits, count in counts.items()
        )
        or sum(counts.values()) != expected_shots
    ):
        raise ValueError("Provider counts do not match the circuit width and requested shots.")


def decode(record: HardwareJob, counts: list[dict[str, int]]):
    if len(counts) != len(record.circuit_depths):
        raise ValueError("Provider result count differs from submitted circuits.")
    if record.task.kind == "suite":
        offset = 0
        children = [child.model_copy(deep=True) for child in record.children]
        for child in children:
            size = len(child.circuit_depths)
            decode(child, counts[offset : offset + size])
            offset += size
        record.children = children
        record.counts = counts
        record.measurement_complete = True
        return
    for item in counts:
        validate_counts(item, record.num_qubits, record.shots)
    task, p, ref = record.task.kind, record.task.parameters, record.classical_reference
    rows = []

    def add(name, classical, quantum, unit, coordinate=None):
        if not all(isfinite(v) for v in (classical, quantum)):
            raise ValueError("Nonfinite result.")
        rows.append(
            HardwareMetric(
                name=name,
                classical=classical,
                quantum=quantum,
                absolute_error=abs(quantum - classical),
                coordinate=coordinate,
                unit=unit,
            )
        )

    if task in ("compiler", "optimization"):
        qubo = QUBO.model_validate(ref["qubo"])
        objective, bits = _best_sample(qubo, counts[0], record.shots)
        optimum = ref["solver"]["objective"]
        if objective < optimum - 1e-9:
            raise ValueError("Sample is below exact optimum.")
        add("Objective (minimize)", optimum, objective, "cost")
        ref["qpu_best_bitstring"] = bits
    elif task == "search":
        success = (
            sum(count for bits, count in counts[0].items() if bits[::-1] in p.marked_states)
            / record.shots
        )
        add("Marked-state success probability", 1.0, success, "probability")
        ref["qpu_oracle_queries_per_attempt"] = ref["iterations"]
        ref["qpu_total_oracle_queries"] = ref["iterations"] * record.shots
    elif task == "materials":
        from app.experiments.materials.circuits import measured_observables

        for i, t in enumerate(ref["coordinates"]):
            measured = asdict(
                measured_observables(
                    counts[2 * i], counts[2 * i + 1], p.num_spins, p.coupling, p.field
                )
            )
            for name in ("magnetization_z", "energy"):
                add(name, ref["observables"][i][name], measured[name], "dimensionless", t)
    else:
        for i, coordinate in enumerate(ref["coordinates"]):
            for flavor, bit in (("electron", "0"), ("other", "1")):
                add(
                    f"{flavor} flavor probability",
                    ref["probabilities"][i][flavor],
                    counts[i].get(bit, 0) / record.shots,
                    "probability",
                    coordinate,
                )
    record.counts = counts
    record.metrics = rows
    record.measurement_complete = True
