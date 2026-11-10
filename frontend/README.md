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
**Convert Python**, then download the result. Function/input names are arbitrary;
named scalar inputs and statically indexed vectors can infer width without `num_bits`.
Quantum controls and mathematical details are optional advanced sections. No circuit
code or second decorator is needed. File contents are never executed.

FastAPI can be started independently using the root README or together with this
frontend using `../dev.sh`. Its materials route runs the existing spin-system simulation
only when requested; compiler execution, optimization, and search remain unavailable.
Neutrino API integration is proposed separately and is not registered in this frontend.

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

- `src/routes/`: primary Overview, Neutrino Lab, and Methodology views. Compiler,
  Materials, Optimization, and Search remain at their original URLs.
- `src/lib/data/navigation.ts`: the three primary links, separate from the retained
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
The light workspace, navy navigation, blue feature panels, 4–6px card corners,
and minimally rounded controls preserve the current design.

## Neutrino Oscillation Lab

The main navigation is **Overview**, **Neutrino Lab**, and **Methodology**.
Overview introduces the science and current availability without example statistics.
Methodology records the model scope and classical validation requirements.

`/neutrinos/` is the primary workspace. Model/flavor selection, energy/distance,
vacuum/constant-density matter, matter parameters, and requested shots are visible
but disabled until capabilities and the API are agreed. There are no assumed
physical defaults or enabled propagation modes. Run sends no requests.

The probability plot starts empty, with no assumed flavor channels or example
dataset. Comparison, accuracy, and circuit/execution information are grouped in
expandable sections rather than empty measurement cards. No physics or error
calculation runs in the browser. Local draft-export helpers remain available for
future integration but are not exposed as an approved request workflow.

Draft discussion types live in `src/lib/neutrinos/proposal.ts`, outside the approved
generated API schema. See [Nick's proposed handoff](../docs/NEUTRINO_INTERFACE_PROPOSAL.md)
for supported models/flavors, units, matter conventions, independent classical
reference, measured errors, encoding, and timing requirements. No neutrino endpoint
is added to the shared client. The existing Materials backend and React scaffold
are preserved.

## Retained workspaces and data provenance

The original routes `/compiler/`, `/optimization/`, `/search/`, and `/materials/`
remain accessible by direct URL, with their source and functionality preserved.
They are hidden from primary navigation and Overview pending the team's decision
about their long-term role. Their backend implementations, shared schemas, and
React reference are unchanged.

## Retained behavior

Optimization supports graph presets, manual partition changes, zoom/reset, QUBO
inspection/copy, trace switching, optional example loading, and labeled JSON export.
Results and charts start empty. **Load example data** reveals illustrative cost
traces and counts, explicitly labeled as examples rather than measured output.
No backend, seed, or optimizer run is attributed to those examples. Execution
measurements remain unavailable.

Example comparisons are UI-only data; they are not cast to `BenchmarkResult`.
Exports separate `example_comparison` / `example_chart_data` from a generated-type
checked `request_preview`. The shared backend requires recorded solver time and
timing inclusion flags when a solver result exists. No placeholder measurement
is fabricated to satisfy that contract.

Setup controls preview future requests. Changing the graph clears example displays;
changing settings does not compute results. Only COBYLA is supported by the current
shared API; SPSA is visibly disabled. The graph counts a selected partition's edges,
not an optimized solution. Reference cuts describe the mathematical presets.

Compiler edits invalidate the returned QUBO, generated script, and plan; requests
use the shared typed API and ignore stale responses. The default example contains
ordinary helpers, named binary choices, and a main caller with one bare decorator.
Optional technical output shows source-to-bit mapping and honest unexecuted gates;
comparison execution remains disabled. Materials and Search controls update conceptual diagrams;
they do not compute observables or Grover probabilities.

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
