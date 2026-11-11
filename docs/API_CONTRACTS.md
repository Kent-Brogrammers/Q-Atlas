# Shared API contracts (foundation v0.1.0)

Source of truth: original `Project_Spec.md` plus executable models in
`backend/app/schemas/contracts.py`. FastAPI serves `/openapi.json` and `/docs`.
`frontend/src/types/api.generated.ts` is generated from that same runtime schema;
`npm run types:generate` regenerates it and `npm run types:check` detects drift.
Never edit generated types by hand. Version/interface changes require the frontend
owner and affected experiment owners to coordinate.

All objects reject unknown fields; numeric values must be finite. In the tables,
**required** means the caller must provide the key, **default** means it can be omitted,
and **nullable** means explicit JSON `null` is accepted. Responses serialize defaults/nulls.
OpenAPI precisely records required keys, enums, defaults, and numeric bounds.

## Endpoints

| Method/path | Request model | Future HTTP 200 model | Owner |
| --- | --- | --- | --- |
| GET `/api/health` | none | `HealthResponse` | Developer 5/integration |
| POST `/api/compiler/analyze` | `CompilerAnalyzeRequest` | `CompilerAnalyzeResult` | Developer 2 |
| POST `/api/compiler/generate` | `CompilerGenerateRequest` | `CompilerGenerateResult` | Developer 2, frontend integration authorized |
| POST `/api/compiler/benchmark/plan` | `CompilerBenchmarkRequest` | `CompilerBenchmarkPlan` | Developer 2, no execution |
| POST `/api/compiler/benchmark` | `CompilerBenchmarkRequest` | `CompilerBenchmarkResult` | Developer 2, consuming Developer 3 runners |
| POST `/api/optimization/run` | `OptimizationRequest` | `OptimizationResult` | Developer 3 |
| POST `/api/search/run` | `SearchRequest` | `SearchResult` | Developer 4 |
| POST `/api/materials/run` | `MaterialsRequest` | `MaterialsResult` | Developer 1 |
| POST `/api/neutrinos/run` | `NeutrinoRequest` | `NeutrinoResponse` | Neutrino experiment + Developer 5 integration |

### Neutrino Lab integration

Executable web models are in `backend/app/schemas/neutrinos.py`, reusing the
experiment's validated inputs and shared validation/timing primitives. All neutrino
inputs are **normalized**, except `theta` in radians; no GeV/km conversion is exposed.

Request example (settings only, not experimental evidence):

```json
{
  "experiment": {
    "parameters": {"theta": 0.2, "delta_m2": 1, "energy": 1, "particle": "neutrino"},
    "layers": [{"distance": 4, "potential": 0}],
    "shots": 4096,
    "seed": 42
  },
  "axis": "distance",
  "samples": 21,
  "max_potential": 2,
  "timeout_seconds": 30
}
```

`axis=distance` samples from zero to the total baseline, traversing each layer in
listed order and truncating the last traversed layer at the requested distance.
It does not rescale the entire profile. `axis=potential` requires one layer and
sweeps potential from zero to `max_potential` at fixed distance. Zero extent returns
one point. Samples default to 21 (range 2–41); potential is bounded to [0,10].
Web runs permit at most 16 layers, total distance at most 100, and
`samples * shots <= 500000`. Local CLI limits remain unchanged. The disposable
worker enforces a wall-clock budget including startup (default 30s, range 0.01–60s).

The response declares model `effective_two_flavor`, units `normalized`, the axis,
aligned `coordinates`, and full measured `results` at each coordinate. Each record
contains both flavors, analytical results where applicable, independent SciPy,
ideal Aer, finite-shot measurements, counts, errors, numerical stability, depth,
timing scopes, actual point seed, and versions. Seeds increment modulo `2**32`.
No probability is encoded as an optimization objective. API startup imports no
quantum packages. Missing simulation dependencies return 503; timeout returns 504;
invalid inputs return 422 through the shared error envelope. Failed workers are
reaped and unexpected failures use the sanitized shared 500 handler.

