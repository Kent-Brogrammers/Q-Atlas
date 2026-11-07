# Developer 3: optimization setup

The source of truth is [the project spec](../Q-Atlas_Codex_Project_Spec.md),
especially sections 6, 7, 9, 12, and 15. The initial repository contained only
that spec and the license; no shared schema, QAOA implementation, or backend
configuration existed.

## Environment and checks

Run from the repository root with Python 3.12 and `uv` installed:

```sh
uv sync --project backend --python python3.12 --locked
uv run --project backend --locked pytest -c backend/pyproject.toml backend/tests
uv run --project backend --locked ruff check backend
uv run --project backend --locked ruff format --check backend
```

The virtual environment lives at `backend/.venv`. `uv.lock` pins the resolved
dependencies; `pyproject.toml` lists supported ranges. The environment includes
NetworkX, NumPy, SciPy, Qiskit, Qiskit Aer, pytest, and Ruff. It has no IBM
credentials or hardware dependency.

This machine's initial Homebrew Python had a broken Expat library link. A
working Python 3.12 interpreter was installed locally at `backend/.python/`
(ignored by Git) for the environment. On another machine, the commands above
use its available Python 3.12; `uv` can download one if needed. No system
Python installation is modified.

To run only classical correctness tests:

```sh
uv run --project backend --locked pytest backend/tests/optimization
```

The quantum environment test executes a one-qubit circuit using
[`qiskit_aer.primitives.SamplerV2`](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.primitives.SamplerV2.html).
It checks local installation and the V2 result API; it is not a QAOA or
performance test. QAOA should use the current
[Qiskit primitives](https://quantum.cloud.ibm.com/docs/en/api/qiskit/primitives).

## Files and ownership

| Path | Responsibility |
| --- | --- |
| `app/experiments/optimization/classical.py` | Evaluate a single assignment for the canonical QUBO in spec section 6.1. |
| `app/quantum/qaoa.py` | Reserved shared runner location for Developers 2 and 3; currently documentation only. |
| `tests/optimization/conftest.py` | Reusable canonical QUBO fixture. |
| `tests/optimization/test_classical.py` | Known objective values, offsets, coefficient signs, assignment indexing, and input guards. |
| `tests/quantum/test_environment.py` | Local Aer V2 sampler smoke test. |

The `__init__.py` files make these directories importable packages. Future
Max-Cut conversion belongs in `app/experiments/optimization/maxcut.py`;
classical solvers can extend `classical.py`. Add benchmark instrumentation only
after agreeing on the shared result schema. No compiler, API, frontend,
materials, or search modules are created in this setup.

## Existing contract and coordination

The spec establishes the JSON QUBO fields and cost formula. `evaluate_qubo`
consumes that mapping directly, without introducing a second model. It expects
an already validated, normalized minimization payload, including finite
coefficients, valid pair indices with `i < j`, and one linear coefficient per
variable. It checks the objective sense and assignment values/length, but is
not a schema validator or normalizer. Assignment entry `i` means `x[i]`;
measurement strings are rejected. This helper evaluates cost, not an optimum.

Before compiler/QAOA integration, coordinate with Developer 2 on:

- One shared Pydantic QUBO model under `app/schemas/`, including duplicate-term
  normalization, binary-square folding, finite-value/index validation, and
  original objective-sense metadata. No shared model exists yet.
- The spec's `run_qaoa(qubo, config)` entry point at `app/quantum/qaoa.py`:
  concrete input/output types, `p`, shots, seed, optimizer/backend selection,
  limits, and error behavior. No callable or config/result classes exist yet.
- Variable-to-qubit mapping and conversion between Qiskit count strings and
  assignment lists. No public measurement-bitstring convention is chosen here.
- Shared circuit-preview helpers so the compiler reuses the same cost layers.
- With the other backend owners and Developer 5, result/status/error fields,
  quality metrics, and timing boundaries (including simulator versus total
  optimization time). No benchmark result schema is implemented here.

## Your next implementation steps

1. Agree on the shared models and bit order with Developer 2.
2. Implement a size-limited brute-force baseline and tiny known-optimum tests.
3. Add NetworkX Max-Cut conversion and verify cut values against QUBO costs.
4. Work through the cost and mixer layers yourself, testing tiny cost-unitary
   phases before adding the optimizer loop and configurable shared runner.
5. Add the heuristic, timing breakdown, and comparable benchmark results later.

QAOA, brute force, heuristics, Max-Cut conversion, and benchmark execution are
deliberately left for that work. This setup makes no performance claims.
