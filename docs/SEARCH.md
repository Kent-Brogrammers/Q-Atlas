# Developer 4: Grover search benchmark

The benchmark compares a measured Grover circuit with classical search in the
existing shared result format. `POST /api/search/run` now exposes the bounded runner.
Shared model fields are unchanged; generated frontend types document the route's
503/504 errors. The Search page is not connected yet.

## Windows setup

Open the repository root in VS Code and select branch `Layth`. The initial setup
installed project-local uv at `backend/.cache/tools/uv.exe`, Python 3.12 under
`backend/.python/`, and dependencies in `backend/.venv/`. These folders are ignored
by Git. No global Python installation, IBM account, or credentials are needed.

For VS Code's Python interpreter, select `backend/.venv/Scripts/python.exe`.
From a PowerShell terminal at the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.experiments.search
.\.venv\Scripts\python.exe -m app.experiments.search.demo
.\.venv\Scripts\python.exe -m pytest tests/search tests/quantum
.\.venv\Scripts\ruff.exe check app/experiments/search tests/search
.\.venv\Scripts\ruff.exe format --check app/experiments/search tests/search
```

On another machine with uv installed, reproduce the locked environment from the
repository root using `uv sync --project backend --locked --all-extras --python 3.12`.
The local download of uv is a convenience, not a committed project dependency.

## Circuit and interpretation

`build_grover_circuit(marked_state, iterations, measure=True)` accepts one target
string or a list of unique targets of the same width, 1–6 qubits, and 0–32 iterations.
These are local circuit-helper limits; the existing
API request schema is unchanged. The oracle uses X gates for target zero bits and
a multi-controlled phase flip. Diffusion reflects about the uniform state, up to
global phase. Each Grover step makes one oracle call per circuit execution.

Displayed strings follow the team's convention: character i is qubit i, left to
right. Qiskit measurement strings list the highest classical bit first, so the
demo reverses them before reporting counts. Leading zeros are preserved.

The demo uses target `101`, two iterations, 1024 shots, and seed 42. It prints
measured counts and success probability alongside ideal theory:

`P(k) = sin²((2k + 1) asin(1 / sqrt(N)))`, with `N = 2^num_qubits`.

The ideal probability is 0.9453125 for this example; measured values fluctuate.
Recorded wall time includes circuit/oracle construction, backend initialization,
transpilation, sampling, and count conversion, but excludes imports and printing.
Depth is measured after transpilation to Aer, not to a physical device's gates.
Shots are repeated circuit executions; k oracle calls refers to one execution,
not the entire sampling batch. This is an ideal simulator, not a hardware run.

The application already knows the target to construct the oracle. Query complexity
assumes oracle access; constructing an explicitly marked circuit is not free, and
this experiment cannot establish practical quantum speedup.

## Classical baseline


`app.experiments.search.classical.run_classical_search` accepts the shared
`SearchRequest`. It checks candidate strings in lexicographic order without
replacement and stops at the first marked state. Input order does not influence
checking order. Leading zeros and the shared qubit-0-first display are preserved.
One set-membership predicate counts as one query; marked-set construction is
included in wall time, rather than counted as an oracle query.

The returned observed query count belongs to that fixed instance. Separately,
`(N + 1) / (M + 1)` is the expected number of checks under uniformly distributed
marked positions, and `N - M + 1` is the worst case, for N candidates and M targets.
These quantities assume stopping at the first success, without replacement. They
must not be labeled as measured runtimes or equated to quantum gate costs.

The baseline checks its deadline before queries and before returning results.
Tests enumerate all target placements in a four-candidate space to verify the
expected and worst-case formulas, in addition to fixed-instance and timeout tests.

## Benchmark runner

`app.experiments.search.runner.run_search(request)` returns the shared `SearchResult`.
It accepts 1–6 qubits, one or more unique marked states, 0–32 iterations, and at most
10000 shots. Unsupported sizes produce a `ValueError` before creating a process;
`request_diagnostics` supplies structured diagnostics for the later API layer.
The broader shared schema remains unchanged; those fields are not a promise that
every schema-valid resource size is supported by this implementation.

With `iterations=None`, the runner selects the better nonnegative integer adjacent
to the first ideal amplification peak, choosing fewer iterations on ties. For
multiple targets, `theta = asin(sqrt(M / N))` in the probability formula above.
The result's `metadata.parameters.iterations` records the effective choice. The
caller request is not mutated, and target list order does not change the circuit
or the stable problem ID.

The runner performs both searches in a disposable spawned process. Its wall-clock
budget includes process startup, imports, both solvers, and receiving/validating
the result. On timeout it terminates and reaps the worker, including native Aer
work. Missing quantum packages produce `SearchDependencyError`; other worker
failures produce `RuntimeError`. No quantum packages are imported by the boundary
module itself, preserving API-only startup for the next integration milestone.

Per-solver `elapsed_ms` excludes worker startup, imports, result-envelope assembly,
serialization, and HTTP. The classical timer includes target-set preparation,
candidate enumeration and extraction. The quantum timer includes all circuit and
oracle construction, backend creation, transpilation, sampling, and count extraction.
Measured transpilation and sampling durations are subintervals of the quantum timer.
Timings describe one cold solver invocation after imports, with no warm-up run.
Record these scopes when comparing runtimes; the timeout budget and reported solver
durations intentionally have different boundaries.

`quantum_oracle_queries` is the iteration count **per shot**. Total calls across
the batch equal `iterations * shots`, recorded in `oracle_assumptions`. The combined
oracle applies a phase flip for every supplied target; a query is not a single gate.
`classical_expected_queries` and `classical_worst_case_queries` retain the assumptions
above. The observed classical check count is recorded in `oracle_assumptions` because
the shared metrics currently have no dedicated field for it. Objectives remain null.

Quantum `best_bitstring` is the most frequent observed bitstring, with lexicographic
tie-breaking; it may be unmarked. Success probability counts **all** marked outcomes
without postselection. Neither raw counts nor a probability sweep is currently part
of the shared response. Seeded measurements reproduce within the same installed
package versions, which are included in metadata; timings naturally fluctuate.

Run the new benchmark with `python -m app.experiments.search` from `backend/`.
The earlier `.demo` command remains a simple single-target circuit demonstration.

## Remaining milestones

Add the iteration sweep and connect real results on the Search page with Developer 5.

## Search API

Start the backend from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs`, expand `POST /api/search/run`, and use **Try it out**.
For a PowerShell request in a second terminal:

