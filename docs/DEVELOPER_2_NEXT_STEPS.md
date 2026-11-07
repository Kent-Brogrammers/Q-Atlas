# Developer 2 implementation guide: compiler to manual testing

Use this guide to take the existing compiler through repeatable manual analysis,
an understandable compiler page, and the eventual shared-solver integration. Work
through the milestones in order. The instructions below describe work to implement;
unchecked tasks are not already available.

The source of truth remains [Project_Spec.md](Project_Spec.md). Keep it unchanged.
Read [COMPILER.md](COMPILER.md) for current syntax and behavior,
[API_CONTRACTS.md](API_CONTRACTS.md) for wire formats, and
[DEVELOPER_3_HANDOFF.md](DEVELOPER_3_HANDOFF.md) for the selected execution interfaces.

## 1. What you can test today

The compiler currently performs:

```text
Pasted source text
  -> Python AST parsing and allowlist validation
  -> symbolic binary polynomial
  -> normalized minimization QUBO
  -> exhaustive equivalence checks for 1–6 bits
  -> symbolic, unexecuted QAOA gate plan
```

The QUBO comes from the submitted expression. For example, a term `3*x[0]*x[2]`
becomes a quadratic coefficient of 3 for pair (0,2). It is a mathematical translation,
not a quantum measurement. The compiler never executes submitted Python.

| Capability | Current state | What it establishes |
| --- | --- | --- |
| Paste one supported marked function | Implemented | The source can be parsed safely |
| Named local terms and sequential assignments | Implemented | Straight-line objective functions can use weights, aliases, and temporary values |
| Fixed range loops and numeric accumulation | Implemented | Bounded objective loops lower to AST assignments and are independently checked against source control flow |
| Squared penalty expressions | Implemented | Named/loop-built linear residuals can be squared and converted to a QUBO |
| Extract constants, linear terms, and pairs | Implemented | A canonical QUBO can be derived |
| Verify all binary assignments for 1–6 bits | Implemented | Expression and QUBO agree within documented tolerance |
| Return parametric gates and logical depth | Implemented | A symbolic circuit plan can be constructed |
| Verify cost-gate phase formulas analytically | Tested | The declared formulas match the cost phase on tiny cases |
| Compare mocked solver outputs | Tested | Integration and result validation work with synthetic fixtures |
| Run classical/QAOA solvers | Shared stubs | Real solver behavior remains unverified |
| Render a circuit preview in the browser | Implemented as a gate table | Symbolic gates, parameters, global phase, and logical depth are readable; a graphical diagram is future work |
| Load a `.py` file | Implemented | Browser reads bounded text into the existing source editor |
| Compile general Python scripts | Outside the current subset | Imports, data-dependent control flow, and helper calls are rejected; local assignments and fixed literal-range loops are supported |

At the latest code-validation checkpoint, 266 pytest cases, four frontend file-reading
checks, Ruff lint/format checks,
frontend generated-type checks, TypeScript checks, and the production build passed.
All seven examples were also checked over actual HTTP, and the compiler page was
checked in Firefox. See [the validation record](COMPILER_MANUAL_CHECKS.md).
That is a recorded checkpoint, not a guarantee about subsequent changes.

### Execution constraint

**Use mocks for solver execution. Do not use the supercomputer, hardware,
credentials, external compute quotas, or run simulator jobs under the current
instruction.** The limited supercomputer allocation is reserved. A future local
execution phase needs a new explicit request; this guide does not authorize it.

Starting the local API, parsing source, constructing a symbolic plan, and running
the current mocked compiler tests do not submit quantum jobs. Never replace live
measurements with synthetic fixtures or label a symbolic preview as executed.

## 2. Ownership and the files you will use

Paths in this table are relative to the repository root.

