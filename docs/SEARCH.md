# Developer 4: Grover search benchmark

The benchmark compares a measured Grover circuit with classical search in the
existing shared result format. `POST /api/search/run` now exposes the bounded runner.
Shared model fields are unchanged; generated frontend types document the route's
503/504 errors. The Search page now calls this API for live comparisons and curves.

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
above. The observed classical check count is also exposed as `classical_observed_queries`.
Objectives remain null.

Quantum `best_bitstring` is the most frequent observed bitstring, with lexicographic
tie-breaking; it may be unmarked. Success probability counts **all** marked outcomes
without postselection. Neither raw counts nor a probability sweep is currently part
of the shared response. Seeded measurements reproduce within the same installed
package versions, which are included in metadata; timings naturally fluctuate.

Run the new benchmark with `python -m app.experiments.search` from `backend/`.
The earlier `.demo` command remains a simple single-target circuit demonstration.

## Structured evidence fields

Three optional nullable fields in `SearchMetrics` expose the evidence directly:

| Field | Meaning |
| --- | --- |
| `successful_shots` | Number of sampled outcomes in the marked set, counting all marked targets |
| `classical_observed_queries` | Predicate checks actually made before the first match for this fixed instance |
| `quantum_total_oracle_queries` | Algorithmic combined-oracle calls across the batch: iterations × shots |

`successful_shots / shots` equals `success_probability`. The total quantum query
count is derived from the executed circuit protocol, not measured CPU operations,
primitive gates, or QPU work. The per-shot `quantum_oracle_queries` field retains
its original meaning. No count is encoded as an optimization objective.

The comparison table displays these fields separately from expected/worst-case
classical query counts and measured wall time. They are included in JSON downloads
without parsing the explanation text. Older responses remain valid without the new
fields and display **Not available**, rather than fabricated or inferred evidence.
Zero successful shots and zero quantum queries remain valid measured/protocol values.

Validation rejects noninteger/negative counts, successful shots above the shot count,
probabilities inconsistent with successful shots, total queries inconsistent with
per-shot queries, and observed classical checks exceeding the stated space/worst case.
Optional totals require their denominator or per-shot fields when provided. Shared
model changes are additive; request limits, bit order, and timing scopes are unchanged.

## Live Search page and probability curves

Start the backend as shown below, then in a second terminal at the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://127.0.0.1:5173/search/` or select **Grover Search** in navigation.
The overview also links to the page. Nothing runs automatically on page load.

- **Run comparison** sends one existing `SearchRequest`, with optional automatic
  iteration selection. The backend reports the effective iteration count.
- **Run repeated trials** measures the same single-run configuration two to five
  times using distinct recorded seeds. See the statistics section below.
- **Measure probability curve** sends iterations 0 through the chosen last value
  (0–12 inclusive), sequentially, overriding the manual single-run iteration setting.
  Points share the targets, shots, seed and per-point timeout. Every probability,
  including theory, comes from an API response. No new sweep endpoint is needed.
- Progress reports completed points. Configuration is disabled while running.
  Editing inputs clears old results; failed/stopped sweeps publish no partial curve.
  **Stop requests** aborts browser transport and prevents subsequent points; an
  in-flight backend worker can continue until it finishes or reaches its timeout.
- The plot and accessible table distinguish measured frequencies from ideal theory.
  Lines join integer samples. Missing values stay unavailable; zero remains zero.
  Select a table row to inspect an iteration's query and runtime comparison.
- **Download measured JSON** exports every completed response with recorded settings,
  versions, timings and oracle assumptions, marked with source `live_search_api`.
  No measurement files or synthetic fixtures are bundled as application defaults.

A curve sweep is one run per iteration, not repeated trials at one iteration. Its points
share a seed; no independent-run distribution or confidence interval is claimed.
The 13-request cap and per-request timeout bound work, but the sequence can take up
to 13 per-point budgets plus transport overhead. Quantum time includes a shot batch;
classical time measures one search. Their ratio is not a matched-success speedup.

## Repeated-run statistics

Choose **Repeated trials** (2–5, default 3) and select **Run repeated trials**. This
mode uses the single-run iteration setting, including backend automatic selection;
it does not repeat the entire iteration curve. No new backend endpoint, dependency,
or shared aggregate schema is introduced.

The browser sends requests sequentially with seeds `(base_seed + trial_index) mod
2^32`. Every request retains the same problem, shots, and manual/automatic iteration
setting. The completed backend results must agree on effective iteration, instance,
shot count, simulator method, timing scope, and package versions. Their seeds must
match the requested seeds and be distinct. A mismatch or failure prevents publication
of a partial batch. Cancellation stops subsequent requests; the current native worker
can finish or reach its per-request deadline, as in curve mode.

The summary reports:

- Arithmetic mean of observed success probabilities across equal-shot trials.
- Observed minimum and maximum success probabilities, also shown as a chart whisker.
- Sample standard deviation: `sqrt(sum((p_i - mean)^2) / (r - 1))`, displayed in
  percentage points (pp). This describes variability of the run probabilities, not
  a standard error or confidence interval.
