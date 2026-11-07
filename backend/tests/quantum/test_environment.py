"""Confirm the local simulator and its V2 result API work before QAOA work."""

import pytest
from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2


@pytest.mark.environment
def test_aer_sampler_v2_executes_a_tiny_circuit():
    circuit = QuantumCircuit(1)
    circuit.x(0)
    circuit.measure_all()

    sampler = SamplerV2(default_shots=32, seed=42)
    result = sampler.run([circuit]).result()

    assert result[0].data.meas.get_counts() == {"1": 32}
