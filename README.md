# Q-Atlas

For the limited quantum-testing allowance, use the
[Qiskit connection setup guide](docs/QUANTUM_CONNECTION_SETUP.md). SDK installation
and the default readiness check submit no jobs; provider authentication/device listing
is a separate operator action. The compiler Test step now offers
[one explicitly confirmed IBM QPU job](docs/COMPILER_IBM_HARDWARE.md), using local
angle training followed by physical sampling.

Q-Atlas is a five-developer quantum computing hackathon project for reproducible,
scientifically honest comparisons with classical methods. It combines a restricted
Python optimization compiler, small spin-system experiments, QAOA optimization, and
Grover search in a SvelteKit application. The original React scaffold is preserved
in `frontend/react-scaffold/` for Developer 5 review; the shared specification is unchanged.

Read the [whole-project scientific report](docs/PROJECT_SCIENTIFIC_REPORT.md) for the
research question, Qiskit approaches, models, classical comparisons, evidence status,
reproduction inputs, citations and limitations across all five experiences.

**Current state: compiler analysis and Python script generation.** Health, safe
Python-to-QUBO analysis, symbolic QAOA circuit previews, and downloadable Qiskit
builder code work. Compiler benchmarking consumes the shared runner entrypoints,
which now implement classical enumeration and local Aer QAOA. Compiler benchmark
requests default to HTTP 501 until the server explicitly enables local execution
with `QATLAS_ENABLE_COMPILER_AER=1`. The compiler UI separately supports an explicit
IBM device selection and one bounded physical sampling job; that flow does not
require the local Aer endpoint flag.
The optimization route at `POST /api/optimization/run` accepts a graph or canonical
QUBO and returns an exact classical baseline and local Aer QAOA comparison. It records
the sampled assignment, objective gap, circuit metrics, timing and provenance in
the [shared result contract](docs/API_CONTRACTS.md). Compiler runner validation uses
mocks and has a local Aer integration smoke test. Circuit previews are constructed
without execution. Other developers' materials and classical work is preserved
alongside the compiler.

Search now runs a bounded local Grover/classical comparison at `POST /api/search/run`,
with measured/theoretical success probabilities, query comparisons, and explicit
timing metadata. See [the search guide](docs/SEARCH.md) for Windows commands, limits,
and API examples. The live Search page at `/search/` provides controls, probability
curves, query/runtime comparisons, errors, and measured JSON export.
Repeated-trial mode adds two to five distinct seeded runs, probability variation,
median runtimes, and raw-record export alongside the summary.
An explicit, dated previously measured fallback and a repeatable API rehearsal command
are documented in the search guide for demo preparation.

See [the compiler guide](docs/COMPILER.md) for supported syntax, diagnostics, limits,
and the mocked QUBO-to-QAOA handoff. The
[Developer 2 next steps](docs/DEVELOPER_2_NEXT_STEPS.md) cover the remaining integration
work and owner handoffs under the current mocks-only constraint.
The [Developer 3 handoff](docs/DEVELOPER_3_HANDOFF.md) records the selected circuit and
solver contracts for optimization integration.

The compiler accepts named local terms, numeric accumulation, bounded literal
`range` loops, and squared penalty expressions inside a marked objective function.
Start with the seven
[pasteable Python examples](examples/compiler/README.md)
and their expected QUBOs. Submitted source is parsed and verified, never executed.
The Svelte compiler page at `/compiler/` uses **load Python → Convert Python →
Download .py**. Put `@qatlas.objective` above the objective; function and input names
are arbitrary, named scalar inputs need no indexing, and width is inferred without
`num_bits`. No circuit function or quantum settings are required. Start with
[named_decisions.py](examples/compiler/programs/named_decisions.py) and the
[script-generation guide](docs/COMPILER_SCRIPT_GENERATION.md). The optional second
`@qatlas.circuit` marker is only for replacing an existing circuit factory.
The page offers [energy-project examples at three through six qubits](examples/compiler/programs/README.md),
defaulting to a six-project selection problem, alongside
three [generated output scripts](examples/compiler/programs/README.md#generated-output-files),
and advanced conversion details plus nonexecuting comparison planning.
Measured results focus on classical solving time and IBM QPU usage, with a runtime
chart and expandable supporting timings. The two readings have distinct scopes;
they are not an end-to-end speedup measurement.
Local numeric weight vectors are supported inside objectives. Test planning remains
nonexecuting; the separate [hardware action](docs/COMPILER_IBM_HARDWARE.md) submits
one confirmed IBM job. User-submitted Python itself is never executed.
See [the manual validation record](docs/COMPILER_MANUAL_CHECKS.md) and
[Developer 5's integration handoff](docs/DEVELOPER_5_HANDOFF.md).

Materials now provides a 2–4-spin TFIM simulation with exact, ideal-circuit, and
finite-shot results; see [the materials guide](docs/MATERIALS.md). No materials
simulations are run as part of compiler validation.

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

From the repository root, after installing dependencies, start both servers from one
terminal (Bash 4.3+):

```sh
./dev.sh
```

In an interactive terminal the launcher prompts for your IBM Quantum API token
(hidden while you paste) and instance name/CRN. Press Enter at the token prompt to
skip. Values are kept only for this launch and passed to the backend, never the
frontend or a saved file. Existing environment credentials are reused. Startup
does not authenticate, run simulations, or submit quantum jobs.
Use `QATLAS_SKIP_QUANTUM_PROMPT=1 ./dev.sh` to skip prompts; non-interactive startup
also skips them automatically.

The launcher works from any current directory when invoked by its path. Both servers
share the terminal output; **Ctrl+C stops both**, including their worker processes.
If either server exits, the other is stopped too. It uses the existing backend virtual
environment and frontend dependencies without installing packages or running experiments.

Open <http://127.0.0.1:5173>. Backend docs are at <http://127.0.0.1:8000/docs>;
health is <http://127.0.0.1:8000/api/health>. Start either server independently.
The frontend serves `/`, `/compiler`, `/neutrinos`, `/materials`, `/optimization`, and
`/search`. The Svelte compiler sends static generation/planning requests; conversion
does not execute user code or run a benchmark. Its Test step can explicitly submit
and retrieve a bounded IBM QPU sample after device selection and authorization.
The Neutrino Lab runs vacuum, matter,
layered propagation, and density sweeps through its own API using normalized inputs;
see [the experiment guide](docs/NEUTRINOS.md). With the quantum extra installed, the
Materials page submits configurable requests and displays returned simulation results,
metrics, and time-series plots. Search runs live comparisons; optimization benchmarks
remain unavailable. React health/request panels remain runnable from
`frontend/react-scaffold/` on port 5174. See [frontend setup](frontend/README.md) for
both applications.

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
npm run test:compiler
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

With the local API running, check the compiler over HTTP from `backend/`:

```sh
.venv/bin/python scripts/check_compiler_api.py
```

This checks health, all seven source examples, and one rejected input. It only calls
health and Analyze, never a solver endpoint. Use `--base-url` for a different API root
and `--timeout` for the socket timeout. See [compiler checks](docs/COMPILER.md).

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
- Shared benchmark endpoints retain synchronous simulator semantics. The compiler's
  separate hardware contracts support explicit single-job submission and retrieval;
  further shared hardware integration requires owner coordination.