| File or directory | Responsibility | Owner |
| --- | --- | --- |
| `backend/app/compiler/analysis.py` | Allowlisted AST, polynomial extraction, verification, diagnostics | Developer 2 |
| `backend/app/compiler/lowering.py` | Bounded loop/accumulation lowering and expansion budgets | Developer 2 |
| `backend/app/compiler/pipeline.py` | Shared-runner handoff, result checks, comparison metadata | Developer 2 |
| `backend/app/api/compiler.py` | Analyze/benchmark endpoints and compiler error mapping | Developer 2 |
| `backend/tests/compiler/` | Focused compiler and mocked integration tests | Developer 2 |
| `backend/app/quantum/circuits.py` | Single shared definition of symbolic cost/mixer gates | Shared handoff; Developer 3 consumes it |
| `backend/app/quantum/qubo.py` | Shared objective evaluator in API bit order | Shared handoff; Developers 2 and 3 consume it |
| `backend/app/quantum/qaoa.py` | Actual QAOA runner, currently a stub | Developer 3 |
| `backend/app/experiments/optimization/solvers.py` | Classical baseline, currently a stub | Developer 3 |
| `backend/app/schemas/contracts.py` | Shared Pydantic contracts | Coordinate affected owners |
| `frontend/src/pages/CompilerPage.tsx` | Source editor and compiler interaction | Developer 5, coordinated with Developer 2 |
| `frontend/src/api/client.ts` | Typed API calls and structured errors | Developer 5 |
| `frontend/src/types/api.generated.ts` | Generated OpenAPI types | Regenerate; never edit by hand |

The proposer authorized Developer 2 to select the shared interface decisions before
Developer 3 starts. Relay the handoff document so both implementations use them.
Changes to schema, objective sense, bit order, or timing definitions still need to
be made visible to the affected owners. Keep other experiment modules out of scope.

## 3. Milestone A: save the current pipeline on Connor

**Owner: Developer 2. Dependency: none.**

The initial compiler and original next-steps document were saved in commits
`995de08` and `4e9ba20`. The later language/preview pipeline is committed as `75539fd`,
and a signed-zero normalization regression fix as `ba11311`. The compiler-page
integration and owner handoffs are kept in a separate commit for frontend review.

From the repository root, inspect the current state before staging anything:

```sh
git branch --show-current
git status --short
git diff --check
git diff
```

`git diff` does not show untracked file contents. Review the new helpers, circuit
tests, and handoff document explicitly as well. Preserve unrelated work if it exists.

After the checks in milestone F pass, stage the reviewed pipeline files:

```sh
git add -- \
  backend/app/compiler/analysis.py backend/app/compiler/pipeline.py \
  backend/app/compiler/lowering.py \
  backend/app/quantum/circuits.py backend/app/quantum/qubo.py \
  backend/app/schemas/contracts.py \
  backend/tests/compiler/test_circuits.py backend/tests/compiler/test_pipeline.py \
  backend/tests/compiler/test_assignments.py backend/tests/compiler/test_examples.py \
  backend/tests/compiler/test_extraction.py examples/compiler/ \
  backend/tests/compiler/test_loops.py \
  backend/tests/compiler/test_penalties.py \
  frontend/src/types/api.generated.ts frontend/src/types/index.ts \
  frontend/package.json frontend/src/pages/CompilerPage.tsx frontend/src/compiler/ \
  frontend/src/components/CompilerAnalysisPanel.tsx \
  frontend/src/components/CircuitPreview.tsx frontend/tests/ \
  README.md docs/API_CONTRACTS.md docs/COMPILER.md \
  docs/DEVELOPER_2_NEXT_STEPS.md docs/DEVELOPER_3_HANDOFF.md \
  docs/DEVELOPER_5_HANDOFF.md docs/COMPILER_MANUAL_CHECKS.md
git diff --cached --check
git diff --cached --stat
git commit -m "feat(compiler): add symbolic circuit previews and validate solver handoffs"
git push origin Connor
```

Use this file list only while it matches the actual change set. Review later
features in separate commits. If the remote branch advances, fetch and reconcile
the changes normally; do not force-push over another developer's work.

