# Seeded classical local search

Developer 3's `run_heuristic(qubo, config)` provides an additional classical baseline
using the established QUBO, QAOAConfig, and SolverResult models. The function lives
in `backend/app/experiments/optimization/heuristics.py`.

The method supports the current 1–16-variable QUBO contract. API baseline selection
and any size-limit extension need coordination with Developer 2 and Developer 5.
The existing compiler and optimization endpoints use the exhaustive baseline.

## Algorithm

1. Begin at the all-zero assignment.
2. Evaluate every assignment obtained by flipping one bit.
3. Move to the lowest-cost neighbor when its cost strictly improves the current cost.
   Equal neighbor costs use API lexicographic order.
4. Stop when every one-bit neighbor has equal or higher cost.
5. Repeat from seven seeded random assignments, using a private `Random(config.seed)`.
6. Return the lowest-cost reached local minimum. Equal final costs select the
   lexicographically smallest reached local-minimum bitstring.

There are eight starts in total. Every cost comes from the shared QUBO evaluator,
including constant offsets and canonical minimization sense. Vertex or variable
`i` remains the left-to-right API bit `x[i]`. The input models and global RNG state
are read-only.

Strictly decreasing moves terminate on the finite assignment space. Plateaus stop
the current search. The algorithm has the identifier `seeded_bit_flip_local_search`
and supplies a valid candidate with an unknown global optimum. Extra starts can
still miss a better basin.

## Reproducible counterexample

For eight independent pairs, assign each variable linear coefficient 1 and each
pair `(0,1), (2,3), ...` coefficient -3. A pair has costs 0, 1, 1, and -1 for
`00`, `01`, `10`, and `11`. Both `00` and `11` are one-bit local minima.

With seed 1 in the tested Python 3.12 environment, eight starts return cost -7.
Exhaustive enumeration gives -8. This example shows how a valid local minimum can
miss the global optimum. Record the Python version when comparing seeded results.

```sh
# From backend/
.venv/bin/python -c '
from app.experiments.optimization.heuristics import run_heuristic
from app.experiments.optimization.solvers import run_classical
from app.schemas.contracts import QUBO, QAOAConfig
problem = QUBO(num_variables=16, linear=[1] * 16, quadratic=[{"i": i, "j": i + 1, "coefficient": -3} for i in range(0, 16, 2)])
config = QAOAConfig(seed=1)
print("heuristic", run_heuristic(problem, config).model_dump_json())
print("exact", run_classical(problem, config).model_dump_json())
'
```

## Timing and interpretation

The method uses `config.seed` and `config.timeout_seconds`. Quantum-specific
configuration fields retain their meanings for the shared QAOA runner.

The monotonic wall-clock interval includes RNG setup, all eight starts, candidate
evaluation, final selection, and result construction. Expiry raises `TimeoutError`.
Objective overflow propagates the shared evaluator's rescaling error.

The classical timing flags follow the exhaustive baseline convention. This path
performs classical search directly. The separate queue, circuit transpilation,
variational angle-optimizer, and shot-sampling phases are absent, and their durations
are null. The complete classical search is included in `elapsed_ms`.

When this method supplies a comparison reference, the global optimality gap stays
unknown. Its algorithm identifier allows the existing comparison code to preserve
that distinction. Compare candidate quality with the exhaustive optimum on small
instances before interpreting runtime measurements.

## Tests

```sh
.venv/bin/python -m pytest tests/optimization/test_heuristics.py -q
.venv/bin/ruff check app/experiments/optimization/heuristics.py tests/optimization/test_heuristics.py
```

Tests cover the exact search trajectory, restart count, seeded reproducibility,
input ownership, canonical sense, offsets, leading zeros, ties, plateaus, dense
16-variable problems, deadline boundaries, measured timing, overflow, the local
minimum counterexample, and comparison handling of an unknown optimum.
