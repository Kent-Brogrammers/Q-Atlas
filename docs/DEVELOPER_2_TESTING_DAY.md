# Developer 2: preparation for the single quantum testing day

Updated 2026-11-10. This is the current operational checklist; it supersedes the
historical next-steps plan. Preserve `Project_Spec.md` as the architectural authority.

## 1. What is ready, and what still prevents a hardware test

The compiler accepts a Python file as text, locates one marked binary objective,
validates its supported AST, extracts a canonical QUBO, checks all binary assignments
for 1–6 inputs, and produces a symbolic circuit and generated Python artifact.
Ordinary surrounding Python is preserved, not validated as a safe runnable program.
One `@qatlas.objective` marker is sufficient. A circuit marker is optional.

The active UI is Svelte at `/compiler/`. It supports file upload, examples, editing,
conversion, line-linked diagnostics, generated downloads, and nonexecuting comparison
plans. It uses the shared panels and navigation. The older React tree is a reference.

| Component | Current status | Next owner/action |
| --- | --- | --- |
| AST, bounded lowering, QUBO equivalence, generation | Implemented and covered by compiler tests | D2: freeze representative objectives |
| Source/config hashes and comparison plan | Implemented, no execution | D2: export and review bundles |
| Offline bundle exporter | Implemented in this update | D2: run commands below |
| Shared exact classical baseline | Implemented on main | D3: retain correctness/deadline checks |
| Shared Qiskit circuit and Aer expectation scorer | Implemented on main; scorer performs simulation | D3: review and test only in an authorized execution phase |
| `app.quantum.qaoa.run_qaoa` | Still raises `NotImplementedError` | D3: optimizer, sampling, deadline, result assembly |
| Provider/QPU adapter | Not implemented or identified | D3 + allocation owner: identify service and limits |
| Hardware result contract | Not agreed; current backend is Aer-only and metadata simulated | D2/D3/D5: approve extension before implementation |
| Live compiler result UI | Execution disabled | D5/D2: wire only after agreed readiness and opt-in |
| Whole-script classical vs quantum runtime | Not implemented | Separate trusted harness and scope decision |

Do not describe the whole system as hardware-ready. Compiler preparation is ready;
the shared execution and provider paths remain explicit release blockers.

## 2. Main/PR audit for this update

Fetched and integrated main through `a1f413b` without discarding teammate changes:

- PR #6, `d4ed923`: classical solver and QAOA circuit construction.
- PR #7, `1719dc4`: live Neutrino backend and frontend.
- PR #8, `b94385e`: QAOA expectation scorer.
- PR #9, `a1f413b`: live Grover search and dashboard/navigation integration.

An open-PR query against base `main` returned no open PRs at this audit. This is a
point-in-time result, not an assurance about future pushes. The connector search
returned no historical PRs, so git history and the GitHub CLI were used to verify.

The compiler link, homepage action, route, typed client, and shared panels remain
present. Neutrino and Search now have real simulation controls: browsing their pages
is distinct from pressing Run. Never use their Run controls during compiler-only QA.
No compiler HTTP/schema change was required by these merges. Generated frontend
types must still pass the drift check against the merged backend.

## 3. Decisions to resolve before booking any job

Record answers here or in a reviewed testing-day issue. Never include credential values.

| Decision | Required answer | Responsible person |
| --- | --- | --- |
| Provider | Actual QPU service/device or HPC simulator/scheduler | Allocation owner |
| Ten-minute limit | QPU usage, scheduler wall time, or full appointment length? | Allocation owner |
| Shared budget | Remaining allowance, other experiments' allocations, reserve | Team lead |
| Job ownership | One submitting operator and one observer | Team lead |
| Access | Backend machine/account permitted to submit; approved SDK version | D3/operator |
| Limits | Per-job cap, total cap, shots, retry policy, cancellation procedure | D3/operator |
| Test objective | Exact source revision, expected optimum, input order | D2 |
| Method | Full optimization on device, or separately trained angles plus final sampling | D3 |
| Evidence | Where job IDs, raw results, versions and usage are stored | D2/operator |

The ten-minute budget is shared and finite. Do not invent a conversion from shots
to seconds. Queue time, device execution time, and allocation accounting may differ.
Use the confirmed provider rules when choosing numeric caps. Reserve a meaningful
portion for recovery; agree the actual split with the other experiment owners.

## 4. D2 work to complete before testing day

### A. Freeze a small test corpus

Choose one primary 3-bit case and one backup. Keep the first experiment at one layer.
Use `examples/compiler/exactly_one.py` as a known reference: constant 10, linear
coefficients [-11, -12, -13], pair coefficients 20, exact minimum -3 at API bitstring
`001`. These are arithmetic expectations, not quantum measurements.

Also keep a maximization case and a deliberately rejected helper-call case for UI
demonstration. Rejected source must never reach a runner. Use the existing full-file
fixtures under `examples/compiler/programs/` to demonstrate preserved surrounding code.

For each selected case, record:

