# Q-Atlas — Codex Project Specification

> **Purpose:** This is the shared implementation brief for a five-person quantum hackathon team. Treat it as the source of truth for architecture, module contracts, deliverables, and integration. It is **not** permission to implement the entire project in one pass.

## 1. Mission

Build **Q-Atlas**, a web application for exploring quantum computing through reproducible, scientifically honest comparisons with classical methods. The platform includes four technical experiences:

1. **Python optimization compiler:** analyze a supported subset of Python objectives, extract a QUBO, and produce a QAOA-compatible circuit and benchmark.
2. **Quantum materials:** model a small spin system and compare a quantum approach with an exact classical reference.
3. **Optimization:** benchmark QAOA against classical Max-Cut/QUBO solvers.
4. **Search:** benchmark Grover's algorithm against classical unstructured search, separating query complexity from measured runtime.

All experiences are accessible through a unified React dashboard. **Do not claim quantum speedup unless supported by measured results and a fair comparison.** Simulator execution is not equivalent to running on a QPU.

## 2. Team ownership

| Owner | Area | Primary responsibility |
|---|---|---|
| Developer 1 | Quantum materials | Spin Hamiltonian, quantum simulation, classical exact reference, material-specific results |
| **Developer 2 (project proposer)** | **Python-to-quantum compiler** | **AST validation, symbolic extraction, QUBO conversion, circuit generation/integration, diagnostics, compiler tests** |
| Developer 3 | Optimization benchmark | Reusable QAOA solver, classical baselines, Max-Cut experiment, benchmark instrumentation |
| Developer 4 | Search benchmark | Grover circuit/oracle, classical search, success probabilities, query/runtime comparison |
| Developer 5 | Frontend and app integration | React UI, code editor, charts, experiment controls, API wiring, error/loading states |

The compiler owner and optimization owner **must share** a QUBO schema and a QAOA execution API. Do not duplicate QAOA engines. Frontend owner coordinates API integration; backend owners remain responsible for exposing their endpoints.

## 3. Scope and non-goals

### MVP
- Works entirely locally with Python and Qiskit Aer; IBM hardware is optional.
- Four accessible sections in the frontend, each with a real working demo.
- One shared benchmark-result schema with experiment-specific metadata.
- A compiler that handles a **restricted, documented subset** of binary polynomial objectives, with explicit errors for unsupported syntax.
- Automated tests and reproducible examples for each experiment.

### Not in MVP
- Arbitrary Python-to-quantum compilation or general-purpose speedups.
- Executing untrusted uploaded Python in the API process.
- Large-scale materials simulations or claims of practical quantum advantage.
- Real hardware as a dependency for the live demo.
- Authentication, billing, cloud infrastructure, or complex job orchestration unless time remains.

## 4. Proposed stack

- **Backend:** Python 3.11+, FastAPI, Pydantic, NumPy, SciPy, Qiskit, Qiskit Aer, pytest.
- **Compiler:** Python `ast` and optionally SymPy; no regex-based parsing and no LLM required for compilation.
- **Optimization:** Qiskit circuits, Qiskit Aer, SciPy classical optimizer, NetworkX for graphs.
- **Frontend:** React + TypeScript + Vite, Tailwind CSS, Monaco Editor (optional), a charting library.
- **Hardware (stretch):** `qiskit-ibm-runtime`, credentials stored in environment variables only.
- **Quality:** Ruff, pytest, TypeScript checks; pin dependencies after a working environment is established.

Avoid relying on legacy Qiskit tutorial APIs without checking installed versions.

## 5. Suggested repository layout

```text
q-atlas/
├── AGENTS.md                     # repo-wide instructions for Codex
├── README.md
├── docs/
│   ├── PROJECT_SPEC.md           # this document
│   ├── API_CONTRACTS.md
│   └── BENCHMARK_METHODOLOGY.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                  # routes for compile, optimization, search, materials
│   │   ├── schemas/              # shared Pydantic models
│   │   ├── compiler/             # AST -> polynomial -> QUBO
│   │   ├── quantum/              # shared QAOA runner and circuit helpers
│   │   ├── experiments/
│   │   │   ├── optimization/
│   │   │   ├── search/
│   │   │   └── materials/
│   │   └── benchmarks/           # timing, validation, result assembly
│   └── tests/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── api/
│       └── types/
└── examples/
    ├── supported_objective.py
    └── sample_experiments.json
```

This is a recommendation, not a mandate to create empty directories or boilerplate before useful work begins.

