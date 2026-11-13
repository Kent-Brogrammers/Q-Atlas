# Q-Atlas final-day roadmap

**Implementation update:** live Optimization and compiler comparisons, bounded studies
across all five workspaces, evidence exports, navigation and scientific presentation
are now implemented. See [release status and demo guide](APP_RELEASE_STATUS.md) for
current behavior and verification. The audit and estimates below describe the starting
point for this implementation.

Prepared November 12, 2026 for the presentation described as tomorrow (November 13).
Based on local revision `5786fd1` **plus the existing uncommitted working tree**.
This is a scoped implementation proposal, not a statement that the remaining features
are complete. The original [project specification](Project_Spec.md) is unchanged.

## Recommended finish line

Lead with one scientific question: **How does matter change neutrino flavor conversion,
and can a small quantum circuit reproduce the prediction with quantified error?**
Use Materials to explain approximation versus sampling, Grover to explain query advantage,
and the compiler to demonstrate how users introduce a new optimization objective.
The app is the instrument supporting the scientific argument.

The supplied challenge notebook evaluates understanding, impact, and especially
creativity/novelty. It explicitly does not require beating every classical baseline.
Its H2/VQE example is a reporting template; adding a chemistry experiment tonight is
unnecessary. The [challenge answers](SCIENCE_CHALLENGE_ANSWERS.md) follow that template.

**Do not make a measured quantum runtime win a condition for finishing.** None is
established by the evidence reviewed here. Grover offers a defensible theoretical
query advantage under its oracle assumptions. Small Aer experiments measure CPU
simulation cost. More parameters do not guarantee a classical/quantum runtime crossover.
[IBM's explanation of Grover's query model](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/grovers)

## What exists, and what actually needs work

| Area | Observed implementation | Remaining presentation gap | Owner |
| --- | --- | --- | --- |
| Neutrinos | Live distance/potential curves; independent analytical/SciPy references; exact one-qubit circuits; existing shot/seed benchmark CLI | Put the scientific question, error interpretation, and downloadable evidence beside the curve; optional repeated-study browser controls | Existing neutrino maintainer (Nick), D3, D5 |
| Materials | Live 2–4-spin open Ising dynamics; time sweep; exact/ideal/shot observables and separated errors | Add an outer steps/shots study and uncertainty presentation; time points alone are not repeated trials | D1, D5 |
| Search | Live runs, iteration curves, 2–5 seeded trials, exports, explicit previously measured fallback | Add a bounded size study and a clear query-scaling figure; keep actual classical checks distinct from expected checks | D4, D5 |
| Optimization | `/api/optimization/run` calls real classical/shared QAOA solvers | **Browser page still loads illustrative fixtures.** Connect the existing endpoint, then add size studies | D3, D5 |
| Compiler | Safe AST extraction, circuit/script generation, comparison planning; local benchmark endpoint behind `QATLAS_ENABLE_COMPILER_AER=1`; separate IBM workflow | **Normal browser comparison prepares a plan without local execution.** Add explicit local comparison and resource controls | D2, D5; D3 owns solver |
| Scaling tools | Working-tree `backend/scripts/benchmark_stress_examples.py` supports sizes/layers/seeds, exact/QAOA/heuristic, raw JSON/CSV/plots | Review and preserve this currently untracked work; use it before building another benchmark engine | D3, D2 |
| Documentation | Scientific report, model guides, benchmark methodology, platform hypothesis | README still says Optimization is HTTP 501 and describes old mocks; reconcile with current code. Platform setup-effort reduction is still unmeasured | Module owners, D5 |

Evidence: [Optimization UI](../frontend/src/routes/optimization/+page.svelte),
[Optimization API](../backend/app/api/optimization.py),
[compiler UI](../frontend/src/routes/compiler/+page.svelte),
[compiler API](../backend/app/api/compiler.py), [search guide](SEARCH.md),
[materials guide](MATERIALS.md), [neutrino benchmarking](NEUTRINO_BENCHMARKING.md),
[stress studies](STRESS_EXAMPLES.md). The active frontend is SvelteKit; the React
directory is a retained scaffold.

