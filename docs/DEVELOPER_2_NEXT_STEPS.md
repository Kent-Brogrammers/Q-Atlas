# Developer 2: remaining work and integration roadmap

Updated: 2026-11-09. Branch: `Connor`.

The current compiler UI is integrated into main's Svelte frontend at `/compiler/`.
It needs only `@qatlas.objective`: function/input names are arbitrary, scalar input
counts or static vector widths are inferred, and no circuit code is required.
Use **Convert Python**, then **Download .py**. Mathematical/circuit/benchmark details
are optional. The React reference and other developers' changes are preserved.
Read [QUANTUM_PRESENTATION.md](QUANTUM_PRESENTATION.md) for the future provider hookup;
the actual provider/cluster has not been identified and no hardware was connected.

After merging main, the full default pytest suite includes real simulator tests.
Under the current mocks-only instruction use the inspected safe selection:

```sh
cd backend
.venv/bin/pytest tests/compiler tests/api tests/schemas tests/optimization tests/materials/test_request_contract.py
```

This selection passed 422 cases. It includes pure classical math, mocked compiler
handoffs, and Pydantic contracts; materials/search/environment simulation suites
were deliberately not run. Historical full-suite counts below precede this merge.

The **file-to-generated-script frontend flow is implemented**. Use **Generate script**
to load a `.py` file, replace an explicitly marked `@qatlas.circuit` factory with
generated Qiskit construction code, preserve the surrounding Python, and download
the result. Read [COMPILER_SCRIPT_GENERATION.md](COMPILER_SCRIPT_GENERATION.md) and try
[script_replacement.py](../examples/compiler/script_replacement.py). No execution is
enabled by this feature. For a broader existing-file pattern, record a concrete input
before extending circuit discovery or factory signatures.

The next increment is also implemented: **local numeric weight vectors**, a
[five-program catalog with two generated output scripts](../examples/compiler/programs/README.md),
and **Prepare comparison** with a downloadable nonexecuting manifest. The full-file
adapter is connected to the existing shared-runner handoff and tested through mocks.
Read [COMPILER_BENCHMARK_PLAN.md](COMPILER_BENCHMARK_PLAN.md) for the current comparison
scope and the separate trusted boundary needed before timing a whole application.

Your compiler is ready for manual source-analysis testing. The next milestone is to
validate objectives you actually want to submit and finish the shared-runner
integration when Developer 3 supplies it. More Python syntax is optional work driven
by those inputs, rather than a prerequisite to trying the current compiler.

This is the current plan for your track. The original [Project_Spec.md](Project_Spec.md)
remains the source of truth. Use [COMPILER.md](COMPILER.md) for supported syntax and
current behavior, and [API_CONTRACTS.md](API_CONTRACTS.md) for the executable contracts.
This document distinguishes completed operations from the remaining integration tasks.

## 1. Current checkpoint

| Area | Already available | Where to look |
| --- | --- | --- |
| Safe Python analysis | One marked objective, local variables, bounded literal-range loops, numeric accumulation, squared penalties | `backend/app/compiler/analysis.py`, `lowering.py` |
| Weighted source inputs | Local numeric list/tuple literals with 1–64 elements and literal/unrolled indices | `backend/tests/compiler/test_vectors.py` |
| QUBO extraction | Canonical minimization, full constant offsets, normalized binary terms, original-sense metadata | `backend/app/schemas/contracts.py` |
| Correctness verification | All binary inputs for 1–6 bits; absolute tolerance 1e-9 without relative scaling | `backend/tests/compiler/` |
| Circuit construction | Shared symbolic gate plan, parameter order, global phase, logical depth | `backend/app/quantum/circuits.py` |
| Benchmark adapter | Revalidates source, isolates each runner's inputs, checks objectives and provenance | `backend/app/compiler/pipeline.py` |
| Browser input | Paste Python or load a local text file; source is never executed | `frontend/src/pages/CompilerPage.tsx` |
| Browser output | Line-linked diagnostics, coefficient tables, original/canonical sense, unexecuted gate table | `frontend/src/components/CompilerAnalysisPanel.tsx`, `CircuitPreview.tsx` |
| Python script output | Full-file passthrough, explicit circuit-factory replacement, 1–8 layers, code preview/download | `backend/app/compiler/generation.py`, `frontend/src/components/GeneratedScript.tsx` |
| Reproducible inputs | Seven source files with expected QUBOs and arithmetic reference values | [examples/compiler](../examples/compiler/README.md) |
| Repeatable API check | Health, seven examples, and a rejection case over HTTP, with no execution routes | `backend/scripts/check_compiler_api.py` |
| Comparison preparation | Complete-file validation, source/generated hashes, canonical instance/config, disabled execution | `POST /api/compiler/benchmark/plan`, `BenchmarkPlanPanel.tsx` |
| Actual optimization | Classical and QAOA entrypoints are still stubs on this branch | Developer 3 dependency |

