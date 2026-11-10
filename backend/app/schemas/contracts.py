"""Wire contracts only: no objective extraction, circuit construction, or solver algorithms."""

import math
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class MaterialsRunConfig(RunConfig):
    """Materials alone permits null for a nondeterministic simulator seed."""

    seed: Seed | None = 42


class QAOAConfig(RunConfig):
    p: int = Field(default=1, ge=1, le=8)
    optimizer: Literal["COBYLA"] = "COBYLA"
    max_iterations: int = Field(default=100, ge=1, le=1000)


class CompilerAnalyzeRequest(Contract):
    source: str = Field(min_length=1, max_length=20_000)


class CompilerBenchmarkRequest(CompilerAnalyzeRequest):
    config: QAOAConfig = Field(default_factory=QAOAConfig)


class CompilerGenerateRequest(CompilerAnalyzeRequest):
    p: int = Field(default=1, ge=1, le=8)


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
    config: MaterialsRunConfig = Field(default_factory=MaterialsRunConfig)
    evolution_time: float = Field(default=1.0, ge=0, le=10)
    trotter_steps: int = Field(default=20, ge=1, le=256)
    time_samples: int = Field(default=1, ge=1, le=21)

    @field_validator("config", mode="before")
    @classmethod
    def accept_shared_config(cls, value: object) -> object:
        # Preserve Python callers passing the original shared config, as well as JSON callers.
        return value.model_dump() if isinstance(value, RunConfig) else value


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
    successful_shots: int | None = Field(
        default=None,
        ge=0,
        le=100_000,
        strict=True,
        description="Number of sampled outcomes in the marked set; not postselected shots.",
    )
    classical_observed_queries: int | None = Field(
        default=None,
        ge=1,
        strict=True,
        description="Actual predicate checks until the first classical match for this instance.",
    )
    quantum_total_oracle_queries: int | None = Field(
        default=None,
        ge=0,
        strict=True,
        description="Combined-oracle applications across all shots: iterations times shots.",
    )

    @model_validator(mode="after")
    def validate_search_evidence(self) -> Self:
        if self.successful_shots is not None:
            if self.shots is None or self.successful_shots > self.shots:
                raise ValueError("successful_shots requires shots and must not exceed it")
            if self.success_probability is not None and not math.isclose(
                self.success_probability,
                self.successful_shots / self.shots,
                rel_tol=0,
                abs_tol=1e-12,
            ):
                raise ValueError("success_probability must equal successful_shots / shots")
        if self.quantum_total_oracle_queries is not None:
            if self.shots is None or self.quantum_oracle_queries is None:
                raise ValueError("total oracle queries require shots and per-shot oracle queries")
            if self.quantum_total_oracle_queries != self.quantum_oracle_queries * self.shots:
                raise ValueError("total oracle queries must equal per-shot queries times shots")
        if self.classical_observed_queries is not None:
            if (
                self.num_qubits is not None
                and self.classical_observed_queries > 1 << self.num_qubits
            ):
                raise ValueError("observed classical queries must not exceed the search space")
            if (
                self.classical_worst_case_queries is not None
                and self.classical_observed_queries > self.classical_worst_case_queries
            ):
                raise ValueError("observed classical queries must not exceed the worst case")
        return self


class MaterialsObservables(Contract):
    """Dimensionless quantities; arrays are in increasing spin/bond order."""

    per_spin_z: list[float] = Field(min_length=2, max_length=4)
    per_spin_x: list[float] = Field(min_length=2, max_length=4)
    magnetization_z: float
    zz_correlations: list[float] = Field(min_length=1, max_length=3)
    energy: float
    state_norm: NonNegative | None = None


class MaterialsObservableErrors(Contract):
    magnetization_z: NonNegative
    zz_correlations: list[NonNegative] = Field(min_length=1, max_length=3)
    energy: NonNegative


class MaterialsTimePoint(Contract):
    time: NonNegative
    exact: MaterialsObservables
    ideal: MaterialsObservables
    measured: MaterialsObservables
    trotter_error: MaterialsObservableErrors
    sampling_error: MaterialsObservableErrors
    total_error: MaterialsObservableErrors
    state_fidelity: Probability
    circuit_depth: int = Field(ge=0)
    shots_per_basis: int = Field(ge=1, le=100_000)


class MaterialsMetrics(BenchmarkMetrics):
    classical_observable: float | None = None
    quantum_observable: float | None = None
    absolute_error: NonNegative | None = None
    ideal_observable: float | None = None
    trotter_absolute_error: NonNegative | None = None
    sampling_absolute_error: NonNegative | None = None
    total_shots: int | None = Field(default=None, ge=1)
    time_series: list[MaterialsTimePoint] = Field(default_factory=list, max_length=21)


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
    initial_state: Bitstring | None = None
    trotter_order: Literal[2] = 2
    execution_methods: list[Literal["scipy_expm", "aer_statevector", "aer_shots"]] = Field(
        default_factory=list
    )
    measurement_bases: list[Literal["Z", "X"]] = Field(default_factory=list)
    transpilation_basis: list[str] = Field(default_factory=list)
    circuit_depth_scope: str | None = None
    ideal_elapsed_ms: NonNegative | None = None
    sampling_seed_policy: str | None = None


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


