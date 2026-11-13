"""Normalized two-flavor web contract; no physical-unit conversion is implied."""

from typing import Literal

from pydantic import Field, model_validator

from app.experiments.neutrinos.model import Experiment
from app.schemas.contracts import Contract, TimingBreakdown


class NeutrinoRequest(Contract):
    experiment: Experiment
    axis: Literal["distance", "potential"] = "distance"
    samples: int = Field(default=21, ge=2, le=41)
    max_potential: float = Field(default=2, ge=0, le=10)
    timeout_seconds: float = Field(default=30, ge=0.01, le=60)

    @model_validator(mode="after")
    def bounded_work(self):
        if self.samples * self.experiment.shots > 500_000:
            raise ValueError("samples * shots must not exceed 500000")
        if len(self.experiment.layers) > 16:
            raise ValueError("web runs support at most 16 layers")
        if sum(layer.distance for layer in self.experiment.layers) > 100:
            raise ValueError("total propagation distance must not exceed 100")
        if self.axis == "potential" and len(self.experiment.layers) != 1:
            raise ValueError("density sweeps require a single constant-density layer")
        return self


class NeutrinoProbabilities(Contract):
    electron: float
    other: float


class NeutrinoAnalytical(NeutrinoProbabilities):
    mixing_strength: float | None
    theta_m: float | None
    frequency: float


class NeutrinoErrors(Contract):
    ideal_vs_numerical: NeutrinoProbabilities
    sampling: NeutrinoProbabilities
    total: NeutrinoProbabilities
    analytical_vs_numerical: NeutrinoProbabilities | None


class NeutrinoSubdivision(Contract):
    subdivisions_per_layer: int
    state_change_l2: float
    scope: str


class NeutrinoNumerics(Contract):
    reference_norm: float
    ideal_norm: float
    state_error_l2: float
    subdivision_check: NeutrinoSubdivision
    approximation: str


class NeutrinoTimings(Contract):
    classical: float
    convergence_check: float
    circuit_end_to_end: float
    ideal_execution: float


class NeutrinoRotation(Contract):
    gate: Literal["ry", "rz"]
    angle: float


class NeutrinoRecord(Contract):
    experiment: Literal["q_neutrino"]
    status: Literal["completed"]
    backend: Literal["aer_simulator"]
    simulated: Literal[True]
    configuration: Experiment
    analytical: NeutrinoAnalytical | None
    numerical: NeutrinoProbabilities
    ideal: NeutrinoProbabilities
    measured: NeutrinoProbabilities
    absolute_errors: NeutrinoErrors
    numerics: NeutrinoNumerics
    num_qubits: Literal[1]
    circuit_depth: int
    shots: int
    counts: dict[str, int]
    circuit_diagram: str | None = None
    rotations: list[NeutrinoRotation] = Field(default_factory=list)
    statevector: tuple[tuple[float, float], tuple[float, float]] | None = None
    basis_gates: list[str]
    timing_ms: NeutrinoTimings
    quantum_timing: TimingBreakdown
    versions: dict[str, str]


class NeutrinoResponse(Contract):
    model: Literal["effective_two_flavor"] = "effective_two_flavor"
    units: Literal["normalized"] = "normalized"
    axis: Literal["distance", "potential"]
    resonance_potential: float | None = None
    coordinates: list[float]
    results: list[NeutrinoRecord]
