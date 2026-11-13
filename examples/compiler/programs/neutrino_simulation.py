"""Electron-neutrino conversion through matter, in the Neutrino Lab's normalized units.

A safe scientific declaration: the compiler reads these literals without executing
Python, generates exact layer-rotation circuits and a standalone SciPy/Aer script.
Run compares the same flavor probabilities at all nine matter potentials.
At potential cos(0.4) ≈ 0.921061 and this distance, conversion should peak.
"""


@qatlas.neutrino
def neutrino_simulation():
    return {
        "experiment": {
            "parameters": {
                "theta": 0.2,
                "delta_m2": 1.0,
                "energy": 1.0,
                "particle": "neutrino",
            },
            "layers": [{"distance": 4.0336988686318564, "potential": 0.0}],
            "shots": 1024,
            "seed": 42,
        },
        "axis": "potential",
        "samples": 9,
        "max_potential": 1.8421219880057702,
        "timeout_seconds": 30,
    }
