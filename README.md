# Q-Atlas

Q-Atlas is a five-developer quantum computing hackathon project for reproducible,
scientifically honest comparisons with classical methods. It combines a restricted
Python optimization compiler, small spin-system experiments, QAOA optimization, and
Grover search in a SvelteKit application. The original React scaffold is preserved
in `frontend/react-scaffold/` for Developer 5 review; the shared specification is unchanged.

**Current state: materials experiment plus shared development foundation.** Health works;
materials runs a 2–4-spin transverse-field Ising experiment with exact, ideal circuit,
and finite-shot results. Compiler, optimization, and search operations remain HTTP 501
stubs. See [the materials guide](docs/MATERIALS.md) for physics, examples, limits, and tests.

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
    ├── package.json               # primary SvelteKit application
    ├── src/
    │   ├── routes/                # overview + four experiment views
    │   ├── lib/                   # reusable controls, graphs, example displays
    │   ├── api/client.ts          # one shared typed transport
    │   └── types/                 # canonical OpenAPI-generated types
    ├── tools/api-types/           # isolated TypeScript 5 generator workspace
    └── react-scaffold/            # preserved React application on port 5174
```

## Setup and run

Prerequisites: Python 3.11+ (Developer 3 uses Python 3.12), [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Node.js 22.17+ (22 LTS or 24+). The lockfiles pin resolved compatible packages.
SvelteKit uses TypeScript 6; the OpenAPI generator is isolated in a workspace
using TypeScript 5.9 to satisfy its peer range. The frontends use
[Vite](https://vite.dev/guide/) and the
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
Use **Check API health** on the overview to test the connection. With the quantum extra
installed, the materials page's request panel displays real simulation results; its UI
labels are still the integration owner's scaffold. Other experiment pages show real 501 responses.
SvelteKit preserves the developed dashboard and displays example data only after
an explicit example action; it sends no live experiment requests. Main's original
React health/request panels remain runnable from `frontend/react-scaffold/` on
port 5174. See [frontend setup](frontend/README.md) for both applications.

No environment file or credentials are required. Optional overrides:

- Backend: `QATLAS_CORS_ORIGINS`, a comma-separated list, defaulting to
  `http://localhost:5173,http://127.0.0.1:5173`. Set in the backend shell.
- Frontend: `VITE_API_BASE_URL`, default `http://127.0.0.1:8000/api`. Set in the
  frontend shell before starting Vite, or in an ignored frontend `.env.local`.
  Every `VITE_` value is public browser configuration; never put secrets there.

## Verify

From `backend/`:

```sh
uv run --locked --all-extras python -c 'from app.main import app; print(app.title)'
uv run --locked --all-extras pytest
uv run --locked --all-extras ruff check .
uv run --locked --all-extras ruff format --check .
```

From `frontend/`:

```sh
npm run types:check
npm run check
npm test
npm run format:check
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
| Developer 1 | `backend/app/experiments/materials/`, `api/materials.py`, `tests/materials/` | TFIM implemented; start with the physics and convergence tests |
| Developer 2 | `backend/app/compiler/`, `api/compiler.py`, `tests/compiler/` | Allowlisted marked AST, diagnostics, normalized QUBO; consume shared runners |
| Developer 3 | `backend/app/quantum/qaoa.py`, `experiments/optimization/solvers.py`, `api/optimization.py`, `tests/optimization/` | QUBO evaluation and classical reference, then shared QAOA and fair timings |
| Developer 4 | `backend/app/experiments/search/`, `api/search.py`, `tests/search/` | Marked-state oracle with explicit wire ordering and query assumptions |
| Developer 5 | `frontend/src/routes/`, `src/lib/`, `src/api/`; preserved `frontend/react-scaffold/` | Review SvelteKit integration and connect typed requests while preserving live errors/loading |

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

- Materials now fixes an open TFIM chain, all-zero initial state, second-order Trotter
  evolution, and dimensionless units with hbar=1; see [the implementation guide](docs/MATERIALS.md).
- Optimization owner must define Max-Cut conversion, baseline selection, gap/ratio
  formulas, and optimizer stopping behavior. Requests accept graphs, but no conversion exists yet.
- Search owner must specify oracle construction cost and classical query assumptions.
- Materials enforces a wall-clock budget using a disposable simulation process. Other
  owners must enforce their runners' budgets; field validation alone cannot stop native work.
- The initial API is synchronous and simulator-only. Any async jobs or hardware contracts
  require coordinated changes, rather than silently extending current semantics.