**Done when:** the reviewed implementation and documentation are on `Connor`, the
generated types match, and no environment files or credentials were staged.

## 4. Milestone B: create reproducible objective examples

**Owner: Developer 2. Dependency: the existing analyzer.**

The following fixtures are now implemented under `examples/compiler/`. Read them as
text or use them to check later language changes:

```text
examples/compiler/
  minimize_three_bits.py
  maximize_three_bits.py
  repeated_terms.py
  six_bits.py
  local_assignments.py
  bounded_loops.py
  exactly_one.py
  expected_qubos.json
  README.md
```

These files are input text for the compiler. **Do not run or import them as Python
modules.** The `qatlas.objective` decorator is a source marker, not an installed
runtime package. Read the files as text and send their contents in the `source` field.

### Example 1: three-bit minimization

Save as `minimize_three_bits.py`:

```python
@qatlas.objective(num_bits=3)
def cost(x):
    return 5 - 2*x[0] + 3*x[0]*x[2]
```

Expected normalized QUBO:

```json
{
  "num_variables": 3,
  "constant": 5.0,
  "linear": [-2.0, 0.0, 0.0],
  "quadratic": [{"i": 0, "j": 2, "coefficient": 3.0}],
  "sense": "minimize",
  "original_sense": "minimize"
}
```

Independent arithmetic checks, not measured solver results:

| API assignment | Expected objective |
| --- | --- |
| `000` | 5 |
| `001` | 5 |
| `100` | 3 |
| `101` | 6 |

The exact minimum is 3; `100` is one optimal assignment. `110` is also optimal
because x[1] is unused. Do not make a test assume every optimum has a unique bitstring.

For the current one-layer preview, expect three H gates, one RZ gate on qubit 0
with coefficient +2, one CP gate on (0,2) with coefficient -3, and three RX gates
with coefficient 2. Parameters are `gamma_0, beta_0`; the global-phase coefficient
is -4. There are eight gates and logical depth 4. `executed` is false and `depth`
is null. These values describe the symbolic construction, not transpiled performance.

### Example 2: three-bit maximization

Save as `maximize_three_bits.py`:

```python
@qatlas.objective(num_bits=3, sense="maximize")
def cost(x):
    return 5 - 2*x[0] + x[1]*x[2]
```

Expected canonical QUBO: constant -5, linear `[2, 0, 0]`, pair (1,2) coefficient -1,
`sense=minimize`, `original_sense=maximize`. Negation includes the constant.

The original maximum is 6 at `011`; its canonical value is -6. For the assignment
`001`, the canonical value is -5 and the original value is 5. This gives a useful
synthetic gap example: a result of -5 compared with exact optimum -6 has gap 1.
Never present those chosen assignments as sampled QAOA output.

### Example 3: squares and repeated pairs

Save as `repeated_terms.py`:

```python
@qatlas.objective(num_bits=3)
def cost(x):
    return 2 + x[0]**2 + 2*x[1]*x[0] - x[0]*x[1] - 3*x[0]
```

Expected QUBO: constant 2, linear `[-2, 0, 0]`, one pair (0,1) with coefficient 1.
This checks binary squares, reversed source factors, duplicate pair normalization,
and retention of unused variables.

### Example 4: six-bit input

Save as `six_bits.py`:

```python
@qatlas.objective(num_bits=6)
def cost(x):
    return (
        9 - x[0] - 2*x[1] - 3*x[2] - 4*x[3] - 5*x[4] - 6*x[5]
        + 2*x[0]*x[5] + x[1]*x[4]
    )
```

Expected QUBO: constant 9, linear `[-1, -2, -3, -4, -5, -6]`, pairs (0,5) with
coefficient 2 and (1,4) with coefficient 1. The diagnostic should report verification
on all 64 binary assignments. The preview must include six qubits.

### Example 5: named local terms

