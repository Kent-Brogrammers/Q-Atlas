# Benchmark methodology

This is the shared measurement agreement, not a performance results report.
The implemented materials comparison follows [its documented timing scopes](MATERIALS.md).
Developer 3 coordinates shared instrumentation with each experiment owner.

## Fair comparisons

1. Run classical and quantum methods on the same mathematical instance, constraints,
   objective sense, and observable. Record inputs and a stable `problem_id`.
2. Compare solvers with solvers. A single `cost(x)` evaluation is not a classical
   optimization baseline for an entire QAOA optimization loop.
3. Always include solution quality/validity with runtime. Include constant offsets in
   QUBO objectives. Keep minimization canonical; use `original_sense` only for display.
4. Use an exact baseline for tiny problems when feasible. If unavailable, label the
   heuristic and leave unknown optimum/gap fields null. Ratios on negative/zero optima
   can be misleading; report null unless the formula is meaningful and documented.
5. Distinguish theoretical query/gate complexity, simulator wall-clock time, and QPU
   wall-clock time. Simulator results are not evidence of hardware quantum advantage.

## Timing

Use a monotonic high-resolution wall clock (e.g. `time.perf_counter_ns`) and report
milliseconds. Do not mix CPU time and wall-clock time. Record warm-up policy, machine,
package versions, backend/method, effective parameters, seeds, shots, repetitions, and
optimizer stop criteria. Exclude HTTP/network rendering time from algorithm timings.

- `end_to_end`: the path from the validated mathematical instance through all needed
  preparation, circuit building, transpilation, optimization, sampling, and result
  extraction. For compiler benchmarks, separately describe source analysis cost;
  don't hide it in one solver's timer. A classical path must likewise include its
  required preparation and result extraction.
- `solver_only`: the declared core solve interval after preparation. Describe what
  was prepared/cached; never present it as end-to-end performance.

Each solver's `timing` declares whether queue, transpilation, optimizer iterations,
and sampling are included in `elapsed_ms`. Record each available duration; use null
when unmeasured. An optimizer timer may contain repeated sampling timers, so durations
may overlap and need not sum to the total. Report simulator execution separately from
the entire QAOA optimization loop. Future hardware work must separate queue time from
execution and requires coordinated backend/schema changes.

Compiler plans now reserve null provider communication fields, displayed as unmeasured
placeholders. Submission, ready-result retrieval, provider queue/processing and full
round trip have proposed measurement boundaries in
[COMPILER_COMMUNICATION_TIMING.md](COMPILER_COMMUNICATION_TIMING.md). Actual remote
wall time must be reported alongside solver/device time when that adapter is connected.
Do not add communication/queue components to a round trip that already contains them.
This preparation addition changes no existing solver timer or result convention.

Apply `timeout_seconds` to each runner, report budget exhaustion as a structured timeout,
and never compare an interrupted solve with a completed one without labeling it. Each
owner must implement cancellation/deadline enforcement before enabling computation.

## Experiment evidence

- **Compiler / optimization:** exhaustive tiny QUBO correctness checks, classical
  reference optimum where feasible, canonical best bitstring and objective, optimizer
  evaluations, QAOA depth/layers/shots/seed, gap or a documented valid ratio. Tests
  must verify sign, phase, constant offset, and bit ordering conventions.
- **Materials:** publish the precise Hamiltonian, boundary conditions, unit convention,
  estimator, and magnetization normalization. Compare the same observable against an
  exact reference. Start with known two-spin cases, Hermiticity, and dimension checks.
- **Search:** document explicitly marked states and oracle construction assumptions.
  Compare theoretical and measured success probabilities. Count oracle calls with a
  clearly stated classical policy (replacement or no replacement, stopping rule,
  expected or worst case). Include oracle construction/circuit cost in runtime; don't
  equate a cheap quantum query with an arbitrarily expensive classical predicate.

## Repetition and reporting

Repeat stochastic runs using recorded seeds; record the actual number of repetitions.
For the first vertical slice, a single run is allowed but must be labeled as such.
Report median, spread, and sample count when repetitions are available; preserve raw
run records in a separately agreed format. The initial single-run wire contract does
not yet define an aggregate distribution format; coordinate that extension before
adding fields. Keep warmed/cold runs distinct and repeat only under comparable settings.

Do not substitute zero for unknown values, fabricate data to fill charts, imply that
statevector simulation is a QPU, or claim speedup from gate/query complexity alone.
Cached demo outputs must be actual previously measured runs with provenance and a
visible cached-results label. Synthetic contract fixtures are for tests only.
