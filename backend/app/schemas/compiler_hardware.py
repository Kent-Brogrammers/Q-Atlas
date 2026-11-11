"""Compiler-specific physical-device contracts; existing Aer schemas stay unchanged."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.contracts import QUBO, Contract, QAOAConfig, SolverResult


class CompilerHardwareRequest(Contract):
    source: str = Field(min_length=1, max_length=20_000)
    backend_name: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    request_id: UUID
    confirmed: Literal[True]
    shots: int = Field(default=128, ge=1, le=128)
    max_execution_seconds: int = Field(default=10, ge=1, le=10)


class CompilerHardwareMeasurement(Contract):
    simulated: Literal[False] = False
    method: Literal["local_angle_training_then_qpu_sampling"] = (
        "local_angle_training_then_qpu_sampling"
    )
    best_bitstring: str
    objective: float
    optimality_gap: float
    shots: int
    counts: dict[str, int]
    quantum_seconds: float | None = None
    retrieval_ms: float


class CompilerHardwareJob(Contract):
    request_id: str
    status: str
    backend_name: str
    job_id: str | None = None
    problem_id: str
    qubo: QUBO
    local_training_config: QAOAConfig
    shots: int
    max_execution_seconds: int
    classical: SolverResult | None = None
    circuit_depth: int | None = None
    angles: list[float] | None = None
    local_training_ms: float | None = None
    submission_ms: float | None = None
    measurement: CompilerHardwareMeasurement | None = None


class CompilerHardwareDevices(Contract):
    backends: list[str]
    reserved_seconds: int
    budget_seconds: int
    message: str = "Local reservation cap, not your provider's remaining allowance."