Use [local_assignments.py](../examples/compiler/local_assignments.py). It includes a
docstring, a named numeric weight, intermediate benefits/penalties, and sequential
reassignment. Expected QUBO: constant 5, linear `[-2, -1, 0]`, pair (0,2) coefficient 3.

### Fixture checks

- [x] Store independently specified expected QUBOs in `expected_qubos.json`, keyed by filename.
- [x] Document each example's purpose and expected supported status in the example README.
- [x] Add one parametrized test in `backend/tests/compiler/test_examples.py` that reads
  each file as text, calls `analyze_source`, and compares its QUBO with the expected model.
- [x] For selected assignments, compare against hand-written arithmetic expectations
  such as the table above. Do not generate all expected outputs using the same extractor.
- [x] Keep timings, shots, and fabricated benchmark results out of these fixtures.

Reuse the existing AST/security tests. Add regressions for new behavior rather than
duplicating every existing test case.

The sixth fixture, [bounded_loops.py](../examples/compiler/bounded_loops.py), is also
implemented. It accumulates weighted four-bit terms and adjacent pairs. Expected
QUBO: constant 5, linear `[-1,-2,-3,-4]`, adjacent pairs with coefficient 2. See the
example README for arithmetic checks and COMPILER.md for literal-range limits.

The seventh fixture, [exactly_one.py](../examples/compiler/exactly_one.py), compiles a
loop-built selection count and squared penalty. It has constant 10, linear
`[-11,-12,-13]`, and all three pair coefficients equal to 20. Its README records all
eight objective values; these are mathematical reference values, not measurements.

**Done when:** all seven files can be pasted into the editor, their expected QUBOs
are documented, and the example test runs without quantum extras or solver calls.

## 5. Milestone C: manually test the current local API

**Owner: Developer 2. Dependency: backend API/dev environment. No simulator required.**

On a fresh checkout, follow the prerequisite installation in [README.md](../README.md).
For this phase use `uv sync --locked` in `backend/`; quantum extras are unnecessary.
Use `npm ci` in `frontend/` if its dependencies are missing.

From the repository root, start the backend in one terminal:

```sh
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, again starting from the repository root:

```sh
cd frontend
npm run dev
```

If uv is installed, `uv run --locked uvicorn ...` is an alternative to the direct
virtual-environment executable. If the executable is missing, finish backend setup
first; do not install quantum packages to fix an API startup problem.

Open <http://127.0.0.1:5173/compiler>. Interactive API documentation is available at
<http://127.0.0.1:8000/docs>. The compiler page now supports both pasted source and
local text-file loading, with structured analysis output and an unexecuted gate table.

### Direct analyze request

This request only parses and analyzes the supplied text:

```sh
curl -i http://127.0.0.1:8000/api/compiler/analyze \
  -H 'Content-Type: application/json' \
  --data '{"source":"@qatlas.objective(num_bits=3)\ndef cost(x):\n    return 5 - 2*x[0] + 3*x[0]*x[2]\n"}'
