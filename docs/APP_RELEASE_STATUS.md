# Final app implementation and demo guide

**Physical hardware update:** all five experiments now have real IBM execution and
classical/QPU analytics. The shared physical demo completed on `ibm_marrakesh` with
2.0 seconds of provider usage for eight circuits. See the
[hardware guide](IBM_HARDWARE_ALL_EXPERIMENTS.md) and
[results](evidence/ibm-qpu-2026-11-12/RESULTS.md). Local workflows below remain available.

This implementation follows [the festival roadmap](FALL_FEST_ROADMAP.md) and
[science challenge answers](SCIENCE_CHALLENGE_ANSWERS.md). The original project
specification, API schemas, minimization convention, bit order and solver timing
definitions are preserved. The existing uncommitted hardware and stress-study work
has been retained.

## Available now

| Workspace | Live single run | Browser parameter studies |
| --- | --- | --- |
| Compiler | Convert supported Python, inspect/download code, then Test → Run local comparison; exact optimum, QAOA sample/gap, depth and timings. Results also appear in Results & analytics | QAOA layers or final shots, repeated over selected seeds |
| Optimization | Graph presets, configurable 3–16-vertex cycles, or custom weighted graph/QUBO JSON; exact classical and shared Aer QAOA comparison | Controlled cycle sizes, layers, or shots |
| Materials | Existing 2–4-spin Ising dynamics with exact, ideal and shot observables | Trotter steps or shots, at the configured terminal time |
| Search | Existing Grover run, iteration curve, seeded trials and explicit recorded fallback | Qubit counts, iterations, or shots; size-study figure distinguishes expected/observed classical checks and quantum queries per attempt |
| Neutrinos | Existing distance/density curves and effective two-flavor model | Shot counts across the same full curve and distinct base seeds |

All five workspaces are in the main sidebar. Each offers live JSON export. The explicit recorded physical-demo loader also works without the backend and labels the archive with its original request date. Study
exports preserve the plan, each effective request, raw responses, package provenance
available from the API, completed/failed/cancelled status, and recomputed summaries.
The Methodology page includes the final science report, physical-result figure, raw evidence, source provenance and an offline presentation ZIP. See PRESENTATION_READINESS.md and PRESENTATION_RUNBOOK.md for the final audit and demo.

## Start and demonstrate

From the repository root, after installing the locked backend and frontend dependencies:

```sh
./dev.sh
```

Open http://127.0.0.1:5173/. The launcher now enables local compiler simulation by
default. Set `QATLAS_ENABLE_COMPILER_AER=0` to retain a conversion-only deployment.
A backend started separately still requires `QATLAS_ENABLE_COMPILER_AER=1` for local
compiler execution. The backend also loads optional `QUANTUM-KEY` and `QUANTUM-CDN` (IBM instance name/CRN) from `.env`; missing values do not prompt or block startup. No IBM account is needed for local experiments. Physical IBM jobs
remain a separate explicitly confirmed action. The physical release completed the shared five-experiment IBM job described above.

For a production-build rehearsal, run `npm run build` in `frontend/`, then
`npm run preview -- --port 5173`. Start the backend in another terminal from `backend/`:

```sh
QATLAS_ENABLE_COMPILER_AER=1 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Suggested live sequence:

1. Neutrinos → MSW resonance → Run experiment. Explain the circuit/reference/shot
   curves and normalized units. Download the full curve.
2. Materials → Run comparison. Explain Trotter versus sampling error, then vary steps.
3. Search → iteration curve; then a size study. Discuss oracle assumptions and query
   counts separately from wall-clock time.
4. Optimization → choose a graph → Run local comparison. Report the gap alongside time.
5. Compiler → Convert Python → Continue to test → Run local comparison → View local
   results & analytics. Unsupported Python is rejected; surrounding source is never run.

Use two values and one seed for a short live study. Use three seeds for a saved
descriptive comparison. Download and inspect evidence before presenting. Search's
explicit previously measured fallback and Methodology's archived figure work without
the backend; other live experiments require the local API.

## Study and measurement behavior

- Choose up to eight distinct integer values and five distinct seeds, with at most
  24 requests, two million final measurement shots, and a 1–120-second suite budget.
  Per-experiment request limits also apply. Grid and aggregate budgets are validated before launch; the backend validates each mathematical request.
- Single comparisons and a page's study cannot launch concurrently. Runs within a
  study are sequential. Changing inputs removes stale results.
- Stop cancels browser waiting and prevents further study requests. Backend workers
  retain their existing execution deadlines; browser cancellation does not certify
  immediate native-process termination. Partial evidence remains downloadable.
- A failed request stops scheduling. Its status and message remain in the export;
  only completed records contribute to statistics. Unknown measurements stay null.
- Every reported metric has its own sample count, median, minimum and maximum. These
  observed ranges are not confidence intervals. Three seeds support descriptive results.
- Search size studies use one explicit all-zero target and automatic iterations.
  Optimization size studies use unit-weight cycles. Neither selects inputs to inflate
  the classical comparator. Cycle graphs are structured teaching cases, not hard instances.
- Materials studies measure the terminal time only. Neutrino studies repeat the whole
  configured curve and summarize mean probability error across its coordinates.
- Reference and circuit timing workloads differ for physical simulations. QAOA uses
  ideal statevector training and final shot sampling. Runtime alone does not establish
  hardware advantage. The classical multistart heuristic remains available in the
  existing stress-study CLI for stronger optimization scaling comparisons.

## Release checks

Final presentation release: **1068 backend tests passed**, all 12 frontend test-file
subtests and seven compiler tests passed, and lint/format, generated types,
Svelte/TypeScript and production build passed. The final browser rehearsal passed
**16 checks** with zero new hardware submissions, including full-cap readiness,
all five live/local and physical views, report/ZIP downloads and explicit offline
physical evidence. See [the final audit](PRESENTATION_READINESS.md).

Earlier local-release backend pytest: **1048 passed**, with 68 dependency deprecation warnings.
Backend Ruff lint/format passed. Frontend Svelte/TypeScript checks, all 11 test-file
subtests, seven compiler tests, generated-type verification and static production
build passed. New study tests cover controlled inputs, bounds, exact shot bookkeeping,
sequential execution, zero measurements, failed points, cancellation, and suite expiry.
Launcher tests verify default local execution and its explicit opt-out.

Production-build Chromium rehearsal passed **19 checks**, including all five workspaces,
live comparisons, two-point studies and raw exports, compiler Results navigation,
scientific evidence assets, input editing, unavailable API behavior, custom JSON and
index errors, duplicate grids, study cancellation, partial failures, the recorded
Search fallback, and a 390px mobile layout. The mobile screenshot was visually
inspected. The [verification record](evidence/app-rehearsal-2026-11-12.json) includes
source hashes and distinguishes real calculations from injected failure tests. Backend tests and
local servers run outside the sandbox because its restrictions stall TestClient and
prevent localhost binding. Temporary browser tooling is under `/tmp`; no browser-testing
package was added to the repository dependencies.

Remaining human release work: rehearse the talk twice on the presentation laptop,
select and retain the final source revision, and freeze before presenting. Arbitrary
Cartesian grids, larger physical models, new algorithms and hardware optimization
studies remain the roadmap's post-festival work.