The last recorded validation passed **368 backend tests**, six frontend source/file
checks, Ruff, generated-type checks, TypeScript checks, and the production build.
An earlier real HTTP/Firefox session checked all seven examples and the compiler UI;
see [COMPILER_MANUAL_CHECKS.md](COMPILER_MANUAL_CHECKS.md) for the cases and later
numerical-hardening checks. These are checkpoints, not guarantees about future edits.

Current endpoints:

| Action | Current result |
| --- | --- |
| Analyze supported source | HTTP 200, supported QUBO and symbolic circuit |
| Analyze unsupported source | HTTP 200, rejected diagnostics, no QUBO/circuit |
| Generate a supported script | HTTP 200, verified QUBO, selected-layer preview, unexecuted Python artifact |
| Generate an invalid/ambiguous script | HTTP 200, rejected diagnostics and no artifact |
| Prepare a supported comparison | HTTP 200, nonexecuting plan with false script/quantum flags and no measurements |
| Prepare a rejected script | Structured HTTP 422 before either runner is called |
| Submit an invalid request payload/config | HTTP 422, structured validation error |
| Benchmark unsupported source | HTTP 422 before any solver call |
| Benchmark supported source while runners are stubs | HTTP 501, shared runner unavailable |
| A mocked runner exceeds its budget | HTTP 504 |
| A mocked runner returns inconsistent values or changes its inputs | Sanitized HTTP 500 |

The Analyze preview is always one layer; Generate uses the selected 1–8 layers.
Neither is evidence of transpilation,
sampling, optimization, solver quality, or runtime advantage.

### Execution constraint

**Keep solver execution mocked. Do not use the supercomputer, hardware, credentials,
external compute quotas, or run simulator jobs under the current instruction.**
The limited supercomputer allocation stays reserved. A future local execution phase
needs a new explicit request; this roadmap does not authorize it.

Local API/UI startup, AST analysis, mathematical verification, symbolic planning,
and the existing mocked compiler tests do not submit quantum jobs. Once real runners
are merged, review test selection and execution controls before running anything
that could invoke them. The compiler page now submits only planning requests and
keeps its execution button disabled. Its underlying benchmark API still consumes
shared runner stubs; review execution controls before replacing them. A future
working runner or frontend control does not supply execution authorization.

## 2. What to do next, in order

