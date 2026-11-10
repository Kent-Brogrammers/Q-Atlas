"""Exact rotation decomposition for each constant-density layer."""

import numpy as np
from qiskit import QuantumCircuit

from app.experiments.neutrinos.model import Experiment
from app.experiments.neutrinos.physics import coefficients


def build_circuit(experiment: Experiment) -> QuantumCircuit:
    circuit = QuantumCircuit(1, name="two_flavor_propagation")
    for layer in experiment.layers:
        x, z = coefficients(experiment.parameters, layer.potential)
        radius = float(np.hypot(x, z))
        if radius == 0 or layer.distance == 0:
            continue
        angle = float(np.arctan2(x, z))
        # Chronological order gives Ry(angle) Rz(2*r*L) Ry(-angle) as a matrix.
        circuit.ry(-angle, 0)
        circuit.rz(2 * radius * layer.distance, 0)
        circuit.ry(angle, 0)
    return circuit