```

Expect HTTP 200, `status=supported`, the QUBO from example 1, a `VERIFIED` diagnostic,
and the symbolic preview. The response must not contain solver timings or samples.

### Manual test matrix

Use the marked-function wrapper from the examples when testing expressions below.

| Input/action | Endpoint | Expected current behavior |
| --- | --- | --- |
| Example 1 | Analyze | 200, supported, correct offset and pair |
| Example 2 | Analyze | 200, canonical negation and original maximization sense |
| Example 3 | Analyze | 200, normalized square and duplicate terms |
| Example 4 | Analyze | 200, six qubits and 64-assignment verification |
| Example 5 | Analyze | 200, named terms resolved in source order |
| bounded_loops.py | Analyze | 200, weighted loop terms and neighbor pairs extracted correctly |
| exactly_one.py | Analyze | 200, squared penalty produces offset 10, linear [-11,-12,-13], and pair coefficients 20 |
| Change a coefficient in example 1 | Analyze | Returned coefficient changes accordingly |
| `return sum(x)` | Analyze | 200, rejected, `UNSUPPORTED_SYNTAX` |
| `return x[3]` with num_bits=3 | Analyze | 200, rejected, `INVALID_INDEX` |
| `return x[0]*x[1]*x[2]` | Analyze | 200, rejected, `HIGHER_ORDER` |
| Invalid Python syntax | Analyze | 200, rejected, `SYNTAX_ERROR` |
| num_bits=7 | Analyze | 200, rejected, `INVALID_MARKER` |
| Empty source or over 20,000 characters | Analyze | 422, request validation error |
| Supported source | Benchmark | 501, shared runner dependency unavailable |
| Unsupported source such as a function call | Benchmark | 422, compiler diagnostics, no solver call |
| Invalid configuration, e.g. shots=0 | Benchmark | 422, request validation error |

In the UI an overlong input may be prevented by the textarea limit; test the API
limit through `/docs` or a direct request. Rejected analysis must have `qubo=null`
and `circuit=null`. Diagnostic locations are one-based when available.

Do not use system commands or file-writing payloads for manual experimentation.
Existing automated malicious-source tests already check rejection without executing
the source. A harmless forbidden call such as `sum(x)` exercises that validation path.

### What to record

- [ ] Example filename and source revision.
- [ ] Supported/rejected result and expected versus actual QUBO.
- [ ] Diagnostic code and line/column for rejected cases.
- [ ] Preview width, `executed=false`, `depth=null`, and parameter order.
- [ ] A short reproduction for any mismatch, followed by a focused regression test.

`GET /api/health` still returns `experiments_ready=false`. That reflects incomplete
experiment execution; it does not mean compiler analysis is unavailable.

**Done when:** you can edit coefficients in the browser, observe corresponding QUBO
changes, obtain useful rejection diagnostics, and distinguish a preview from execution.

## 6. Milestone D: make the compiler page understandable

**Owner: Developer 5 for UI; Developer 2 supplies examples and acceptance checks.**

The user authorized implementing this compiler-page integration as part of the
agenda. The basic experience is now implemented for Developer 5 review, with no new
API endpoint. Use [DEVELOPER_5_HANDOFF.md](DEVELOPER_5_HANDOFF.md) for ownership review
and remaining frontend work.

### File-by-file implementation plan

| File | Implemented responsibility |
| --- | --- |
| `frontend/src/pages/CompilerPage.tsx` | Separate typed analysis state from benchmark state; replace stale status copy; render structured analysis |
| `frontend/src/components/CompilerAnalysisPanel.tsx` | Diagnostics, normalized coefficients, and original sense |
| `frontend/src/components/CircuitPreview.tsx` | Symbolic gates, parameters, global phase, and logical depth |
| `frontend/src/compiler/source.ts` | Example source, bounded file reads, angle formatting |
| `frontend/src/api/client.ts` | Reuse existing `api.analyze`, `api.compilerBenchmark`, and `ApiError` handling |
| `frontend/src/types/index.ts` | Reuse existing named compiler/circuit types |

These components now exist and use the existing styling without a new runtime
dependency. A readable gate table is provided; an SVG renderer remains optional future work.

### Source and analysis controls

- [x] Explain that the editor accepts one marked binary objective, with a 1–6-bit limit.
- [x] Load the reproducible examples without silently altering their source.
- [x] Preserve the submitted source when a request fails.
- [x] Disable duplicate submissions and show a loading state.
- [x] Clear or mark previous results stale when source changes. Prevent an earlier
  response from being displayed as the analysis of newly edited text.
- [x] Treat HTTP 200 with `status=rejected` as an analysis rejection, not success.
- [x] Display diagnostic severity, message, line, and column. Support missing locations.

### QUBO and circuit display

- [x] Show constant, indexed linear coefficients, and canonical pair terms.
- [x] Explain that unused variables remain part of the declared width.
- [x] Show canonical minimization sense and the original sense separately.
- [x] Label the preview as symbolic and unexecuted, with one preview layer.
- [x] Render qubit i as x[i]. Display parameter-scaled angles without evaluating strings.
- [x] Distinguish `logical_depth` from transpiled depth, which is currently unavailable.
- [ ] Explain that Analyze uses p=1 even if a later benchmark uses another configured p.
- [x] Retain raw JSON as optional developer detail, not the only explanation of results.

### Comparison state

Keep comparison eligibility tied to supported, current source. A supported analysis
does not establish that the runners exist. The current API has no per-runner capability
field, and health readiness is not a compiler capability signal.

For this stage, label comparison as awaiting shared solvers, or handle the existing
501 response with a clear message. Do not add fake measurements to make the screen
look complete. Any new readiness contract needs coordination and regenerated types.

For original maximization display, negate canonical objective values. Compute gaps
using canonical values; changing display sense must not change solver semantics.

### Optional file input

The local `.py` file control is implemented. It reads text into the same editor and
submits `{source}` through the existing endpoint, enforces the source character limit,
and preserves server-side validation. A late file read cannot overwrite newer edits.
Treat the filename/extension as a convenience, not a security check. No module import,
server filesystem write, uploaded-code execution, or additional upload endpoint is needed.

**Done when:** a first-time user can trace source -> terms -> QUBO -> symbolic gates,
understand rejected input, and see why comparison is unavailable.

## 7. Milestone E: hand execution to Developer 3

**Owners: Developer 3 implements the runners; Developer 2 verifies compiler integration.**

Send [DEVELOPER_3_HANDOFF.md](DEVELOPER_3_HANDOFF.md), the shared helper files, and the
example objectives. Those decisions are already selected; do not create another QAOA
implementation under `app/compiler/`.

### Existing decisions to preserve

| Topic | Selected contract |
| --- | --- |
| QUBO | Existing shared Pydantic model; constant included; minimization canonical |
| Original maximization | Negate the entire objective upstream and preserve original_sense |
| API bit order | x[0] first, fixed width, leading zeros retained |
| Symbolic construction | `build_qaoa_preview(qubo, p=config.p)` in the shared quantum module |
| Parameter order | Explicit gamma_0, beta_0, gamma_1, beta_1, ... list |
| Gate convention | Shared RZ/CP cost mapping, global phase, and RX(2*beta) mixer |
| Evaluation | `evaluate_qubo(qubo, bitstring)` includes the constant |
| Exact baseline label | brute_force; general signed-QUBO approximation ratio stays null |
| Future simulation metadata | Initial method statevector; method changes must update provenance |
| Timing | Each solver reports its end-to-end interval; source analysis is outside both |
| Errors | Missing runner -> 501; TimeoutError -> 504; inconsistent result -> sanitized 500 |

### Developer 3 deliverables

- [ ] A shared Qiskit adapter consuming the symbolic plan and its explicit parameters.
- [ ] A classical exact baseline for the compiler's tiny inputs.
- [ ] The reusable `run_qaoa(qubo, config)` implementation, with no source parsing.
- [ ] Measurement/count conversion into API bit order.
- [ ] Finite, consistent objective/assignment results and matching qubit/shot metrics.
- [ ] Deadline enforcement that includes native work, optimizer stopping behavior,
  measured timing components, and reproducibility metadata.

Implementation and mocked checks can proceed under the existing constraint. Running
the new solvers, including local simulation, requires a later explicit execution request.

### Your Developer 2 integration responsibilities

- [ ] Keep compiler tests patched at the shared runner boundaries, even after real
  runners are implemented. They must not unexpectedly start execution.
- [ ] Keep validation of source before any runner call and pass the same QUBO/config
  to both solver paths.
- [ ] Preserve objective/assignment validation and nonnegative exact-gap checks.
- [ ] Ensure rejected source never reaches a runner and missing/failed solvers never
  become completed measurements.
- [ ] Coordinate updates to stub-assertion tests in `backend/tests/optimization/`
  with Developer 3 when those stubs are replaced.
- [ ] Regenerate frontend types if a coordinated integration change alters contracts.

**Done when:** the actual runner implementations can satisfy the compiler contracts
and the mocked compiler suite still runs without executing them. This milestone
alone does not establish runtime performance or authorize quantum jobs.

## 8. Milestone F: run the appropriate checks

### Current mocks-only checks

From `backend/`, with the API/dev environment installed:

```sh
.venv/bin/pytest tests/compiler
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Equivalent `uv run --locked ...` commands are appropriate when uv is available.
The focused compiler tests require no quantum extras. Once other owners add real
execution tests, review which checks invoke them before running the entire suite
under a mocks-only restriction; do not assume all future tests remain job-free.

