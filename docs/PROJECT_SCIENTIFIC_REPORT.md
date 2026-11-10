# Q-Atlas: scientific question, implementation, comparison and reproducibility

This report covers the **whole project**: Python compilation, materials dynamics,
QAOA optimization, Grover search, the Neutrino Lab, and their shared frontend/backend.
It answers the five project requirements below. Implementation descriptions refer to
the repository at the November 10, 2026 checkpoint (`e75555a`); `Project_Spec.md` remains unchanged.

**Evidence status:** this report introduces no new simulator or hardware runs.
Results are explicitly classified as analytical references, previously recorded
local simulations, or pending measurements. Qiskit Aer runs on a classical computer.
No hardware speedup or quantum advantage has been established.

## 1. Choose a concrete scientific question

**How accurately do small Qiskit circuits reproduce independently calculated physical
observables and optimization/search targets, and how does accuracy or solution quality
change with circuit approximation and sampling resources?**

We make that question testable using fixed, small instances:

| Experience | Concrete question | Independent reference | Main comparison |
| --- | --- | --- | --- |
| Python compiler | Does translating a marked three-bit selection objective preserve its value for every binary assignment? | Safe source interpretation and independently specified coefficients | Source/QUBO agreement over all eight inputs |
| Materials | How accurately does a three-spin circuit reproduce magnetization under transverse-field Ising dynamics as Trotter steps and shots change? | Dense matrix exponential | Trotter, sampling and total observable error |
| Optimization | How close does bounded QAOA get to the optimal cut of a unit-weight triangle? | Exhaustive classical enumeration | Best sampled cut, canonical objective gap, resources and time |
| Search | How does a three-qubit marked-state success probability change with Grover iteration count? | Analytical amplification formula and classical search | Success probability, query counts and measured runtime |
| Neutrinos | How does a constant matter potential change electron-to-other flavor conversion in an effective two-flavor model? | Analytical constant-density probability and independent SciPy evolution | Flavor probabilities, normalization and numerical/sampling errors |

The physical studies test observable accuracy; the combinatorial studies test solution
quality and search behavior. They share reproducibility and comparison methodology,
but do not pretend to be one physical model or one universal quantum algorithm.

The expected patterns are: compiler equivalence; decreasing Trotter error in the
convergent regime; reduced typical sampling uncertainty with more shots; oscillatory
Grover success rather than indefinite improvement; and matter-dependent neutrino
mixing. QAOA quality is stochastic and need not improve monotonically in a finite run.

## 2. Implement a Qiskit-based approach

These approaches are implemented in the repository; the report points to working
code rather than introducing a second copy of any algorithm.

| Component | Implemented approach | Reproducible source |
| --- | --- | --- |
| Compiler | Allowlisted Python AST → bounded symbolic polynomial → canonical QUBO → exhaustive verification → circuit plan/generated Qiskit Python | [analysis.py](../backend/app/compiler/analysis.py), [lowering.py](../backend/app/compiler/lowering.py), [generation.py](../backend/app/compiler/generation.py) |
| Shared QAOA | Parameterized Qiskit circuit, CPU Aer expectation scoring, seeded COBYLA search, final transpilation and finite-shot sampling | [qaoa_circuit.py](../backend/app/quantum/qaoa_circuit.py), [qaoa_expectation.py](../backend/app/quantum/qaoa_expectation.py), [qaoa_optimization.py](../backend/app/quantum/qaoa_optimization.py), [qaoa.py](../backend/app/quantum/qaoa.py) |
| Materials | Second-order symmetric product-formula circuit using RX and RZZ; ideal statevector and Z/X-basis shot measurements | [circuits.py](../backend/app/experiments/materials/circuits.py), [physics.py](../backend/app/experiments/materials/physics.py), [experiment.py](../backend/app/experiments/materials/experiment.py) |
| Optimization | Graph-to-QUBO conversion, exact enumeration and the same shared QAOA runner used by the compiler | [maxcut.py](../backend/app/experiments/optimization/maxcut.py), [solvers.py](../backend/app/experiments/optimization/solvers.py), [experiment.py](../backend/app/experiments/optimization/experiment.py) |
| Search | Explicit marked-state phase oracle, diffusion, bounded iteration count and Aer measurements | [circuits.py](../backend/app/experiments/search/circuits.py), [classical.py](../backend/app/experiments/search/classical.py), [runner.py](../backend/app/experiments/search/runner.py) |
| Neutrinos | One-qubit exact rotation decomposition for each constant-density layer; ideal and finite-shot simulation | [circuit.py](../backend/app/experiments/neutrinos/circuit.py), [physics.py](../backend/app/experiments/neutrinos/physics.py), [runner.py](../backend/app/experiments/neutrinos/runner.py) |
| Integration | FastAPI/Pydantic contracts and typed SvelteKit frontend; separate compiler input, code, test preparation and analytics views | [main.py](../backend/app/main.py), [contracts.py](../backend/app/schemas/contracts.py), [compiler page](../frontend/src/routes/compiler/+page.svelte) |

