"""Confirm the local simulator and its V2 result API work before QAOA work."""

import pytest


@pytest.mark.environment
def test_aer_sampler_v2_executes_a_tiny_circuit():
    qiskit = pytest.importorskip("qiskit", reason="Install the optional quantum extra")
    primitives = pytest.importorskip("qiskit_aer.primitives", reason="Install the quantum extra")
    circuit = qiskit.QuantumCircuit(1)
    circuit.x(0)
    circuit.measure_all()

    sampler = primitives.SamplerV2(default_shots=32, seed=42)
    result = sampler.run([circuit]).result()

    assert result[0].data.meas.get_counts() == {"1": 32}