| Existing compiler test file | What to preserve |
| --- | --- |
| `test_extraction.py` | Exhaustive equivalence, normalization, unsupported syntax, malicious inputs, resource limits |
| `test_assignments.py` | Local scope, aliases/reassignment, all binary inputs, assignment targets/limits, and unused invalid code |
| `test_loops.py` | Literal ranges, accumulation, nesting/indices/scope, expansion limits, and verification against original source loops |
| `test_penalties.py` | Squared residuals across all inputs, maximization, binary identities, degree limits, and finite numeric behavior |
| `test_analysis_contract.py` | Supported/rejected response validity and diagnostic locations |
| `test_circuits.py` | Analytical cost-phase formulas, preparation/mixer declarations, parameters, logical depth |
| `test_pipeline.py` | Mocked handoff, maximization, nonzero gap, errors, rejection of inconsistent results |
| `test_examples.py` | Implemented example-to-expected-QUBO regression checks |

After a shared contract change, regenerate from `frontend/`:

```sh
npm run types:generate
```

For frontend changes or contract updates, also run:

```sh
npm run test:compiler
npm run types:check
npm run typecheck
npm run build
```

Review the generated diff alongside the backend change. Do not edit generated
TypeScript manually. Run `git diff --check` before committing.

The original HTTP tests stalled inside the restricted sandbox's test-client event
loop and passed outside it. If a test stalls, investigate whether it is application
behavior or the execution environment. Do not enable hardware, simulators, or fake
production results to get a green test run.

