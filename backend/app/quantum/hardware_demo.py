"""Small five-experiment physical demonstration in one capped Runtime job."""

from uuid import uuid4

from app.schemas.hardware import HardwareRequest


def demo_request(request_id=None):
    config = {"p": 1, "max_iterations": 20, "shots": 128, "timeout_seconds": 30}
    tasks = [
        {
            "kind": "compiler",
            "parameters": {
                "source": "@qatlas.objective\ndef select(red, blue):\n"
                "    return 5 - 2*red + blue + red*blue\n",
                "config": config,
            },
        },
        {
            "kind": "optimization",
            "parameters": {
                "problem": {
                    "kind": "graph",
                    "num_vertices": 3,
                    "edges": [
                        {"i": 0, "j": 1, "coefficient": 1},
                        {"i": 1, "j": 2, "coefficient": 1},
                        {"i": 0, "j": 2, "coefficient": 1},
                    ],
                },
                "config": config,
            },
        },
        {
            "kind": "search",
            "parameters": {
                "num_qubits": 3,
                "marked_states": ["001"],
                "iterations": 2,
                "config": {"shots": 128, "seed": 42},
            },
        },
        {
            "kind": "materials",
            "parameters": {
                "num_spins": 2,
                "coupling": 1,
                "field": 0.7,
                "evolution_time": 1,
                "trotter_steps": 4,
                "time_samples": 1,
                "observable": "magnetization",
                "config": {"shots": 128, "seed": 42},
            },
        },
        {
            "kind": "neutrinos",
            "parameters": {
                "experiment": {
                    "parameters": {"theta": 0.2, "delta_m2": 1, "energy": 1},
                    "layers": [{"distance": 4.0336988686318564, "potential": 0}],
                    "shots": 128,
                    "seed": 42,
                },
                "axis": "potential",
                "samples": 3,
                "max_potential": 1.8421219880057702,
            },
        },
    ]
    return HardwareRequest(
        task={"kind": "suite", "parameters": tasks},
        request_id=request_id or uuid4(),
        confirmed=True,
        shots=128,
        max_execution_seconds=10,
    )