## Priority order and acceptance criteria

Effort ranges below are planning estimates, not promises. Work can be divided among
the existing owners. Protect the final two hours for evidence review and rehearsal.

| Priority / budget | Concrete task | Done when |
| --- | --- | --- |
| P0 · 30 minutes | Agree on the main science question and allowed claims; read the answer document together | Each presenter can explain the model, circuit, classical reference, and limitations without the UI |
| P0 · 1–2 hours | D3/D5 wire Optimization presets to its existing endpoint | Changing a control changes the actual request; results come from the response; stale fixtures disappear; failure/cancel/export work |
| P0 · 1–2 hours | D2/D5 expose the existing local compiler comparison | Analyze → inspect QUBO → explicit local run yields assignment, objective gap, settings and timings; disabled-server state is explained; uploaded Python is never executed |
| P0 · 1–2 hours | D3 plus experiment owners capture bounded evidence using existing runners | Every displayed result has its full input, raw response, versions, seeds, source provenance and timing scope; include classical quality and errors |
| P0 · 45–60 minutes | D5/module owners fix stale copy and result labels | Example, previously measured, live Aer, and physical QPU results cannot be mistaken for one another; units and workloads are visible |
| P0 · final 2 hours | All owners run gates, rehearse on the presentation laptop, freeze | Two successful rehearsals; exports open offline; an explicit fallback works without credentials/network; no new feature work after freeze |
| P1 · 2–4 hours if P0 is green | Add a consistent bounded study experience to each live page | Choose one sweep axis, fixed controls, seeds, run budget; progress/stop; quality/error and runtime plots; download full evidence |
| P2 · after the festival | Arbitrary Cartesian grids, bigger models, new algorithms, hardware optimization studies, universal experiment scheduler | Separate reviewed design and measured need |

If time slips, keep Optimization clearly labeled as a preview and show a recorded CLI
comparison instead. Keep compiler conversion as its live story if its local-run UI is
not ready. A thoroughly explained live Neutrino/Search path plus measured fallback is
preferable to presenting an incomplete benchmark as operational. These are fallback
choices; the integration gaps remain on the backlog.

## Parameterization: choose a study, then run its finite grid

Interpret “run all parameters” as **run every value in the selected, bounded study**.
Continuous controls have infinitely many values; a Cartesian product grows rapidly.
For example, 6 sizes × 3 depths × 3 shot counts × 5 seeds × 3 graph families is 810
configurations before running the separate solvers. Show the planned work before launch.

Provide three modes using the same underlying experiment runners:

1. **Single run:** choose all supported controls and inspect one real result.
2. **Sweep one axis:** choose an explicit list/range; hold other scientific inputs fixed.
3. **Repeat selected study:** distinct recorded seeds at each point; summarize median,
   observed spread and sample count, while retaining all raw responses.

“Run selected suite” can queue the named presets below in sequence, with per-study and
overall deadlines. A checkbox list can select studies; it should not silently launch
every possible combination. Start with offline CLI evidence if browser integration
cannot fit into the remaining time.

### Recommended presets

All are local simulation. Three seeds are a descriptive demo sample, not a precise
performance estimate. Expand repetitions only after the small suite is reliable.

