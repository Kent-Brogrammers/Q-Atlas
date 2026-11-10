# Compiler -> optimization handoff

These are the interface decisions selected by Developer 2 while implementing the
compiler pipeline. The project proposer authorized making these decisions ahead of
Developer 3's work and will relay this document. The original specification is
unchanged. Developers 3 and 5 are the impacted owners.

## Execution remains mocked

Do not use the supercomputer, hardware, external quotas, credentials, or run simulator
jobs under the current instruction. PR #13 (`8451ce2`) implements both shared local
runners. Compiler tests replace either the runners or the actual QAOA worker with
synthetic results; none run Aer. See [the testing-day runbook](DEVELOPER_2_TESTING_DAY.md).

### Completed local QAOA handoff

The compiler consumes your `run_qaoa` unchanged: bounded worker, angle optimization,
final transpilation/sampling, x[0]-first measured assignment and canonical objective.
It validates schema, objective/assignment, width/shots, optimizer evaluation cap,
timing components and reported deadline. Angle-search records remain distinct from
sampled solver results. Reported timing components may overlap and are not summed.

The compiler HTTP benchmark now defaults off. Only the server environment setting
`QATLAS_ENABLE_COMPILER_AER=1` opts into the local Aer path; the compiler page still
prepares code/plans only. This adds no shared schema or provider changes. Missing
optional dependencies map to sanitized HTTP 501; expiry maps to 504.
Direct trusted Python runner calls and other experiment endpoints are not covered
by this compiler HTTP guard. Hardware requires separate policy/provenance agreement.

## Shared helpers to consume

### Proposed provider communication measurement handoff

D2 has added a compiler-plan-only `communication_timing` block, defaulting all fields
to null. No shared solver timer semantics change. D3/D5 should review the field
boundaries and future measured-result integration in
[COMPILER_COMMUNICATION_TIMING.md](COMPILER_COMMUNICATION_TIMING.md): submission,
ready-result retrieval, queue, remote processing, and full round trip. Instrument the
future provider adapter; do not substitute Aer runtime for remote transfer or add
overlapping intervals to an already inclusive total.

The compiler now accepts arbitrary function/vector names and declared named scalar
inputs, with `@qatlas.objective` width inference. Scalars map to existing canonical
indices in signature order. The new INPUT_MAPPING diagnostic exposes that association;
the QUBO and runner inputs remain unchanged. See [QUANTUM_PRESENTATION.md](QUANTUM_PRESENTATION.md)
for the still-disabled provider integration and the unresolved QPU/HPC allocation type.

```python
from app.quantum.circuits import build_qaoa_preview
from app.quantum.qubo import evaluate_qubo

plan = build_qaoa_preview(qubo, p=config.p)
value = evaluate_qubo(qubo, "011")  # For a three-variable QUBO; x[0]=0.
```

`build_qaoa_preview(QUBO, p: int = 1) -> CircuitPreview` accepts 1–8 layers and uses
the shared QUBO width (up to 16). It has no quantum-package imports or job submission.
The compiler's source frontend stays limited to 1–6 bits for exhaustive verification.

`evaluate_qubo(QUBO, bitstring: str) -> float` includes the constant, requires exact
width, and rejects nonbinary inputs and nonfinite totals. API strings put `x[0]`
on the left, preserving leading zeros. This is an evaluator, not a solver baseline.

## Circuit decisions

- Prepare every qubit with H.
- Parameter order is `gamma_0, beta_0, gamma_1, beta_1, ...`. Use this explicit list
  when binding parameters; do not assume a library's automatic parameter ordering.
- For each layer: RZ(-gamma × linear[i]) on qubit i, then CP(-gamma × coefficient)
  for each canonical pair (i,j), then RX(2 × beta) on every qubit.
- Omit zero linear gates. Pair terms are already combined and sorted by the QUBO model.
- Add global phase `-gamma × (constant + sum(linear[i]/2))` per layer. The RZ
  convention otherwise introduces an extra phase; CP supplies pair phases directly.
  Including this offset makes the cost unitary exactly `exp(-i gamma C(x))`.
- A gate angle is `{parameter, coefficient}`; form the product using a trusted
  parameter lookup. Do not evaluate string expressions or submitted source.
- No measurements are included. The future runner owns measurement wiring and count
  conversion: measure qubit i into classical bit i and reverse ordinary Qiskit count
  strings at the adapter boundary to obtain API bit order.

Developer 3 should translate this shared plan to the installed Qiskit circuit API
and reuse it for execution. Keep a single gate-mapping definition in
`app/quantum/circuits.py`; do not reimplement cost layers in the compiler or runner.
Finite-coefficient overflow in the phase helper raises ValueError and calls for
rescaling the instance.

