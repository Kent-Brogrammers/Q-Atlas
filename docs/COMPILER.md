# Developer 2 compiler

The compiler implements source parsing, allowlist validation, binary polynomial
extraction, QUBO normalization, exhaustive verification, diagnostics, and the
benchmark adapter. It never executes submitted Python. The project specification
is unchanged; the analysis response now includes a typed symbolic circuit preview.

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
  no defaults, and one final return expression. The parameter name can differ from `x`.
- An optional leading function docstring and up to 64 local assignments before the
  return. Each assignment has one plain name target, e.g. `penalty = 3*x[0]*x[2]`.
  Right-hand sides use the same expression allowlist. Names must be assigned before
  use. Reassigning a local uses its previous value on the right-hand side; aliases
  preserve the value at assignment time. The binary-vector parameter cannot be rebound.
- Numeric local accumulation with `+=`, `-=`, and `*=`. The local must already be
  assigned. Attribute/subscript mutation remains unsupported.
- Fixed `for i in range(...)` loops with 1–3 literal integer arguments (signed
  literals are allowed). Bounds/step have magnitude at most 64, step is nonzero,
  and each range must contain 1–64 values. Empty ranges are rejected in this initial
  loop subset. At most two loops may be nested; a loop cannot have an `else` clause.
  `range` must be unshadowed, and loop indices cannot also be ordinary assignment
  targets or shadow the binary parameter/another active loop index.
- Loop indices in expressions, including `x[i]` and bounded integer `+`/`-` index
  offsets such as `x[i+1]`. Only known loop indices are substituted; ordinary local
  names remain unsupported as indices. After a loop the index retains its last value.
- `num_bits` as an integer literal from 1 to 6. The compiler's smaller limit permits
  exhaustive verification; the shared QUBO contract still supports up to 16 variables.
- Finite integer/float literals, parentheses, unary `+`/`-`, and `+`, `-`, `*`.
- Literal binary indexing in range. Products may have at most two distinct bits.
  Repeated bits collapse using `x[i]*x[i] = x[i]`.
- Squared expressions with exponent literal `2`, including named terms and linear
  constraint penalties such as `(x[0] + x[1] - 1)**2`. Expansion must not produce a
  monomial involving more than two distinct bits. Arbitrary powers and powers with
  ordinary local-name exponents remain unsupported. The same binary-product rules
  apply to multiplication and squares, including nested squares.
- Optional marker `sense="maximize"`. The compiler negates every coefficient,
  including the constant, and records `original_sense="maximize"`. Solver values
  remain canonical minimization values; negate them to display original maxima.

Imports, top-level code, additional decorators/functions, annotations, chained or
unpacking assignments, data-dependent/while loops, calls outside the special range
form, attributes, undefined names, dynamic/negative indices, division, and
higher-order polynomials are rejected. Even dead expressions such as `0*run()` are
validated and rejected. Source is bounded to 20,000 characters, 2,048 AST nodes,
and AST depth 64. Source assignments/accumulations are capped at 64; loop lowering
is capped at 256 expanded assignments and 8,192 expanded AST nodes. Extreme
coefficients that overflow or fail the numerical equivalence check are rejected;
users should rescale such objectives.

For example, this marked function is supported without executing it:

```python
@qatlas.objective(num_bits=3)
def cost(x):
    """A small benefit/penalty objective."""
    weight = 2
    benefit = weight*x[0] + x[1]
    penalty = 3*x[0]*x[2]
    total = 5 - benefit
    total = total + penalty
    return total
```

It produces constant 5, linear `[-2, -1, 0]`, and pair (0,2) coefficient 3. Every
assignment is validated, including unused locals and expressions multiplied by
zero. Reading an undefined local produces `UNDEFINED_NAME`; invalid assignment
targets produce `INVALID_ASSIGNMENT`. Indices still require literals: assigning
`i = 0` does not make `x[i]` supported. [Example source files](../examples/compiler/README.md)
can be read as text or pasted into the compiler page; they are not executable modules.

The [bounded-loop example](../examples/compiler/bounded_loops.py) accumulates weighted
linear terms and adjacent pair terms with two fixed loops. Loop bounds must be
literal integers; `range(num_bits)`, `range(i+1, 6)`, keyword arguments, arbitrary
iterables, and empty ranges are not part of this initial loop subset. Reusing an
index in separate sequential loops is allowed. Loop indices may not be explicitly
assigned anywhere else in the function. Index offset literals/intermediate arithmetic
must stay within ±64, and each final binary index must be within the declared width.