| Study | Vary | Hold fixed | Work / comparison |
| --- | --- | --- | --- |
| Neutrino science centerpiece | 9 potentials over `[0, 1.842121988]`; shots `{256,1024,4096}`; base seeds `{42,142,242}` | theta=0.2, splitting=energy=1, neutrino, distance=4.033698869 | 9 curve requests / 81 points; probability and error. **Recorded with this roadmap.** |
| Materials convergence | steps `{1,2,4,8,16,32}` × seeds `{42,142,242}` | N=3, J=1, h=0.7, t=1, one time point, 4096 shots/basis | 18 requests; ideal-vs-exact error against steps and depth |
| Materials sampling | shots `{256,1024,4096}` × same seeds | Same physics, 32 steps, one time point | 9 requests; sampling error separately from Trotter error |
| Grover mechanism | iterations `0..6` | n=3, target `001`, shots=1024, seed=42 | Existing 7-point curve; explain overshooting the first amplification peak |
| Grover size | n=`{2,3,4,5,6}` × seeds `{42,142,242}`, automatic iterations | One marked state, 1024 shots | 15 requests; report analytic uniform-position expected checks plus actual target/check count. Do not select target placement to manufacture a classical slowdown |
| QAOA size | n=`{6,8,10,12}` × seeds `{7,42,99}` | Same deterministic graph family, p=1, 1024 final shots, 20 evaluation budget, one instance | 12 matched comparisons; exact enumeration, classical heuristic, QAOA; runtime **and** gap |
| QAOA depth | p=`{1,2,3}` × same seeds | n=6, same graph, shots=1024, same 20 evaluation budget | 9 comparisons; depth/parameters and quality; more depth need not improve a bounded optimizer |
| Compiler equivalence + comparison | Existing 3–6-bit examples; selected seeds | Explicit coefficient/source versions, fixed QAOA settings | Exhaustive source/QUBO verification and solver comparison. Different examples are not automatically a controlled size-scaling family |

Run QAOA size/depth grids through the existing stress CLI; do not route >6-bit source
through the compiler. Check its current working-tree tests before using it as evidence.
Use one instance initially. If batching multiple instances, every solver must solve
the same full batch, and figures must say “batch runtime.”

### Supported controls and real limits

| Experience | Expose / retain | Important implementation bounds |
| --- | --- | --- |
| Compiler | Source/coefficients, p, shots, seed, evaluation budget, timeout | Compiler ≤6 bits; shared QUBO runner ≤16. Seed changes sampling/optimization, not source size |
| Optimization | Graph/QUBO, size/family, weights, p, shots, seed, evaluation budget | Shared config p=1–8; COBYLA only; max_iterations=1–1000; timeout ≤60s per solver |
| Materials | N, J, h, t, steps, time points, observable, shots, seed | Open Ising only, N=2–4, steps=1–256, times=1–21; existing work caps apply |
| Search | n, targets, iterations or auto, shots, seed | Runner n=1–6, iterations=0–32, shots ≤10000; schema bounds alone are broader |
| Neutrinos | Angle, signed splitting, energy, particle, layers/potential, distance, axis, samples, shots, seed | Existing web/CLI resource caps differ; validate through existing request and runner. No physical km/GeV conversion UI |

Disabled/unimplemented options must stay disabled. Propose new limits to the owner
instead of removing guards to chase a runtime crossover.

### Interface proposal for owner review

D3 coordinates study aggregation; D1/D2/D4/Nick retain model and runner ownership;
D5 owns presentation. Reuse `backend/app/schemas/` and the existing typed clients.
The first pass can orchestrate existing single-run requests without a new API.

A browser/local export envelope should contain a format version, experiment, base
request, sweep field/values, requested seeds, effective requests, status per point,
raw responses, summary definition, and provenance. This is a **proposal**, not a new
shared contract. Do not reinterpret existing timer, bit-order, or objective fields.
Agree with impacted owners before changing contracts; regenerate types with
`npm run types:generate` if a wire contract changes.

Run sequentially for interpretable timings. Validate the complete plan before launch;
show point count and shots; enforce existing per-run limits plus a proposed 120-second
demo-suite budget. On stop, schedule no more work; distinguish browser abort from
actual backend termination. Existing worker deadlines remain essential. Export failed,
timed-out and cancelled points as such; exclude them from completed-run statistics and
never plot them as zero. Retain partial evidence with an incomplete-suite label.

## How to compare honestly

Use separate panels for **scientific answer/quality**, **measured runtime**, and
**theoretical resources**. A combined speedup badge would erase important differences.

