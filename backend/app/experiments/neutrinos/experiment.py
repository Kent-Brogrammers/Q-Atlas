"""Measured local experiment records, deliberately separate from the HTTP contracts."""

from importlib.metadata import version
from time import perf_counter

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.library import SaveStatevector

from app.experiments.neutrinos.circuit import build_circuit
from app.experiments.neutrinos.model import Experiment
from app.experiments.neutrinos.physics import analytical, numerical, probabilities
from app.schemas.contracts import TimingBreakdown


def run(experiment: Experiment) -> dict:
    start = perf_counter()
    reference = numerical(experiment)
    classical = probabilities(reference)
    classical_ms = (perf_counter() - start) * 1000
    convergence_start = perf_counter()
    refined = numerical(experiment, subdivisions=2)
    convergence_ms = (perf_counter() - convergence_start) * 1000
    start = perf_counter()
    backend = AerSimulator(method="statevector", max_parallel_threads=1)
    circuit = build_circuit(experiment)
    compile_start = perf_counter()
    compiled = transpile(circuit, basis_gates=["ry", "rz"], optimization_level=0, num_processes=1)
    compile_ms = (perf_counter() - compile_start) * 1000
    saved = compiled.copy()
    saved.append(SaveStatevector(1), [0])
    ideal_start = perf_counter()
    result = backend.run(saved, shots=1).result()
    if not result.success:
        raise RuntimeError("Aer statevector execution failed")
    state = np.asarray(result.get_statevector(0))
    ideal = probabilities(state)
    ideal_ms = (perf_counter() - ideal_start) * 1000
    measured = compiled.copy()
    measured.measure_all()
    sample_start = perf_counter()
    result = backend.run(measured, shots=experiment.shots, seed_simulator=experiment.seed).result()
    if not result.success:
        raise RuntimeError("Aer sampling failed")
    counts = result.get_counts(0)
    shot = {
        "electron": counts.get("0", 0) / experiment.shots,
        "other": counts.get("1", 0) / experiment.shots,
    }
    sampling_ms = (perf_counter() - sample_start) * 1000
    circuit_ms = (perf_counter() - start) * 1000
    prediction = (
        analytical(experiment.parameters, experiment.layers[0])
        if len(experiment.layers) == 1
        else None
    )
    return {
        "experiment": "q_neutrino",
        "status": "completed",
        "backend": "aer_simulator",
        "simulated": True,
        "configuration": experiment.model_dump(mode="json"),
        "analytical": prediction,
        "numerical": classical,
        "ideal": ideal,
        "measured": shot,
        "absolute_errors": {
            "ideal_vs_numerical": {key: abs(ideal[key] - classical[key]) for key in ideal},
            "sampling": {key: abs(shot[key] - ideal[key]) for key in ideal},
            "total": {key: abs(shot[key] - classical[key]) for key in ideal},
            "analytical_vs_numerical": None
            if prediction is None
            else {key: abs(prediction[key] - classical[key]) for key in ideal},
        },
        "numerics": {
            "reference_norm": float(np.linalg.norm(reference)),
            "ideal_norm": float(np.linalg.norm(state)),
            "state_error_l2": float(np.linalg.norm(state - reference)),
            "subdivision_check": {
                "subdivisions_per_layer": 2,
                "state_change_l2": float(np.linalg.norm(refined - reference)),
                "scope": "constant-layer numerical stability, not smooth-profile convergence",
            },
            "approximation": "exact constant-layer propagators; floating-point error only",
        },
        "num_qubits": 1,
        "circuit_depth": measured.depth(),
        "shots": experiment.shots,
        "counts": counts,
        "circuit_diagram": str(measured.draw(output="text", fold=-1)),
        "rotations": [
            {"gate": item.operation.name, "angle": float(item.operation.params[0])}
            for item in compiled.data
        ],
        "statevector": [(float(a.real), float(a.imag)) for a in state],
        "basis_gates": ["ry", "rz"],
        "timing_ms": {
            "classical": classical_ms,
            "convergence_check": convergence_ms,
            "circuit_end_to_end": circuit_ms,
            "ideal_execution": ideal_ms,
        },
        "quantum_timing": TimingBreakdown(
            includes_queue=False,
            includes_transpilation=True,
            includes_optimizer=False,
            includes_sampling=True,
            transpilation_ms=compile_ms,
            sampling_ms=sampling_ms,
        ).model_dump(),
        "versions": {
            package: version(package) for package in ("numpy", "scipy", "qiskit", "qiskit-aer")
        },
    }


def density_sweep(experiment: Experiment, potentials: list[float]) -> list[dict]:
    """Compare constant densities on the same baseline; validate the grid first."""
    from app.experiments.neutrinos.model import DensitySweep, Layer

    sweep = DensitySweep(experiment=experiment, potentials=potentials)
    if len(experiment.layers) != 1:
        raise ValueError("density sweep requires a single constant-density baseline")
    layers = [Layer(distance=experiment.layers[0].distance, potential=v) for v in sweep.potentials]
    return [
        run(
            Experiment(
                parameters=experiment.parameters,
                layers=[layer],
                shots=experiment.shots,
                seed=(experiment.seed + i) % 2**32,
            )
        )
        for i, layer in enumerate(layers)
    ]