- Median classical and quantum solver times, retaining all trials and excluding no
  warm-up run. Even-sized medians average the two middle values. Solver timing scopes
  remain as documented above; worker startup is outside reported solver durations.
- Trial count, distinct seeds, shots per trial, and total shots across the batch.

Missing timings make the corresponding median unavailable rather than averaging a
subset. Missing probabilities or invalid/mismatched records prevent aggregation.
If theoretical probabilities are unavailable, the summary does not fabricate them.
The range and sample deviation are descriptive statistics over a small set of seeded
simulator runs; neither bounds the true probability or establishes runtime advantage.

The trial table lists every seed and measured probability and lets you inspect each
raw response. Each raw record still has `metadata.repetitions=1`; the browser summary
does not rewrite those records to imply backend aggregation. Editing controls clears
the summary and all old results. The workload is capped at five requests and 50000
shots, and can consume up to five per-request budgets plus transport overhead.

JSON downloads now include `mode` (`single`, `curve`, or `trials`), `trial_summary`
(null outside trials), and the unchanged `results` array. The source remains
`live_search_api`. The summary is a presentation/export object, not a `SearchResult`.
It records the actual seeds, probabilities, sample deviation, medians, and shot counts;
all raw evidence is retained for independent review.

Manual verification used the default three-qubit `001` configuration and seeds
42, 43, 44, then verified the summary and three raw records in the downloaded JSON.
Unit tests cover known statistics, odd/even medians, zeros, missing evidence,
mismatched metadata, sequential limits, wraparound seeds, failures and cancellation.

### Demo rehearsal

1. Use three qubits, target `001`, 1024 shots and seed 42.
2. Run a comparison: automatic selection uses two iterations. Compare the recorded
   success rate with ideal theory (0.9453125); measured values can vary by version.
3. Measure iterations 0 through 6. Point out the drop after the first amplification
   peak and later oscillation; more iterations are not always better.
4. Select iteration 4 to inspect low success. Compare per-shot oracle calls against
   classical expected/worst-case checks separately from measured wall time.
5. Download JSON and inspect seven result records. Change targets to `001, 110` and
   run a single comparison to demonstrate multiple targets.
6. Enter an invalid target to verify clear errors and removal of stale measurements.

Manual browser verification covered a real seven-point curve, a two-target run,
invalid-input handling and a seven-record JSON export. Frontend tests cover request
validation, sequential limits, cancellation, failures, response metadata, zero/missing
probabilities and typed transport. Svelte checks cover accessibility/compiler diagnostics.
Configuration/results stack on narrow screens and sit side by side on desktop.

Core search MVP, typed evidence fields, and bounded repeated-run statistics are implemented.
Demo/regression hardening is also implemented as described below. Coordinate further
shared-schema changes with Developers 3/5. Hardware and practical quantum advantage
are not claimed.

## Demo preparation and regression checks