- Search: Grover oracle calls per circuit, all shots' oracle calls, success probability,
  actual classical checks, and uniform-position expected checks are different metrics.
  At n=6 with one mark, first-peak k=6 gives ideal success ≈0.996586; the classical
  uniform-position expectation is 32.5 checks. These are analytical predictions.
  Accounting for one verification query and repeat-until-success gives about
  `(6+1)/0.996586 = 7.024` expected queries under an ideal restart model. None is a
  measured wall-clock win or the cost of the full 1024-shot study.
- QAOA: compare the same QUBO with exact enumeration **and** the existing classical
  heuristic; report gap/validity as well as runtime. The local statevector expectation
  scorer enumerates all `2^n` assignment costs. It does not demonstrate hardware scaling.
- Materials/Neutrinos: current circuit timers include ideal and shot simulations,
  while the classical reference performs a different workload. Label the costs;
  do not divide them into an end-to-end speedup claim. Match requested accuracy and
  outputs before a future performance study.
- Hardware: provider QPU usage omits local angle training, communication and other costs.
  A shorter device duration than CPU solve time is not sufficient evidence of speedup.
  New quota-consuming jobs require explicit approval; they are not a demo dependency.
- Record cold/warm policy, package versions, machine, seeds, exact inputs, repetitions,
  source revision and relevant source hashes. Do not fit an asymptotic crossover from
  a few tiny simulator points. Three repetitions support descriptive ranges, not strong
  statistical claims. See [measurement agreement](BENCHMARK_METHODOLOGY.md).

## Evidence already prepared in this pass

The [answer document](SCIENCE_CHALLENGE_ANSWERS.md) includes a fresh local neutrino
study with [raw responses](evidence/fall-fest-2026-11-12/neutrino-resonance.json),
[validated review](evidence/fall-fest-2026-11-12/neutrino-resonance-review.md),
[source provenance](evidence/fall-fest-2026-11-12/provenance.json), and a figure.
There were 81 point results; maximum ideal-vs-SciPy conversion error was
`3.054e-16` after rounding upward. No hardware ran. Timings were collected during
a readiness-check session with concurrent test activity and are not a controlled
performance study. No new quantum runtime advantage is claimed.

## Release gates and presentation

From `backend/`, run `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check .`, and
`.venv/bin/ruff format --check .`. From `frontend/`, run `npm run check`, `npm test`,
`npm run test:compiler`, `npm run types:check`, and `npm run build`. Add tests for new
integration/sweep behavior, especially stale responses, cancellation, bounds, raw
exports and summary arithmetic. Test only changes made; avoid duplicate QAOA logic.

Readiness checks performed for this document are recorded in the answer document.
Automated checks do not substitute for browser rehearsal on the presentation laptop.

- [ ] Review and preserve the existing uncommitted hardware/stress work; identify the
  exact release revision. Do not bundle unrelated edits just to make the tree clean.
- [x] Fix both integration gaps or label/demote those routes explicitly.
- [ ] Run one valid request and one invalid request through each live page.
- [x] Verify backend unavailable, timeout, cancel/retry, input edits and export behavior.
  (Suite-deadline unit coverage; browser cancellation/recovery and export checks.)
- [x] Confirm fixtures never become measured evidence and unknown metrics stay unknown.
- [ ] Save selected results and figures locally; use Search's explicit recorded fallback.
- [ ] Open the saved Markdown/figure/JSON offline; do not depend on venue Wi-Fi or QPU queues.
- [ ] Bring the challenge answers, a one-slide circuit explanation and the evidence files.
- [ ] Rehearse twice, freeze the source, and record versions before presenting.

Suggested five-minute sequence: 45s scientific question and impact; 90s neutrino model,
circuit and resonance figure; 45s Materials error distinction; 45s Grover query versus
runtime; 45s compiler extensibility; 30s limitations and next experiment. If the actual
slot is shorter, keep the neutrino explanation and one supporting example.
