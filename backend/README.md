# Developer 3: optimization workspace

The source of truth is [the project specification](../docs/Project_Spec.md).
Shared runtime contracts are in `app/schemas/contracts.py`; the agreed request,
result, bit-order, and timing conventions are documented in
[API contracts](../docs/API_CONTRACTS.md).

## Environment and checks

Use Python **3.12** for Developer 3 work; `backend/.python-version` selects it.
The shared API still supports the Python versions declared in `pyproject.toml`.
From the repository root:

```sh
uv sync --project backend --all-extras --locked --python 3.12
uv run --project backend --all-extras --locked pytest
uv run --project backend --all-extras --locked ruff check backend
uv run --project backend --all-extras --locked ruff format --check backend
```

Quantum dependencies remain an optional extra so API-only contributors do not
need Qiskit. Developer 3 uses `--all-extras` to retain NetworkX, NumPy, SciPy,
Qiskit, and Qiskit Aer. The virtual environment is `backend/.venv`; the lockfile
pins both API and quantum dependencies.
The Aer smoke test skips explicitly in API-only environments without the extra.

This machine uses a working Python 3.12 interpreter under ignored `backend/.python/`
because the initial Homebrew Python had a broken Expat link. Other machines can
use their own Python 3.12 or let uv download it. No system Python is modified.
No IBM credentials or hardware are required.

## Module responsibilities

| Path | Responsibility |
| --- | --- |
| `app/schemas/contracts.py` | Team-owned canonical Pydantic models and normalization. |
| `app/experiments/optimization/classical.py` | Evaluate one binary assignment, including the objective constant. |
| `app/experiments/optimization/solvers.py` | Agreed `run_classical(qubo, config)` stub shared with the compiler. |
| `app/quantum/qaoa.py` | Agreed synchronous `run_qaoa(qubo, config)` stub shared with the compiler. |
| `app/api/optimization.py` | Validated optimization route; currently returns structured HTTP 501. |
| `tests/optimization/test_classical.py` | Hand-calculated values, input guards, and shared-model integration. |
| `tests/optimization/test_shared_interface.py` | Shared runner boundaries remain explicit stubs. |
| `tests/quantum/test_environment.py` | One-qubit local Aer `SamplerV2` installation smoke test. |

`evaluate_qubo` accepts the shared `QUBO` model or a mapping validated through that
model. Duplicate normalization, finite coefficients, and pair-index rules come
from the shared schema. Assignment entry `i` means `x[i]`; strings are rejected.
This is objective evaluation, not optimization. It does not call either runner.

API bitstrings are `x[0]x[1]...x[n-1]`, left to right, with leading zeros preserved.
Qiskit count strings must be converted at the sampler boundary. Preserve the
canonical minimization sense and objective constant in all future results.

## Your next implementation steps

1. Implement a size-limited brute-force baseline behind the agreed `run_classical`
   interface, with known-optimum tests and measured timing.
2. Add NetworkX Max-Cut conversion and verify cut values against QUBO costs.
3. Work through cost/mixer layers and tiny phase tests before implementing the
   shared QAOA runner yourself. Reuse `QAOAConfig` and `QAOAResult`.
4. Enforce `timeout_seconds` throughout execution and populate the shared timing
   flags and measured durations. Do not invent unavailable measurements.
5. Coordinate circuit-preview helpers with Developer 2, baseline/quality formulas
   with backend owners, and result displays with Developer 5.

No QAOA, brute-force solver, heuristic, Max-Cut converter, or benchmark execution
is implemented here. Existing API/schema scaffolding and other owners' modules
are retained from main.