- Problem meaning, units, penalty weights, intended feasible selections.
- Function signature order, vector indices where applicable, original objective sense.
- Expected constant, linear/pair terms, independently checked assignments and optimum.
- Input/source hash, generated-source hash, canonical problem ID, repository commit.
- Supported/rejected outcome and diagnostic locations.

Keep variable counts and grammar frozen unless a chosen case exposes a real defect.
Unsupported arbitrary Python is not a reason to execute it to discover its meaning.

### B. Generate an offline evidence bundle

From the repository root, with the existing backend environment installed:

```sh
cd backend
.venv/bin/python -m scripts.prepare_compiler_day \
  ../examples/compiler/exactly_one.py \
  --output /tmp/q-atlas-exactly-one-preflight.zip --p 1 --shots 256 --seed 42
```

Shots and seed here are proposed configuration only. This command does not sample,
optimize, import the source, contact a provider, or use credentials. It validates
bounded UTF-8 input and refuses to overwrite an existing bundle. Choose a new output
name for each intentional revision. A rejected input exits nonzero without a bundle.

The ZIP contains fixed relative filenames:

| File | Meaning |
| --- | --- |
| `input.py` | Exact source text supplied for review |
| `generated.py` | Generated artifact, still unexecuted/untrusted text |
| `plan.json` | Existing typed plan: canonical QUBO, configuration, gate/parameter order, hashes, blockers |
| `manifest.json` | SHA-256 and byte length for payload files; compiler-preparation status and Python/Pydantic versions |
| `README.txt` | Execution boundary and bit-order notes |

The archive is deterministic for identical input/config/environment. Its manifest is
an integrity aid, not a signature or a provider readiness certificate. Retain its
SHA-256 and `git rev-parse HEAD` in the test record. The manifest intentionally contains
no measured performance, trained angles, hardware authorization, or credential data.
Do not treat an exported `generated.py` as a sandboxed application.

### C. Run the inspected, nonexecuting regression selection

```sh
cd backend
.venv/bin/pytest tests/compiler -q
.venv/bin/ruff check app/compiler scripts/prepare_compiler_day.py tests/compiler
.venv/bin/ruff format --check app/compiler scripts/prepare_compiler_day.py tests/compiler
```

The compiler suite uses symbolic/arithmetic checks and mocks at runner boundaries.
Do **not** reuse the old broad `tests/optimization` selection: main now includes
`test_qaoa_expectation.py`, which runs Aer. Full pytest also includes other owners'
simulator tests. Inspect changes to test selection before every future rehearsal.

```sh
cd frontend
npm run types:check
npm run typecheck
npm test
npm run test:compiler
npm run format:check
npm run build
```

For browser verification, launch `./dev.sh` from the repository root. On `/compiler/`:

1. Load the chosen .py file, convert it, and download the generated artifact.
2. Verify exact output contents and original caller/function names.
3. Open conversion details; check canonical coefficients and declared bit order.
4. Prepare and download a comparison plan; both execution flags must remain false.
5. Edit source while a response is pending; old results/downloads must not reappear.
6. Load a rejected example; select its diagnostic line and confirm no stale download.
7. Exercise the layout on desktop and 375px mobile width.
8. Navigate through the new Neutrino/Search pages without pressing Run, then return.

Compiler browser traffic should be confined to generation and plan endpoints (plus
static assets). No `/run` or `/compiler/benchmark` call belongs in this rehearsal.

## 5. Exact backend handoff to Developer 3

D2 continues to consume the shared runner; do not create a second QAOA engine.
Send this document and `DEVELOPER_3_HANDOFF.md` yourself before the execution freeze.

Required shared-runner completion:

- Implement `run_qaoa(qubo, config) -> QAOAResult` using the shared circuit/scorer.
- Honor explicit gamma/beta parameter order, including zero-coefficient cases.
- Convert measured bit ordering to canonical x[0]-first assignment order exactly once.
- Recompute objective including constant; preserve canonical minimization for maximization.
- Report actual shots, optimizer evaluations, transpiled depth and honest timing flags.
- Enforce deadline/cancellation during execution; a check after blocking work is insufficient.
- Keep input QUBO/config immutable. D2 passes independent copies and rejects mutation.
- Return schema-valid finite results. D2 now revalidates mutable nested solver models
  before accepting timings/metrics, then checks assignments, objectives and requested shots.
- Test timeout, invalid response, mutation and stochastic/suboptimal outcomes with mocks.

Current compiler benchmark metadata assumes Aer statevector execution. It cannot be
reused unchanged for a physical QPU. This is a **proposal for D3/D5 review**, not a
silently implemented shared API change: add a default-off server execution gate,
explicit provider readiness, durable job identity/status, QPU provenance and budget
accounting, plus cancellation and retry semantics. Extend schemas and regenerate
frontend types only after the owners agree the fields.

The existing compiler benchmark endpoint is an execution-capable integration entrypoint;
a disabled UI button is not a backend access-control mechanism. Do not expose it for
live use merely because a future `run_qaoa` implementation lands. Finish the agreed
server execution gate and deadline enforcement first. No enable flag is introduced
by the offline exporter.

## 6. Provider rehearsal gates