The live Svelte page uses generated types and this endpoint; earlier
`frontend/src/lib/neutrinos/proposal.ts` remains a historical discussion draft,
not the live wire format. See `docs/NEUTRINOS.md` for physical conventions.

Health returns `{"status":"ok","service":"q-atlas","backend":"aer_simulator","experiments_ready":false}`.
This signals API readiness, not readiness of all experiments. Compiler analysis,
generation, and nonexecuting comparison plans are available. Compiler benchmarking
revalidates source and returns 422 for rejected source or 501 while shared runners
are unavailable. Materials and search return real simulation results with HTTP 200;
optimization still validates first and returns HTTP 501:

```json
{"status":"error","error":{"code":"NOT_IMPLEMENTED","message":"Optimization benchmark is not implemented. Developer 3 owns this feature.","diagnostics":[]}}
```

Invalid payloads return **422** with the same envelope and `VALIDATION_ERROR`.
Routing/method errors return `NOT_FOUND`/`METHOD_NOT_ALLOWED` (404/405); unexpected
exceptions return sanitized INTERNAL_ERROR (500). Compiler runner TimeoutError
and materials/search worker timeouts map to TIMEOUT (504). Materials/search use HTTP_ERROR (503)
when optional quantum dependencies are missing; HTTP_ERROR covers other HTTP failures.
Errors expose no stack traces or submitted field values. Each diagnostic has required
`code`, `message`, `severity` (`error|warning|info`), and optional nullable one-based
`line` and `column`. Validation diagnostic messages identify a field path.

## Canonical QUBO

```json
{
  "num_variables": 3,
  "constant": 0.0,
  "linear": [10.0, 20.0, 0.0],
  "quadratic": [{"i": 0, "j": 1, "coefficient": 15.0}],
  "sense": "minimize",
  "original_sense": "minimize"
}
```

`C(x) = constant + Σ linear[i] x[i] + Σ coefficient x[i] x[j]`, with binary `x[i]`.
This is a contract example, not measured evidence.

| Field | Meaning and presence |
| --- | --- |
| `num_variables` | Required integer, 1–16; exact width of assignments |
| `constant` | Default 0; objective offset, included in every reported objective |
| `linear` | Required finite coefficient array of exactly `num_variables` elements |
| `quadratic` | Default empty; up to 4096 submitted pair terms; each has required integer `i`, `j` and finite `coefficient` |
| `sense` | Default/only value `minimize`; maximization is never a solver convention |
| `original_sense` | Default `minimize`; `maximize` records that the upstream producer negated the **entire** original objective, including the constant |

Pair indices must satisfy `0 <= i < j < num_variables`. The shared model combines
duplicate pairs, drops zero combined terms, sorts pairs by `(i,j)`, and rejects overflow
or nonfinite sums. Reversed pairs and diagonal terms are rejected. Producers must fold
binary `x[i]**2` into linear terms before calling the schema; no extraction algorithm
is supplied. Objective coefficients have the problem's own units, not milliseconds.
When `original_sense=maximize`, the UI negates a canonical result for original-value display.

**Bit order:** API strings are `x[0]x[1]...x[n-1]`, left to right, with leading zeros
preserved. `"100"` means `x[0]=1, x[1]=0, x[2]=0`; `x[i]` maps to qubit `i`.
Qiskit count strings conventionally put the highest classical bit first; owners must
convert at the adapter boundary when measuring qubit `i` into classical bit `i`.
Never use an integer conversion that discards leading zeros or silently reverse API inputs.

## Requests and limits