class CircuitAngle(Contract):
    """Angle in radians: coefficient * the named variational parameter."""

    parameter: str = Field(pattern=r"^(gamma|beta)_[0-7]$")
    coefficient: float


class CircuitGate(Contract):
    name: Literal["h", "rz", "cp", "rx"]
    qubits: list[Annotated[int, Field(ge=0, lt=MAX_VARIABLES)]] = Field(min_length=1, max_length=2)
    angle: CircuitAngle | None = None

    @model_validator(mode="after")
    def validate_gate(self) -> Self:
        arity = 2 if self.name == "cp" else 1
        if len(self.qubits) != arity or len(set(self.qubits)) != arity:
            raise ValueError("gate must have the correct number of distinct qubits")
        if (self.name == "h") != (self.angle is None):
            raise ValueError("only h has no angle; rotation gates require an angle")
        return self


class CircuitPreview(CircuitMetadata):
    """Symbolic, untranspiled QAOA plan. No sampling or execution evidence."""

    kind: Literal["qaoa_logical_preview"] = "qaoa_logical_preview"
    executed: Literal[False] = False
    depth: None = None  # Transpiled depth is unavailable for a symbolic preview.
    p: int = Field(ge=1, le=8)
    parameters: list[str] = Field(min_length=2, max_length=16)
    gates: list[CircuitGate] = Field(min_length=1, max_length=2048)
    global_phase: list[CircuitAngle] = Field(min_length=1, max_length=8)
    logical_depth: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        expected = [name for layer in range(self.p) for name in (f"gamma_{layer}", f"beta_{layer}")]
        if self.parameters != expected:
            raise ValueError("parameters must be ordered gamma_0, beta_0, ... for p layers")
        angles = self.global_phase + [gate.angle for gate in self.gates if gate.angle is not None]
        if any(angle.parameter not in expected for angle in angles):
            raise ValueError("angle references an undeclared parameter")
        if any(qubit >= self.num_qubits for gate in self.gates for qubit in gate.qubits):
            raise ValueError("gate references a qubit outside the circuit width")
        return self


class CompilerAnalyzeResult(Contract):
    status: Literal["supported", "rejected"]
    diagnostics: list[Diagnostic]
    qubo: QUBO | None = None
    circuit: CircuitPreview | None = None

    @model_validator(mode="after")
    def validate_analysis(self) -> Self:
        if self.status == "supported" and self.qubo is None:
            raise ValueError("supported analysis requires a normalized QUBO")
        if self.status == "rejected" and (self.qubo is not None or self.circuit is not None):
            raise ValueError("rejected analysis cannot include a QUBO or circuit")
        return self


class GeneratedPythonArtifact(Contract):
    filename: Literal["q_atlas_generated.py"] = "q_atlas_generated.py"
    source: str = Field(min_length=1, max_length=150_000)
    entrypoint: str = Field(min_length=1)
    replaced_function: str | None = None
    executed: Literal[False] = False


class CompilerGenerateResult(CompilerAnalyzeResult):
    artifact: GeneratedPythonArtifact | None = None

    @model_validator(mode="after")
    def validate_artifact(self) -> Self:
        if (self.status == "supported") != (self.artifact is not None):
            raise ValueError("only supported generation requires an artifact")
        return self


class CompilerCommunicationPlan(Contract):
    """Reserved provider timing fields in ms; preparation emits null, never measurements.

    Submission is request-to-job-acknowledgement, retrieval is ready-result download
    and decoding. Round trip includes remote wait/processing and client overhead;
    it is not an extra duration to add to those overlapping components.
    """

    submission_ms: NonNegative | None = None
    result_retrieval_ms: NonNegative | None = None
    queue_ms: NonNegative | None = None
    remote_processing_ms: NonNegative | None = None
    round_trip_ms: NonNegative | None = None


class CompilerBenchmarkPlan(Contract):
    """A reproducible future comparison, with no execution or measured results."""

    status: Literal["planned"] = "planned"
    comparison_scope: Literal["objective_optimization"] = "objective_optimization"
    script_execution_enabled: Literal[False] = False
    quantum_execution_enabled: Literal[False] = False
    problem_id: str = Field(min_length=1, max_length=128)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entrypoint: str = Field(min_length=1)
    qubo: QUBO
    config: QAOAConfig
    circuit: CircuitPreview
    communication_timing: CompilerCommunicationPlan = Field(
        default_factory=CompilerCommunicationPlan
    )
    classical_runner: Literal["app.experiments.optimization.solvers.run_classical"] = (
        "app.experiments.optimization.solvers.run_classical"
    )
    quantum_runner: Literal["app.quantum.qaoa.run_qaoa"] = "app.quantum.qaoa.run_qaoa"
    blockers: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.circuit.p != self.config.p or self.circuit.num_qubits != self.qubo.num_variables:
            raise ValueError("planned circuit must match the QUBO width and configuration")
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