## 6. Shared contracts — agree on these before implementation

### 6.1 QUBO representation

Use a portable JSON-compatible representation, **not** Python tuple keys in API JSON:

```json
{
  "num_variables": 3,
  "constant": 0.0,
  "linear": [10.0, 20.0, 0.0],
  "quadratic": [{"i": 0, "j": 1, "coefficient": 15.0}],
  "sense": "minimize"
}
```

Meaning: `C(x) = constant + sum(linear[i] * x[i]) + sum(quadratic[k].coefficient * x[i] * x[j])`, for binary `x[i] in {0,1}`. Require `i < j` for pair terms; fold `x[i]**2` into linear coefficients because binary squares equal themselves. Normalize duplicate terms, reject invalid indices/non-finite coefficients, and document bit order. Keep objective **minimization** canonical; convert maximization by negating coefficients and track the original sense for display.

### 6.2 Benchmark result

```json
{
  "experiment": "optimization",
  "problem_id": "maxcut-demo-1",
  "backend": "aer_simulator",
  "classical": {"algorithm": "brute_force", "elapsed_ms": 12.0, "objective": -4.0},
  "quantum": {"algorithm": "qaoa", "elapsed_ms": 1840.0, "objective": -4.0},
  "metrics": {"num_qubits": 4, "circuit_depth": 24, "shots": 1024},
  "metadata": {"seed": 42, "timing_scope": "end_to_end", "simulated": true}
}
```

**Example values are placeholders, not experimental evidence.** Allow nullable/not-applicable fields and experiment-specific metrics. Include error and status representations. Record whether queue time, transpilation, optimizer iterations, and shot sampling are included in each timer. Prefer repeated runs and report distributions when feasible.

### 6.3 Suggested API endpoints

- `POST /api/compiler/analyze` — accept source text, return supported/rejected status, diagnostics, normalized QUBO and circuit metadata if possible. **Parse only; never execute arbitrary source.**
- `POST /api/compiler/benchmark` — run validated extracted objective through approved classical/QAOA solvers.
- `POST /api/optimization/run` — graph or QUBO input; return classical and QAOA comparison.
- `POST /api/search/run` — search space, marked states, iteration settings; return probability and query comparisons.
- `POST /api/materials/run` — small spin-model parameters; return quantum and classical observables.
- `GET /api/health` — readiness.

Use Pydantic models for request/response validation. Define timeout/size limits and clear failure messages. For expensive runs, add asynchronous job endpoints only if necessary.

## 7. Compiler — Developer 2 (owned by project proposer)

### User experience
User pastes Python into the code editor and clicks **Analyze**. Q-Atlas highlights a recognized objective, shows extracted variables/terms and compiler diagnostics, renders the generated circuit, and offers **Run comparison**. Show measured performance and objective quality; don't label QAOA automatically “optimized” or “faster.”

### Supported syntax, initial milestone
- Explicitly marked objective function (e.g., `@qatlas.objective(num_bits=3)`). The annotation is a **marker inspected in source**, not code that the API executes.
- One return expression with numeric constants, binary-variable indexing `x[0]`, `+`, `-`, multiplication by constants, and pairwise `x[i]*x[j]`.
- Parentheses and unary negation.
- Optional later: local assignments, fixed-range loops, constant folding, bounded helper constructs.
- Reject function calls, imports, arbitrary attribute access, data-dependent loops, unknown names, higher-order terms, dynamic indices, and unsupported statements in the initial version.

### Pipeline
`source -> ast.parse -> find marked function -> validate allowlisted AST -> symbolic polynomial IR -> normalize QUBO -> verify -> circuit generation -> benchmark`.

**Do not execute source to extract its meaning.** AST parsing alone is not semantic validation: track variable scope, operator semantics, and constants carefully. SymPy can simplify expressions after validation, but is not an arbitrary-Python compiler.

### Correctness checks
- For small `n`, evaluate the extracted objective and QUBO over all `2^n` binary assignments using a safe interpreter of the supported AST, not `eval` or `exec`.
- Unit tests for signs, constant offsets, repeated terms, `x_i^2`, variable order, unsupported syntax, and malicious-looking inputs.
- Circuit cost-unitary checks for tiny problems (up to irrelevant global phase), plus end-to-end comparison against exact classical optimum.

