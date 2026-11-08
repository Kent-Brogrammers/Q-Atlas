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
