# Q-Atlas frontend

The ongoing SvelteKit + TypeScript + Tailwind CSS frontend, built on `chris-dev3` for Developer 5
and the rest of the team to continue. The root project specification is unchanged;
its React recommendation still needs team alignment before the spec is updated.
There was no existing frontend to migrate or replace.

## Run locally

Use Node **22.17+** (Node 24 LTS recommended) and npm:

```sh
cd frontend
npm ci
npm run dev
```

Open the Local URL printed by Vite, normally `http://127.0.0.1:5173`.
Fonts are bundled locally; no external font request is needed.

```sh
npm run check
npm test
npm run format:check
npm run build
npm run preview
```

`check` includes TypeScript and Svelte accessibility/compiler warnings. Tests use
Node's built-in runner and cover API failures, response shape, and fixture
consistency. `build` prerenders all five views into `build/`; a static server must
serve directory `index.html` files. No Node server or Python process is required
for the current UI.

## Structure

- `src/routes/`: Overview, Compiler, Materials, Optimization, Search, and the
  persistent navigation shell. All experiments have distinct shareable URLs.
- `src/lib/components/`: reusable panels, badges, measurements, accessible
  controls, graph/chart renderers, and the lighter experiment views.
- `src/lib/types/contracts.ts`: TypeScript mirrors of spec §6.1 and §6.2.
- `src/lib/api/client.ts`: a fetch client for the documented benchmark endpoints,
  runtime response checks, cancellation, timeout, and explicit errors.
- `src/lib/data/`: navigation metadata, static graph/QUBO fixtures, and labeled
  example benchmark data. There are no solvers in this directory.
- `src/app.css`: common design tokens, responsive shell, controls, and typography;
  individual views/components own their remaining styles.
- `tests/`: API boundary and fixture correctness tests.

SvelteKit 3 config lives in `vite.config.ts`; `#lib/*` imports are declared in
`package.json`. This follows the current
[SvelteKit configuration](https://svelte.dev/docs/kit/migrating-to-sveltekit-3).
Tailwind CSS 4 is integrated through its Vite plugin and provides layout utilities.
Shared design tokens and scoped CSS handle the application shell and scientific
visualizations. Charts use SVG without an additional charting runtime.

`FeatureBanner.svelte`, `LibraryOverview.svelte`, and `SolverComparison.svelte`
provide the shared blue introduction card, unmeasured execution status, and
interactive quality/time comparison. The existing light workspace, navy navigation,
blue feature panels, experiment cards, and analytics column are preserved.
IBM Plex Sans handles UI text; Plex Mono handles code, numbers, and technical metadata.
Cards use 4–6px corners, controls use minimal rounding, and solid backgrounds and
borders define the hierarchy without decorative shadows or gradients.

## Current behavior and data provenance

Overview and Optimization are the developed workspaces. Optimization supports
graph presets, manual partition changes, graph zoom/reset, QUBO inspection/copy,
trace switching, optional example-data loading, and labeled JSON export. Results and
charts start empty. The **Load example data** action reveals the existing
illustrative cost traces and counts, labeled as **example data, not measured
results**. These examples are not attributed to a backend or a seeded optimizer
run. Execution times, circuit depth, measurement shots, qubit count, and optimizer
evaluation count remain `null` in the example benchmark payloads. No elapsed-time
comparison is fabricated.

Setup controls preview future requests. Changing the graph selects its graph/QUBO
preset and clears the example result displays. Changing layers/shots/seed/optimizer
does not compute new results or change example chart values. The interactive graph
counts edges in a user-selected partition; it does not optimize that partition.
Known reference cuts and graph sizes describe the built-in mathematical problems,
not measured experiment activity.

Compiler has an editable local source area and a bundled static QUBO example;
editing source clears the example output. It never executes or analyzes source.
Materials and Search have lightweight controls and conceptual visualizations.
They do not calculate physical observables or Grover probabilities.

## Backend handoff

The app currently makes **no live experiment requests**. The API client is an
independent integration boundary, with no silent fallback from errors to mocks.
Pass a base URL and the team's approved request payload when connecting a view.
Benchmark response fields retain the documented names and nullable measurements;
`metrics` and `metadata` permit experiment-specific JSON. This frontend does not
replace backend validation or establish new public request envelopes.

Coordinate with the backend owners before wiring requests:

1. Confirm graph/QUBO request envelopes, QAOA configuration, limits, and structured
   status/error responses; these have not been implemented in the backend.
2. Confirm variable-to-qubit and measurement bit order. Current QUBO/partition
   indexing uses `x[i]`, and search ket labels are illustrations only.
3. Agree on timing boundaries, simulator-only time, quality/gap fields, and
   repeated-run metrics. Missing measurements must stay unavailable.
4. Configure FastAPI CORS or a same-origin `/api` proxy when the backend exists.
   Prerendered static hosting and FastAPI can remain separate services.

SvelteKit replaces React components/hooks and React routing with Svelte
components, runes, snippets, and file routing. The JSON API contracts and Python
algorithms do not depend on that choice. Developer 5 should review that framework
decision and the shared component boundaries before broad integration.

Design uses an original Q-Atlas mark, locally bundled IBM Plex typefaces, and
restrained scientific diagrams. White and light-gray workspaces contrast with
deep navy navigation and blue feature cards. No IBM logo or affiliation is implied.
