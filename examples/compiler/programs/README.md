# Full-program compiler examples

Load these files as text in **Compiler → Convert Python**, or choose them from
**Example** and click **Load example**. The picker now uses the portfolio family
below; the older supported/rejected fixtures remain available as files for
compiler diagnostics. Do not run/import the input files:
the `qatlas` decorators are static source markers, removed in the output.

## Energy-project portfolios (current UI examples)

Choose the highest-impact projects while meeting a fixed selection target.
Each named binary decision maps to one qubit. A squared penalty of 30 enforces
the selection count, and solar/storage and insulation/heating pairs get synergy
bonuses when those projects are present. The UI defaults to the six-qubit case.

| Input | Selection target | Exact canonical minimum |
| --- | --- | --- |
| [portfolio_3.py](portfolio_3.py) | 1 of 3 projects | -8 |
| [portfolio_4.py](portfolio_4.py) | 2 of 4 projects | -15 |
| [portfolio_5.py](portfolio_5.py) | 2 of 5 projects | -15 |
| [portfolio_6.py](portfolio_6.py) | 3 of 6 projects | -22 |

These are mathematical reference values, not measured QPU results. Tests verify
the compiled objective against independent arithmetic for all 8–64 assignments.
For six qubits, `110100` selects solar, insulation and storage and attains -22.
All four examples use one objective decorator and preserve a normal Python caller.
The one-layer hardware path supports all four, with the same 128 shots and
10-second requested QPU cap; larger circuits can still be rejected by the provider
if the cap is insufficient. Loading or converting never submits a job.

## Stress examples (also in the UI picker)

| Input | What it stresses | Exact canonical minimum | One optimal API bitstring |
| --- | --- | ---: | --- |
| [stress_maxcut_6.py](stress_maxcut_6.py) | 15 weighted interactions, competing triangle edges | -57 | `000111` |
| [stress_partition_6.py](stress_partition_6.py) | Load balancing, count constraint, 15 interactions and a broad penalty scale | 4 | `010110` |
| [stress_conflicts_6.py](stress_conflicts_6.py) | Task rewards versus nine conflicts, including two triangles | -10 | `010100` |

These exact values come from independent arithmetic over all 64 assignments,
verified against compilation in tests. They are not sampled quantum results.
For partitioning, the total load is 90, but no allowed selection reaches load 45;
the optimum selects three tasks with load 43 or 47. For task selection, the best
conflict-free reward is 10. API bitstrings put `x[0]` first.

All three use the current six-qubit compiler ceiling. They stress connectivity,
penalties, and solution quality; they cannot make 64-candidate classical enumeration
computationally difficult. More layers or larger penalty coefficients alone do not
establish a harder classical problem or a quantum speedup. Hardware submission
still requires its existing explicit confirmation and quota limits.

For **8-, 12-, and 16-qubit local examples** and exact/heuristic/QAOA comparisons,
see [the scaling guide](../../../docs/STRESS_EXAMPLES.md). Those use the existing
shared runner directly; the compiler's width limit is unchanged.

## Additional syntax and rejection fixtures

| Input | Expected result | Reason/reference |
| --- | --- | --- |
| [named_decisions.py](named_decisions.py) | Supported | One bare decorator; arbitrary function name and three named scalar choices; ordinary helpers/main preserved |
| [weighted_selection.py](weighted_selection.py) | Supported | Dataclass report/helper/main preserved; local tuple weights and a squared selection penalty compiled |
| [weighted_maximize.py](weighted_maximize.py) | Supported | JSON report/helper/main preserved; local list weights and conflicts compiled with canonical minimization |
| [rejected_helper_call.py](rejected_helper_call.py) | Rejected: `UNSUPPORTED_SYNTAX` | Calling a user helper inside the objective is outside the allowlist |
| [rejected_dynamic_loop.py](rejected_dynamic_loop.py) | Rejected: `INVALID_LOOP` | A binary input controls a loop bound |
| [rejected_higher_order.py](rejected_higher_order.py) | Rejected: `HIGHER_ORDER` | A three-variable product is not quadratic |

[expected.json](expected.json) records independent coefficients and expected rejection
codes. It is separate from the original seven-case objective-only smoke manifest.
The frontend imports its selected fixtures as raw text, not executable Python or mock API data.

The selection case has constant 24, linear coefficients [-21,-19,-22,-20], and all
six pair coefficients 12. Its mathematical minimum is -7 at `1010`, choosing weights
3 and 4 with exactly two selections. The maximization case has canonical constant 0,
linear [-2,-7,-3], pairs (0,1)=4 and (1,2)=6, and canonical minimum -7 at `010`;
its original maximization value is 7. These are arithmetic references, not measurements.

## Generated output files

- [named_decisions_qaoa.py](generated/named_decisions_qaoa.py)
- [weighted_selection_qaoa.py](generated/weighted_selection_qaoa.py)
- [weighted_maximize_qaoa.py](generated/weighted_maximize_qaoa.py)

These are one-layer generated snapshots, formatted with Ruff. The marked circuit
factory was replaced and the surrounding Python preserved. Tests compare each
snapshot's AST with fresh compiler output, so formatting does not hide stale logic.
Neither snapshot has been executed. Calling its builder manually would require
Qiskit and return an unbound circuit; no solver or job submission is generated.

For a supported input, **Prepare comparison** downloads a manifest containing the
verified instance, requested configuration, source/generated hashes, and runner
handoff. Planning executes neither script nor solver. The separate explicitly
confirmed [IBM hardware action](../../../docs/COMPILER_IBM_HARDWARE.md) samples
the extracted objective without executing the surrounding application. See
[benchmark planning](../../../docs/COMPILER_BENCHMARK_PLAN.md) and
[script generation](../../../docs/COMPILER_SCRIPT_GENERATION.md).

The compiler also includes [neutrino_simulation.py](neutrino_simulation.py), a
`@qatlas.neutrino` scientific declaration. It generates the Neutrino Lab's exact
propagation circuits and compares them with an independent classical reference.
It is separate from binary QUBO examples; see
[the compiler walkthrough](../../../docs/COMPILER_NEUTRINO_EXAMPLE.md).