| Priority | Task | Owner | Dependency | Completion evidence |
| --- | --- | --- | --- | --- |
| P0 | Analyze one real objective you want to use | You, Developer 2 | None | Reproducible source plus expected/actual analysis |
| P1, done | Generate and download a replacement circuit script in the frontend | You, frontend integration authorized | Shared gate plan | Real API/Firefox checks cover upload, replacement, matching download contents, layers, and stale results |
| P1, done | Add weighted complete programs and supported/rejected examples | You | Bounded literal vectors | Five catalog outcomes and two generated snapshots verified statically |
| P1, done | Prepare the eventual classical/QAOA comparison | You | Full-file extraction and shared runner interfaces | Plans call no runners; full-file comparison adapter passes mocked handoffs |
| P0 | Relay the selected runner contract | You and Developer 3 | Teammate review | Documented agreement on the existing handoff |
| P1, done | Make the analysis-only API smoke check repeatable | You | Current analyzer and local API | Nine real HTTP checks pass; stopped-server failure is verified |
| P1, done | Close identified integration-test gaps | You | Existing mocked tests | Both runner error paths and mutation-then-timeout are covered |
| P1 | Review the compiler page integration | Developer 5, with you | Existing page/handoff | Reviewed UI behavior and any concrete follow-up issues |
| P2 | Connect actual shared implementations safely | You and Developer 3 | Their implementations and execution opt-in design | Compiler integration still passes with mocks; live tests identified separately |
| P2 | Verify a tiny local comparison | You and Developer 3 | Explicit execution authorization | Recorded correctness and provenance checks |
| P3 | Extend the supported language if needed | You | A real rejected objective | One documented construct, bounded implementation, focused tests |

The smoke script and identified failure-path tests are now implemented. Your next
product task is trying a meaningful objective file and recording what happens.
Further compiler coding should address an observed mismatch or an agreed integration need.

## 3. P0: validate a real objective

### Start the local application

Follow [README.md](../README.md) for prerequisites. On a fresh backend environment,
`uv sync --locked` installs API/dev dependencies; quantum extras are unnecessary
for this stage. Install frontend dependencies with `npm ci` if needed.

From the repository root, start the backend in one terminal:

```sh
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

From the repository root in a second terminal:

```sh
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173/compiler>. API documentation is at
<http://127.0.0.1:8000/docs>. No account, environment file, or credentials are needed
for the default local setup.

### Choose and check an input

- [ ] Select a small binary objective with 3–6 variables and an expected meaning.
- [ ] Begin with one supported marked function. Keep imports, general helper calls,
  and data-dependent control flow out of the submitted function.
- [ ] For a complete script, use **Generate script** and mark its zero-argument circuit
  factory with `@qatlas.circuit`. Confirm the downloaded Python replaces that factory
  and preserves the surrounding code. For an objective-only check, select **Analyze
  objective only**, load it with **Load a Python file**, and click **Analyze**.
- [ ] Check the constant, indexed linear terms, pairs, original sense, and width.
- [ ] Verify a few assignments independently by arithmetic. For important tiny
  instances, record every binary assignment or an independently known optimum.
- [ ] Edit a coefficient and confirm old results clear and the next QUBO changes.
- [ ] Try a harmless unsupported expression and check its diagnostic location.
- [ ] Record any rejection before deciding whether the grammar needs an extension.

The seven existing examples are a baseline, not a substitute for your intended use
case. Their `.py` files are compiler input text; do not run or import them as modules.

Useful reference case: [exactly_one.py](../examples/compiler/exactly_one.py) produces
constant 10, linear [-11,-12,-13], and all three pair coefficients equal to 20. Its
mathematical minimum is -3 at API assignment `001`. Those are arithmetic expectations,
not measurements from a solver. The source supplies the penalty weight; the compiler
does not choose a weight or emit a separate constraint-feasibility result.

### Record a case

Use the following as a template for an issue or a small case README:

```text
Case name:
Source filename and source revision:
Intended binary variables and objective units:
Original objective sense:
Expected constant / linear / quadratic terms:
Independent assignment -> objective checks:
Observed supported/rejected status:
Observed diagnostic code and line/column:
Observed normalized QUBO and preview width:
Mismatch or unsupported construct:
Next action: fix / document / request one language extension / no change
```

Save project-owned, shareable cases under `examples/compiler/` with independently
specified expectations. Keep credentials and local environment files out of commits.
If the analysis is correct, you do not need to add new syntax to consider the case done.

**Done when:** at least one intended objective has a reproducible accepted result,
or its exact unsupported construct is documented with an agreed next action.

## 4. P0: relay the contract to Developer 3

Send [DEVELOPER_3_HANDOFF.md](DEVELOPER_3_HANDOFF.md) yourself. It contains the decisions
already selected for the compiler; this document does not contact another teammate.

Ask them to consume these interfaces:

