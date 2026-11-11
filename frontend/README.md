# Q-Atlas frontend

The ongoing SvelteKit + TypeScript + Tailwind CSS frontend. The shared project
specification is preserved at `docs/Project_Spec.md`; its React recommendation
has not been rewritten. Main's React scaffold is retained as a separately runnable
reference in `react-scaffold/` for Developer 5 to review.

## Run locally

Use Node **22.17+** and npm:

```sh
cd frontend
npm ci
npm run dev
```

Open Vite's local URL, normally `http://127.0.0.1:5173`. Fonts are bundled locally.
The Svelte compiler at `/compiler/` now sends static generation/planning requests:
load a normal Python file, mark one function with `@qatlas.objective`, click
**Convert Python**, then follow the four separate views: **Python input → Compiled
code → Test → Results & analytics**. Conversion opens the compiled code automatically;
**Continue to test** opens comparison preparation, and **Prepare test plan** opens
analytics. Back buttons and the step navigation preserve the current source and
downloads. Editing source or layers clears downstream data. Test preparation runs
no solvers; performance metrics remain unmeasured. Function/input names are arbitrary;
named scalar inputs and statically indexed vectors can infer width without `num_bits`.
The Test step also offers **Load IBM devices** and an explicitly confirmed physical
job: one layer, at most three inputs, 128 shots and a 10-second QPU cap. The backend
trains angles locally and samples the final bound circuit on the selected QPU.
Use **Check hardware job**, **Cancel hardware job** and **Download QPU record** to
manage the recorded request; there is no automatic submission or polling.
See the [hardware runbook](../docs/COMPILER_IBM_HARDWARE.md) for quota and recovery.
Quantum controls and mathematical details are optional advanced sections. No circuit
code or second decorator is needed. File contents are never executed.

FastAPI can be started independently using the root README or together with this
frontend using `../dev.sh`. Its materials route runs the existing spin-system
simulation only when requested; the Materials route displays live results. The
Neutrino Lab and Grover Search also use their live backend APIs. The compiler
workflow never executes user code. Hardware metadata, submission and retrieval use
separate typed compiler endpoints. Optimization runs local classical/QAOA comparisons
through `POST /api/optimization/run`.

```sh
npm run check
npm test
npm run format:check
npm run types:check
npm run build
npm run preview
```

`check` includes TypeScript and Svelte accessibility/compiler warnings. Tests cover
shared request serialization, canonical error envelopes, cancellation, and graph /
example-data consistency. `build` prerenders all seven routes into `build/`.

## Structure

- `src/routes/`: primary Overview, Python Compiler, Neutrino Lab, Grover Search, and Methodology views.
  Materials and Optimization remain accessible at their original URLs; Materials
  provides the live Ising-chain request and result view.
- `src/lib/data/navigation.ts`: the five primary links, separate from the retained
  experiment catalog in `experiments.ts`.
- `src/lib/components/`: reusable panels, controls, SVG diagrams, and example displays.
- `src/types/api.generated.ts`: the canonical types generated from FastAPI OpenAPI.
- `src/types/index.ts`: named exports used by both frontends.
- `src/api/client.ts`: the shared typed fetch client, with structured errors,
  cancellation, and a 65-second transport timeout for the API's 60-second run limit.
- `src/lib/api/client.ts` and `src/lib/types/contracts.ts`: compatibility re-exports,
  with no parallel transport implementation or manually copied API schema.
- `src/lib/types/examples.ts`: presentation-only example values, explicitly distinct
  from measured backend result contracts.
- `src/lib/data/`: fixed mathematical graph/QUBO presets and labeled chart examples.
- `tools/api-types/`: OpenAPI generator workspace. It uses TypeScript 5 for the
  generator's peer range; SvelteKit uses its required TypeScript 6 independently.
- `react-scaffold/`: preserved React source with an independent package/build,
  importing the same shared client and generated types.

SvelteKit 3 configuration lives in `vite.config.ts`; `#lib/*` imports are declared
in `package.json`. Tailwind CSS 4 is integrated through its Vite plugin. IBM Plex
Sans handles UI text; Plex Mono handles code, numbers, and technical metadata.
The warm-neutral editorial palette uses `#FAFAF8` for the canvas, `#F5F0EB` for
cards and navigation, `#1C1917` / `#57534E` for text, `#0369A1` for interactive
elements, `#C2410C` for accent states, `#166534` for success, and `#D6D3D1` for
dividers. Cards use 4–6px corners and controls remain minimally rounded.

## Neutrino Oscillation Lab

The main navigation is **Overview**, **Python Compiler**, **Neutrino Lab**, **Grover Search**, and **Methodology**.
Overview provides a prominent **Open Python Compiler** action, a compiler capability
summary, and the existing Neutrino science/availability information without example statistics.
Methodology records the model scope and classical validation requirements.

`/neutrinos/` is the live two-flavor propagation workspace. It supports vacuum,
constant matter, two equal-length matter layers, and a matter-potential sweep for
neutrinos and antineutrinos. Inputs and outputs use normalized units; the initial
state is electron flavor, and the other channel is an effective active-flavor
combination. The backend returns SciPy reference, ideal Qiskit, and finite-shot
results with metrics and timing. See [the experiment guide](../docs/NEUTRINOS.md)
for the model, assumptions, and limitations. The UI starts without fabricated
results, validates settings before requests, and shows backend errors explicitly.

## Retained workspaces and data provenance

The compiler at `/compiler/` is linked from the sidebar and Overview. The original
`/optimization/` and `/materials/` remain accessible by direct URL. Materials sends
live requests to its implemented backend endpoint. Optimization runs a local Aer
comparison against the exact classical baseline. `/search/` is linked from primary navigation and runs live Grover /
classical comparisons. Shared schemas and the React reference remain available.