```powershell
$searchBody = @{
    num_qubits = 3
    marked_states = @('001')
    iterations = 2
    config = @{ shots = 1024; seed = 42; timeout_seconds = 30 }
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/search/run' `
    -ContentType 'application/json' -Body $searchBody | ConvertTo-Json -Depth 10
```

Requests use the existing `SearchRequest`. Omit `iterations` or send null for
automatic selection. HTTP 200 returns a validated `SearchResult`; failure responses
contain only the shared error envelope, never fabricated solver measurements:

| HTTP status | Code | Meaning |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | Malformed inputs or unsupported resource limits |
| 503 | `HTTP_ERROR` | Install the optional backend quantum dependencies |
| 504 | `TIMEOUT` | Total worker runtime budget exhausted; worker is stopped |
| 500 | `INTERNAL_ERROR` | Unexpected failure, with sanitized public details |

Resource diagnostics are checked before a worker starts. Exceptions never expose
internal details in public responses. API startup still works without Qiskit/Aer;
execution requires the quantum extra. A failed request does not fall back to examples.

The API tests cover real single/multiple-target runs, malformed and unsupported
requests, worker timeouts, dependency errors, sanitized failures, and dependency-free
startup. Shared availability tests no longer classify search as a stub. The stale
compiler-stub assertions in the materials test were removed because the compiler has
its own implemented API tests.

### Refreshing API types on Windows

The existing `npm run types:export` command uses `.venv/bin/python` (Unix layout).
From `frontend/`, use the same exporter/generator with the Windows interpreter:

```powershell
..\backend\.venv\Scripts\python.exe ..\backend\scripts\export_openapi.py |
    Set-Content -Encoding utf8 openapi.json
npm.cmd run generate --workspace @q-atlas/api-types
npm.cmd run generate --workspace @q-atlas/api-types -- --check
```

`openapi.json` is ignored intermediate output. Commit the generated TypeScript when
the documented operation changes. No new dependency or transport client is required.

The four follow-up commit groups are classical baseline, benchmark runner, API,
then probability curves/frontend integration. Review and approval precede each commit.