`lowering.py` turns accepted loops/accumulations into a bounded sequence of ordinary
AST assignments for symbolic extraction. The safe numeric verifier separately walks
the original source loops on each binary assignment, rather than verifying only the
lowered program. A test deliberately corrupts lowering and checks that verification
detects the resulting objective mismatch. No user function or runtime decorator is
invoked; the range operations are compiler-owned arithmetic on validated integers.

The independent safe interpreter and the extracted QUBO must agree on every one of
the `2**num_bits` inputs, within relative/absolute tolerance `1e-9`. API bitstrings
remain `x[0]x[1]...x[n-1]`; no bit-order or objective-sense contracts changed.

## Squared penalty objectives

You can express a constraint preference as a squared linear residual, for example:

```python
@qatlas.objective(num_bits=3)
def cost(x):
    selected = x[0] + x[1] + x[2]
    penalty = 10*(selected - 1)**2
    benefit = x[0] + 2*x[1] + 3*x[2]
    return penalty - benefit
```

This produces constant 10, linear `[-11,-12,-13]`, and three pairs with coefficient
20. The [exactly-one example](../examples/compiler/exactly_one.py) expresses the same
objective using a loop. For this tiny example the mathematical minimum is -3 at
`001`; the example README lists all eight reference values. These are arithmetic
expectations, not quantum samples or benchmark measurements.

The compiler uses one binary-polynomial multiplication routine for ordinary products
and squares. Identities such as `(x[0]*x[1])**2 = x[0]*x[1]` remain valid, but
`(x[0]*x[1] + x[2])**2` is rejected because expansion produces a cubic term. General
quadratization or introducing auxiliary variables is outside this subset. Calls or
undefined names in squared expressions are still rejected, even in unused locals.

The source supplies the weight and penalty sign. The compiler translates that
unconstrained binary objective; it does not choose a sufficient weight, infer a
constraint system, or emit separate feasibility metrics. Source squares are checked
numerically against the QUBO on every input, with nonfinite intermediates rejected.

## QUBO -> QAOA handoff (mocked execution)

`app.compiler.pipeline.benchmark_qubo(qubo, config)` consumes the existing interfaces:

```python
app.experiments.optimization.solvers.run_classical(qubo, config)
app.quantum.qaoa.run_qaoa(qubo, config)
```

Developer 3's execution entrypoints remain untouched and are still explicit stubs.
Per the current request, no hardware, supercomputer, simulator, credentials, or external compute
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

The compiler checks that each solver's objective matches its assignment, that
bitstrings have exactly the QUBO width in API order, and that QAOA metrics match the
requested qubit and shot counts. An allegedly exact baseline cannot report an
objective above a valid QAOA solution. Inconsistent results fail with sanitized HTTP
500 rather than being displayed as completed measurements. Objective checks use
relative/absolute tolerance `1e-9`; the exact-gap ordering check uses absolute `1e-9`.

## Symbolic circuit previews

Successful analysis now calls the shared pure helper
`app.quantum.circuits.build_qaoa_preview(qubo, p=1)`. The response's `circuit` contains
an ordered parametric gate plan, explicit global phase terms, parameter order, and
logical depth. `executed=false` and `depth=null` distinguish the plan from transpiled
or measured results. No optimizer, simulator, or quantum package is invoked.

The shared helper supports one to eight layers for Developer 3's future runner;
analysis uses one layer because its request does not carry execution configuration.
The compiler contains no QAOA engine and no duplicate phase/mixer construction.

Developer 3 still supplies actual Qiskit assembly, transpilation, optimization, and
execution. The selected initial simulation method for that future handoff is
statevector, as recorded in benchmark metadata. See
[DEVELOPER_3_HANDOFF.md](DEVELOPER_3_HANDOFF.md) for the precise selected interfaces,
phase formulas, bit order, timing responsibilities, and remaining integration work.

## Checks

From `backend/`, after the standard API/dev dependency installation:

```sh
uv run --locked pytest tests/compiler
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

No quantum extras are needed. The focused tests cover exhaustive one-to-six-bit
extraction, signs/constants/squared penalties/pair normalization, malicious and unsupported
syntax, local scope, bounded loop semantics/expansion limits, the mocked HTTP pipeline,
and sanitized solver failures.
Analytical checks verify the cost gate phases, including offsets and maximization,
without simulating a quantum state. Actual Qiskit assembly, transpilation, sampling,
and optimizer correctness remain Developer 3 integration checks; mock results are
not evidence of solver performance or quantum advantage.