| Interface | Current responsibility |
| --- | --- |
| `build_qaoa_preview(qubo, p=config.p)` | Single shared definition of symbolic preparation, cost gates, mixers, parameters, phase |
| `evaluate_qubo(qubo, bitstring)` | Assignment objective including constant, in API order |
| `run_classical(qubo, config) -> SolverResult` | Their classical baseline implementation |
| `run_qaoa(qubo, config) -> QAOAResult` | Their shared quantum execution implementation |

Confirm the following before they implement against a different assumption:

- [ ] Minimization remains canonical, including negation of the entire original
  maximization objective. Return assignment cost, not the optimizer's expectation.
- [ ] API strings put x[0] first and preserve leading zeros; qubit i corresponds to x[i].
- [ ] Use the explicit gamma_0, beta_0, ... order and the shared gate plan.
- [ ] Preserve the cost phase, constant/global phase, and RX(2*beta) mixer conventions.
- [ ] Supply objective and full-width assignment from both runners, plus correct
  qubit/shot metrics from QAOA.
- [ ] Treat input QUBO/config models as read-only. The adapter supplies independent
  deep copies and rejects persistent mutation.
- [ ] Use the shared evaluator for returned costs. Objective matching uses absolute
  tolerance 1e-9, with no relative tolerance that grows with a large offset.
- [ ] `brute_force` is the exact-baseline label used for the comparison gap; general
  signed-QUBO approximation ratios stay null.
- [ ] Initial simulation provenance is statevector; coordinate any method change.
- [ ] Each solver reports its own end-to-end timer and genuine timing components.
  Source analysis and common request-boundary validation/isolation are outside both.
- [ ] Enforce deadlines including native work and raise TimeoutError on budget expiry.
- [ ] Agree how real execution will remain opt-in while the current mocks-only
  instruction is active. The current contracts do not define an execution-mode field.

Suggested message to adapt:

> The compiler and file-input page are ready on Connor, with correctness hardening
> through 6df303d. Please use docs/DEVELOPER_3_HANDOFF.md and the shared circuit/QUBO
> helpers for your runner. Compiler tests stay mocked. Before connecting real
> execution, let's confirm input immutability, absolute objective tolerance, bit
> order, statevector provenance, timings, and how execution will be enabled explicitly.

Developer 3 owns Qiskit assembly, transpilation, optimizer/sampling behavior, and the
classical solver. You own consuming and checking their results. Keep one QAOA engine.

**Done when:** the selected contract has been relayed and any changes are recorded
before cross-module code or schema changes are made. A prepared handoff document is
not evidence that the teammate has received or implemented it.

## 5. P1, complete: use the reusable analysis-only API smoke check

The earlier temporary HTTP checks are now complemented by a committed, repeatable
analysis-only checker. Use it when starting the API or reviewing compiler integration.

### Implemented files and interface

| File | Purpose |
| --- | --- |
| `backend/scripts/check_compiler_api.py` | Read examples as text, send analysis requests, compare with expected QUBOs |
| `backend/tests/compiler/test_api_smoke.py` | Check the smoke utility with controlled HTTP responses |
| `docs/COMPILER.md` | Document the command, expected outcome, and failure interpretation |

These files now exist. With a local API running:

```sh
cd backend
.venv/bin/python scripts/check_compiler_api.py --base-url http://127.0.0.1:8000/api
```

The default socket timeout is 5 seconds. Use `--timeout 2` to select another value
in (0, 60]. The current result is nine checks: health, seven supported source files,
and one unsupported-call rejection. New manifest examples are included automatically.

### Completed requirements

- [x] Use existing dependencies or the standard library; no new package is needed.
- [x] Default to the local API and apply a finite HTTP timeout.
- [x] Load the seven source files with `read_text` and load expected_qubos.json as JSON.
  Never import the objective files or execute their decorators.
- [x] Call only health and compiler analyze endpoints. Do not call benchmark,
  optimization, materials, or search: those could execute jobs after other owners merge.