### Future live local solver checks — only after explicit authorization

Start with tiny instances on the local machine; no supercomputer is needed for the
initial compiler acceptance checks. Leave hardware and external quotas out of this phase.

- [ ] Test the actual Qiskit cost unitary against the objective phase on tiny cases.
- [ ] Compare actual shared classical results with independently known tiny optima.
- [ ] Recompute the objective of every returned assignment with the shared evaluator.
- [ ] Verify asymmetric bitstrings, leading zeros, constants, and original maximization.
- [ ] Check the configured seed, p, shots, optimizer budget, and timeout behavior.
- [ ] Record actual versions, method, seeds, counts, quality, timings, and transpiled depth.
- [ ] Label QAOA as stochastic; a finite-budget run may return a suboptimal assignment.
  Assert assignment validity and objective consistency rather than assuming exact optimality.
- [ ] Repeat a small recorded setup where practical and retain actual results separately
  from synthetic test fixtures.

Use [BENCHMARK_METHODOLOGY.md](BENCHMARK_METHODOLOGY.md). Analytical phase checks and
mocked solver outputs do not verify actual assembly, optimizer behavior, sampling,
execution time, or quantum advantage.

## 9. Decide on broader script support after the initial flow works

Bring one or two actual objective scripts you want to submit and identify exactly
which unsupported construct prevents their analysis. Extend the language one
construct at a time; unrestricted Python compilation is outside the MVP.

Straight-line local assignments are now implemented, for example:

