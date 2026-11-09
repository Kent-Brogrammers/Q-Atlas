# Compiler page integration handoff

The user authorized implementing the compiler-page integration after the Developer 2
pipeline, including the November 9 file-to-generated-script workflow for Developer 5 review.
Other experiment pages, shared fetch behavior, and the application shell are unchanged.

## Implemented files

| File | Purpose |
| --- | --- |
| `frontend/src/pages/CompilerPage.tsx` | Typed analysis/comparison state, source input, local file reading, async request guards |
| `frontend/src/components/CompilerAnalysisPanel.tsx` | Diagnostics with line selection, canonical coefficients, original/solver sense, raw JSON |
| `frontend/src/components/CircuitPreview.tsx` | Ordered symbolic gate table, explicit parameter order/global phase, logical depth |
| `frontend/src/components/GeneratedScript.tsx` | Read-only generated Python, download Blob lifecycle, replacement/entrypoint explanation |
| `frontend/src/compiler/source.ts` | Example source, bounded file-text loading, parameter-angle formatting |
| `frontend/tests/compiler-source.test.mjs` | Six built-in Node checks for file-reading, download names, and example behavior |

`npm run test:compiler` runs the small test module with native Node type stripping.
It adds no frontend testing package or runtime dependency. The additive
`POST /api/compiler/generate` endpoint uses `CompilerGenerateRequest` and
`CompilerGenerateResult`/`GeneratedPythonArtifact`; OpenAPI types were regenerated.
The existing Analyze/Benchmark contracts are unchanged.

## Behavior to preserve

- In objective-only mode, pasted or file-loaded Python is text submitted through `api.analyze({source})`.
  Do not import, execute, or dynamically evaluate it on either side.
- The default **Generate script** workflow sends `api.generateScript({source,p})`.
  It accepts surrounding Python as opaque passthrough text and replaces only an
  explicit `@qatlas.circuit` zero-argument factory. The displayed gate plan uses the
  requested p. The separate **Analyze objective only** mode retains one-layer analysis.
- Show generated code and a named `.py` download only when `artifact` exists. Clear
  it on source/layer/workflow changes and ignore late generation responses. Revoke
  Blob URLs when the artifact disappears or the component unmounts.
- Keep the generated/unexecuted label and explain that the builder returns an
  unbound Qiskit circuit. Preserved Python is not validated as a runnable application.
- File input accepts `.py`/text. The extension is a convenience, not validation.
  Reject empty source and source over 20,000 characters; refuse reads over 80,000
  bytes before reading. Preserve the editor contents on a failed read.
- HTTP 200 can carry `status=rejected`. Render diagnostics and omit QUBO/preview
  panels; a rejection is not an HTTP error and must not look like successful analysis.
- Diagnostic buttons select the corresponding one-based source line. Missing
  diagnostic locations remain supported.
- Changing source invalidates analysis/comparison data. Revision guards reject
  late API responses and stale file reads; an older read cannot replace a newer edit.
- Suppress duplicate submissions while a request is pending. A supported analysis
  belongs to that source revision; editing it requires analysis again before comparison.
- Ordinary request errors preserve the submitted source. A 501 comparison explains
  the missing shared solver dependency and leaves its supported analysis visible.
- Benchmark requests currently use server-default QAOA configuration. Parameter
  controls and structured benchmark charts are future work.
- Keep maximization coefficients/solver values canonical, and show original sense
  separately. Do not negate canonical gaps when displaying an original maximization.
- The preview is a symbolic description: label **Not executed**, distinguish logical
  depth from unavailable transpiled depth, and use the returned parameter ordering.
- Raw JSON is optional detail. The main display uses diagnostics/coefficient tables
  and a gate table, without fake timings, measurements, or success charts.

See [COMPILER_SCRIPT_GENERATION.md](COMPILER_SCRIPT_GENERATION.md) for input/output
examples, marker restrictions, and generation request/result semantics.

## Review and remaining frontend work

- [ ] Review the compiler page in the team's intended layout/style.
- [ ] If needed, replace the gate table with an SVG circuit diagram using the same
  returned plan. Do not rebuild cost/mixer formulas in the frontend.
- [ ] Add accessible benchmark controls/results when Developer 3 supplies actual
  runners. The current endpoint safely returns 501; no per-runner capability field exists.
- [ ] Coordinate any readiness/configuration contract extensions with backend owners
  and regenerate types. Health's `experiments_ready=false` is not a compiler capability flag.
- [ ] Fit future browser regressions into the team's chosen frontend test stack.

The present browser checks used temporary Firefox tooling outside the repository;
they are recorded evidence, not a new project CI dependency. See
[COMPILER_MANUAL_CHECKS.md](COMPILER_MANUAL_CHECKS.md) for cases and reproduction.

## Validation commands

From `frontend/`:

```sh
npm run test:compiler
npm run types:check
npm run typecheck
npm run build
```

No simulator, hardware, supercomputer allocation, or credentials are required.
