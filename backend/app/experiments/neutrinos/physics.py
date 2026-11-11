"""Independent analytic and dense-matrix reference, without Qiskit imports."""

import numpy as np
from scipy.linalg import expm

from app.experiments.neutrinos.model import Experiment, Layer, Parameters


def coefficients(parameters: Parameters, potential: float) -> tuple[float, float]:
    k = parameters.delta_m2 / parameters.energy
    sign = 1 if parameters.particle == "neutrino" else -1
    # sin(pi) has a small floating-point residual at the exact zero-mixing endpoint.
    transverse = 0.0 if parameters.theta == np.pi / 2 else k * np.sin(2 * parameters.theta)
    return transverse, sign * potential - k * np.cos(2 * parameters.theta)


def analytical(parameters: Parameters, layer: Layer) -> dict:
    x, z = coefficients(parameters, layer.potential)
    frequency = float(np.hypot(x, z))
    strength = float((x / frequency) ** 2) if frequency else None
    conversion = strength * np.sin(frequency * layer.distance) ** 2 if frequency else 0.0
    # theta_m in [0, pi/2], including signed mass splitting via the squared transverse term.
    theta_m = float(np.arctan2(abs(x), -z) / 2) if frequency else None
    return {
        "electron": float(1 - conversion),
        "other": float(conversion),
        "mixing_strength": strength,
        "theta_m": theta_m,
        "frequency": frequency,
    }


def hamiltonian(parameters: Parameters, potential: float) -> np.ndarray:
    # Construct entries directly from the flavor-basis equation, not circuit rotations.
    k = parameters.delta_m2 / parameters.energy
    matter = potential if parameters.particle == "neutrino" else -potential
    diagonal = matter - k * np.cos(2 * parameters.theta)
    off_diagonal = 0.0 if parameters.theta == np.pi / 2 else k * np.sin(2 * parameters.theta)
    return np.array([[diagonal, off_diagonal], [off_diagonal, -diagonal]], dtype=complex)


def numerical(experiment: Experiment, *, subdivisions: int = 1) -> np.ndarray:
    """Evolve constant layers; subdivision checks numerical stability, not density accuracy."""
    if not isinstance(subdivisions, int) or not 1 <= subdivisions <= 64:
        raise ValueError("subdivisions must be an integer between 1 and 64")
    state = np.array([1, 0], dtype=complex)
    for layer in experiment.layers:
        step = expm(
            -1j
            * hamiltonian(experiment.parameters, layer.potential)
            * layer.distance
            / subdivisions
        )
        for _ in range(subdivisions):
            state = step @ state
    return state


def probabilities(state: np.ndarray) -> dict[str, float]:
    values = np.abs(state) ** 2
    return {"electron": float(values[0]), "other": float(values[1])}