### Circuit mapping
For `C(x) = c + sum a_i x_i + sum b_ij x_i x_j`, use a QAOA cost layer implementing `exp(-i gamma C)`, with e.g. `RZ(-gamma*a_i)` for linear terms and `CP(-gamma*b_ij)` for pair terms, up to a global phase for the RZ mapping. Add RX mixer layers and a classical optimizer through the **shared** QAOA runner. Verify phase/sign conventions in tests.

### Integration agreement
Compiler exports a validated QUBO and diagnostics. Optimization module owns reusable `run_qaoa(qubo, config)` and classical solver interfaces. Compiler may provide circuit previews via shared circuit helpers, but must not fork a second QAOA implementation.

### Definition of done
A user submits a supported three-to-six-bit objective; the compiler extracts the correct QUBO, rejects unsupported inputs with helpful messages, and the frontend can launch a reproducible benchmark against a classical solver.

## 8. Materials — Developer 1

- Start with a 2–4-spin Ising or Heisenberg model, not a realistic bulk material.
- Construct a Hamiltonian with explicit units and boundary conditions.
- Implement a quantum simulation/estimation method feasible on Aer; compare a defined observable (e.g., energy or magnetization) to exact diagonalization using NumPy/SciPy.
- Expose spin count, coupling, and field controls. Plot observables and absolute error.
- Explain whether “quantum” refers to statevector simulation, shot-based circuit simulation, or QPU execution.
- Tests: known two-spin cases, Hermitian Hamiltonian, dimensions, reference agreement.
- **Done:** one parameterized example produces reproducible classical and quantum results with meaningful plots.

## 9. Optimization — Developer 3

- Build Max-Cut instances with NetworkX and convert to canonical minimization QUBO.
- Implement classical brute force for small `n` and a documented heuristic for larger `n`.
- Implement reusable QAOA with configurable layers `p`, shots, seed, classical optimizer, and backend.
- Return best bitstring, objective, approximation/optimality gap where exact optimum is known, optimizer evaluations, circuit depth, and timing breakdown.
- Separate simulator execution time from end-to-end QAOA optimization time.
- Tests: QUBO cost consistency, tiny Max-Cut known optima, deterministic seeded simulator smoke tests.
- **Done:** a 4–8-vertex graph runs both solvers and returns valid comparable results; compiler can call the QAOA interface.

## 10. Search — Developer 4

- Build a phase oracle for explicitly marked bitstrings; document oracle construction assumptions.
- Implement Grover diffusion and configurable iteration count on small search spaces.
- Compare measured success probabilities with theory and classical expected/worst-case oracle queries.
- **Do not** compare one quantum oracle call to an arbitrarily expensive classical predicate without accounting for oracle implementation.
- Plot success probability versus iterations; record qubit count, depth, shot count, and wall-clock runtime.
- Tests: one marked state in 2–4 qubits, expected amplitude amplification behavior, correct measurement bit ordering.
- **Done:** users can pick a marked state and see quantum success probability and fair query-complexity comparison.

## 11. Frontend and integration — Developer 5

- Build four experiment routes plus a landing/dashboard page.
- Use typed API clients and reusable result panels: metrics, timing breakdown, charts, backend badges, errors.
- Compiler page: source editor, **Analyze**, diagnostics with line numbers, extracted QUBO, circuit preview, **Run comparison**.
- Materials page: Hamiltonian parameters and observable plots.
- Optimization page: graph controls/visualization, solver comparison.
- Search page: marked-state/iteration controls and success probability chart.
- Start with mock API payloads matching shared schemas, then wire live endpoints.
- Make loading, failure, and long-running operations obvious; avoid fake live data in final demo.
- **Done:** a user can navigate to every experiment, submit a request, and see real backend results.

## 12. Benchmark methodology and scientific guardrails

1. Compare the **same mathematical problem and input instance** on classical and quantum paths.
2. Distinguish **objective evaluation** from **optimization**: a function `cost(x)` is not a classical solver. If users provide only an objective, compare generated solvers, not the time to call `cost(x)` versus time to optimize with QAOA.
3. Record solution quality and constraint validity alongside runtime.
4. Distinguish **theoretical query/gate complexity**, **simulator runtime**, and **real-QPU runtime**.
5. For QPU runs, report queue, transpilation, optimization loop, sampling, and total time separately where measurable.
6. Label stochastic results; include shots, seeds, repetition count, and optimizer settings.
7. Don't imply that statevector simulation provides hardware speedup.
8. Display unsupported/not-applicable metrics as such; never fabricate data.

## 13. Security and reliability