- [x] Validate supported status, QUBO contents, circuit width, executed=false, and depth=null.
- [x] Include a harmless unsupported source and require rejected status, diagnostics,
  qubo=null, and circuit=null.
- [x] Print a concise per-case pass/fail summary and return a nonzero process exit
  status on connection failure, timeout, wrong status, malformed response, or mismatch.
- [x] Report useful field differences rather than silently accepting a partial match.
- [x] Distinguish API readiness from experiment readiness. experiments_ready=false
  currently does not mean analysis is unavailable.
- [x] Keep the tool free of mock success measurements, benchmark timings, and source imports.
- [x] Refuse redirects, including one targeting benchmark, and bound response size.

### Focused tests

31 controlled-transport cases cover success, wrong coefficients, malformed responses,
preview labeling/width/layers, signed zeros, connection errors/timeouts, HTTP errors,
fixture/CLI failures, redirect rejection, and refusal of execution routes. Real HTTP
checks separately passed all nine cases. After the real API was stopped, the command
returned code 1 and submitted no source cases. See the manual validation record.

**Completed:** one command checks the seven examples and a rejection case on the
running local API, fails visibly when the backend is stopped, and submits no jobs.

## 6. P1: preserve the completed compiler handoff-test coverage

The current suite already covers extraction, source scopes, loops, squares, analytical
cost phases, mocked comparisons, large offsets, invalid solver results, and persistent
input mutation. Read the existing tests before adding cases that repeat them.

The identified error-path gaps are now covered. Add further cases only for a concrete
regression or integration need:

| Behavior | Test location | Coverage |
| --- | --- | --- |
| Classical runner raises TimeoutError | `backend/tests/compiler/test_pipeline.py` | Implemented: 504 and QAOA never called |
| A runner changes its copy and then raises | Same file | Implemented for both runners: original QUBO/config preserved, sanitized 504 |
| Source analysis fails before handoff | Same file | Existing tests: no runner called; UI preservation checked separately |
| A new real objective regression | `test_examples.py` or a focused new case | Add when needed, with independent expected values |

Keep the code change as narrow as the observed failure. The compiler should continue to:

- Revalidate source on every benchmark request.
- Give each runner an independent copy of the same mathematical instance/configuration.
- Retain original canonical QUBO, seed, settings, and stable problem ID for provenance.
- Check assignment width/order and objective consistency with absolute tolerance 1e-9.
- Reject a claimed exact optimum above a valid QAOA result, beyond the declared tolerance.
- Return sanitized errors without inventing measurements or leaking exception internals.

Do not fix an integration failure by weakening degree/scope validation, relaxing the
objective tolerance, dropping constant offsets, or changing bit order silently.

**Done when:** any new boundary regression has a focused test and the current
compiler test suite remains completely independent of actual solver execution.

## 7. P1: have Developer 5 review the implemented compiler page

Use [DEVELOPER_5_HANDOFF.md](DEVELOPER_5_HANDOFF.md). File loading, coefficient tables,
line-linked diagnostics, stale-result guards, and the symbolic gate table are already
implemented. Review these rather than planning to build them again.

Your part is to provide reliable examples and confirm the mathematical presentation:

- [ ] File-loaded content is the source actually submitted for analysis.
- [ ] HTTP 200 rejected analyses have actionable diagnostics and no stale success panels.
- [ ] Changing source invalidates prior analysis and comparison eligibility.
- [ ] Failed or late file reads preserve newer user edits.
- [ ] Canonical solver sense and original maximization sense remain distinguishable.
- [ ] The displayed preview is explicitly unexecuted; its depth is logical, not transpiled.
- [ ] The page explains that Analyze uses one preview layer. If later comparison
  controls allow a different p, the UI must not imply that the old preview matches that run.
- [ ] Missing shared runners remain a clear unavailable state, not a fake result.

Developer 5 owns optional graphical circuit diagrams, richer editor controls, browser
regression infrastructure, and benchmark charts. A gate table is sufficient for the
current compiler milestone. No new runtime dependency is required just to make the
mathematical result inspectable.

