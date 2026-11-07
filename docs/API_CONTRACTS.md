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
| POST `/api/compiler/benchmark` | `CompilerBenchmarkRequest` | `CompilerBenchmarkResult` | Developer 2, consuming Developer 3 runners |
| POST `/api/optimization/run` | `OptimizationRequest` | `OptimizationResult` | Developer 3 |
| POST `/api/search/run` | `SearchRequest` | `SearchResult` | Developer 4 |
| POST `/api/materials/run` | `MaterialsRequest` | `MaterialsResult` | Developer 1 |

Health returns `{"status":"ok","service":"q-atlas","backend":"aer_simulator","experiments_ready":false}`.
This signals API readiness, not readiness of all experiments. Materials now returns
real simulation results with **HTTP 200**; compiler, optimization, and search POST
operations still validate first and return **HTTP 501**:

```json
{"status":"error","error":{"code":"NOT_IMPLEMENTED","message":"Search benchmark is not implemented. Developer 4 owns this feature.","diagnostics":[]}}
```

Invalid payloads return **422** with the same envelope and `VALIDATION_ERROR`.
Routing/method errors return `NOT_FOUND`/`METHOD_NOT_ALLOWED` (404/405); unexpected
exceptions return sanitized `INTERNAL_ERROR` (500). Materials returns `TIMEOUT` (504)
when its bounded worker exceeds the budget and `HTTP_ERROR` (503) when its optional
quantum dependencies are missing. `HTTP_ERROR` also covers other HTTP failures.
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
- `CompilerBenchmarkRequest`: same `source`, plus default `config: QAOAConfig`.
  Benchmarking must revalidate/extract source on the server; no trusted client-extracted objective.
- `OptimizationRequest`: required discriminated `problem`, plus default QAOA config.
  `{"kind":"qubo","qubo":...}` uses the canonical QUBO. A graph uses
  `{"kind":"graph","num_vertices":3,"edges":[{"i":0,"j":1,"coefficient":1}]}`.
  Graphs have 2–16 vertices, 1–120 unique undirected edges, `i<j`, finite weights,
  no self-loops. `coefficient` is the edge weight, not yet a QUBO coefficient.
  Developer 3 implements and documents the Max-Cut conversion.
- `SearchRequest`: required `num_qubits` (1–16), required `marked_states` (1–256 unique
  binary strings, each exactly that width), optional nullable `iterations` (0–256;
  default null delegates iteration selection to the future owner), and default run config.
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

For compiler, optimization, and search these are validated limits, not runtime isolation.
Their stubs do no expensive work. Materials runs in a spawned process that is terminated
and reaped on timeout, including during native simulator work; startup/import time counts
against that wall-clock budget, but not the benchmark's numerical timings.
Future owners must enforce deadlines throughout their work, including native simulator
calls, rather than wrapping a blocking call in a timer that cannot cancel it. The compiler
owner must add AST node/depth limits along with the parser; no parser exists here.
There is no asynchronous job API, request-body transport limiter, or hardware execution.

## Analysis response

`CompilerAnalyzeResult` requires `status` (`supported|rejected`) and `diagnostics`.
`qubo` and `circuit` default null. `supported` requires a normalized QUBO; `rejected`
cannot include a QUBO or circuit. Circuit metadata has required `num_qubits` and
optional nullable `depth`, plus default backend `aer_simulator`. Circuit metadata is
a preview description, not proof of execution or a benchmark.

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

```python
from app.quantum.qaoa import run_qaoa
from app.experiments.optimization.solvers import run_classical

# Both are intentional NotImplementedError stubs in this foundation.
# run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult
# run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult
```

Developer 3 implements these synchronous, in-process functions; Developer 2 consumes
them after safe AST validation/extraction. Inputs are canonical, outputs include measured
timings and full objective offsets. Runners raise `TimeoutError` on budget expiry;
future API owners map it to HTTP 504 `TIMEOUT`. Validation stays at the shared boundary.
Source parsing, graph conversion, HTTP handling, and hardware execution do not belong
inside the shared QAOA runner. Preview circuit helpers must be coordinated, not duplicated.