- **Never execute untrusted Python uploads** in the API server. `ast.parse` plus a strict allowlist is the MVP path.
- No `eval`, `exec`, or dynamic import of user-submitted code.
- Limit source length, AST depth/node count, number of binary variables, shot count, optimizer iterations, and runtime.
- Keep IBM credentials and API keys out of Git and logs; use `.env` locally with `.gitignore`.
- Return structured errors rather than stack traces to users.
- Use simulator fallback for all demos.

## 14. Implementation sequence and integration checkpoints

### Day 1: contracts and skeleton
- Agree on QUBO, result schemas, bit order, and API endpoints.
- Set up backend/frontend development commands, tests, linting, and mock responses.
- Each owner commits a minimal vertical slice to their module.

### Days 2–3: independent MVPs
- Compiler: parse and extract a tiny QUBO with tests.
- Optimization: run classical baseline and QAOA on a tiny QUBO.
- Materials: compare a tiny spin system to exact diagonalization.
- Search: run a known Grover instance and show measured success probability.
- Frontend: all four routes and mocked result views.

### Days 4–5: connect real results
- Wire compiler QUBO into optimization runner.
- Expose stable endpoints; integrate frontend one route at a time.
- Add timing and accuracy metadata; fix inconsistent conventions.

### Final days: hardening and demo
- Add failure cases, test reproducibility, optimize demo runtimes, and prepare cached fallback outputs **clearly labeled as previously measured**.
- Try IBM hardware only if account access, queue, and time permit.
- Freeze scope early enough to rehearse an end-to-end demo.

## 15. Codex working rules

1. **Read this spec and the repository before editing.** Identify which module the current task concerns.
2. **Stay within the assigned module** unless explicitly asked to modify shared schemas or integration code.
3. Before implementing cross-module changes, state the proposed interface and impacted owners.
4. Prefer the smallest working implementation with tests over broad scaffolding.
5. Run relevant tests and type/lint checks; report what passed and what couldn't run.
6. Never silently change the QUBO schema, bit order, objective sense, or benchmark timing definitions.
7. Do not introduce MCP servers or third-party packages unless they solve a concrete need.
8. Do not claim a benchmark improvement without recorded experimental evidence.
9. Ask before running hardware jobs that use external quotas or credentials.
10. For user-submitted Python, parse/validate only; do not execute it.

## 16. Suggested initial Codex prompts

**Compiler owner:**
> Read `docs/PROJECT_SPEC.md`. Implement only the compiler MVP: allowlisted AST parser for marked binary objective functions, normalized QUBO schema, structured diagnostics, and exhaustive correctness tests for up to six variables. Coordinate through the shared QUBO schema; do not implement a second QAOA engine. First inspect the repository and propose a small file-by-file plan.

**Optimization owner:**
> Read `docs/PROJECT_SPEC.md`. Implement the canonical QUBO evaluator, brute-force baseline, reusable QAOA runner, and a small Max-Cut example. Document sign and bit-order conventions, benchmark end-to-end time, and add tests. First inspect the repository and propose a small plan.

**Materials owner:**
> Read `docs/PROJECT_SPEC.md`. Build a 2–4-spin Ising model experiment with a Qiskit simulation and a NumPy/SciPy exact reference, then expose reproducible observables and tests. First inspect the repository and propose a small plan.

**Search owner:**
> Read `docs/PROJECT_SPEC.md`. Implement a small Grover search benchmark with a marked-state oracle, success-probability curves, classical query comparisons, and tests. Separate query complexity from measured runtime. First inspect the repository and propose a small plan.

**Frontend owner:**
> Read `docs/PROJECT_SPEC.md`. Build the React app with four experiment pages, a shared typed API client, and mock data matching the agreed response schemas. Prioritize a functioning end-to-end UX, then connect live endpoints. First inspect the repository and propose a small plan.

## 17. Final acceptance checklist

- [ ] Compiler recognizes and correctly translates a supported objective.
- [ ] Unsupported Python is rejected safely with useful diagnostics.
- [ ] Compiler and optimization modules share one QUBO/QAOA interface.
- [ ] Optimization, search, and materials experiments each produce real reproducible results.
- [ ] Classical comparisons solve the same problem and report quality as well as runtime.
- [ ] Frontend displays all four features and handles errors/loading.
- [ ] At least one end-to-end live demo works without IBM hardware.
- [ ] Tests run and dependencies/setup instructions are documented.
- [ ] No unsupported claims of quantum advantage or fabricated measurements.