If the team adds browser tests, preserve the real cases in the manual validation record:
file loading, diagnostic line selection, maximization, oversized input, stale API
responses, stale file reads, and a narrow viewport. The earlier temporary browser
harness is not a committed CI suite; agree on that test stack before adding packages.

**Done when:** the frontend owner has reviewed the implemented page and any remaining
UI work has a concrete owner and acceptance criterion.

## 8. P2: integrate Developer 3's implementations without losing the safe default

This work starts when the shared implementations are available. It is a dependency,
not missing compiler parsing functionality.

### Review before connecting

- [ ] Inspect the actual shared API and result types against the handoff.
- [ ] Confirm use of the shared gate plan and evaluator rather than a duplicate engine.
- [ ] Confirm that original inputs survive both success and failure unchanged.
- [ ] Confirm method, version, seed, p, shots, optimizer budget, and stop behavior.
- [ ] Confirm real transpiled depth is reported in benchmark metrics; preview logical
  depth is never substituted as a measurement.
- [ ] Confirm timeout enforcement covers native work, not only a timer after a blocking call.
- [ ] Agree which commands/tests may invoke real execution and how opt-in is enforced.

Do not add an execution flag to requests, change readiness models, or alter shared
schemas unilaterally. Record the chosen design with Developers 3 and 5 and regenerate
frontend types if the wire contract changes. No such new field exists today.

### Keep tests separated

- Compiler unit/integration tests should continue patching both runner boundaries.
- Developer 3 should replace their stub-assertion tests when implementing those stubs.
  Do not invoke new runners simply to preserve an old NotImplementedError test.
- Coordinate any registration/selection of opt-in quantum integration tests before
  modifying the shared pytest defaults, because they affect every backend owner.
- After other experiment implementations land, inspect the complete pytest suite
  before running it under a mocks-only restriction. Focused compiler checks remain
  the safe default if other owners' execution behavior has not been reviewed.

**Done when:** the shared implementations can satisfy the compiler's contracts,
mocked compiler checks still pass, and actual-execution checks are explicitly
identified and kept out of routine mocks-only runs.

## 9. P2: verify a tiny local comparison only when explicitly authorized

This phase is not authorized by the current instruction. Prepare its cases and test
plan now; do not run them yet. The initial tiny acceptance instances should use a
local machine rather than the reserved supercomputer allocation.

After authorization and the shared implementation are available:

1. Use a tiny reproducible instance with independently known values. The exactly-one
   example provides a known optimum and asymmetric API assignment `001`.
2. Check the actual assembled cost unitary against exp(-i gamma C), including the
   constant/global phase. Analytical formula tests do not prove Qiskit assembly.
3. Check qubit/classical-bit wiring and conversion of count strings to x[0]-first order.
4. Check that actual classical exact results agree with the known optimum.
5. Recompute each returned assignment's objective using the shared evaluator.
6. Record seed, p, shots, optimizer settings/evaluations, versions, method, timing
   flags/components, transpiled depth, assignment, objective, and canonical gap.
7. Exercise deadline failure and require a structured error without a completed result.
8. Confirm the browser presents actual backend results with simulator labeling and
   unavailable metrics left null.

QAOA is stochastic and may return a suboptimal assignment for a finite budget. Require
valid assignments, matching objectives, correct provenance, and fair quality reporting;
do not make a general test assume it always finds the exact optimum.

Use [BENCHMARK_METHODOLOGY.md](BENCHMARK_METHODOLOGY.md). Separate source analysis and
common boundary work from both solver intervals as documented. Record actual results
separately from synthetic fixtures, and do not claim quantum advantage from simulator
runtime, gate counts, or mocked outputs. Hardware/supercomputer use remains separately
authorized, even if a future local simulator test is approved.

**Done when:** a small authorized real comparison has a reproducible correctness
record with genuine provenance, and error/timeout paths remain honest.

## 10. P3: extend Python support only when an intended input needs it

Keep unsupported constructs as explicit diagnostics until there is a concrete case.
The MVP is a restricted binary-objective compiler, not arbitrary Python execution.

