# Developer 4: first Grover milestone

This milestone is a local circuit demo, not the completed search benchmark. The
search HTTP endpoint remains an explicit 501 stub. Shared contracts and frontend
types are unchanged.

## Windows setup

Open the repository root in VS Code and select branch `Layth`. The initial setup
installed project-local uv at `backend/.cache/tools/uv.exe`, Python 3.12 under
`backend/.python/`, and dependencies in `backend/.venv/`. These folders are ignored
by Git. No global Python installation, IBM account, or credentials are needed.

For VS Code's Python interpreter, select `backend/.venv/Scripts/python.exe`.
From a PowerShell terminal at the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.experiments.search.demo
.\.venv\Scripts\python.exe -m pytest tests/search tests/quantum
.\.venv\Scripts\ruff.exe check app/experiments/search tests/search
.\.venv\Scripts\ruff.exe format --check app/experiments/search tests/search
```

On another machine with uv installed, reproduce the locked environment from the
repository root using `uv sync --project backend --locked --all-extras --python 3.12`.
The local download of uv is a convenience, not a committed project dependency.

## Circuit and interpretation

`build_grover_circuit(marked_state, iterations, measure=True)` supports one target,
1–6 qubits, and 0–32 iterations. These are local circuit-helper limits; the existing
API request schema is unchanged. The oracle uses X gates for target zero bits and
a multi-controlled phase flip. Diffusion reflects about the uniform state, up to
global phase. Each Grover step makes one oracle call per circuit execution.

Displayed strings follow the team's convention: character i is qubit i, left to
right. Qiskit measurement strings list the highest classical bit first, so the
demo reverses them before reporting counts. Leading zeros are preserved.

The demo uses target `101`, two iterations, 1024 shots, and seed 42. It prints
measured counts and success probability alongside ideal theory:

`P(k) = sin²((2k + 1) asin(1 / sqrt(N)))`, with `N = 2^num_qubits`.

The ideal probability is 0.9453125 for this example; measured values fluctuate.
Recorded wall time includes circuit/oracle construction, backend initialization,
transpilation, sampling, and count conversion, but excludes imports and printing.
Depth is measured after transpilation to Aer, not to a physical device's gates.
Shots are repeated circuit executions; k oracle calls refers to one execution,
not the entire sampling batch. This is an ideal simulator, not a hardware run.

The application already knows the target to construct the oracle. Query complexity
assumes oracle access; constructing an explicitly marked circuit is not free, and
this experiment cannot establish practical quantum speedup.

## Next small milestones

1. Add a classical no-replacement search baseline and query assumptions/tests.
2. Add an iteration sweep comparing theoretical and sampled success probabilities.
3. Integrate the existing search response contract and enforce runtime limits before
   enabling the API; coordinate result/timing interpretations with Developers 3/5.
4. Connect the search page with Developer 5 and rehearse a reproducible demo.

Keep commits grouped by completed behavior: circuit foundation, classical baseline,
probability sweep, then API integration. Review and approval precede each commit.