From `backend/`, with the quantum extra installed, run:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_search_demo.py
.\.venv\Scripts\python.exe scripts/prepare_search_demo.py --verify
```

The first command exercises the actual FastAPI endpoint in-process through TestClient;
no HTTP server, external network, IBM credentials or hardware is required. It records
seven curve points and three trials, probes one/multiple targets and boundary sizes
(including 6 qubits / 32 iterations), and checks validation and timeout errors.
Only after all checks pass does it write
`frontend/src/lib/search/previously-measured.json`. `--output PATH` selects another
destination. The second command validates the saved evidence without running simulation.
If committing a regenerated recording, run
`npx.cmd prettier --write src/lib/search/previously-measured.json` from `frontend/`
after recording. Formatting changes no measurements or provenance values.

The recording identifies its timestamp, source revision, dirty working-tree flag,
SHA-256 hashes of the relevant source files, Python/OS, and per-result package versions.
Hashes describe the source bytes on the recording machine; line endings can differ on
other checkouts. A recording from a dirty tree is disclosed in the banner and export.
These checks establish format/evidence consistency, not that old timings apply to
the current machine. Regenerate intentionally before a rehearsal; recordings do not
refresh during page load or silently replace a failed experiment.

### Explicit offline fallback

The page's **Load recorded curve** and **Load recorded trials** buttons require an
explicit action and make no API requests. They load real previously measured records,
restore the matching configuration, and show a prominent **Previously measured demo —
not a live run** banner, timestamp and revision. Editing inputs clears the recording
and its provenance. Live runs always clear recorded data first. No error handler loads
a recording automatically.

Recorded downloads use source `previously_measured_search_demo`, include the recording
provenance and raw results, and use filename `q-atlas-search-recorded-demo.json`.
Live downloads retain source `live_search_api` and filename `q-atlas-search-results.json`.
The same export builder handles reactive page state through JSON serialization;
regression tests cover proxies as well as plain records.

### Browser rehearsal checklist

| Check | Expected behavior |
| --- | --- |
| Initial page | Empty charts; no auto-loaded measurements |
| Run comparison | Real probabilities, timings and evidence fields |
| Measure curve 0–6 | Seven results with the expected amplification oscillation |
| Run 3 trials | Seeds 42, 43, 44; summary plus each raw run |
| Stop an active curve | No partial result is published; controls become usable |
| Run again after stopping | A fresh comparison succeeds without stale responses |
| Edit controls | Previous results, summaries and recorded provenance disappear |
| Invalid target | Clear validation error; no fabricated result |
| Backend unavailable | Connection error and empty results; no automatic fallback |
| Explicit recorded load | Dated banner and matching configuration, even without API |
| Download live/recorded | Correct source label, raw records and provenance where applicable |

Manual browser checks confirmed cancellation/recovery, connection failure without
fallback, explicit recorded loading while disconnected, clearing on edits, restoring
the saved configuration, and downloading a seven-record file with recorded provenance.
Unit/API tests cover both supported modes and malformed evidence. No additional
browser automation package is required for the checklist.

The repository also has two pre-existing Windows-incompatible QAOA timeout tests in
Developer 3's module; their `ctypes.CDLL(None).sleep` helper fails on Windows. Report
those separately from search checks and coordinate their repair with Developer 3.

## Search API usage

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

## Configurable repeated benchmarks

### Circuit gate resources

Live search results include `metrics.circuit_gate_counts`: a sorted histogram of
gate names from the actual Aer-transpiled circuit used for execution. The selected
result panel shows the sum as **Gates per transpiled circuit** and the histogram as
**Gate breakdown**, alongside the existing transpiled depth. API and sweep JSON
retain this histogram for each measured run.

These counts cover one circuit, independent of shots. They count top-level Qiskit
`Gate` instances, excluding measurement, reset, barriers and other non-gate
instructions. A retained multi-controlled or composite gate counts once; no extra
hardware-basis transpilation is performed to produce this metric. Counts depend on
the simulator's supported operations, transpiler settings, seed and package versions.
They do not represent native hardware costs, internal Aer execution operations, or
the shot-batch query count. Older recorded demos lack this measurement and show
“Not available”; they are not silently remeasured or assigned estimated counts.

See [Qiskit circuit data and operations](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.QuantumCircuit).

### Sampling intervals in the dashboard

Single-run and curve results show pointwise **95% Wilson score intervals** from
the integer successful-shot and total-shot counts. The chart uses dashed whiskers;
the results table provides numerical bounds for each run, including recorded demos.
Intervals remain nonzero in width for zero or all successful shots. Older records
without counts show “Not available”; probabilities are never rounded into counts.

These approximate intervals assume independent Bernoulli shots at a fixed success
probability and describe sampling uncertainty. Nominal 95% coverage describes the
interval procedure under repeated sampling, rather than a probability that the
fixed parameter lies in a particular observed interval. They do not quantify model
error or device noise and are not a simultaneous confidence band over a curve.
The repeated-trial chart retains its descriptive min/max range; the individual
trial rows show their own sampling intervals, with no pooled interval for the mean.
Measured JSON exports retain raw counts so the intervals can be recomputed.
Method: [NIST Wilson confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm),
two-sided, z = 1.959963984540054, without continuity correction.

### Command-line batches

The fixed demo recorder remains unchanged. For a custom local batch, run the
search sweep from `backend/` in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.experiments.search.sweep `
  --num-qubits 3 --marked-states 001 110 `
  --iterations 0 1 2 3 4 --shots 256 1024 --seeds 42 43 44 `
  --timeout 30 --total-timeout 300 --output "$env:TEMP\search-sweep.json"
```

Use a new output filename each time. The parent directory must already exist;
an existing file or symlink is never replaced. This example executes 30 runs:
five iteration counts × two shot counts × three seeds. Targets are supplied
together as one marked set, rather than as separate search instances. To compare
different marked sets, run separate commands with different output filenames.

The JSON contains the complete plan, raw shared `SearchResult` records, UTC
recording time, source revision/dirty status, source-file hashes, Python/OS and
per-run package versions. Summaries group runs by iteration and shots and report
mean/minimum/maximum success probability, sample standard deviation (null for a
single seed), theoretical probability, and median classical/quantum solver time.
Ranges and standard deviations describe these seeded observations; they are not
confidence intervals. Seeds are reused between groups, so groups are not
independent replicate samples. Seeded probabilities should reproduce in the same
environment; measured runtimes need not.

Limits: 1–6 qubits, 0–32 iterations, 1–10000 shots, up to 16 distinct seeds,
eight shot counts, and 256 total runs. Every grid axis must contain unique values.
The default grid is iterations 0–6, shots 256/1024, seeds 42/43/44 (42 runs).
The total budget defaults to 300 seconds and is capped at 3600; each run defaults
to 30 seconds (maximum 60), reduced to the remaining suite budget when necessary.
Worker startup is included in those deadlines. Suite elapsed time includes runner
overhead and summary computation, excludes initial provenance collection and file
serialization; solver timing definitions remain in each raw result.

On validation, dependency, timeout or execution failure the command exits with
status 1 and publishes no report. It does not replace the frontend's recorded
demo, change API contracts, contact IBM, or submit hardware jobs. These are local
Aer measurements; query counts and simulator runtime remain separate comparisons.
