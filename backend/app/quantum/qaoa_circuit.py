"""Qiskit circuit construction from the shared symbolic QAOA gate plan."""

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

from app.quantum.circuits import build_qaoa_preview
from app.schemas.contracts import QUBO


def build_qaoa_circuit(qubo: QUBO, p: int = 1) -> tuple[QuantumCircuit, tuple[Parameter, ...]]:
    """Return a parameterized circuit and the plan's explicit parameter order.

    Parameters are gamma_0, beta_0, gamma_1, beta_1, ... even for zero costs.
    Bind with a Parameter-to-value mapping built from the returned tuple. Using
    assign_parameters(mapping, strict=False) also handles unused parameters.

    x[i] maps to qubit i. The circuit contains H preparation, the shared cost and
    mixer gates, and their global phase. Measurement wiring, transpilation, and
    execution belong to the future runner. Import this optional-Qiskit module
    only where concrete quantum circuit construction is needed.
    """
    plan = build_qaoa_preview(qubo, p=p)
    parameters = {name: Parameter(name) for name in plan.parameters}
    circuit = QuantumCircuit(plan.num_qubits, name="qaoa")
    gate_methods = {"h": circuit.h, "rz": circuit.rz, "cp": circuit.cp, "rx": circuit.rx}

    for gate in plan.gates:
        if gate.angle is None:
            gate_methods[gate.name](*gate.qubits)
        else:
            angle = parameters[gate.angle.parameter] * gate.angle.coefficient
            gate_methods[gate.name](angle, *gate.qubits)
    for phase in plan.global_phase:
        circuit.global_phase += parameters[phase.parameter] * phase.coefficient

    return circuit, tuple(parameters.values())
