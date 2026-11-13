"""Resource counts for the actual simulator circuit, without extra transpilation."""

from collections import Counter

from qiskit import QuantumCircuit
from qiskit.circuit import Gate


def circuit_gate_counts(circuit: QuantumCircuit) -> dict[str, int]:
    """Count top-level Gate instances; measurements/reset/barriers are not gates.

    A retained multi-controlled or custom composite gate counts once. Do not infer
    native-device costs or internal Aer execution operations from this histogram.
    """
    return dict(
        sorted(
            Counter(
                instruction.operation.name
                for instruction in circuit.data
                if isinstance(instruction.operation, Gate)
            ).items()
        )
    )