## Preview versus evidence

The analyze endpoint returns the one-layer plan, independently of future benchmark
configuration. The preview identifies itself with `kind=qaoa_logical_preview` and
`executed=false`. Its `logical_depth` counts parallel layers of the declared gates.
`depth` remains null because no transpilation has happened. The backend field names
the intended target; it does not claim that Aer was invoked.

The compiler page now renders `gates`, `parameters`, and `global_phase` from the
generated `CircuitPreview` type in a readable table, with an unexecuted label and
collapsed raw JSON. No image payload or new endpoint was needed. Developer 5 owns
further UI work; a graphical circuit diagram and benchmark charts remain future work.

Analytical tests verify the diagonal cost-phase formulas for all assignments of a
tiny QUBO, including constant offsets, both original senses, and multiple layers.
They do not evolve quantum states or establish correctness of a future Qiskit
adapter, optimizer, sampling procedure, or hardware implementation.

## Generated Python export

The compiler now exposes `POST /api/compiler/generate` and a frontend `.py` download.
It serializes `build_qaoa_preview(qubo, p)` into standalone Qiskit construction calls,
including the declared parameters and global phase. No new phase/mixer formulas,
optimizer, measurement wiring, or execution engine were introduced. It does not import
Qiskit or run the downloaded file during generation/tests.

The export replaces an explicit `@qatlas.circuit` factory while preserving surrounding
Python as text. Actual runner signatures, bit order, objective sense, timing, and
mocked execution constraints remain unchanged. Continue consuming the shared gate
models for the runner rather than parsing generated strings. See
[COMPILER_SCRIPT_GENERATION.md](COMPILER_SCRIPT_GENERATION.md).

## Runner contract to implement later

The full-file compiler now supports local numeric weight vectors and reuses static
generation before handing its verified QUBO/config to these same runner interfaces.
`POST /api/compiler/benchmark/plan` prepares hashes, the canonical instance ID, config,
preview, and runner references without invoking either runner. The frontend uses only
that planning endpoint and keeps execution disabled. Tests exercise full-file runner
handoffs only through mocks; no test imports or executes a submitted/generated script.

The planned comparison scope is `objective_optimization`, not whole-application
runtime. A trusted full-application execution/timing boundary remains separate work;
do not add arbitrary uploaded-Python execution to the shared solver. See
[COMPILER_BENCHMARK_PLAN.md](COMPILER_BENCHMARK_PLAN.md). Input/output signatures,
canonical sense, bit order, shared gates, timing flags, and ownership remain unchanged.

Existing signatures and ownership remain:

```python
run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult
run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult
```

- Return canonical minimization objectives including the constant. Preserve
  `original_sense` for display; never reverse the solver's objective sense.
- For compiler comparisons, both results must supply a matching objective and a
  valid full-width bitstring. QAOA must supply matching `num_qubits` and `shots`.
  The compiler checks these before returning a completed result.
- Report assignment costs using the shared evaluator. The compiler checks absolute
  objective differences against `1e-9`, without a relative tolerance that grows with
  constant offsets. Return the cost of the best assignment, not an optimizer's mean
  expectation. Ill-conditioned source/QUBO mismatches are rejected during analysis.
- Treat supplied QUBO/config models as read-only. The compiler supplies each runner
  an independent deep copy, checks for persistent mutation, and retains the original
  instance/seed/settings for comparison metadata. Build working representations
  internally. Input mutation is an integration failure with sanitized HTTP 500.
- `brute_force` is the exact baseline label used to populate the canonical
  objective gap. Other algorithms leave the comparison gap unknown. General signed
  QUBO approximation ratios remain null.
- An allegedly exact optimum above a valid QAOA solution is an integration failure,
  not a negative gap to hide. Solver inconsistencies become sanitized HTTP 500 errors.
- Initial execution is specified as Aer statevector simulation in the compiler's
  metadata. If a different method is needed, coordinate the provenance change first.
- Each solver's end-to-end timer includes its own preparation/result extraction;
  source parsing and exhaustive verification stay outside both timers. Return
  measured timing flags/components, with null for unmeasured durations.
  Common request-boundary validation and input isolation also stay outside both
  solver intervals; neither timer is advertised as complete HTTP request latency.
- Enforce `timeout_seconds`, including native calls, and raise TimeoutError. Compiler
  HTTP mapping is 504. No fake results on expiry or missing dependencies.
- Report transpiled depth in benchmark metrics, never preview logical depth.

Before authorizing any real execution, verify actual
circuit construction, phase conventions, API count ordering, reproducibility, and
timings with separately authorized local checks. No performance claims follow
from the synthetic fixtures or symbolic previews.
