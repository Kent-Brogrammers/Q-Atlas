"""Shared symbolic QAOA construction, without a simulator or execution engine.

Developer 3's runner should consume this gate plan when constructing Qiskit circuits.
No source parsing, optimizer, measurements, native quantum imports, or jobs belong here.
"""

import math

from app.schemas.contracts import QUBO, CircuitAngle, CircuitGate, CircuitPreview


def build_qaoa_preview(qubo: QUBO, p: int = 1) -> CircuitPreview:
    """Build |+> preparation, exp(-i gamma C), then exp(-i beta sum X), p times.

    x[i] maps to qubit i. RZ(-gamma*a_i) contributes an unwanted global phase
    +gamma*a_i/2, removed by -gamma*(constant + sum(a_i/2)). CP(-gamma*b_ij)
    supplies pair phases directly. The mixer is RX(2*beta), with no measurements.
    """
    if type(p) is not int or not 1 <= p <= 8:
        raise ValueError("p must be an integer from 1 to 8")
    try:
        offset = -math.fsum([qubo.constant, *(a / 2 for a in qubo.linear)])
    except OverflowError as exc:
        raise ValueError("global phase coefficient overflow; rescale the QUBO") from exc
    if not math.isfinite(offset):
        raise ValueError("global phase coefficient must be finite")
    gates = [CircuitGate(name="h", qubits=[i]) for i in range(qubo.num_variables)]
    phases = []
    parameters = []
    for layer in range(p):
        gamma, beta = f"gamma_{layer}", f"beta_{layer}"
        parameters.extend([gamma, beta])
        phases.append(CircuitAngle(parameter=gamma, coefficient=offset))
        for i, coefficient in enumerate(qubo.linear):
            if coefficient:
                gates.append(
                    CircuitGate(
                        name="rz",
                        qubits=[i],
                        angle=CircuitAngle(parameter=gamma, coefficient=-coefficient),
                    )
                )
        for term in qubo.quadratic:
            gates.append(
                CircuitGate(
                    name="cp",
                    qubits=[term.i, term.j],
                    angle=CircuitAngle(parameter=gamma, coefficient=-term.coefficient),
                )
            )
        gates.extend(
            CircuitGate(name="rx", qubits=[i], angle=CircuitAngle(parameter=beta, coefficient=2))
            for i in range(qubo.num_variables)
        )
    # ASAP scheduling on the declared logical gates; not transpiled/backend depth.
    ready = [0] * qubo.num_variables
    for gate in gates:
        finish = max(ready[i] for i in gate.qubits) + 1
        for i in gate.qubits:
            ready[i] = finish
    return CircuitPreview(
        num_qubits=qubo.num_variables,
        p=p,
        parameters=parameters,
        gates=gates,
        global_phase=phases,
        logical_depth=max(ready),
    )