Aer provides the local simulation implementation; its statevector and sampling modes
must be identified explicitly in every result. [Qiskit Aer documentation](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html)

## 3. Explain the models, algorithms, assumptions and implementation

### 3.1 Compiler and binary optimization

For binary variables, the canonical minimized objective is

```text
C(x) = c + sum_i a_i x_i + sum_(i<j) b_ij x_i x_j,   x_i in {0,1}.
```

Binary squares reduce to linear terms. Maximization negates the entire original
objective, including its constant, while retaining original-sense metadata.
Named scalar inputs map to bits in signature order; vector inputs use index order.
API bitstrings put x[0] first. Measured Qiskit strings require explicit conversion.

The source compiler handles a documented bounded subset, including local arithmetic,
fixed loops and quadratic penalties. For 1–6 inputs it checks every assignment using
a safe interpreter and the extracted QUBO. It never executes uploaded source.
Surrounding Python is preserved as text; a generated script is not a certified safe
application. See [supported syntax and limits](COMPILER.md).

QAOA alternates cost evolution and X-mixer layers from a uniform superposition:

```text
|psi> = product over layers [exp(-i beta_l sum_i X_i) exp(-i gamma_l C)] |+>^n.
```

The shared plan implements linear cost terms with RZ rotations, pair terms with
controlled phase, and mixers with RX. Signs and global phase are tracked. Seeded
COBYLA minimizes the ideal statevector expectation; the final sampled result is the
best observed assignment, which is distinct from mean expectation. This follows the
hybrid variational idea of [Farhi, Goldstone and Gutmann (2014)](https://arxiv.org/abs/1411.4028).

For Max-Cut, each edge contributes `w(x_i+x_j-2x_ix_j)` to cut weight. The solver
minimizes its negative. The exact baseline enumerates all assignments and evaluates
the same canonical objective. On current tiny problems this is a strong baseline;
no claim of practical quantum speedup is implied.

### 3.2 Materials: transverse-field Ising dynamics

The implemented physical model is an open chain of 2–4 Pauli spins:

```text
H = -J sum_i Z_i Z_(i+1) - h sum_i X_i
|psi(t)> = exp(-iHt)|00...0>,     hbar = 1.
```

Parameters are dimensionless simulation units. The initial state is not generally
the ground state. This is real-time dynamics, not a ground-state prediction for a
specific material.

Write `H=A+B`, separating ZZ interactions and transverse X fields. With `dt=t/r`,
the circuit repeats `exp(-iA dt/2) exp(-iB dt) exp(-iA dt/2)` for `r` steps.
Each ZZ half-step uses `RZZ(-J dt)` and each field step uses `RX(-2h dt)`.
These factors follow Qiskit's half-angle rotation convention.
[Qiskit RZZ definition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RZZGate)

An independently constructed dense Hamiltonian and SciPy matrix exponential provide
the reference. “Exact” means no product-formula approximation, subject to floating-point
error. [SciPy expm](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html)

We compare magnetization `sum_i <Z_i>/N`, bond correlations, and total energy.
Z-basis shots estimate Z/ZZ; Hadamard-rotated shots estimate X. Energy requires both
bases. Shots per basis per time point must not be confused with total samples.
Separate ideal-vs-reference Trotter error from measured-vs-ideal sampling error.
At fixed model/time, the symmetric split has second-order convergence in its
appropriate regime; the repository documents its implementation in [MATERIALS.md](MATERIALS.md).

### 3.3 Grover search

For `N=2^n` candidates and `M` explicitly marked states, initialize a uniform state,
apply a phase oracle and diffusion `k` times, then measure. The ideal marked-state
probability is `sin^2((2k+1)theta)`, with `theta=asin(sqrt(M/N))`.
The probability can fall after excessive iterations. Grover's query advantage assumes
an oracle model; oracle construction and circuit gates are additional costs.
[Grover (1996)](https://arxiv.org/abs/quant-ph/9605043)

The classical baseline checks strings lexicographically without replacement and stops
at first success. Its observed count depends on target placement. The separately
reported mean `(N+1)/(M+1)` assumes uniformly distributed marked positions; worst case
is `N-M+1`. Query counts are not wall-clock measurements. The application already
knows targets to build its explicit oracle, so this is an algorithm demonstration,
not a claim to discover previously unknown database content faster.

### 3.4 Neutrino flavor propagation

The implemented model has two effective flavors: electron `|0>` and other `|1>`,
initially electron flavor. It assumes coherent relativistic propagation at fixed
energy through prescribed constant or ordered piecewise-constant matter layers.
It omits full three-flavor mixing and CP effects. This is a controlled approximation
to the physics described by the [PDG neutrino review](https://pdg.lbl.gov/2025/reviews/rpp2025-rev-neutrino-mixing.pdf).

In the repository's normalized units:

```text
kappa = delta_m2 / energy
x = kappa sin(2theta)
z = s*potential - kappa cos(2theta),  s=+1 neutrino, -1 antineutrino
G = xX + zZ;  r = sqrt(x^2+z^2)
P(e -> other) = (x^2/r^2) sin^2(rL), for r != 0.
```

When `r=0`, evolution is identity. Inputs are normalized, not directly km, GeV,
or measured density. `NEUTRINOS.md` specifies the reference-scale conversion.

For a layer, `alpha=atan2(x,z)`. The chronological Qiskit sequence is
`RY(-alpha)`, `RZ(2rL)`, `RY(alpha)`, implementing the required unitary up to the
removed identity phase. Ordered layers compose chronologically. Independent dense
SciPy evolution checks the circuit; a constant-layer analytical formula is also
available. Probability normalization, zero-distance and matter-sign cases are
important validation controls. See [NEUTRINOS.md](NEUTRINOS.md).

## 4. Present meaningful results and a classical comparison

### 4.1 Analytical/compiler reference results

These are derived expectations, **not newly measured Qiskit or QPU results**.

For [exactly_one.py](../examples/compiler/exactly_one.py):

```text
C(x) = 10(x0+x1+x2-1)^2 - (x0+2x1+3x2)
     = 10 - 11x0 - 12x1 - 13x2 + 20x0x1 + 20x0x2 + 20x1x2.
```

| API assignment | Objective |
| --- | ---: |
| 000 | 10 |
| 001 | -3 |
| 010 | -2 |
| 011 | 5 |
| 100 | -1 |
| 101 | 6 |
| 110 | 7 |
| 111 | 34 |

Thus the exact optimum is **-3 at 001**. Compiler extraction has a concrete eight-input
equivalence target. A future sampled result must report its own assignment/objective;
its canonical gap is `C_sampled - (-3)`, not an assumed zero.

| Experience / fixed case | Reference result | Interpretation |
| --- | --- | --- |
| Triangle Max-Cut, three unit edges | Maximum cut 2; minimized QUBO optimum -2 | QAOA should be compared with this exact optimum; success is not guaranteed |
| Search, N=8, M=1, k=0 | Ideal marked probability 1/8 | Uniform-state control |
| Search, N=8, M=1, k=2 | Ideal probability 121/128 = 0.9453125 | Analytical amplification target, not measured shots |
| Same search with marked string 001 | Lexicographic classical search takes 2 checks; uniform-position mean 4.5, worst case 8 | Avoid presenting the mean as the observed fixed-instance count |
| Materials, t=0 | Mz=1 and energy `-J(N-1)` | Initial-state control; transverse X expectation is zero |
| Neutrinos, zero propagation distance | P(e)=1 and P(other)=0 | Identity-evolution control |
| Neutrinos, theta=pi/8, kappa=1, s=+1, potential=sqrt(2)/2, L=pi/sqrt(2) | z=0, r=1/sqrt(2), P(other)=1 | Analytical resonant full-conversion case in normalized units |

At 4096 independent binary shots, the largest binomial standard error is
`1/(2 sqrt(4096)) = 0.0078125`. This is a theoretical uncertainty scale, not a
confidence interval measured from this project's hardware.

### 4.2 Previously documented materials simulator result

[MATERIALS.md](MATERIALS.md) records a local simulator excerpt dated 2026-11-07,
using Qiskit 2.6.2 and Aer 0.18.2: N=3, J=1, h=0.7, final t=1, 32 Trotter steps,
five time points, 4096 shots per basis, seed 42. Total samples were 40,960.

| Terminal magnetization quantity | Previously documented value |
| --- | ---: |
| Independent dense reference | 0.494298828263 |
| Ideal Trotter circuit | 0.494156985103 |
| Finite-shot circuit estimate | 0.484212239583 |
| Ideal-vs-reference error | 0.000141843160 |
| Shot-vs-ideal error | 0.009944745520 |
| Shot-vs-reference error | 0.010086588680 |

For this recorded case the sampling discrepancy exceeds the Trotter discrepancy,
suggesting that more product-formula steps alone would not address its largest
observed error component. That observation does not establish a general resource
optimum. Absolute component errors do not generally add; their near/additive
relationship here follows the directions of these particular deviations.

**Provenance limitation:** these numbers are carried forward from the committed guide,
not independently rerun for this report. The excerpt is not a complete archived raw
response. Retain a full raw result and environment/commit record in the next approved
reproduction before treating it as a fully audited experimental dataset.

### 4.3 Recorded Grover search curve and classical comparison

Main PR #20 includes [previously-measured.json](../frontend/src/lib/search/previously-measured.json),
recorded at **2026-11-10 18:31:09 UTC** through the local FastAPI TestClient on Windows
with Python 3.12.16, Qiskit 2.6.2, Aer 0.18.2 and NumPy 2.5.4. The curve uses
three qubits, target `001`, 1024 shots, seed 42 and iteration counts 0–6.

| Iterations k | Ideal probability | Recorded success probability | Successful shots / 1024 |
| --- | ---: | ---: | ---: |
| 0 | 0.125000000 | 0.132812500 | 136 |
| 1 | 0.781250000 | 0.803710938 | 823 |
| 2 | 0.945312500 | 0.962890625 | 986 |
| 3 | 0.330078125 | 0.363281250 | 372 |
| 4 | 0.012207031 | 0.013671875 | 14 |
| 5 | 0.547973633 | 0.579101563 | 593 |
| 6 | 0.999786377 | 1.000000000 | 1024 |

The recorded curve exhibits the predicted amplification oscillation, including the
drop between k=2 and k=4. The k=6 sample being all successes does not prove that the
true probability is exactly one. This single seeded curve is not an uncertainty study.

At k=2 the record reports **0.028 ms** for classical search and approximately
**101.550 ms** for the local Grover simulation. Classical search observed two checks;
Grover used two combined-oracle queries per shot, or **2048 across its sampling batch**.
The simulator includes circuit preparation/execution work beyond the cheap classical
predicate, so these times are descriptive of the recorded implementation and machine.
They show no wall-clock speedup. Per-shot query counts are not equivalent to full
sampling-batch work or physical gate counts.

The recording identifies source revision `2ebc81f32334a977cfaa5b3ff4fcc683e8510e43`,
sets **working_tree_dirty=true**, and includes SHA-256 source-file hashes and complete
result records. Exact recording source therefore cannot be identified by that commit
alone; retain the hashes and disclose the dirty state. These are explicitly previously
measured local simulator results, not a live run performed for this report. See
[the Search evidence/rehearsal guide](SEARCH.md#demo-preparation-and-regression-checks).

### 4.4 Measurements still required

| Study | Required measured output | Current report status |
| --- | --- | --- |
| Compiler/QAOA selection | Sampled assignment, gap, evaluations, actual shots/depth, timing | Pending new recorded experiment |
| Triangle QAOA | Quality distribution across fixed seeds and budgets | Pending |
| Materials convergence | Error versus steps, then shots, holding other inputs fixed | One historical excerpt; new sweep pending |
| Grover | Measured success versus k and theoretical curve, fixed-instance classical counts | Recorded curve above; independently repeated/cross-machine studies pending |
| Neutrinos | Probability versus matter potential/distance, ideal and shot errors | Model/analytical targets given; new raw evidence pending |
| Physical QPU | Device/job ID, mapping, raw outcomes, actual usage | No hardware measurement claimed |

The [Neutrino benchmark workflow](NEUTRINO_BENCHMARKING.md) already supports repeated
shot/seed studies with full raw responses and distribution summaries. Its existence
is not evidence that a particular benchmark dataset was executed or obtained here.

## 5. Reproducible code, citations and limitations

### 5.1 Environment and nonexecuting reproduction

Record `git rev-parse HEAD`, operating system/machine, Python version and the installed
package versions. Dependencies are specified in [pyproject.toml](../backend/pyproject.toml)
and locked in [uv.lock](../backend/uv.lock). The active UI setup is in
[frontend/README.md](../frontend/README.md). No notebook is necessary because the
repository provides source, fixed inputs, API entrypoints and a compiler preparation CLI.

The following preparation commands perform no quantum job:

```sh
cd backend
uv sync --locked --all-extras
.venv/bin/python -m scripts.prepare_compiler_day \
  ../examples/compiler/exactly_one.py \
  --output /tmp/q-atlas-report-preflight.zip --p 1 --shots 256 --seed 42
```

Installation can require downloading dependencies. The exporter validates source as
text and freezes generated code, the typed plan and hashes; it never runs that code.
Use a new output filename if the file already exists. Preserve the ZIP unchanged.

### 5.2 Inputs for separately authorized local experiments

**The following API calls execute local simulations. They are provided for subsequent
authorized reproduction and were not run to write this report.** They use no physical
QPU, but still consume local computation. Start FastAPI using the project README,
then submit/save complete JSON responses with the chosen commit and versions.

Compiler benchmark payload, endpoint `POST /api/compiler/benchmark`:

```json
{
  "source": "@qatlas.objective\ndef select(red, blue, green):\n    return 10*(red+blue+green-1)**2-red-2*blue-3*green\n",
  "config": {"p": 1, "shots": 1024, "seed": 42, "max_iterations": 100, "timeout_seconds": 30}
}
```

Only after separate authorization, its backend must be started with
`QATLAS_ENABLE_COMPILER_AER=1`; by default this endpoint returns execution-disabled
HTTP 501. The frontend compiler Test stage continues to prepare plans only.

Optimization payload, endpoint `POST /api/optimization/run`:

```json
{
  "problem": {"kind": "graph", "num_vertices": 3, "edges": [
    {"i": 0, "j": 1, "coefficient": 1},
    {"i": 1, "j": 2, "coefficient": 1},
    {"i": 0, "j": 2, "coefficient": 1}
  ]},
  "config": {"p": 1, "shots": 1024, "seed": 42, "max_iterations": 100, "timeout_seconds": 30}
}
```

Materials payload: use the committed
[materials_request.json](../backend/examples/materials_request.json), endpoint
`POST /api/materials/run`. It specifies the historical example's complete settings.

Search payload, endpoint `POST /api/search/run`:

```json
{
  "num_qubits": 3, "marked_states": ["001"], "iterations": 2,
  "config": {"shots": 4096, "seed": 42, "timeout_seconds": 30}
}
```

Neutrino payload, endpoint `POST /api/neutrinos/run`:

```json
{
  "experiment": {
    "parameters": {"theta": 0.2, "delta_m2": 1, "energy": 1, "particle": "neutrino"},
    "layers": [{"distance": 1, "potential": 0}], "shots": 4096, "seed": 42
  },
  "axis": "distance", "samples": 3, "timeout_seconds": 30
}
```

For a payload saved as `/tmp/request.json`, the general execution pattern is:

```sh
# Example for an authorized search reproduction; change endpoint to match the payload.
curl --fail-with-body http://127.0.0.1:8000/api/search/run \
  -H 'Content-Type: application/json' --data-binary @/tmp/request.json
```

Use the existing domain guides for accepted limits and CLI alternatives. Repeat with
recorded seeds, separate cold/warm runs, and save raw responses rather than copying
only dashboard summaries. The same seed is not a cross-version reproducibility guarantee.

### 5.3 Required evidence and fair timing

Report input hashes, actual backend/method, seeds, shots, repetitions, circuit depth,
optimizer budget, errors or objective quality, and complete timing scopes. Include
the exact classical method and the same mathematical instance for both paths.
Full distributions are more useful than a favorable single stochastic run.

For physical-device work, additionally preserve job IDs, device mapping, raw counts,
queue/processing intervals, actual quota use, submission and retrieval durations, and
whole-comparison wall time. Remote round trip already contains waits and transfer;
do not add overlapping components again. Current communication fields are null
placeholders, described in [COMPILER_COMMUNICATION_TIMING.md](COMPILER_COMMUNICATION_TIMING.md).

### 5.4 Limitations

- These are tiny, classically tractable problems. Qiskit simulation does not establish
  performance on a physical quantum computer or asymptotic practical advantage.
- Materials is an ideal short Ising chain, not a fitted model of a real bulk material.
  Dense exact references and statevector storage scale exponentially with spin count.
- Neutrinos uses normalized effective two-flavor unitary dynamics, not full three-flavor
  phenomenology, detector simulation or a measured physical density dataset.
- QAOA uses classical optimization and ideal simulator expectations before final shots;
  finite budgets and local optima can produce suboptimal solutions.
- The compiler supports restricted binary objectives, not arbitrary Python acceleration.
  It does not execute uploaded programs or benchmark complete application runtimes.
- Search's marked-state oracle is supplied explicitly. Query-model gains do not erase
  oracle construction, repeated-shot, communication or compilation costs.
- Ideal Aer lacks real-device errors unless deliberately modeled; hardware noise,
  calibration, topology and queue behavior require separate investigation.
- The historical materials excerpt has incomplete raw-data provenance. The Search
  recording discloses a dirty working tree. Compiler/QAOA and neutrino empirical
  comparisons still need authorized recorded measurements for this report.

### 5.5 Sources

The explanatory references are linked where used above. Core references are
[Farhi et al., QAOA (2014)](https://arxiv.org/abs/1411.4028),
[Grover, database search (1996)](https://arxiv.org/abs/quant-ph/9605043),
[PDG, neutrino masses/mixing/oscillations (2025)](https://pdg.lbl.gov/2025/reviews/rpp2025-rev-neutrino-mixing.pdf),
[Qiskit Aer API](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html),
[Qiskit RZZ conventions](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RZZGate),
and [SciPy matrix exponential](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html).
Repository implementation details and the historical materials numbers are attributed
to the linked source files and domain guides, rather than to those external papers.
