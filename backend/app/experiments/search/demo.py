"""Run with: python -m app.experiments.search.demo (from backend/)."""

import json
from math import asin, sin, sqrt
from time import perf_counter

from qiskit import transpile
from qiskit_aer import AerSimulator

from app.experiments.search.circuits import build_grover_circuit


def main() -> None:
    marked_state, iterations, shots, seed = "101", 2, 1024, 42
    start = perf_counter()
    circuit = build_grover_circuit(marked_state, iterations)
    simulator = AerSimulator()
    compiled = transpile(circuit, simulator, seed_transpiler=seed)
    raw_counts = simulator.run(compiled, shots=shots, seed_simulator=seed).result().get_counts()
    counts = {state[::-1]: count for state, count in raw_counts.items()}
    elapsed_ms = (perf_counter() - start) * 1000
    theta = asin(1 / sqrt(2 ** len(marked_state)))
    print(
        json.dumps(
            {
                "marked_state": marked_state,
                "bit_order": "leftmost bit is qubit 0; Qiskit counts reversed",
                "iterations": iterations,
                "oracle_calls_per_shot": iterations,
                "shots": shots,
                "seed": seed,
                "counts": dict(sorted(counts.items())),
                "measured_success_probability": counts.get(marked_state, 0) / shots,
                "theoretical_success_probability": sin((2 * iterations + 1) * theta) ** 2,
                "transpiled_circuit_depth": compiled.depth(),
                "elapsed_ms": elapsed_ms,
                "timing_scope": "circuit construction through count conversion; excludes imports",
                "simulated": True,
                "note": "Single local Aer run; not a classical benchmark or evidence of speedup.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
