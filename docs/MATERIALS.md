# Quantum materials: a small transverse-field Ising chain

This module studies **real-time dynamics**, not a ground-state solver or a realistic
bulk material. It implements 2–4 spins on an open chain, starting in `|00...0>`:

```text
H = -J sum(i=0..N-2) Z_i Z_(i+1) - h sum(i=0..N-1) X_i
psi(t) = exp(-i H t) |00...0>
```

All parameters use **dimensionless simulation units with hbar = 1**. Time is reduced
simulation time, not seconds; `timeout_seconds` is a separate wall-clock budget.
`Z` has eigenvalues +1 for bit 0 and -1 for bit 1. Positive J favors aligned neighboring
spins; negative J favors opposite neighbors. The transverse X field mixes Z-basis states.
These are Pauli operators, rather than physical angular-momentum operators with hbar/2 factors.
The all-zero state is reproducible, but is generally not the ground state when h is nonzero.

## How the two calculations work

The independent classical reference in `backend/app/experiments/materials/physics.py`
constructs every operator using NumPy Kronecker products. A spin-i operator has identities
on the other sites. The Hamiltonian is a dense `2**N` square Hermitian matrix; SciPy
[`expm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html)
computes the propagator. “Exact” here means no Trotter approximation, up to floating-point
roundoff. The reference imports no Qiskit and does not derive its matrix from the circuit.

The circuit in `backend/app/experiments/materials/circuits.py` starts with Qiskit's default
all-zero state. Write H = A + B, with A the ZZ interactions and B the X field. One symmetric
second-order Suzuki–Trotter step, with dt = t/r, is:

```text
exp(-i A dt/2) exp(-i B dt) exp(-i A dt/2)
```

Repeat this r times. All ZZ terms commute with one another, as do all X terms, so each
block is implemented exactly. The two blocks generally do not commute, which causes
Trotter error. At fixed parameters, the global error scales as O(1/r**2) in the convergent
regime. If J=0 or h=0 the split is exact, apart from numerical roundoff.

Qiskit defines [`RX(theta) = exp(-i theta X/2)`](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RXGate)
and [`RZZ(theta) = exp(-i theta ZZ/2)`](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RZZGate).
The minus signs in our Hamiltonian therefore require:

- ZZ half-step: `RZZ(-J*dt)` on every nearest-neighbor pair.
- X full-step: `RX(-2*h*dt)` on every spin.
- Another ZZ half-step, in the same pair order.

The matrix and gate-sign tests compare the **entire two-spin unitary**, rather than only
Z probabilities, which alone cannot detect every sign or phase mistake.

## Observables and measurement

Every time point reports:

| Quantity | Definition |
| --- | --- |
| `per_spin_z[i]` | `<Z_i>` |
| `per_spin_x[i]` | `<X_i>` |
| `magnetization_z` | `sum_i <Z_i> / N`, normalized to [-1,1] |
| `zz_correlations[i]` | `<Z_i Z_(i+1)>`, one value for each of N-1 open-chain bonds |
| `energy` | Total `<H>`, **not** energy per spin |
| `state_norm` | L2 statevector norm for exact/ideal states; null for measured results |

The noiseless [Aer simulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html)
runs the actual Trotter circuit in two ways: an unmeasured statevector and finite-shot
measurements. All are classical computer simulations; no QPU or device noise is involved.

Z measurements provide magnetization and ZZ correlations in one setting. To measure X,
apply a Hadamard to every qubit before measurement, since Hadamard-Z-Hadamard = X.
The energy estimate includes **both** settings:

```text
E_shots = -J sum_i mean(z_i*z_(i+1)) - h sum_i mean(x_i)
```

Multiply outcomes **within each shot** before averaging a correlation; multiplying two
separate means would generally lose correlations. Every shot measures all spins.
`config.shots` is the number of shots **per measurement basis per time point**, so
`metrics.total_shots = 2 * shots * time_samples`. X measurements are retained even when
h=0 so the same full observable set is always available.

Spin i maps to qubit i. Dense array indices use `|q_(N-1)...q_0>`. Aer count strings
likewise put the highest measured bit first. The decoder reverses these strings into
spin-zero-first arrays: Aer `"001"` means spin Z values `[-1,+1,+1]`.
Leading zeros and every spin position matter.

## Run and inspect

From the repository root, in one terminal:

```sh
cd backend
uv sync --locked --all-extras
uv run --locked --all-extras uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

From the repository root, in another terminal:

```sh
curl --fail-with-body -sS http://127.0.0.1:8000/api/materials/run \
  -H 'Content-Type: application/json' \
  --data-binary @backend/examples/materials_request.json
```

The committed example requests N=3, J=1, h=0.7, t=1, 32 Trotter steps, five time
points, and 4096 shots per basis with seed 42. An empty `{}` request also works using
the original defaults plus t=1, 20 Trotter steps, and a single time point.
The optional quantum extra is required to run materials; without it the API still
starts and returns structured HTTP 503 for this feature.

Previously measured local simulator output for that example (2026-11-07, Qiskit 2.6.2,
Aer 0.18.2), showing the terminal magnetization metrics as a response excerpt:

```json
{
  "status": "completed",
  "experiment": "materials",
  "backend": "aer_simulator",
  "metrics": {
    "num_qubits": 3,
    "shots": 4096,
    "total_shots": 40960,
    "classical_observable": 0.49429882826299937,
    "ideal_observable": 0.49415698510334,
    "quantum_observable": 0.4842122395833333,
    "absolute_error": 0.010086588679666053,
    "trotter_absolute_error": 0.00014184315965937166,
    "sampling_absolute_error": 0.009944745520006681
  }
}
```

The full response also contains the five time points, all observables/errors, measured
timings, and provenance. These values describe classical simulator output, not a QPU run.

## Contract and plotting handoff

The existing `MaterialsResult` benchmark envelope and scalar metrics remain in place.
The Materials route submits the documented Ising request fields to the shared typed
API client and displays response metrics, provenance, timings, and exact/ideal/measured
time-series values. Failed or cancelled requests do not fall back to example data.

- `time_samples=1`: one result at `evolution_time`.
- `time_samples>1`: an evenly spaced grid from zero through `evolution_time`, inclusive.
  Each point evolves a **fresh** all-zero state with the same number of Trotter steps;
  this is not chained evolution or sequential measurement of one state.
- `metrics.time_series[k]` contains `time`, `exact`, `ideal`, `measured`, the three error
  objects below, pure-state fidelity `abs(<exact|ideal>)**2`, circuit depth, and shots per basis.
- Existing `classical_observable`, `quantum_observable`, and `absolute_error` summarize
  the terminal time and the requested `observable` (`energy` or `magnetization`).
  `quantum_observable` means **shot-based** here. `ideal_observable` is reported separately.
- Plot time against `exact.magnetization_z`, `ideal.magnetization_z`, and
  `measured.magnetization_z`. Plot each error's magnetization/energy or any indexed bond
  correlation separately. The response contains real simulation output, not mock chart data.

Errors are absolute component-wise differences for magnetization, every ZZ bond, and energy:

| Error | Difference |
| --- | --- |
| `trotter_error` | ideal circuit minus exact evolution |
| `sampling_error` | measured circuit minus ideal circuit |
| `total_error` | measured circuit minus exact evolution |

Their absolute magnitudes need not add: signed errors can cancel. Even at t=0, energy
can have finite-shot error from X measurements, although Z magnetization and ZZ outcomes
are deterministic. Increasing shots reduces typical sampling error as O(1/sqrt(shots));
increasing Trotter steps addresses a different error source.

## Limits, reproducibility, and timing

Implemented requests require `model=ising`, `boundary=open`, 2–4 spins, J and h in
[-10,10], t in [0,10], 1–256 Trotter steps, and 1–21 time samples. A multi-point sweep
requires positive terminal time. Additional work limits are `time_samples*trotter_steps
<= 2048` and `2*time_samples*shots <= 1,000,000`. Shots retain the shared 1–100,000 bound.
The old scaffold's Heisenberg, periodic, and 5–8-spin options remain deserializable for
contract compatibility, but the route explicitly rejects them with HTTP 422 diagnostics.

The seed defaults to 42. Materials alone also accepts `config.seed=null` for unseeded
sampling. Point k uses `(seed+k) modulo 2**32`; Aer handles the two circuits in that
point's job. Repeatability is tested within the recorded package versions and configuration,
not promised across arbitrary library changes. Different times are not repeated trials:
`metadata.repetitions` stays 1. `problem_id` hashes the normalized mathematical request,
excluding shot/seed/timeout settings and Trotter resolution.

Timings are wall-clock milliseconds over the **whole sweep**, with separate classical
and circuit paths. Classical time includes dense-H construction, exponentiation, and
observable extraction. Circuit time includes simulator creation, circuit construction,
transpilation, ideal simulation, shot simulation, and result extraction. Transpilation
and sampling sub-timers are explicit; `metadata.ideal_elapsed_ms` measures statevector
simulation alone. Depth is the maximum of the compiled Z/X measurement circuits, including
basis rotations and measurements, in the ideal Aer `rx,rzz,h` basis. This is not a
hardware-native depth estimate. There is no queue or optimizer timer.

The circuit path deliberately computes both ideal and shot results, while the classical
path computes one exact reference per time. These are **different workloads**, not a
speedup comparison. HTTP, interpreter startup/imports, process cleanup, and response
serialization are excluded from algorithm timers. The wall-clock timeout includes worker
startup/imports; a separate spawned process is terminated and reaped on timeout and the
route returns HTTP 504 `TIMEOUT`. Cleanup can add a short delay beyond the numerical
budget. API request validation occurs before starting that worker.

## Tests and study path

From `backend/`:

```sh
uv run --locked --all-extras pytest tests/materials -q
uv run --locked --all-extras pytest -q
uv run --locked --all-extras ruff check .
uv run --locked --all-extras ruff format --check .
```

Read the code in this order:

1. `physics.py` and `test_physics.py`: Kronecker products, Hermitian matrices, matrix
   exponentials, normalized statevectors, expectation values, and conserved energy.
2. `circuits.py`: rotation conventions, noncommuting operators, second-order splitting,
   measurement basis changes, and bit ordering.
3. `test_measurements.py`: why correlations use joint outcomes and why finite samples
   require statistical tolerances rather than exact equality.
4. `experiment.py`, `runner.py`, and `test_sweep.py`: how scientific results become typed,
   reproducible API data with an enforceable runtime budget.

Try J=0 and predict `Mz(t)=cos(2*h*t)` and `ZZ(t)=cos(2*h*t)**2` before running.
Then set h=0: Z observables stay fixed and only phases change. Finally turn on both
terms and double Trotter steps to distinguish approximation error from shot noise.

Remaining scope: frontend controls/charts belong to Developer 5. Periodic boundaries,
Heisenberg interactions, larger chains, alternate initial states, confidence intervals,
hardware noise, and IBM hardware execution are not implemented. This experiment validates
small-system quantum dynamics and numerical approximation; it establishes no quantum advantage.