For each proposed language feature:

- [ ] Save a minimal input currently rejected and explain the objective it should mean.
- [ ] Specify accepted syntax, scope, numeric semantics, and resource bounds first.
- [ ] Identify the expected QUBO and independent assignment checks.
- [ ] Update validation/lowering and the independent source interpreter together.
- [ ] Test before-definition reads, shadowing, unused forbidden syntax, nonfinite
  intermediates, degree limits, and expansion limits relevant to the feature.
- [ ] Preserve source/QUBO equivalence on every binary input for the supported width.
- [ ] Update COMPILER.md and examples without changing shared conventions silently.
- [ ] Keep one feature per reviewable change.

Possible candidates, if a real objective needs them, include immutable numeric module
constants, additional compile-time integer forms, or empty-range semantics with full
validation. None is a required next feature or implemented promise. Imports, arbitrary
helper calls, data-dependent loops, larger variable counts, and general quadratization
are separate scope decisions; do not bundle them into integration work.

## 11. Files and checks to use for your next change

| Task | Primary files |
| --- | --- |
| Source semantics and numerical verification | `backend/app/compiler/analysis.py` |
| Bounded statements/loop lowering | `backend/app/compiler/lowering.py` |
| Shared result checks and provenance | `backend/app/compiler/pipeline.py` |
| HTTP mapping | `backend/app/api/compiler.py` |
| Regression cases | `backend/tests/compiler/` and `examples/compiler/` |
| Solver interface expectations | `docs/DEVELOPER_3_HANDOFF.md` |
| Frontend behavior review | `docs/DEVELOPER_5_HANDOFF.md` |
| Real check evidence | `docs/COMPILER_MANUAL_CHECKS.md` |

For the current mocks-only code, from `backend/`:

```sh
.venv/bin/pytest tests/compiler
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/ruff check ../examples/compiler
.venv/bin/ruff format --check ../examples/compiler
```

The full-suite command above is appropriate for the inspected code at this checkpoint;
reassess it after real execution tests are added. Equivalent `uv run --locked ...`
commands work when uv is installed. Existing compiler checks need no quantum extras.
The API test client previously stalled inside the restricted sandbox and passed outside
it; investigate that environment issue separately from an application regression.

From `frontend/` when affected:

```sh
npm run test:compiler
npm run types:check
npm run typecheck
npm run build
```

After a coordinated wire-contract change, first run `npm run types:generate` and
review its diff. Do not edit generated TypeScript manually.

For each finished change, run `git diff --check`, review tracked and untracked files,
commit only the intended paths on Connor, and push without force. Give the reviewer
the concrete behavior change, relevant checks, and any remaining dependency. Preserve
Project_Spec.md, existing API conventions, and other owners' modules.

## 12. Completion criteria for your track

### Ready now: source-analysis testing

- [x] Supported source becomes a verified normalized QUBO and unexecuted gate plan.
- [x] Local file input and readable browser output are implemented and checked.
- [x] Reproducible examples, diagnostics, numerical checks, and mocked handoffs exist.
- [ ] Your intended objective has been tried and its result or exact unsupported form recorded.
- [x] The analysis-only smoke command is implemented and reproducible.
- [x] Full-file text input can generate/download Python with an explicit circuit-factory replacement.
- [ ] Developers 3 and 5 have received/reviewed their respective handoffs.

### Ready later: full compiler benchmark acceptance

- [ ] Developer 3's classical and QAOA implementations satisfy the selected contracts.
- [ ] Routine compiler tests remain mocked; real execution is separately identified/opt-in.
- [ ] Explicit authorization for the local execution phase has been provided.
- [ ] Actual circuit assembly, counts, objective quality, provenance, and timeouts are verified.
- [ ] A user can submit a supported 3–6-bit objective and view a reproducible, honestly
  labeled comparison in the frontend.

Until the later criteria are met, the accurate status is: **the Developer 2 source
compiler and symbolic preview are ready; live solver comparison awaits the shared
implementation and separate execution authorization.**
