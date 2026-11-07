"""Wire contracts only: no objective extraction, circuit construction, or solver algorithms."""

import math
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_VARIABLES = 16
Backend = Literal["aer_simulator"]
Experiment = Literal["compiler", "optimization", "search", "materials"]
NonNegative = Annotated[float, Field(ge=0)]
Probability = Annotated[float, Field(ge=0, le=1)]
Bitstring = Annotated[str, Field(pattern=r"^[01]+$", max_length=MAX_VARIABLES)]
Seed = Annotated[int, Field(ge=0, le=2**32 - 1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class QuadraticTerm(Contract):
    i: int = Field(ge=0)
    j: int = Field(ge=0)
    coefficient: float


class QUBO(Contract):
    """Minimize C(x); linear[i] multiplies x[i], pairs require i < j."""

    num_variables: int = Field(ge=1, le=MAX_VARIABLES)
    constant: float = 0.0
    linear: list[float] = Field(max_length=MAX_VARIABLES)
    quadratic: list[QuadraticTerm] = Field(default_factory=list, max_length=4096)
    sense: Literal["minimize"] = "minimize"
    original_sense: Literal["minimize", "maximize"] = "minimize"

    @model_validator(mode="after")
    def canonicalize(self) -> Self:
        if len(self.linear) != self.num_variables:
            raise ValueError("linear must contain exactly num_variables coefficients")
        pairs: dict[tuple[int, int], float] = {}
        for term in self.quadratic:
            if not 0 <= term.i < term.j < self.num_variables:
                raise ValueError("quadratic indices must satisfy 0 <= i < j < num_variables")
            key = (term.i, term.j)
            pairs[key] = pairs.get(key, 0.0) + term.coefficient
            if not math.isfinite(pairs[key]):
                raise ValueError("combined quadratic coefficients must be finite")
        self.quadratic = [
            QuadraticTerm(i=i, j=j, coefficient=value)
            for (i, j), value in sorted(pairs.items())
            if value != 0
        ]
        return self


class RunConfig(Contract):
    backend: Backend = "aer_simulator"
    shots: int = Field(default=1024, ge=1, le=100_000)
    seed: Seed = 42
    timeout_seconds: float = Field(default=30, gt=0, le=60)


class QAOAConfig(RunConfig):
    p: int = Field(default=1, ge=1, le=8)
    optimizer: Literal["COBYLA"] = "COBYLA"
    max_iterations: int = Field(default=100, ge=1, le=1000)


class CompilerAnalyzeRequest(Contract):
    source: str = Field(min_length=1, max_length=20_000)


class CompilerBenchmarkRequest(CompilerAnalyzeRequest):
    config: QAOAConfig = Field(default_factory=QAOAConfig)


class GraphEdge(QuadraticTerm):
    """i/j are vertices; coefficient is the finite edge weight."""


class GraphInput(Contract):
    kind: Literal["graph"]
    num_vertices: int = Field(ge=2, le=MAX_VARIABLES)
    edges: list[GraphEdge] = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_edges(self) -> Self:
        seen: set[tuple[int, int]] = set()
        for edge in self.edges:
            key = (edge.i, edge.j)
            if not 0 <= edge.i < edge.j < self.num_vertices or key in seen:
                raise ValueError("edges must be unique and satisfy 0 <= i < j < num_vertices")
            seen.add(key)
        return self


class QUBOInput(Contract):
    kind: Literal["qubo"]
    qubo: QUBO


class OptimizationRequest(Contract):
    problem: Annotated[GraphInput | QUBOInput, Field(discriminator="kind")]
    config: QAOAConfig = Field(default_factory=QAOAConfig)


class SearchRequest(Contract):
    num_qubits: int = Field(ge=1, le=MAX_VARIABLES)
    marked_states: list[Bitstring] = Field(min_length=1, max_length=256)
    iterations: int | None = Field(default=None, ge=0, le=256)
    config: RunConfig = Field(default_factory=RunConfig)

    @model_validator(mode="after")
    def validate_states(self) -> Self:
        if any(len(state) != self.num_qubits for state in self.marked_states):
            raise ValueError("each marked state must have num_qubits bits")
        if len(set(self.marked_states)) != len(self.marked_states):
            raise ValueError("marked_states must be unique")
        return self


class MaterialsRequest(Contract):
    model: Literal["ising", "heisenberg"] = "ising"
    num_spins: int = Field(default=2, ge=2, le=8)
    coupling: float = 1.0
    field: float = 0.5
    boundary: Literal["open", "periodic"] = "open"
    observable: Literal["energy", "magnetization"] = "energy"
    config: RunConfig = Field(default_factory=RunConfig)


class TimingBreakdown(Contract):
    """Milliseconds; null means unmeasured. Inclusion flags are mandatory evidence."""

    includes_queue: bool
    includes_transpilation: bool
    includes_optimizer: bool
    includes_sampling: bool
    queue_ms: NonNegative | None = None
    transpilation_ms: NonNegative | None = None
    optimizer_ms: NonNegative | None = None
    sampling_ms: NonNegative | None = None


class SolverResult(Contract):
    algorithm: str = Field(min_length=1)
    elapsed_ms: NonNegative
    objective: float | None = None
    best_bitstring: Bitstring | None = None
    timing: TimingBreakdown


class BenchmarkMetrics(Contract):
    num_qubits: int | None = Field(default=None, ge=1, le=MAX_VARIABLES)
    circuit_depth: int | None = Field(default=None, ge=0)
    shots: int | None = Field(default=None, ge=1, le=100_000)


class OptimizationMetrics(BenchmarkMetrics):
    optimality_gap: NonNegative | None = None
    approximation_ratio: float | None = None
    optimizer_evaluations: int | None = Field(default=None, ge=0)


class SearchMetrics(BenchmarkMetrics):
    success_probability: Probability | None = None
    theoretical_success_probability: Probability | None = None
    quantum_oracle_queries: int | None = Field(default=None, ge=0)
    classical_expected_queries: NonNegative | None = None
    classical_worst_case_queries: int | None = Field(default=None, ge=0)


class MaterialsMetrics(BenchmarkMetrics):
    classical_observable: float | None = None
    quantum_observable: float | None = None
    absolute_error: NonNegative | None = None


class BenchmarkMetadata(Contract):
    seed: Seed | None
    repetitions: int = Field(default=1, ge=1)
    timing_scope: Literal["end_to_end", "solver_only"]
    simulated: Literal[True] = True
    simulation_method: Literal["statevector", "matrix_product_state", "density_matrix"]
    versions: dict[str, str] = Field(default_factory=dict)


class OptimizationMetadata(BenchmarkMetadata):
    qubo: QUBO
    config: QAOAConfig


class SearchMetadata(BenchmarkMetadata):
    parameters: SearchRequest
    oracle_assumptions: str = Field(min_length=1)


class MaterialsMetadata(BenchmarkMetadata):
    parameters: MaterialsRequest
    hamiltonian_convention: str = Field(min_length=1)
    energy_unit: str = Field(min_length=1)
    observable_unit: str = Field(min_length=1)


class QAOAResult(SolverResult):
    algorithm: Literal["qaoa"] = "qaoa"
    backend: Backend = "aer_simulator"
    objective: float
    best_bitstring: Bitstring
    metrics: OptimizationMetrics


class BenchmarkResult(Contract):
    """Common envelope. Owners return the experiment-specific subtype below."""

    experiment: Experiment
    problem_id: str = Field(min_length=1, max_length=128)
    backend: Backend
    status: Literal["completed"] = "completed"
    classical: SolverResult | None
    quantum: SolverResult | None
    metrics: BenchmarkMetrics
    metadata: BenchmarkMetadata


class CompilerBenchmarkResult(BenchmarkResult):
    experiment: Literal["compiler"] = "compiler"
    quantum: QAOAResult | None
    metrics: OptimizationMetrics
    metadata: OptimizationMetadata


class OptimizationResult(BenchmarkResult):
    experiment: Literal["optimization"] = "optimization"
    quantum: QAOAResult | None
    metrics: OptimizationMetrics
    metadata: OptimizationMetadata


class SearchResult(BenchmarkResult):
    experiment: Literal["search"] = "search"
    metrics: SearchMetrics
    metadata: SearchMetadata


class MaterialsResult(BenchmarkResult):
    experiment: Literal["materials"] = "materials"
    metrics: MaterialsMetrics
    metadata: MaterialsMetadata


class Diagnostic(Contract):
    code: str
    message: str
    severity: Literal["error", "warning", "info"]
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class CircuitMetadata(Contract):
    num_qubits: int = Field(ge=1, le=MAX_VARIABLES)
    depth: int | None = Field(default=None, ge=0)
    backend: Backend = "aer_simulator"


class CompilerAnalyzeResult(Contract):
    status: Literal["supported", "rejected"]
    diagnostics: list[Diagnostic]
    qubo: QUBO | None = None
    circuit: CircuitMetadata | None = None

    @model_validator(mode="after")
    def validate_analysis(self) -> Self:
        if self.status == "supported" and self.qubo is None:
            raise ValueError("supported analysis requires a normalized QUBO")
        if self.status == "rejected" and (self.qubo is not None or self.circuit is not None):
            raise ValueError("rejected analysis cannot include a QUBO or circuit")
        return self


class ErrorDetail(Contract):
    code: Literal[
        "NOT_IMPLEMENTED",
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "METHOD_NOT_ALLOWED",
        "TIMEOUT",
        "INTERNAL_ERROR",
        "HTTP_ERROR",
    ]
    message: str
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ErrorResponse(Contract):
    status: Literal["error"] = "error"
    error: ErrorDetail


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"
    service: Literal["q-atlas"] = "q-atlas"
    backend: Backend = "aer_simulator"
    experiments_ready: Literal[False] = False
