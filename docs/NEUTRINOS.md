# Q-Neutrino: matter-dependent flavor oscillations

Research question: **How does matter density influence neutrino flavor oscillations,
and how accurately can Qiskit reproduce the predicted behavior?**

This independent local experiment implements milestones 1–3: vacuum, constant
matter, and ordered piecewise-constant layers. It uses one simulated qubit. It
preserves Q-Matter. The browser integration adds a separate neutrino API contract.
Smooth profiles and
adaptive integration are a later, unimplemented milestone.

## Physics and interpretation

Neutrinos are detected through flavor-dependent interactions. Flavor states are
superpositions of mass states; different propagation phases produce oscillating
detection probabilities. Here `|0>` represents electron flavor and `|1>` one
effective other active flavor. The initial state is always electron flavor.

Coherent forward scattering in electron-rich matter changes the electron-flavor
potential. The MSW effect can enhance effective mixing. Antineutrinos have the
opposite matter-potential sign. This is an effective two-flavor approximation,
not a complete three-flavor Standard Model simulation. See the
[PDG neutrino review, sections 14.4–14.5](https://pdg.lbl.gov/2023/reviews/rpp2023-rev-neutrino-mixing.pdf).

Assume relativistic, coherent propagation at fixed energy through prescribed,
static, ordinary matter. In natural units (`hbar = c = 1`), use
`Delta m² = m2² - m1²`, mixing angle `theta` in radians, and
`V = sqrt(2) G_F N_e >= 0`. The trace-subtracted physical Hamiltonian is

```text
H = (Delta m² / 4E) sin(2 theta) X
  + [s V/2 - (Delta m² / 4E) cos(2 theta)] Z
s = +1 for neutrinos, -1 for antineutrinos
U(L) = exp(-i H L)
```

The removed identity term changes only a global phase. For nonzero splitting,
`a = 2 E s V / Delta m²`; resonance requires `a = cos(2 theta)` and
nonzero transverse mixing. For `theta < pi/4`, a positive splitting permits
neutrino resonance in ordinary matter; a negative splitting permits
antineutrino resonance. Labels describe this effective pair, not a full
three-flavor ordering determination.

## Units and implementation equations

**Every CLI/Python input except the angle is dimensionless.** No eV, GeV, km,
mass-density, or electron-density conversion API is exposed. Choose fixed
positive reference scales `Delta0` (mass squared) and `E0` (energy). Define

```text
L0 = 4 E0 / Delta0          V0 = Delta0 / (2 E0)
delta_m2 = Delta m²/Delta0  energy = E/E0
distance = L/L0            potential = V/V0
```

`L0` has inverse-energy units in natural units. The numerical defaults are
illustrative normalized values, not measured neutrino parameters. At fixed
scales, the potential sweep is proportional to electron number density.
The dimensionless generator, called `hamiltonian()` in code, is `G = L0 H`:

```text
k = delta_m2 / energy
x = k sin(2 theta)
z = s potential - k cos(2 theta)
G = x X + z Z
r = sqrt(x² + z²)
P(e -> other) = (x²/r²) sin²(r distance)
P(e -> e) = 1 - P(e -> other)
```

Vacuum gives `sin²(2 theta) sin²(k distance)`. Matter mixing strength is
`sin²(2 theta_m) = x²/r²`. We report
`theta_m = atan2(abs(x), -z)/2` in `[0, pi/2]`; this convention removes the
unobservable sign of the transverse coupling by flavor rephasing. For positive
splitting it reduces to the input angle in vacuum. Signed splittings can
relabel the matter eigenstates, so use mixing strength for comparisons.
When `r = 0`, evolution is identity and the mixing angle/strength are `null`
because the degenerate eigenbasis is undetermined. Zero splitting is supported
without evaluating the singular ratio `a`.

Maximum mixing means `z = 0`; complete conversion additionally requires
`r distance = pi/2` modulo `pi`. A density peak in mixing does not imply a
conversion peak at an arbitrary fixed distance.

## Circuit and independent reference

For `alpha = atan2(x, z)`, each layer has the exact decomposition

```text
U = Ry(alpha) Rz(2 r distance) Ry(-alpha)
```

The circuit appends gates chronologically as `Ry(-alpha)`, `Rz(2 r distance)`,
`Ry(alpha)`. The factor of two follows Qiskit's
[`Ry(beta) = exp(-i beta Y/2)` convention](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RYGate).
There are no entangling gates or Trotter approximation. Zero-length or zero-
generator layers add no gates. Transpilation preserves the `ry`, `rz` basis
at optimization level zero. Reported depth includes final measurement:
normally `3 * active_layers + 1`.

`physics.py` constructs the dense flavor-basis matrix directly and uses
[SciPy `expm`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html),
independently of the circuit rotation construction. Both paths apply the first
listed layer first: `U_total = U_last ... U_second U_first`. Aer provides an
ideal statevector and a separate finite-shot measurement run. With one qubit,
count keys `0` and `1` map directly to electron and other flavor.

Layer order is tested on full matrices and complex states. Reversing a real
two-flavor profile can preserve flavor probabilities, so probabilities alone
cannot reliably catch an ordering bug.

## Run locally

Use the existing backend environment with the project's `quantum` dependencies.
From the repository root:

```bash
cd backend
.venv/bin/python -m app.experiments.neutrinos vacuum
.venv/bin/python -m app.experiments.neutrinos resonance
.venv/bin/python -m app.experiments.neutrinos layers

# Keep the same density sweep but use a shorter baseline:
.venv/bin/python -m app.experiments.neutrinos resonance --distance 0.7
# Antineutrino resonance for negative effective splitting:
.venv/bin/python -m app.experiments.neutrinos resonance --particle antineutrino --delta-m2 -1
# Two equal-length regions, total distance 2:
.venv/bin/python -m app.experiments.neutrinos layers --distance 2 --potentials 0.1 1.4

.venv/bin/python -m pytest tests/neutrinos -q
.venv/bin/ruff check app/experiments/neutrinos tests/neutrinos
```

All modes accept `--theta`, `--delta-m2`, `--energy`, `--distance`, `--particle`,
`--shots`, and `--seed`. Resonance accepts a custom `--potentials` grid; its
default has 21 points from zero to twice the resonant potential. Its default
distance is the first conversion maximum at resonance. The CLI rejects a
resonance demo when the chosen parameters do not permit positive-density
resonance. Vacuum rejects matter inputs. Layer mode accepts exactly two
potentials, with equal lengths; Python callers can supply arbitrary lengths:

```python
from app.experiments.neutrinos.experiment import run
from app.experiments.neutrinos.model import Experiment, Layer, Parameters

result = run(Experiment(
    parameters=Parameters(theta=0.4, energy=1.5),
    layers=[Layer(distance=0.8, potential=0.1), Layer(distance=1.1, potential=1.4)],
    shots=8192,
    seed=42,
))
```

Validated demonstration bounds: angle `[0, pi/2]`, signed splitting `[-10,10]`,
energy `[0.01,100]`, distance per layer `[0,100]`, potential `[0,10]`,
1–64 layers, 1–100000 shots, and 32-bit unsigned seed. Sweeps accept 1–41
potentials and a single-layer baseline. All inputs must be finite. These are
computational bounds, not physical constraints. Extreme choices may place the
automatic resonance grid or baseline outside these bounds; supply a valid grid
and distance explicitly.

## Output and observed examples

Every JSON record includes configuration, package versions, analytical results
(single layer only), numerical probabilities, ideal probabilities, measured
probabilities, counts, shots, circuit depth, errors for both flavors, norms,
and timing. A sweep increments the initial seed for each point modulo `2**32`;
each record contains its actual seed. Timings vary; identical seeds reproduce
counts in the tested software environment, not necessarily across versions.

Recorded default commands with 4096 shots, initial seed 42, NumPy 2.5.4,
SciPy 1.18.1, Qiskit 2.6.2, and Aer 0.18.2 produced:

| Configuration | Ideal conversion | Measured conversion | Mixing strength | Depth |
| --- | ---: | ---: | ---: | ---: |
| Vacuum, distance 1 | 0.1073769585 | 0.1005859375 | 0.1516466453 | 4 |
| Resonance, potential 0.9210609940, distance 4.0336988686 | 1.0 | 1.0 | 1.0 | 4 |
| Layers, potentials 0.2 then 1.4, lengths 0.5 each | 0.1393258847 | 0.1364746094 | Not a single-layer quantity | 7 |

All use `theta=0.2`, `delta_m2=energy=1`, neutrinos. Resonance is sweep point
10 and uses seed 52. Ideal versus numerical probability errors in these rows
are below `3e-16`; sampling errors are separate and much larger off resonance.
These are simulator observations, not hardware measurements or evidence of
quantum advantage.

`timing_ms.classical` covers one dense reference evolution and probability
extraction. `convergence_check` covers a second evolution with two substeps
per layer. `circuit_end_to_end` covers backend creation, circuit construction,
transpilation, ideal execution, and shot sampling. Nested timing fields report
transpilation, ideal execution, and sampling separately; they overlap the total.
Imports, analytical evaluation, and JSON serialization are excluded. There is
no hardware queue or optimizer. These differing workloads and small matrices
do not constitute a speedup benchmark.

## Validation and next investigations

The dedicated tests cover vacuum and constant-density formulas, both signs of
splitting, antineutrinos, normalization, zero distance/mixing/splitting, full
gate matrices, ordered layers, validation, reproducible counts, and statistical
consistency. Matrix/state tolerances are approximately `1e-13`; subdivision
tests permit `1e-12`. Shot tests use the conservative binomial bound
`6 * 0.5/sqrt(shots)` on absolute sampling error.

Each result reports reference and ideal norms, their complex-state difference,
and the state change after splitting each constant layer in two. Tests also
check subdivision into 1, 2, 8, and 64 pieces. Constant-layer evolution has no
time-step truncation; this checks numerical stability of matrix exponentials
and floating-point arithmetic. It does **not** establish convergence for an
underlying smooth density profile.

Next, map mixing strength and conversion independently over density and
distance; compare the neutrino/antineutrino sign cases; measure sampling error
versus shot count across multiple seeds. A later smooth-profile study should
compare uniform/adaptive layers against an independent ODE integrator and
report discretization convergence. Any stellar-inspired profile must be
labeled a toy profile, not a realistic solar model.

The model excludes three-flavor interference, CP phases, absorption,
decoherence, energy distributions, neutrino-neutrino interactions, and
realistic solar/supernova transport. It studies a controlled propagation model
and its circuit representation, not new neutrino physics.

## File map

- `backend/app/experiments/neutrinos/model.py`: local validated inputs.
- `physics.py`: analytical and independent dense reference calculations.
- `circuit.py`: exact single-qubit layer propagators.
- `experiment.py`: Aer execution, sweeps, errors, stability, timing, versions.
- `__main__.py`: JSON CLI examples; `__init__.py`: package marker.
- `backend/tests/neutrinos/`: vacuum, matter, and layer validation.
- `docs/NEUTRINOS.md`: conventions, usage, evidence, and limitations.

## Browser integration

Start both servers in separate terminals:

```bash
cd /Users/nickv/Developer/Q-Atlas/backend
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd /Users/nickv/Developer/Q-Atlas/frontend
npm run dev
```

Open http://127.0.0.1:5173/neutrinos/ and click **Run experiment**. The vacuum,
MSW resonance, and two-layer buttons load configurations; execution happens only
when requested. The resonance preset uses the documented positive-splitting
neutrino example with a potential sweep at a fixed baseline. Select a point below
the chart to inspect mixing, conversion, errors, timing, and the full JSON record.
Inputs are explicitly normalized; the former GeV/km placeholders are replaced.

`POST /api/neutrinos/run` accepts the validated experiment plus `axis`, `samples`,
`max_potential`, and `timeout_seconds`. A distance curve follows the profile in
order up to each sampled location, including a partial final layer. A density
sweep instead compares separate constant environments on one baseline. The backend
performs every physics calculation; the browser projects returned values into
the plot. Lines show SciPy and ideal Qiskit, dots show shot measurements.
Full request/response semantics and work limits are in `API_CONTRACTS.md`.

Additional integration files: `backend/app/schemas/neutrinos.py`,
`backend/app/api/neutrinos.py`, experiment `web.py`/`runner.py`,
`backend/tests/neutrinos/test_web.py`, frontend `live.ts`, the lab route/chart,
typed client/generated types, and `frontend/tests/neutrinos-live.test.ts`.
