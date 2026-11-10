"""Reusable local Aer statevector scoring for the shared QAOA circuit."""

from collections.abc import Sequence
from math import isfinite

import numpy as np
from qiskit.circuit.exceptions import CircuitError
from qiskit_aer import AerSimulator
from qiskit_aer.library import SaveStatevector

from app.quantum.qaoa_circuit import build_qaoa_circuit
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO


class QAOAExpectation:
    """Prepare once, then evaluate mean QUBO cost at gamma/beta angle vectors.

    The public parameter order is gamma_0, beta_0, gamma_1, beta_1, ... .
    Scores use all noiseless statevector probabilities and include the constant.
    This synchronous internal primitive performs local CPU simulation. The future
    run_qaoa boundary owns the overall execution deadline and measurement results.
    """

    def __init__(self, qubo: QUBO, p: int = 1) -> None:
        self._circuit, self._parameters = build_qaoa_circuit(qubo, p=p)
        width = qubo.num_variables
        # Aer basis indices have qubit 0 on the right, while the API puts x[0] first.
        self._costs = np.fromiter(
            (evaluate_qubo(qubo, format(index, f"0{width}b")[::-1]) for index in range(1 << width)),
            dtype=float,
            count=1 << width,
        )
        self._circuit.append(SaveStatevector(width), range(width))
        self._simulator = AerSimulator(
            method="statevector",
            device="CPU",
            precision="double",
            max_parallel_threads=1,
            max_parallel_experiments=1,
            zero_threshold=0.0,
        )

    @property
    def num_parameters(self) -> int:
        """Number of declared angles, including those in zero-cost layers."""
        return len(self._parameters)

    def __call__(self, angles: Sequence[float]) -> float:
        """Return sum(P(x) * C(x)) for one complete finite angle vector."""
        try:
            values = np.asarray(angles)
            if np.iscomplexobj(values):
                raise ValueError("angles must be real")
            values = np.asarray(values, dtype=float)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                "angles must be a one-dimensional vector of finite real numbers"
            ) from error
        if values.shape != (self.num_parameters,) or not np.isfinite(values).all():
            raise ValueError(f"angles must contain exactly {self.num_parameters} finite numbers")
        try:
            circuit = self._circuit.assign_parameters(
                dict(zip(self._parameters, values, strict=True)), strict=False
            )
        except (CircuitError, ArithmeticError, ValueError) as error:
            raise ValueError("angles cannot be bound to finite circuit rotations") from error
        if not isfinite(float(circuit.global_phase)) or any(
            not isfinite(float(angle)) for gate in circuit.data for angle in gate.operation.params
        ):
            raise ValueError("angles produce non-finite circuit rotations")

        result = self._simulator.run(circuit, shots=1).result()
        if not result.success:
            raise RuntimeError("Aer statevector evaluation failed")
        state = np.asarray(result.get_statevector(0), dtype=complex)
        if state.shape != self._costs.shape or not np.isfinite(state).all():
            raise RuntimeError("Aer returned an invalid statevector")
        probabilities = np.abs(state) ** 2
        if not np.isclose(probabilities.sum(), 1, rtol=0, atol=1e-10):
            raise RuntimeError("Aer returned an unnormalized statevector")
        expectation = float(np.dot(probabilities, self._costs))
        if not isfinite(expectation):
            raise ValueError("expectation overflow; rescale the QUBO")
        return expectation
