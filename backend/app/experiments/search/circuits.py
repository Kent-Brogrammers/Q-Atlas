"""Small Grover circuits; displayed bit i maps to qubit i (not Qiskit order)."""

from qiskit import QuantumCircuit


def build_phase_oracle(marked_state: str) -> QuantumCircuit:
    """Flip exactly one basis state's phase using an explicitly supplied target.

    The target is known to the circuit builder: this is an oracle-model demo,
    not discovery of information unknown to the application.
    """
    if not isinstance(marked_state, str) or not 1 <= len(marked_state) <= 6:
        raise ValueError("marked_state must contain 1 to 6 binary characters")
    if set(marked_state) - {"0", "1"}:
        raise ValueError("marked_state must contain only 0 and 1")
    circuit = QuantumCircuit(len(marked_state), name="oracle")
    zero_wires = [i for i, bit in enumerate(marked_state) if bit == "0"]
    for wire in zero_wires:
        circuit.x(wire)
    _phase_flip_all_ones(circuit)
    for wire in zero_wires:
        circuit.x(wire)
    return circuit


def _phase_flip_all_ones(circuit: QuantumCircuit) -> None:
    target = circuit.num_qubits - 1
    if target == 0:
        circuit.z(0)
    else:
        circuit.h(target)
        circuit.mcx(list(range(target)), target)
        circuit.h(target)


def build_diffusion(num_qubits: int) -> QuantumCircuit:
    """Reflect about the uniform state, up to an irrelevant global phase."""
    if type(num_qubits) is not int or not 1 <= num_qubits <= 6:
        raise ValueError("num_qubits must be an integer from 1 to 6")
    circuit = QuantumCircuit(num_qubits, name="diffusion")
    circuit.h(range(num_qubits))
    circuit.x(range(num_qubits))
    _phase_flip_all_ones(circuit)
    circuit.x(range(num_qubits))
    circuit.h(range(num_qubits))
    return circuit


def build_grover_circuit(
    marked_state: str | list[str], iterations: int, *, measure: bool = True
) -> QuantumCircuit:
    """Prepare a uniform state and apply the requested number of Grover steps.

    Measurement strings from Qiskit must be reversed before display to preserve
    the shared x[0]x[1]... convention. A list defines one combined phase oracle;
    its internal target-by-target construction cost is not one primitive gate.
    """
    if type(iterations) is not int or not 0 <= iterations <= 32:
        raise ValueError("iterations must be an integer from 0 to 32")
    states = [marked_state] if isinstance(marked_state, str) else marked_state
    if not isinstance(states, list) or not states:
        raise ValueError("provide a target string or a nonempty list of target strings")
    # Validate individual targets before inspecting widths or duplicate values.
    oracles = [build_phase_oracle(state) for state in states]
    width = oracles[0].num_qubits
    if any(oracle.num_qubits != width for oracle in oracles) or len(set(states)) != len(states):
        raise ValueError("marked states must be unique and have the same width")
    oracle = QuantumCircuit(width, name="oracle")
    for target_oracle in oracles:
        oracle.compose(target_oracle, inplace=True)
    circuit = QuantumCircuit(width)
    circuit.h(range(circuit.num_qubits))
    diffusion = build_diffusion(circuit.num_qubits)
    for _ in range(iterations):
        circuit.compose(oracle, inplace=True)
        circuit.compose(diffusion, inplace=True)
    if measure:
        circuit.measure_all()
    return circuit