- `CompilerAnalyzeRequest`: required `source`, 1–20,000 characters. The decorator marker
  remains text. Analysis never imports, evaluates, or executes it.
  The marked function may contain a leading docstring, up to 64 source assignments
  (including numeric `+=`, `-=`, `*=`), fixed literal-range loops, and one final return.
  Loop ranges must be nonempty with 1–64 iterations, bounds/step within ±64, no shadowed
  range/index variables, no else, and nesting at most two levels. Expansion is limited
  to 256 assignments and 8,192 AST nodes. Sequential local reassignment is supported; undefined local
  reads produce `UNDEFINED_NAME` and invalid targets produce `INVALID_ASSIGNMENT`.
  The source subset remains limited to 1–6 bits and binary quadratics. Indices are
  literals or substituted loop indices with bounded integer +/- offsets. Invalid
  loop forms produce `INVALID_LOOP`; all source is still parsed/interpreted without execution.
  Squared allowlisted expressions with literal exponent 2 are supported, including
  named/loop-built linear penalties. Expansion involving more than two distinct bits
  in a monomial is rejected as `HIGHER_ORDER`; overflow is rejected as
  `NONFINITE_COEFFICIENT`. There is no automatic penalty-weight selection or constraint schema.
- `CompilerBenchmarkRequest`: same `source`, plus default `config: QAOAConfig`.
  Benchmarking revalidates supported complete files through static generation,
  including marker checks, and passes only the verified QUBO/config to shared runners.
  No trusted client-extracted objective or Python script execution is involved.
  The planning endpoint reuses this request without calling either runner.
- `CompilerGenerateRequest`: required `source` with the same character/AST bounds,
  plus `p` (default 1, range 1–8). Accepts a complete script containing one top-level
  marked objective and an optional `@qatlas.circuit` zero-argument factory. Surrounding
  Python is preserved as opaque text; only the objective is interpreted and verified.
  Analyze remains objective-only; Generate and the benchmark adapter accept supported
  full-file wrappers. Local numeric list/tuple literals of 1–64 finite signed elements
  can supply objective weights. Element access is literal or a bounded unrolled-loop
  index; whole-vector arithmetic, aliasing, slicing, mutation, and dynamic input are rejected.
- `OptimizationRequest`: required discriminated `problem`, plus default QAOA config.
  `{"kind":"qubo","qubo":...}` uses the canonical QUBO. A graph uses
  `{"kind":"graph","num_vertices":3,"edges":[{"i":0,"j":1,"coefficient":1}]}`.
  Graphs have 2–16 vertices, 1–120 unique undirected edges, `i<j`, finite weights,
  no self-loops. `coefficient` is the edge weight, not yet a QUBO coefficient.
  Developer 3 implements and documents the Max-Cut conversion.
