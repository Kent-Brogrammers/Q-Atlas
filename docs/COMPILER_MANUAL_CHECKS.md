# Compiler manual validation record

This records local integration checks of the compiler and its browser page. These
are source-analysis/UI correctness checks, not classical or quantum performance
measurements. No simulator, hardware, supercomputer, or credential-based jobs ran.
No synthetic solver measurements were installed into the live API.

## Checkpoint

- Compiler implementation commit: `75539fd`.
- Canonical zero-coefficient fix found during HTTP validation: `ba11311`.
- Backend suite: 266 passing pytest cases; Ruff lint/format checks passed.
- Frontend: four file-reading checks passed; generated-type checks, TypeScript
  checks, and production build passed.
- Browser session: Firefox 159.0, with actual local Vite/FastAPI servers.
- Integration ports were 5179 (frontend) and 8011 (API), with matching CORS/base URL
  settings. These checks do not change the default development ports.

The browser driver was installed under `/tmp` only. The browser checks below were
run against actual analysis responses; deliberate client-side delays were used for
the two stale-result cases. No fake success responses replaced the analysis API.

## Direct HTTP cases

All seven `.py` files in [examples/compiler](../examples/compiler/README.md) were
read as text and submitted to `POST /api/compiler/analyze`. Every case returned:

- HTTP 200 and `status=supported`.
- A QUBO matching [expected_qubos.json](../examples/compiler/expected_qubos.json).
- A symbolic circuit with `executed=false` and `depth=null`.

Additional checks:

| Request | Observed result |
| --- | --- |
| Analyze marked objective containing `return sum(x)` | 200, rejected, `UNSUPPORTED_SYNTAX` |
| Benchmark that rejected source | 422, `VALIDATION_ERROR`, compiler diagnostics |
| Benchmark the supported exactly-one example | 501, `NOT_IMPLEMENTED`, shared runner unavailable |

The first direct comparison exposed signed zeros for unused maximization terms.
The compiler now applies objective negation before filling absent terms with +0.0;
a regression checks both unused linear coefficients and an absent constant.

## Browser cases

| Interaction | Observed result |
| --- | --- |
| Analyze default squared-penalty source | Real API QUBO has linear [-11,-12,-13]; readable coefficient/gate panels appear |
| Request comparison | 501 dependency message; existing supported analysis remains visible |
| Load bounded_loops.py and analyze | Editor loads file text, old panels clear, four-bit QUBO matches expectations |
| Paste unsupported call and analyze | Source rejected; prior QUBO/preview hidden; diagnostic selects the source line |
| Load maximization example | Canonical/original-sense explanation appears |
| Load a 20,001-character file | Read rejected; previous editor contents preserved |
| Edit source while an earlier analysis response is held | Earlier response discarded; fresh analysis uses the edited source |
| Edit source while an earlier file read is held | Earlier file cannot overwrite the newer edit |
| Inspect at 375px viewport | No page-level horizontal overflow |
| Check uncaught page errors across the session | None observed |

The page was also visually inspected after successful analysis. Its gate table is
explicitly labeled **Not executed** and separates logical depth from transpiled depth.
These observations cover the listed cases; future changes still need their own checks.

## Reproduce locally

Start the normal backend/frontend using [README.md](../README.md). Open
`http://127.0.0.1:5173/compiler`, then:

1. Analyze the default example; inspect the QUBO and the symbolic gate table.
2. Load each example `.py` file using **Load a Python file**, then Analyze.
3. Paste the unsupported-call example above; click the diagnostic line button.
4. Restore the example and request comparison; expect the current 501 dependency message.
5. Change coefficients; confirm old results disappear and a new analysis reflects them.
6. Check keyboard access, a narrow viewport, and a file exceeding the character limit.
7. For API response races, use browser network throttling and edit while analysis is
   pending. Controlled delayed file reads are best covered by a browser test harness.