Complete these before the limited hardware appointment, under separate explicit
authorization for any actual local simulation or hardware access:

- [ ] Provider and allocation semantics recorded; account access checked by its owner.
- [ ] Shared runner complete; mocked failure and cancellation paths pass.
- [ ] Server execution gate and hardware-specific schema reviewed by D3/D5.
- [ ] Tiny circuit signs/global phase and measurement mapping checked on authorized local execution.
- [ ] Freeze angles if using local training plus device sampling; label training costs separately.
- [ ] Provider transpilation/ISA requirements, SDK version and device limits verified against current official docs.
- [ ] One conservative job configuration approved with explicit usage ceiling.
- [ ] No automatic retry on timeout, page refresh, disconnect, or unknown job status.
- [ ] Reconnection retrieves the existing job ID rather than submitting a duplicate.
- [ ] Cancellation tested with mocks; operator knows how to check remote job state.
- [ ] Fallback presentation works without a provider or network.

Provider-specific SDK calls cannot be finalized until the service is identified.
Use `QUANTUM_PRESENTATION.md` as context; recheck its provider links and dated quota
statements before acting. No provider-specific claim in that older document replaces
the allocation owner's actual limits.

## 7. Testing-day sequence

### Before the shared window

Freeze commits, environments, source/config bundles and expected arithmetic values.
Run offline checks, open the app, rehearse the click path, and verify local evidence
storage. Assign operator/observer roles. Close other experiment submission controls.
Agree go/no-go and reserve usage with the team; do not discover dependencies during
the allocated compute time.

### First authorized submission

1. Verify remaining allowance through the approved provider workflow.
2. Match source/problem/config hashes to the frozen case.
3. Confirm device, p, shots, parameter values, per-job limit and aggregate remaining cap.
4. Obtain explicit authorization for that job; record who approved it.
5. Submit once. Persist job ID immediately, before waiting for completion.
6. Poll/retrieve that ID. If disconnected, recover its status; do not resubmit blindly.
7. Save raw counts/results and actual provider usage before interpreting the outcome.
8. Validate width, measurement mapping, count totals and assignment objectives.
9. Compare against the shared classical reference for the same objective and instance.
10. Review remaining budget and correctness before approving any second job.

Stop for mismatched hashes, unverified bit mapping, invalid result shapes, missing
usage information, unknown job status, exceeded budget, or loss of cancellation control.
Do not spend the remaining allowance debugging basic compiler semantics on hardware.

## 8. Evidence record and fair comparisons

Create one record per authorized attempt, including failed/cancelled ones:

```text
Case / repository commit / bundle SHA-256:
Source SHA-256 / generated SHA-256 / canonical problem ID:
Original sense / canonical coefficients / variable order:
Operator / authorization / UTC timestamps:
Provider / device / backend type / SDK and package versions:
Job ID / status / recovery or cancellation action:
p / requested and actual shots / seed policy / parameter values and ordering:
Training method / training time / optimizer evaluation count:
Logical qubits / physical layout / classical-register mapping / transpiled depth:
Raw counts artifact / normalization and mapping checks:
Best assignment / recomputed canonical objective / original-sense value:
Exact classical assignment and objective / canonical optimality gap:
Queue / transpilation / optimizer / sampling / total wall intervals:
Provider-reported usage / cumulative usage / remaining allowance:
Validation outcome / limitations / next decision:
```

A finite-budget stochastic result may be suboptimal. Validate consistency, report the
gap, and retain failures. Never call mock output a measurement. Never call Aer on an
HPC node physical quantum execution. Whole-script runtime requires a separately reviewed
trusted harness; an objective function call is not a fair classical optimization baseline.

## 9. Fallback and completion criteria

Before any hardware run, fallback consists of static compilation, mathematical
verification, gate plans and downloadable generated code. After an authorized run,
saved results may be shown as **previously measured**, with device/date/job ID and
configuration visible. Do not silently replace missing live data with fixtures.

D2 is prepared when frozen cases and bundles exist, the compiler regression suite is
green, the current UI workflow passes, and D3/D5 acknowledge the execution handoff.
The team is hardware-ready only when all provider gates above are satisfied.
An implemented source compiler does not remove the shared runner/provider dependency.

## 10. Validation record for this update

- Compiler suite: **363 passed**, including offline archive integrity, no solver calls,
  rejected input, overwrite protection, and mutated-result validation regressions.
- Ruff lint and formatting checks passed for compiler modules, tests and the new CLI.
- Frontend generated-type drift, type checks, tests, formatting and production build passed.
- Firefox checked the merged frontend against a local API: named input upload, conversion,
  exact downloaded contents, planning, rejected diagnostics, stale responses and mobile layout.
  Only compiler generation/plan API endpoints were requested; no browser errors occurred.
- The documented exporter successfully produced an exactly-one bundle locally.
- The restricted-environment HTTP TestClient stalled; the same inspected compiler suite
  completed outside the sandbox in under a second. This was not a simulator test run.

These checks establish the offline preparation workflow. They do not establish actual
circuit execution, hardware access, speedup, or completion of the shared runner.
