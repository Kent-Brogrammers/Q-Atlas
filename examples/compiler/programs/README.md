# Full-program compiler examples

Load these files as text in **Compiler → Convert Python**, or choose them from
**Example** and click **Load example**. Do not run/import the input files:
the `qatlas` decorators are static source markers, removed in the output.

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
The frontend imports these fixtures as raw text, not executable Python or mock API data.

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
handoff. Both script and quantum execution remain disabled. See
[benchmark planning](../../../docs/COMPILER_BENCHMARK_PLAN.md) and
[script generation](../../../docs/COMPILER_SCRIPT_GENERATION.md).
