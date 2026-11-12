"""Additive physical-QPU contracts. Existing simulator contracts retain their meaning."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.contracts import (
    CompilerBenchmarkRequest,
    Contract,
    MaterialsRequest,
    OptimizationRequest,
    SearchRequest,
)
from app.schemas.neutrinos import NeutrinoRequest


class CompilerTask(Contract):
    kind: Literal["compiler"]
    parameters: CompilerBenchmarkRequest


class OptimizationTask(Contract):
    kind: Literal["optimization"]
    parameters: OptimizationRequest


class SearchTask(Contract):
    kind: Literal["search"]
    parameters: SearchRequest


class MaterialsTask(Contract):
    kind: Literal["materials"]
    parameters: MaterialsRequest


class NeutrinosTask(Contract):
    kind: Literal["neutrinos"]
    parameters: NeutrinoRequest


SingleHardwareTask = Annotated[
    CompilerTask | OptimizationTask | SearchTask | MaterialsTask | NeutrinosTask,
    Field(discriminator="kind"),
]


class SuiteTask(Contract):
    kind: Literal["suite"]
    parameters: list[SingleHardwareTask] = Field(min_length=1, max_length=5)


HardwareTask = Annotated[
    CompilerTask | OptimizationTask | SearchTask | MaterialsTask | NeutrinosTask | SuiteTask,
    Field(discriminator="kind"),
]


class HardwareRequest(Contract):
    task: HardwareTask
    request_id: UUID
    confirmed: Literal[True]
    backend_name: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    shots: int = Field(default=128, ge=1, le=128)
    max_execution_seconds: int = Field(default=10, ge=1, le=10)


class HardwareMetric(Contract):
    name: str
    coordinate: float | None = None
    classical: float
    quantum: float
    absolute_error: float
    unit: str


class HardwareTimings(Contract):
    classical_ms: float | None = None
    local_training_ms: float | None = None
    preparation_ms: float | None = None
    transpilation_ms: float | None = None
    submission_ms: float | None = None
    retrieval_ms: float | None = None
    observed_wall_ms: float | None = None
    quantum_seconds: float | None = None
    provider_queue_ms: float | None = None
    provider_execution_ms: float | None = None


class HardwareJob(Contract):
    request_id: str
    task: HardwareTask
    problem_id: str
    created_at_utc: str
    updated_at_utc: str
    status: str
    backend_name: str | None = None
    job_id: str | None = None
    simulated: Literal[False] = False
    shots: int
    max_execution_seconds: int
    circuit_depths: list[int] = Field(default_factory=list)
    num_qubits: int | None = None
    counts: list[dict[str, int]] = Field(default_factory=list)
    classical_reference: dict = Field(default_factory=dict)
    metrics: list[HardwareMetric] = Field(default_factory=list)
    timings: HardwareTimings = Field(default_factory=HardwareTimings)
    shared_job_timings: HardwareTimings | None = None
    children: list["HardwareJob"] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)
    message: str = ""
    measurement_complete: bool = False
    timing_note: str = (
        "Classical and hardware timers describe different intervals. "
        "Provider usage is not end-to-end runtime. Observed wall time includes polling delay. "
        "Queue and execution use provider timestamps where available. No speedup is inferred."
    )