## Retained behavior

Optimization retains its graph presets, manual partitions, zoom/reset, QUBO
inspection/copy, and explicitly labeled examples. **Run comparison** sends the
selected graph, layers, shots, seed, optimizer budget and per-solver deadline through
the existing typed client. The live response supplies assignments, objectives,
optimality gap, actual depth/shots, evaluations, timing and reproducibility metadata.
The graph can display the returned QAOA or classical partition, and manual node
changes are labeled as the user's partition. Bitstrings put x[0] first.

Changing configuration or resetting clears results and aborts pending transport.
Duplicate submissions are suppressed, and late/cancelled responses are ignored.
**Stop waiting** ends the client wait while the backend retains its bounded solver
deadlines. Backend errors are displayed with retryable controls.

Measured JSON export retains the exact request, complete response and
`source=live_local_simulator`. The timing details identify each end-to-end solver
interval and the QAOA optimizer, final transpilation and sampling components.
Nullable measurements display as unavailable and measured zeros remain zero.

**Load example data** reveals the retained illustrative objective traces and count
histograms with explicit example labels. The live contract supplies a best sampled
assignment and aggregate metrics. Its optimizer trace and full measurement counts
need a coordinated contract extension before measured chart integration.

Compiler edits invalidate the returned QUBO, generated script, and plan; requests
use the shared typed API and ignore stale responses. The default example contains
ordinary helpers, named binary choices, and a main caller with one bare decorator.
Optional technical output shows source-to-bit mapping and honest unexecuted gates;
physical sampling is available through the explicitly authorized Test flow. Its
measurements stay separate from the nonexecuting plan and the local Aer contract.
Materials and Search use their live APIs.

## Grover Search

Open `/search/` or select **Grover Search** in navigation. Start FastAPI at
`http://127.0.0.1:8000` with the backend quantum extra installed. Configure 1–6 qubits,
unique marked bitstrings, shots and seed, then run a comparison or measure a curve.
The page starts empty and never substitutes examples when an API request fails.

Curves measure iterations 0 through a chosen last iteration (at most 12), with
sequential calls to the existing typed `api.search` transport. Every point preserves
the full backend response. The chart plots measured and backend-theoretical success
probabilities, with a table for exact values and per-iteration comparisons. Progress,
stopping, structured errors, missing values, reproducibility metadata and JSON download
are included. Changing controls clears old results.

Stopped/failed sweeps do not display incomplete results as completed curves. Stopping
aborts browser requests; native backend work may finish or reach its per-request
deadline. These are simulator measurements and oracle-model query counts, not practical
speedup evidence. See [the search guide](../docs/SEARCH.md) for timing scopes, assumptions,
Windows commands and a demo rehearsal.

`src/lib/search/live.ts` validates settings and orchestrates bounded sweeps;
`SearchProbabilityChart.svelte` plots returned probabilities. Tests use synthetic
fixtures only in `tests/search-live.test.ts`, never in the live application.

**Run repeated trials** measures the same single-run configuration two to five times,
using sequential seeds incremented modulo `2^32`. `src/lib/search/trials.ts` validates
the completed records and summarizes mean probability, observed min/max, sample
standard deviation, median solver times, seeds, and total shots. The chart shows a
mean point and observed-range whisker; this is not a confidence interval. The trial
table preserves individual results and seeds. JSON exports include the presentation
summary separately from raw API responses; each raw run still reports one repetition.
Failures/cancellation publish no partial summary. Tests for aggregation, metadata,
seed wraparound and request control are in `tests/search-trials.test.ts`.

For rehearsals, **Load recorded curve/trials** explicitly loads previously measured
local API responses with a dated banner and source revision. Nothing loads on page
startup or as an automatic error fallback. Recorded downloads retain a distinct
source label and provenance; editing controls clears the recording. The matching
configuration is restored when loading it. The backend script
`scripts/prepare_search_demo.py` regenerates the recording only after real endpoint
checks pass; `--verify` checks a saved bundle without simulation. See the search guide
for the full rehearsal checklist. `tests/search-recorded.test.ts` covers provenance,
evidence consistency, independent copies and reactive-state JSON export.

## API types and integration

After backend environment setup, run:

```sh
npm run types:generate
npm run types:check
```

The first command exports FastAPI's actual schema and regenerates the committed
TypeScript. The second checks for drift. Never hand-edit generated types. A normal
frontend build uses committed types and needs no running Python server.

Both frontends use `createApiClient()` / `api` from `src/api/client.ts`. The default
API base URL is `http://127.0.0.1:8000/api`; `VITE_API_BASE_URL` overrides it. It is
public browser configuration, never a place for credentials. TypeScript enforces
endpoint/request/result types; FastAPI owns runtime model validation. Failed live
requests never fall back to example data.

Request envelopes, x[0]-first API bitstrings, and timing fields are established in
[API contracts](../docs/API_CONTRACTS.md). Reuse them when wiring the Svelte views.
Keep structured 501/422 errors visible, preserve nullable measurements, and do not
change shared contracts without coordinating with the affected owners.

## Preserved React scaffold

```sh
cd frontend/react-scaffold  # from the repository root
npm ci
npm run typecheck
npm run build
npm run dev
```

This reference runs at `http://127.0.0.1:5174`. It retains main's original React
pages, request panels, health check, and live API error display. It shares API types
and transport with SvelteKit rather than forking contracts. Generate types from
the parent frontend first if contracts change; see `react-scaffold/README.md`.
