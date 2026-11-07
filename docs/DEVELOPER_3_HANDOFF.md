# Compiler -> optimization handoff

These are the interface decisions selected by Developer 2 while implementing the
compiler pipeline. The project proposer authorized making these decisions ahead of
Developer 3's work and will relay this document. The original specification is
unchanged. Developers 3 and 5 are the impacted owners.

## Execution remains mocked

Do not use the supercomputer, hardware, external quotas, credentials, or run simulator
jobs under the current instruction. `run_classical` and `run_qaoa` remain stubs;
compiler integration tests replace them with synthetic results. Nothing here
authorizes execution. The helpers below are pure construction/evaluation functions.

## Shared helpers to consume

```python
from app.quantum.circuits import build_qaoa_preview
from app.quantum.qubo import evaluate_qubo

plan = build_qaoa_preview(qubo, p=config.p)
value = evaluate_qubo(qubo, "011")  # For a three-variable QUBO; x[0]=0.
```

`build_qaoa_preview(QUBO, p: int = 1) -> CircuitPreview` accepts 1–8 layers and uses
the shared QUBO width (up to 16). It has no quantum-package imports or job submission.
The compiler's source frontend stays limited to 1–6 bits for exhaustive verification.

`evaluate_qubo(QUBO, bitstring: str) -> float` includes the constant, requires exact
width, and rejects nonbinary inputs and nonfinite totals. API strings put `x[0]`
on the left, preserving leading zeros. This is an evaluator, not a solver baseline.

## Circuit decisions

- Prepare every qubit with H.
- Parameter order is `gamma_0, beta_0, gamma_1, beta_1, ...`. Use this explicit list
  when binding parameters; do not assume a library's automatic parameter ordering.
- For each layer: RZ(-gamma × linear[i]) on qubit i, then CP(-gamma × coefficient)
  for each canonical pair (i,j), then RX(2 × beta) on every qubit.
- Omit zero linear gates. Pair terms are already combined and sorted by the QUBO model.
- Add global phase `-gamma × (constant + sum(linear[i]/2))` per layer. The RZ
  convention otherwise introduces an extra phase; CP supplies pair phases directly.
  Including this offset makes the cost unitary exactly `exp(-i gamma C(x))`.
- A gate angle is `{parameter, coefficient}`; form the product using a trusted
  parameter lookup. Do not evaluate string expressions or submitted source.
- No measurements are included. The future runner owns measurement wiring and count
  conversion: measure qubit i into classical bit i and reverse ordinary Qiskit count
  strings at the adapter boundary to obtain API bit order.

Developer 3 should translate this shared plan to the installed Qiskit circuit API
and reuse it for execution. Keep a single gate-mapping definition in
`app/quantum/circuits.py`; do not reimplement cost layers in the compiler or runner.
Finite-coefficient overflow in the phase helper raises ValueError and calls for
rescaling the instance.

## Preview versus evidence

The analyze endpoint returns the one-layer plan, independently of future benchmark
configuration. The preview identifies itself with `kind=qaoa_logical_preview` and
`executed=false`. Its `logical_depth` counts parallel layers of the declared gates.
`depth` remains null because no transpilation has happened. The backend field names
the intended target; it does not claim that Aer was invoked.

Developer 5 can render `gates`, `parameters`, and `global_phase` from the generated
`CircuitPreview` type. No image payload or new endpoint is required. The existing
UI still displays JSON; a visual circuit renderer remains Developer 5 work.

Analytical tests verify the diagonal cost-phase formulas for all assignments of a
tiny QUBO, including constant offsets, both original senses, and multiple layers.
They do not evolve quantum states or establish correctness of a future Qiskit
adapter, optimizer, sampling procedure, or hardware implementation.

## Runner contract to implement later

Existing signatures and ownership remain:

```python
run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult
run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult
```

- Return canonical minimization objectives including the constant. Preserve
  `original_sense` for display; never reverse the solver's objective sense.
- For compiler comparisons, both results must supply a matching objective and a
  valid full-width bitstring. QAOA must supply matching `num_qubits` and `shots`.
  The compiler checks these before returning a completed result.
- `brute_force` is the exact baseline label used to populate the canonical
  objective gap. Other algorithms leave the comparison gap unknown. General signed
  QUBO approximation ratios remain null.
- An allegedly exact optimum above a valid QAOA solution is an integration failure,
  not a negative gap to hide. Solver inconsistencies become sanitized HTTP 500 errors.
- Initial execution is specified as Aer statevector simulation in the compiler's
  metadata. If a different method is needed, coordinate the provenance change first.
- Each solver's end-to-end timer includes its own preparation/result extraction;
  source parsing and exhaustive verification stay outside both timers. Return
  measured timing flags/components, with null for unmeasured durations.
- Enforce `timeout_seconds`, including native calls, and raise TimeoutError. Compiler
  HTTP mapping is 504. No fake results on expiry or missing dependencies.
- Report transpiled depth in benchmark metrics, never preview logical depth.

Before enabling any real execution, replace the runner stubs and verify actual
circuit construction, phase conventions, API count ordering, reproducibility, and
timings with separately authorized local checks. No performance claims follow
from the synthetic fixtures or symbolic previews.