- `SearchRequest`: required `num_qubits` (1–16), required `marked_states` (1–256 unique
  binary strings, each exactly that width), optional nullable `iterations` (0–256;
  default null selects the best integer beside Grover's first theoretical peak), and default run config.
  The implemented search runner supports 1–6 qubits, 0–32 iterations, and at most
  10000 shots; broader schema-valid sizes receive structured 422 diagnostics before
  simulation. Single and multiple marked states are supported. See [search guide](SEARCH.md)
  for query semantics, effective parameters, timing scopes, and reproducible examples.
- `MaterialsRequest`: defaults `model=ising` (`ising|heisenberg`), `num_spins=2` (2–8),
  `coupling=1`, `field=0.5`, `boundary=open` (`open|periodic`), `observable=energy`
  (`energy|magnetization`), and materials run config. These original fields remain intact.
  The implemented route supports **Ising, open boundaries, 2–4 spins, and coupling/field
  in [-10,10]**; other scaffold options receive explicit HTTP 422 diagnostics.
  New optional fields default to `evolution_time=1` (0–10 dimensionless time),
  `trotter_steps=20` (1–256), and `time_samples=1` (1–21). A single sample evaluates
  the terminal time; a sweep includes both zero and the terminal time, which must be
  positive for sweeps. Work limits: `time_samples*trotter_steps <= 2048` and
  `2*time_samples*config.shots <= 1,000,000`.
  `MaterialsRunConfig` preserves shared defaults but additionally accepts `seed=null`.
  Coupling, field, energy, and evolution time use dimensionless units with hbar=1.

`RunConfig` defaults: `backend=aer_simulator` (only allowed backend), `shots=1024`
(1–100,000), `seed=42` (unsigned 32-bit integer), `timeout_seconds=30` (>0, ≤60 seconds).
`QAOAConfig` adds `p=1` (1–8 layers), `optimizer=COBYLA` (only initial optimizer),
`max_iterations=100` (1–1000). Counts and seeds are unitless; timeouts are **seconds**.

These are validated interface limits. The shared QAOA runner performs local Aer work
inside a spawned worker with a whole-run deadline. Compiler HTTP execution defaults
off unless `QATLAS_ENABLE_COMPILER_AER=1` is set on the backend; disabled comparisons
return the existing HTTP 501 error envelope. Analysis, generation and plans remain
nonexecuting. Materials uses a spawned worker terminated/reaped on timeout,
including native work; startup counts against its deadline, outside numerical timers.
Future runners must enforce deadlines throughout native calls. The compiler enforces
source/node/depth limits and verifies all assignments for 1–6 bits; see [the compiler guide](COMPILER.md).
There is no asynchronous job API, request-body transport limiter, or hardware execution.

## Analysis response

Source function names and binary-input names are arbitrary. The marker may be bare
`@qatlas.objective` or an optional call with `num_bits`/`sense`. Named scalar
parameters map to canonical bits in declaration order; a single vector can use any
name and static indices. Without num_bits, width is the scalar count or highest
statically used vector index plus one. Existing 1–6-bit/source limits still apply.
`INPUT_MAPPING` is an informational diagnostic; no QUBO, bit-order, timing, or runner
contract changed. Explicit num_bits retains trailing unused vector positions.

`CompilerAnalyzeResult` requires `status` (`supported|rejected`) and `diagnostics`.
`qubo` and `circuit` default null. `supported` requires a normalized QUBO; `rejected`
cannot include a QUBO or circuit. Supported analyses include a `CircuitPreview` for
one QAOA layer. It retains `num_qubits` and backend `aer_simulator` (the intended
execution target), and adds:

- `kind=qaoa_logical_preview`, `executed=false`, `p=1` for analysis responses.
- `parameters` in explicit `gamma_0, beta_0, ...` order.
- `gates`: ordered `h|rz|cp|rx` operations with qubit indices. Angles are either null
  for H, or `{parameter, coefficient}` meaning radians = coefficient × parameter.
- `global_phase`: parameter-scaled phase terms, including constant objective offsets.
- `logical_depth`: parallel layers of the symbolic gates before any transpilation.

`depth` remains null: logical depth is not measured backend/transpiled depth. The
preview contains no measurements, samples, optimization results, or execution timing.
Rejected analysis still returns `circuit=null`. See
[the Developer 3 handoff](DEVELOPER_3_HANDOFF.md) for gate/sign conventions and shared helpers.

## Generated Python response

`CompilerGenerateResult` extends the analysis fields with nullable `artifact`.
Supported generation requires the artifact; rejected generation requires null
artifact/QUBO/circuit. The returned preview uses the requested p rather than Analyze's
fixed one layer. Nothing executes on this endpoint.

`GeneratedPythonArtifact` contains complete rewritten `source` (1–150,000 characters),
default filename `q_atlas_generated.py`, nonempty `entrypoint`, nullable
`replaced_function`, and `executed=false`. The browser derives a download name from
the uploaded filename. No backend path is accepted and no file is stored server-side.
The objective marker is removed; an explicitly marked circuit factory is replaced,
or a fresh builder is appended if none is marked. Surrounding Python is opaque
passthrough content, not an approved executable program. See
[script-generation semantics](COMPILER_SCRIPT_GENERATION.md) for accepted markers and limits.

## Nonexecuting compiler comparison plan

`POST /api/compiler/benchmark/plan` returns `CompilerBenchmarkPlan` after full-file
static generation. Unsupported source/config returns structured HTTP 422 before
any runner call. The response includes `status=planned`,
`comparison_scope=objective_optimization`, literal false `script_execution_enabled`
and `quantum_execution_enabled`, stable canonical `problem_id`, source/generated
SHA-256 hashes, builder `entrypoint`, QUBO, effective QAOA config, matching unexecuted
preview, shared runner names, and remaining blockers. There are no measurement fields.
The preview width and p must match the QUBO/config. No request flag enables execution.
Nothing is persisted or run. See [benchmark planning](COMPILER_BENCHMARK_PLAN.md).

## Shared benchmark results

All four result subtypes use the same envelope:

| Field | Meaning and presence |
| --- | --- |
| `experiment` | Fixed by subtype: `compiler`, `optimization`, `search`, or `materials` |
| `problem_id` | Required 1–128-character stable instance identifier, generated by the owner |
| `backend` | Required `aer_simulator`; simulator results must be labeled accordingly |
| `status` | Default/only `completed`; failures use `ErrorResponse`, never invented measurements |
| `classical`, `quantum` | Required keys; nullable `SolverResult` for unavailable/not-applicable paths |
| `metrics` | Required experiment-specific metrics object; its fields are optional and nullable |
| `metadata` | Required experiment-specific provenance object |

`SolverResult` requires a nonempty `algorithm`, nonnegative `elapsed_ms`, and `timing`.
Optional nullable `objective` is the canonical problem value; `best_bitstring` follows
the API order above. `timing` requires four boolean flags: `includes_queue`,
`includes_transpilation`, `includes_optimizer`, `includes_sampling`. Its nullable optional
`queue_ms`, `transpilation_ms`, `optimizer_ms`, `sampling_ms` are measured durations in
milliseconds. A null duration means unmeasured, not zero. Flags describe inclusion in
`elapsed_ms`; unavailable components must not be invented. Nested timers can overlap;
do not add them blindly.

Optimization/compiler `quantum` uses `QAOAResult`, a `SolverResult` subtype that additionally
requires a finite `objective`, `best_bitstring`, and `OptimizationMetrics`; `algorithm`
defaults to/only permits `qaoa`, and backend defaults to `aer_simulator`. The quantum
result's metrics describe its run; the envelope metrics add comparison quantities.

Common optional nullable metrics: `num_qubits`, `circuit_depth` (parallel gate layers
after transpilation; record the gate basis/backend), `shots` (sample count). Experiment additions:

- Optimization/compiler: `optimality_gap` (nonnegative canonical objective difference from
  the exact optimum), `approximation_ratio` (unitless; nullable when mathematically
  inappropriate, with the producer's formula documented), `optimizer_evaluations` (count).
- Search: `success_probability`, `theoretical_success_probability` (0–1),
  `quantum_oracle_queries` (count), `classical_expected_queries` (nonnegative expectation),
  `classical_worst_case_queries` (count). These are query counts, never milliseconds.
  Optional nullable `circuit_gate_counts` maps gate names to positive integer counts
  in one Aer-transpiled search circuit. It excludes measurement, reset, barriers and
  other non-gate instructions. Composite gates retained by transpilation count once;
  this is not a native-hardware decomposition or a count of internal Aer operations.
  The sum is the per-circuit gate total, never multiplied by shots. Null/omitted means
  unavailable; an empty map means a measured circuit with zero gates.
  Optional nullable evidence fields: `successful_shots` (marked outcomes among all
  shots), `classical_observed_queries` (actual fixed-instance predicate checks), and
  `quantum_total_oracle_queries` (combined-oracle calls across the sampling batch,
  equal to per-shot queries times shots). New evidence counts must be integers;
  successful shots cannot exceed shots and must agree with the reported probability.
  Observed classical queries cannot exceed a supplied space/worst-case bound. Totals
  require the corresponding shot/per-shot fields. Missing fields preserve legacy
  responses; null means unavailable. These algorithmic query totals are not hardware
  gate counts or measured simulator operations. See [search evidence](SEARCH.md#structured-evidence-fields).
- Materials: `classical_observable`, `quantum_observable`, `absolute_error`; units come
  from metadata. These summarize the terminal time's selected observable; quantum means
  shot-based. New optional metrics: `ideal_observable`, `trotter_absolute_error`,
  `sampling_absolute_error`, `total_shots`, and `time_series` (default empty for legacy
  fixtures; populated by the implementation). Magnetization is mean Pauli Z per spin;
  energy is total reduced energy. Shots count **per basis per time**, with two bases.

Common metadata requires nullable `seed`, `timing_scope` (`end_to_end|solver_only`), and
`simulation_method` (`statevector|matrix_product_state|density_matrix`). Defaults:
`repetitions=1`, `simulated=true` (only value), `versions={}` (package name → version).
Owners must populate versions for reproducibility. Additional required provenance:

- Optimization/compiler: normalized `qubo` and effective `config`.
- Search: effective `parameters: SearchRequest` and nonempty `oracle_assumptions`.
- Materials: effective `parameters: MaterialsRequest`, nonempty `hamiltonian_convention`,
  `energy_unit`, and `observable_unit`. Additive optional fields describe `initial_state`,
  `trotter_order` (default 2), `execution_methods`, `measurement_bases`, `transpilation_basis`,
  `circuit_depth_scope`, `ideal_elapsed_ms`, and `sampling_seed_policy`.

Each materials time-series point has required `time`, `exact`, `ideal`, `measured`,
`trotter_error`, `sampling_error`, `total_error`, `state_fidelity` (0–1), `circuit_depth`,
and `shots_per_basis`. All three observable objects contain `per_spin_z`, `per_spin_x`,
`magnetization_z`, `zz_correlations`, and `energy`, with optional nullable `state_norm`
(L2 norm; null for shot results). Arrays use increasing spin index; bond i joins i and i+1.
Each error object contains nonnegative absolute differences for `magnetization_z`,
`zz_correlations`, and `energy`: ideal/exact, measured/ideal, and measured/exact respectively.
The errors need not add. No new field is required from an existing request or legacy
result fixture. See [the materials guide](MATERIALS.md) for equations, timing scope,
seed derivation, depth interpretation, and a tested request example.

Null fields are explicitly not applicable/unmeasured. Synthetic test fixtures exercise
serialization only and must never appear in the UI as experimental evidence.

## Shared execution handoff

Compiler plans additionally include optional `communication_timing`, defaulting to
an object with nullable `submission_ms`, `result_retrieval_ms`, `queue_ms`,
`remote_processing_ms`, and `round_trip_ms`. Current preparation always emits null;
these are provider timing placeholders, not experimental measurements. This leaves
the shared solver `TimingBreakdown` unchanged. See
[communication measurement boundaries](COMPILER_COMMUNICATION_TIMING.md).

```python
from app.quantum.qaoa import run_qaoa
from app.experiments.optimization.solvers import run_classical

# Both shared local runners are implemented; calling QAOA performs Aer simulation.
# run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult
# run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult
```

Developer 3 implements these synchronous, in-process functions; Developer 2 consumes
them after safe AST validation/extraction. Inputs are canonical, outputs include measured
timings and full objective offsets. Runners raise `TimeoutError` on budget expiry;
future API owners map it to HTTP 504 `TIMEOUT`. Validation stays at the shared boundary.
Source parsing, graph conversion, HTTP handling, and hardware execution do not belong
inside the shared QAOA runner. Circuit construction is now shared via
`app.quantum.circuits.build_qaoa_preview(qubo, p=1) -> CircuitPreview`; objective checking
is shared via `app.quantum.qubo.evaluate_qubo(qubo, bitstring) -> float`. These pure
helpers execute no jobs. Developer 3 should consume the plan instead of duplicating
gate mapping. The compiler validates solver objective/assignment consistency and
QAOA qubit/shot metrics before returning a completed comparison. Invalid shared
results return sanitized HTTP 500, never an invented completed measurement.
The compiler gives each runner independent copies of the validated instance/config
and rejects persistent input mutations. Objective matching uses absolute tolerance
`1e-9` with no relative tolerance, so large constant offsets cannot hide discrepancies.
These checks do not change the QUBO representation, bit order, canonical sense, or
solver timing flags. Common boundary validation/isolation is outside solver intervals.
