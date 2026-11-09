# Python file to generated QAOA script

The compiler page accepts a `.py` file, extracts its marked binary objective, and
downloads Python containing a generated Qiskit circuit builder. The backend treats
the input and output as text/AST data. It never imports the file, calls its functions,
imports Qiskit, or submits a quantum job.

## Use the frontend

Start the API and frontend using [README.md](../README.md), then open
<http://127.0.0.1:5173/compiler>.

1. Keep **Generate script** selected.
2. Choose **Load a Python file**, paste a script, or click **Load example**.
3. Mark one supported objective with `@qatlas.objective(num_bits=N)`.
4. Put old circuit construction in one zero-argument function and mark that function
   with `@qatlas.circuit`. Its name is preserved when the implementation is replaced.
5. Select 1–8 QAOA layers, then click **Generate Python script**.
6. Review the generated Python, normalized QUBO, and symbolic gate plan.
7. Click **Download .py**. A file named `model.py` downloads as `model_qaoa.py`.

Try [script_replacement.py](../examples/compiler/script_replacement.py). The original
source stays in the editor. Editing it, loading another file, or changing layers or
workflow clears the prior download; late requests cannot restore old results.

The separate **Analyze objective only** workflow retains the original single-function
analysis/comparison behavior. Whole scripts belong in Generate, and the original
Analyze/Benchmark endpoints still accept only their existing objective subset.

## Input markers and replacement behavior

```python
# Ordinary imports, helpers, and caller code may surround the marked functions.

@qatlas.objective(num_bits=3)
def cost(x):
    return 5 - 2*x[0] + 3*x[0]*x[2]


@qatlas.circuit
def build_circuit():
    # This function's entire implementation will be replaced.
    from qiskit import QuantumCircuit
    old = QuantumCircuit(3)
    old.x(0)
    return old


if __name__ == "__main__":
    print(build_circuit())
```

The objective follows the existing [supported language](COMPILER.md): 1–6 bits,
binary quadratic arithmetic, supported locals, bounded loops, and squared penalties.
It cannot depend on surrounding globals, imports, or helper calls. Its values are
independently verified against the normalized QUBO on every binary assignment.

Both markers are inspected statically; no runtime `qatlas` package is needed. The
output removes the objective's marker and preserves its function/body as ordinary
Python. It removes the complete marked circuit function, including its marker, and
inserts a new zero-argument function with the same name. Existing calls such as
`build_circuit()` stay as written.

The circuit marker is exactly `@qatlas.circuit`, without parentheses. It permits one
top-level synchronous function, with no arguments, return annotation, or additional
decorators. Multiple objectives, multiple circuit markers, nested marked functions,
and incompatible factory signatures produce diagnostics and no downloadable artifact.
Original-file line locations are preserved in objective diagnostics.

If no circuit marker exists, the compiler appends `build_qatlas_circuit()`, choosing a
numbered suffix if that name is already used. It reports the resulting entrypoint.
Unmarked circuit code remains unchanged. The compiler does not infer which arbitrary
Python statements are circuits or automatically delete imports, helpers, measurements,
or job submissions elsewhere in a file. Put the whole construction you intend to
replace inside the marked factory.

## What the generated builder contains

The builder imports `QuantumCircuit` and `Parameter` locally, creates named gamma/beta
parameters, emits the ordered H/RZ/CP/RX calls from
`app.quantum.circuits.build_qaoa_preview`, adds its explicit global phase, and returns
the unbound circuit. The displayed plan and emitted code use the same selected p.
Parameter order remains `gamma_0, beta_0, gamma_1, beta_1, ...`; x[i] maps to qubit i.
When binding angles later, map values explicitly by parameter name rather than
assuming the order of Qiskit's parameter collection matches this declared order.
The serializer does not calculate a separate cost mapping or create a second solver.

The circuit has no measurements, optimized angles, sampling, execution backend calls,
or timing claims. Its purpose is circuit construction. Developer 3 still owns actual
assembly/execution integration and optimization through the shared runner.

Qiskit is needed only when someone manually calls the exported builder. The emitted
construction API was checked against IBM's official
[QuantumCircuit reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.QuantumCircuit)
and [Parameter reference](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.Parameter).
Actual exported-code execution remains untested under the current mocks-only instruction.

Surrounding Python is copied verbatim, including imports, helpers, comments, and
caller code, with its existing line endings. It is opaque passthrough content and
is not validated for application correctness or safety. Replacing the factory changes
its result to an unbound `QuantumCircuit`; check callers that expected a bound circuit,
counts, a tuple, or some other return value. Review the preserved script before manually
running it: preserved top-level code would run at that time. Generation itself runs none
of that code, and the original file is never overwritten.

## API

`POST /api/compiler/generate` accepts JSON, using the existing source transport:

```json
{"source":"... complete Python source ...", "p":2}
```

`source` has the existing 1–20,000-character bound. `p` defaults to 1 and is bounded
to 1–8. The complete input shares the existing 2,048-node/64-depth AST bounds; only
the marked objective enters the allowlisted interpreter. Its existing scope,
coefficient, loop-expansion, and verification limits remain in effect.

A successful HTTP 200 `CompilerGenerateResult` extends the existing analysis fields:

| Field | Meaning |
| --- | --- |
| `status` | `supported` after successful extraction/generation |
| `diagnostics` | Verification and generation messages |
| `qubo` | Verified canonical minimization instance |
| `circuit` | Unexecuted shared preview for the selected p |
| `artifact.filename` | Default `q_atlas_generated.py`; the browser may derive a name from the input |
| `artifact.source` | Complete rewritten Python, bounded to 150,000 characters |
| `artifact.entrypoint` | Name of the generated zero-argument factory |
| `artifact.replaced_function` | Old factory name, or null when appending |
| `artifact.executed` | Always false |

Rejected source returns HTTP 200 with `status=rejected`, error diagnostics, and null
QUBO/circuit/artifact. Invalid request fields return the existing structured HTTP 422
envelope. Generated source is returned to the requesting browser; it is not saved
on the backend. No filename or filesystem path is accepted by this API.

## Verification and remaining work

`backend/tests/compiler/test_generation.py` checks all seven independent QUBO fixtures,
emitted gate/phase/parameter ASTs, newline and surrounding-code preservation, collision
handling, original diagnostic locations, marker/signature rejection, request bounds,
and absence of solver calls. Tests never execute generated or submitted Python.

The real API/Firefox checks covered local `.py` loading, replacement, matching download
contents, layers, diagnostics, stale results, objective-only Analyze, and mobile width.
See [COMPILER_MANUAL_CHECKS.md](COMPILER_MANUAL_CHECKS.md).

Next, try an intended objective/script and record its result. Broader circuit discovery,
parameterized factory signatures, multiple replacement regions, and adapting arbitrary
Python algorithms require concrete source examples and a separately specified boundary.
Live optimization remains the shared-runner dependency, with execution still mocked.