Run the frontend checks in [Developer 5's handoff](DEVELOPER_5_HANDOFF.md) and the
backend checks in [COMPILER.md](COMPILER.md). The source subset remains restricted;
these checks do not establish arbitrary-Python support or live QAOA correctness.

## Follow-up numerical and input-integrity checks

Subsequent compiler hardening passed 274 pytest cases, including new regressions for
large constant offsets and mutation of shared inputs. The source
`1e12 + (1e16 + x[0] - 1e16)` previously passed a relative-tolerance check despite
an objective discrepancy of 1. It now returns `VERIFICATION_FAILED`, while a
consistent large-offset expression remains supported.

Wrong shared objectives and persistent changes to either the supplied QUBO or
configuration now fail with sanitized HTTP 500. Each runner receives independent
input copies; the caller's original instance/configuration remain unchanged. These
follow-up checks use mock runners and are separate from the earlier Firefox session.

## Analysis-only operations checker

The reusable command `backend/scripts/check_compiler_api.py` was verified against
a real local API on port 8011. It passed all nine checks: one health request, seven
supported source examples, and one unsupported-call rejection. The server request
log contained only GET health and POST compiler/analyze. No benchmark or other
execution endpoint was contacted.

After stopping that temporary server, the same command returned process exit code
1, reported that the API could not be reached, and submitted no source cases.
This negative run was performed outside the network sandbox, so it checked the
stopped service rather than relying on a sandbox connection denial.

The backend suite now passes 310 cases, including 31 checker transport/validation
cases and the additional classical-error/mutation-then-timeout cases. Frontend
file-reading tests, generated-type checks, TypeScript checks, production build, and
Ruff checks also passed. These operation checks use no simulator or supercomputer.

## Full-file script generation and frontend, 2026-11-09

The temporary API ran on port 8011 and Vite on 5179 with that local origin allowed.
Real HTTP generation requests for all seven objective fixtures returned their
independently specified QUBOs, two-layer symbolic previews, and unexecuted Python
artifacts. Source files and downloaded Python were handled only as data.

Firefox 159.0 checked the actual compiler page:

- The default full-script example generated a `build_circuit()` replacement. Its
  download Blob matched `artifact.source` exactly, omitted the old X-gate body,
  and preserved the caller. The download name was `example_qaoa.py`.
- Loading `script_replacement.py` cleared the old download. Selecting two layers
  produced matching two-layer code/preview and `script_replacement_qaoa.py`.
- Rejected source had no code/download or stale success output. Its original-file
  line diagnostic selected the correct source line.
- Editing during a delayed generation request prevented its old result from
  restoring a download. A new request used the new coefficient and appended a builder
  for objective-only source without a replacement marker.
- Changing layers/workflows invalidated the output. Objective-only Analyze still
  returned a supported result through its original endpoint.
- The page fit a 375px viewport without page-level horizontal overflow. No uncaught
  browser errors occurred, and only compiler Analyze/Generate API routes were requested.

The backend suite passed 339 tests; six frontend tests, generated-type checks,
TypeScript checks, Ruff, and the production build passed. Added static regression
cases cover parenthesized/multiline decorators, original line locations, CRLF/bare-CR
preservation, source name collisions, missing final newlines, and marker ambiguity.
These checks did not execute exported/user Python, import Qiskit, or run a simulator,
supercomputer, hardware, or solver job. Actual Qiskit execution remains unverified
under the current instruction. The temporary browser harness remains outside the repo.

## Weight vectors, program catalog, and comparison planning

The next increment passed **368 backend tests**, six frontend source/file tests,
generated-type checks, TypeScript checks, Ruff, and the production build. Tests
cover literal-vector math on every binary assignment, invalid/mutated vectors,
independent verification, five documented program outcomes, generated snapshot ASTs,
and full-file benchmark handoffs with both runners mocked. Plan contracts reject
true execution flags and circuit/config inconsistencies.

Real local HTTP checks used the five catalog programs: two returned verified
generation plus HTTP 200 plans, and three returned the documented rejection code
plus HTTP 422 planning errors. Source/generated hashes matched their exact text,
plan p matched the preview, and plans contained no timing measurements.

Firefox 159.0 checked the actual example chooser and planning UI against that API:

- Each chooser option loaded source text identical to its repository fixture.
- Both supported examples generated Python and a comparison-plan download whose
  JSON exactly matched the API response. The execution button remained disabled.
- All three rejected examples had no output download and could not prepare a plan.
- Three selected QAOA layers appeared consistently in generation and planning.
- Editing source during a delayed planning response prevented stale manifests and
  generated scripts from reappearing.
- The full plan fit a 375px viewport; no uncaught browser errors occurred.
- The browser requested only compiler generation and `/benchmark/plan` endpoints.
  It never requested the benchmark execution endpoint.

Two output `.py` snapshots were generated/formatted as text and compared by AST only.
No input/output script, solver, simulator, hardware, or supercomputer job was run.
The temporary local servers were used only for these static operations. No live
performance measurements or quantum-advantage claims follow from these checks.

## Marker-only conversion, naming flexibility, and main integration

The compiler accepts arbitrary objective/vector names and named scalar inputs.
One bare `@qatlas.objective` marker infers scalar count or bounded static vector
width. Tests verify every binary assignment for 1–6 named inputs in both senses,
declaration order, local weights/loops, signature errors, input rebinding, and
nonexecuting generation/planning. The new named-decision example and generated
snapshot are checked as text/AST only.

Main's SvelteKit workspace, Materials/Search/classical code, and Neutrino page were
preserved. The active Svelte compiler now uses load Python → Convert Python →
Download .py, with quantum options and benchmark details collapsed. The React
reference was preserved under `frontend/react-scaffold/`, sharing types, transport,
and compiler helpers. Both frontend builds/type checks passed; Svelte reported zero
errors/warnings, frontend tests and generated-type/format checks passed, and Ruff passed.

The inspected safe backend selection passed **422 tests**:

```sh
cd backend
.venv/bin/pytest tests/compiler tests/api tests/schemas tests/optimization tests/materials/test_request_contract.py
```

The full default suite now contains other owners' simulator execution tests, so it
was deliberately not run. This selection covers compiler/API/contracts, pure classical
math, and mocked or unavailable shared runners without any quantum computation.

Firefox checked the actual Svelte page against a local API: one-decorator default
source with natural names and no circuit code; exact download contents and preserved
caller; named-scalar upload; renamed-vector width inference; optional input-order and
planning details; disabled execution; line-selected unsupported-call diagnostics;
discarded late responses; 375px layout; and the retained Neutrino route. There were
no browser errors. Only compiler generation/planning endpoints were requested.

No submitted/generated Python, simulator, hardware, or supercomputer job was executed.
The provider connection remains a documented future integration, not an enabled path.

## Guided compiler workflow

The active Svelte compiler now has four separate views, with Back/Next actions and
guarded step navigation. Browser regression cases:

1. Start at Python input; later steps are disabled and no generated-code panel is shown.
2. Convert supported source; only Compiled code opens, with exact preview/download content.
3. Go back and forward without editing; preserve source and artifacts without another request.
4. Continue to Test; preparation is available and execution remains disabled.
5. Fail a preparation request; stay on Test, retain the compiled artifact, and allow retry.
6. Prepare successfully; open Results & analytics with the exact downloadable plan,
   static compilation metrics, and explicit unmeasured runtime/quality fields.
7. Navigate back, then edit source/layers; disable later steps and clear old artifacts/plans.
8. Reject an unsupported objective; stay at input and retain diagnostic line selection.
9. Delay conversion, edit source, then release the response; remain at input with no stale output.
10. Exercise upload, keyboard focus, stage navigation, and every view at 375px width.

Firefox verified the flow against a local API. Requests were confined to generation
and nonexecuting plan endpoints. No simulator or hardware execution was performed.
