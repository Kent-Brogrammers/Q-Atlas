# Q-Atlas

Q-Atlas is a five-developer quantum computing hackathon project for reproducible,
scientifically honest comparisons with classical methods. It combines a restricted
Python optimization compiler, small spin-system experiments, QAOA optimization, and
Grover search in one React application.

**Current state: compiler analysis plus development foundation.** Health and safe
Python-to-QUBO analysis work. Compiler benchmarking is wired to the shared runner
interfaces, which remain Developer 3 stubs; supported benchmark requests and the
other experiment routes return HTTP 501. Execution is mocked in compiler tests only.
There are no circuit/solver implementations or experimental measurements.

See [the compiler guide](docs/COMPILER.md) for supported syntax, diagnostics, limits,
and the mocked QUBO-to-QAOA handoff.

Read [the original specification](docs/Project_Spec.md) completely before implementing
features. The original file and its casing are preserved.

## Repository

```text
.
├── AGENTS.md
├── README.md
├── docs/
│   ├── Project_Spec.md             # original source of truth
│   ├── API_CONTRACTS.md
│   └── BENCHMARK_METHODOLOGY.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── scripts/export_openapi.py
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                    # one route module per feature + errors
│   │   ├── schemas/contracts.py    # canonical Pydantic contracts
│   │   ├── compiler/               # Developer 2
│   │   ├── quantum/qaoa.py         # Developer 3 shared runner stub
│   │   ├── experiments/
│   │   │   ├── materials/          # Developer 1
│   │   │   ├── optimization/       # Developer 3; classical runner stub
│   │   │   └── search/             # Developer 4
│   │   └── benchmarks/            # shared timing/result assembly
│   └── tests/                     # api, schemas, compiler, materials, optimization, search
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx                # overview + four feature routes
        ├── pages/                 # Developer 5
        ├── components/            # minimal request/response panels
        ├── api/client.ts          # typed fetch client
        └── types/                 # generated API types + named exports
```

## Setup and run

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Node.js 22.12+ (22 LTS or 24+). The lockfiles pin resolved compatible packages.
The TypeScript 5.9 pin is intentional: the OpenAPI generator's peer range is TypeScript 5.
The frontend uses [Vite](https://vite.dev/guide/) and the
[Tailwind Vite plugin](https://tailwindcss.com/docs/installation/using-vite).

From the repository root, in the backend terminal:

```sh
cd backend
uv sync --locked
uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

This installs only API/dev dependencies. Quantum developers also run
`uv sync --locked --all-extras` and use `uv run --locked --all-extras ...` so uv retains
NumPy, SciPy, Qiskit, Qiskit Aer, and NetworkX. No IBM account is needed.

In a separate terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Backend docs are at <http://127.0.0.1:8000/docs>;
health is <http://127.0.0.1:8000/api/health>. Start either server independently.
The frontend serves `/`, `/compiler`, `/materials`, `/optimization`, and `/search`.
Use **Check API health** on the overview to test the connection. Compiler analysis
returns a real QUBO; benchmark/other experiment requests show real 501 responses.
Sample inputs contain no measured results.

No environment file or credentials are required. Optional overrides:

- Backend: `QATLAS_CORS_ORIGINS`, a comma-separated list, defaulting to
  `http://localhost:5173,http://127.0.0.1:5173`. Set in the backend shell.
- Frontend: `VITE_API_BASE_URL`, default `http://127.0.0.1:8000/api`. Set in the
  frontend shell before starting Vite, or in an ignored frontend `.env.local`.
  Every `VITE_` value is public browser configuration; never put secrets there.

## Verify

From `backend/`:

```sh
uv run --locked python -c 'from app.main import app; print(app.title)'
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

From `frontend/`:

```sh
npm run types:check
npm run typecheck
npm run build
```

`types:check` exports OpenAPI using `backend/.venv/bin/python` and checks that committed
TypeScript matches. Backend setup is needed for this check, but the frontend server
and build run independently using the committed generated types. Following a contract
change, run `npm run types:generate` from `frontend/`, review the generated diff, and
commit the types with the backend change. `frontend/openapi.json` is ignored intermediate output.

## Developer handoff

| Owner | Begin here | First owned implementation/test |
| --- | --- | --- |
| Developer 1 | `backend/app/experiments/materials/`, `api/materials.py`, `tests/materials/` | Define Hamiltonian signs/units; known two-spin reference |
| Developer 2 | `backend/app/compiler/`, `api/compiler.py`, `tests/compiler/` | Allowlisted marked AST, diagnostics, normalized QUBO; consume shared runners |
| Developer 3 | `backend/app/quantum/qaoa.py`, `experiments/optimization/solvers.py`, `api/optimization.py`, `tests/optimization/` | QUBO evaluation and classical reference, then shared QAOA and fair timings |
| Developer 4 | `backend/app/experiments/search/`, `api/search.py`, `tests/search/` | Marked-state oracle with explicit wire ordering and query assumptions |
| Developer 5 | `frontend/src/pages/`, `components/`, `api/`, `App.tsx` | Replace minimal request panels with controls; preserve live errors/loading |

All backend paths in the table are relative to `backend/` where shortened. Shared
contracts are in `backend/app/schemas/contracts.py`; timing guidance is in
[benchmark methodology](docs/BENCHMARK_METHODOLOGY.md). Developer 3 coordinates benchmark
helpers with all owners. No second QAOA engine belongs in the compiler.

## Branches and pull requests

1. Branch from updated `main`: `git switch -c codex/<module>-<change>` (or the team's agreed prefix).
2. Keep each PR within its owner's module; coordinate cross-module contracts first.
3. Include the problem, resulting behavior, and exact validation commands/results.
4. Include regenerated frontend types whenever contracts change. Ask the impacted
   owner(s) to review. Never commit local environments, credentials, or fabricated results.
5. Merge small vertical slices after relevant checks pass. Do not replace stubs in
   other owners' modules as part of unrelated work.

## Integration decisions still owned by the team

- Materials owner must select the exact Hamiltonian, estimation method, sign convention,
  and physical or dimensionless units before producing results.
- Optimization owner must define Max-Cut conversion, baseline selection, gap/ratio
  formulas, and optimizer stopping behavior. Requests accept graphs, but no conversion exists yet.
- Search owner must specify oracle construction cost and classical query assumptions.
- Each owner must enforce the declared runtime budget inside their eventual implementation;
  `timeout_seconds` validation alone does not interrupt Python or native simulator work.
- The initial API is synchronous and simulator-only. Any async jobs or hardware contracts
  require coordinated changes, rather than silently extending current semantics.