```text
@qatlas.objective(num_bits=3)
def cost(x):
    benefit = 2*x[0] + x[1]
    penalty = 3*x[0]*x[2]
    return 5 - benefit + penalty
```

This example is now supported. The implemented scope rules are:

- One plain name target per assignment, up to 64 assignments, one final return,
  and an optional leading function docstring.
- Explicit symbolic scope and independent numeric scope. Names must be defined
  before use. Local reassignment uses the previous right-hand-side values; saved
  aliases retain the value from their own assignment.
- No rebinding of the binary-vector parameter, chained/unpacking/annotated assignment,
  or mutation of attributes/subscripts. Numeric local +=, -=, and *= are now supported.
- Full validation of unused assignments, including expressions that simplify to zero,
  and finite numeric intermediate values on every verified binary input.
- Unchanged AST/source limits, quadratic degree limits, exhaustive verification,
  minimization sense, and API bit order.
- Parse and interpret the allowlisted subset; never use eval, exec, or
  dynamic import to discover an objective's meaning.

Fixed literal-range loops are now implemented with at most two nesting levels and
strict source/expansion limits. Empty or dynamic ranges, while/async loops, loop else,
break/continue, explicit loop-index reassignment, and general calls remain rejected.
Loop indices and +/- offsets can be used for indexing; ordinary local names cannot.
The original source loops are numerically interpreted independently of AST lowering
for exhaustive verification. Preserve that independence when extending the language.

Literal-exponent squares of allowlisted expressions are also implemented. This
includes named residuals and loop-built totals. Expansion must remain quadratic;
there is no automatic quadratization, auxiliary-variable generation, penalty-weight
selection, or separate constraint-feasibility reporting. The shared QUBO contract
and bit order are unchanged.

Broader helper calls, imports, data-dependent control flow, and larger variable
counts remain separate decisions. Do not add them incidentally while fixing the UI.

## 10. Final readiness checklist

### Ready for your own manual analysis testing

- [x] Current pipeline saved on Connor and standard setup documented.
- [x] Seven reproducible source examples and expected QUBOs checked.
- [x] Editing source changes extracted coefficients as expected.
- [x] Rejected input gives actionable diagnostics with no partial QUBO/circuit.
- [x] Browser displays the QUBO and explicitly unexecuted preview clearly.
- [x] Unavailable comparisons are explained without fabricated data.
- [x] Compiler tests, affected lint/type checks, and build pass.

### Ready for a separately authorized local solver test

- [ ] Developer 3 has received and implemented the shared execution handoff.
- [ ] Actual assembly/measurement wiring and timeout behavior are ready to verify.
- [ ] Compiler tests remain mocked and execution tests are explicitly identified.
- [ ] Timing scope, statevector provenance, and exact-baseline naming agree.
- [ ] Tiny reference instances, seeds, parameters, and result-recording procedure are prepared.
- [ ] Explicit authorization has been given for the local execution phase.

Until the second checklist is complete, keep the milestone description precise:
source analysis and symbolic QAOA construction work; live solver comparison remains
pending. The supercomputer allocation stays unused.

## 11. Immediate agenda after the compiler-language milestones

1. The language/preview pipeline and canonical-zero fix are committed on Connor,
   followed by the separately reviewable compiler-page integration and check record.
2. All seven fixtures have passed direct HTTP checks. Next choose an objective you
   want to submit, load it in the compiler page, and record any unsupported constructs.
3. Give Developer 5 [the frontend handoff](DEVELOPER_5_HANDOFF.md) for review of the
   implemented result display, stale-result handling, and local text-file loading.
4. Give Developer 3 [the shared handoff](DEVELOPER_3_HANDOFF.md) and keep compiler
   integration tests mocked while the actual runners are implemented.
5. Once separately authorized, verify the tiny local solver path and measured
   provenance according to milestone F. Keep the supercomputer allocation unused.

Prioritize this usable integration flow over broadening the AST allowlist further.
