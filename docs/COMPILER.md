# Developer 2 compiler

The compiler implements source parsing, allowlist validation, binary polynomial
extraction, QUBO normalization, exhaustive verification, diagnostics, and the
benchmark adapter. It never executes submitted Python. The project specification
and shared wire models are unchanged.

## Supported source

```python
@qatlas.objective(num_bits=3)
def cost(x):
    return 5 - 2*x[0] + x[1]*x[2]
```

The decorator is a source marker, not an imported or executed Python decorator.
Submit this text to `POST /api/compiler/analyze` as `{"source": "..."}`. A supported
response contains a canonical QUBO with constant `5`, linear `[-2, 0, 0]`, and pair
`(1, 2)` with coefficient `1`. Diagnostics report verification on all eight inputs.
An unsupported source returns HTTP 200 with `status=rejected`, a diagnostic code,
and a one-based line/column when available. No rejected response contains a QUBO.

The initial compiler accepts:

- Exactly one synchronous marked function with one unannotated positional parameter,
  no defaults, and one return expression. The parameter name can differ from `x`.
- `num_bits` as an integer literal from 1 to 6. The compiler's smaller limit permits
  exhaustive verification; the shared QUBO contract still supports up to 16 variables.
- Finite integer/float literals, parentheses, unary `+`/`-`, and `+`, `-`, `*`.
- Literal binary indexing in range. Products may have at most two distinct bits.
  Repeated bits collapse using `x[i]*x[i] = x[i]`; literal `x[i]**2` is also supported.
- Optional marker `sense="maximize"`. The compiler negates every coefficient,
  including the constant, and records `original_sense="maximize"`. Solver values
  remain canonical minimization values; negate them to display original maxima.

Imports, top-level code, additional decorators/functions, annotations, assignments,
loops, calls, attributes, unknown names, dynamic/negative indices, division, and
higher-order polynomials are rejected. Even dead expressions such as `0*run()` are
validated and rejected. Source is bounded to 20,000 characters, 2,048 AST nodes,
and AST depth 64. Extreme coefficients that overflow or fail the numerical
equivalence check are rejected; users should rescale such objectives.

The independent safe interpreter and the extracted QUBO must agree on every one of
the `2**num_bits` inputs, within relative/absolute tolerance `1e-9`. API bitstrings
remain `x[0]x[1]...x[n-1]`; no bit-order or objective-sense contracts changed.

## QUBO -> QAOA handoff (mocked execution)

`app.compiler.pipeline.benchmark_qubo(qubo, config)` consumes the existing interfaces:

```python
app.experiments.optimization.solvers.run_classical(qubo, config)
app.quantum.qaoa.run_qaoa(qubo, config)
```

Developer 3's files remain untouched and are still explicit stubs. Per the current
request, no hardware, supercomputer, simulator, credentials, or external compute
quota is used. Compiler tests inject synthetic solver results at these boundaries;
those fixtures are never installed into the live API or presented as measurements.

`POST /api/compiler/benchmark` reanalyzes the submitted source before invoking any
runner. Supported input currently returns HTTP 501 `NOT_IMPLEMENTED`, identifying
the shared Developer 3 dependency. Rejected input returns HTTP 422 with compiler
diagnostics; future runner timeouts map to HTTP 504 `TIMEOUT`. Unexpected exceptions
use the existing sanitized HTTP 500 envelope.

The adapter forwards the same QUBO/config to both runners and preserves their
objectives, bitstrings, and measured solver timings. Source analysis is outside
both solver timers. Instance IDs hash the canonical QUBO, without storing source.
Comparison gaps are populated only for the exact `brute_force` baseline;
approximation ratios stay null for general signed QUBOs. Metadata includes the
effective instance/config, seed, single-run provenance, and installed package versions.

Developer 3 must supply the shared QAOA implementation and circuit-preview helper
before a live comparison or generated circuit is available. The adapter currently
expects statevector simulation, which must be confirmed with that owner before
enabling real execution. Analysis leaves `circuit=null`; it does not invent circuit
depth or imply circuit execution. The compiler contains no QAOA engine and performs
no duplicate phase/mixer construction.

## Checks

From `backend/`, after the standard API/dev dependency installation:

```sh
uv run --locked pytest tests/compiler
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

No quantum extras are needed. The focused tests cover exhaustive one-to-six-bit
extraction, signs/constants/squares/pair normalization, malicious and unsupported
syntax, parser limits, the mocked HTTP pipeline, and sanitized solver failures.
Quantum phase/sign and simulator correctness remain Developer 3 integration checks;
mock results are not evidence that a quantum circuit is correct.
