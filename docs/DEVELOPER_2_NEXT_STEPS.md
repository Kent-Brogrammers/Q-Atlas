# Developer 2 next steps

This is the follow-up plan for the compiler implementation in commit `995de08`.
The source of truth remains [Project_Spec.md](Project_Spec.md); current behavior is
documented in [COMPILER.md](COMPILER.md).

## Current checkpoint

- Safe source-to-QUBO analysis works for one to six bits, with exhaustive verification
  and structured diagnostics. Submitted Python is never executed.
- The benchmark adapter forwards the same canonical QUBO and configuration to the
  existing classical and QAOA interfaces. Successful execution is tested with mocks.
- Developer 3's shared runners remain stubs. Live supported benchmark requests return
  HTTP 501; rejected source returns 422. Runner timeouts are mapped to 504.
- Analysis returns `circuit=null`; generated circuits and previews are not implemented.
- Validation at this checkpoint: 105 pytest cases passed, Ruff lint/format checks
  passed, frontend generated-type checks/type checks and production build passed.

**Execution constraint: mocks only.** Do not use the supercomputer, quantum hardware,
credentials, external compute quotas, or run simulator jobs. The user has reserved
the limited supercomputer allocation. A later execution phase needs a new explicit
request; this plan does not authorize it. Synthetic results belong in tests and must
never be presented as live or previously measured results.

## 1. Agree on the shared circuit handoff

**Owners: Developers 2 and 3; involve Developer 5 for preview output.**

- [ ] Ask Developer 3 to define a shared circuit-construction/preview helper that can
  be consumed without running an optimizer, sampling, or submitting any jobs.
- [ ] Confirm the helper's arguments, returned metadata, and ownership before coding
  the compiler adapter. Keep cost layers, mixers, and QAOA execution in the shared
  quantum module; do not implement a second engine under `app/compiler/`.
- [ ] Confirm the spec's cost-unitary sign convention, treatment of constant/global
  phase, and mapping of `x[i]` to qubit `i`. API strings remain `x[0]` first.
- [ ] Agree with Developer 5 on how to render a circuit. The existing wire model only
  carries qubit count, optional depth, and backend; it has no circuit image or gate
  payload. Propose any needed schema/API extension before changing it.

Completion: a documented shared interface and a mock of that interface, with no
execution. Until it exists, preserve `circuit=null` instead of inventing preview data.

## 2. Finish compiler integration checks with mocks

**Owner: Developer 2.** Keep additions focused rather than building a broad test suite.

- [ ] Add a maximization handoff case that checks negation of the constant, linear,
  and pair coefficients, while preserving `original_sense` for display.
- [ ] Cover a nonzero exact optimality gap and asymmetric bitstrings to catch offset
  and bit-order regressions at the shared-runner boundary.
- [ ] When the preview helper is agreed, mock it and verify compiler metadata and
  failure handling without executing a circuit.
- [ ] Review metadata with Developer 3: the current adapter assumes statevector
  simulation and recognizes `brute_force` as the exact baseline. Confirm these
  assumptions before enabling any real runner.
- [ ] When shared stubs are replaced, keep compiler tests explicitly mocked so a
  routine test run cannot unexpectedly start quantum execution. Update tests that
  currently assert the stubs' availability only as part of that coordinated change.

Relevant files: `backend/app/compiler/analysis.py`, `pipeline.py`,
`backend/app/api/compiler.py`, and `backend/tests/compiler/`.

## 3. Connect the compiler experience

**Owners: Developer 5 for UI; Developer 2 for compiler endpoint behavior.**

- [ ] Replace the compiler page's stale message that analysis is unimplemented.
- [ ] Display supported/rejected status, diagnostic line/column, and normalized QUBO.
- [ ] Explain that live comparison awaits the shared runners and handle 501 cleanly.
  Preserve loading/error states and show unavailable circuit previews honestly.
- [ ] Coordinate original-sense display: solver objectives stay canonical minimization
  values; original maximization values are obtained by negating them.
- [ ] Regenerate frontend types with `npm run types:generate` after any agreed contract
  change. Do not edit generated TypeScript manually.

Completion: supported three-to-six-bit objectives can be analyzed from the existing
compiler page, rejected source has actionable feedback, and missing execution is clear.

## 4. Validate the next change

From `backend/`, with API/dev dependencies installed:

```sh
uv run --locked pytest tests/compiler
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

From `frontend/` when contracts or UI are affected:

```sh
npm run types:check
npm run typecheck
npm run build
```

The current compiler tests require no quantum extras. The original HTTP tests stalled
inside the restricted sandbox's test-client event loop and passed outside it; distinguish
that environment issue from a code regression. Do not resolve test failures by enabling
hardware, simulators, or fabricated production measurements.

## Deferred work

Local assignments, fixed-range loops, larger compiler inputs, and helper constructs
are optional language extensions, not the next milestone. Retain the strict allowlist
until the initial compiler integration is complete.

Actual circuit phase/unitary checks and comparisons against an exact classical optimum
remain unverified by mocks. If real local execution is later explicitly requested,
coordinate it with Developer 3, enforce time budgets including native calls, and record
seeds, shots, package versions, timing scope, and solution quality according to
[BENCHMARK_METHODOLOGY.md](BENCHMARK_METHODOLOGY.md). Hardware or supercomputer use must
remain separately authorized. Do not claim quantum advantage from synthetic fixtures.
