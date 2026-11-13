# Q-Atlas presentation runbook

## Start on the presentation laptop

Use the existing installed environment and locked dependencies. From the repository root:

```sh
./dev.sh
```

Open http://127.0.0.1:5173/. No credentials are required for local runs or the recorded
physical demo. If present, `.env` credentials stay in the backend. Startup submits no
hardware jobs. Avoid installing/upgrading packages immediately before presenting.

Experiment pages have shortcuts for **Local experiment**, **Physical QPU** and
**Parameter study**. Select Physical QPU to expand its settings and recorded results.
The dedicated `/hardware/` page opens this section by default. The sticky
**Navigation ↑** link returns to the page menu, including on phones.

For a rehearsal using the production build, run `npm run build` from `frontend/`,
then serve it with `npm run preview -- --port 5173`. Start the backend separately:

```sh
cd backend
QATLAS_ENABLE_COMPILER_AER=1 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If the backend cannot start, keep the frontend running and open `/hardware/` →
**Load recorded physical demo**. The banner explicitly says previously measured.
If Node is unavailable after a build, the static app can also be served from the root:

```sh
python3 -m http.server 5173 --bind 127.0.0.1 --directory frontend/build
```

The downloadable presentation ZIP contains the report, figure, raw counts, executed
QPY circuits and resource metadata. It contains no environment file or credentials.

## Five-minute narrative

| Time | Action | What to explain |
| --- | --- | --- |
| 0:00–0:40 | State the scientific question; open Methodology | Matter changes neutrino flavor conversion; circuits are tested against independent references |
| 0:40–1:45 | Neutrinos → MSW resonance → Run experiment | Generator xX+zZ; resonance and propagation phase are distinct; normalized units; one qubit |
| 1:45–2:50 | Physical QPU Analytics | All five ran on `ibm_marrakesh`; completed job ID; real counts and classical errors; 2.0s usage belongs to the whole shared job |
| 2:50–3:30 | Materials or final figure | Exact versus Trotter versus measured; more steps and more shots address different errors |
| 3:30–4:10 | Search results | Grover has query advantages under an oracle model; 109/128 actual shots; device and oracle gates still cost work |
| 4:10–4:45 | Compiler → Convert Python → Continue to test | Restricted AST → QUBO; source is never executed; same shared QAOA engine as Optimization |
| 4:45–5:00 | Final report / future work | Actual hardware demonstrated; practical runtime advantage and setup-effort reduction remain unproven |

For a short live parameter study, choose two values and one seed. Do not launch a
large suite during the talk. Keep the measured figure open so a slow run can be
explained using saved evidence without pretending it is a new measurement.

## Questions likely to matter

**Did it actually run on hardware?** Yes: job `dbr0sthabdes73fp2v60`, `ibm_marrakesh`,
eight circuits and 1024 samples. Raw records, provider IDs, native circuits and
qubit mappings are archived. The paper/report distinguishes these from local Aer.

**Was it faster than classical?** No practical speedup is established. Classical
references totalled about 8.69ms on these tiny instances. Provider usage was 2.0s
for the shared job, with separate local training, network and observed wall costs.
Those different scopes cannot be divided into a per-experiment speedup.

**What is actually novel?** The integrated, extensible and reproducible workflow:
physical inputs/objectives → inspected circuits → independent references → quality,
error and resource evidence. The quantum algorithms themselves are established.
Bundling all five into one physical job was a concrete resource-management choice;
usage savings against five separate jobs were not measured.

**Why not claim 156-qubit simulation?** Transpilation expands the device register to
156 wires. The scientific encodings use only one to three logical qubits in the
recorded demonstration, with routing/native resources reported separately.

**Is resonant conversion just an X gate?** At this chosen distance, yes, up to global
phase; IBM reduced it to X plus measurement. That follows from the model. The
off-resonance points retain phase rotations and test the full parameter dependence.

**Why does a QPU result differ from the reference?** Materials has product-formula
approximation as well as shot/device effects. Other ideal model circuits have finite
sampling and physical implementation errors. One job cannot isolate all noise sources.

**Why does Search not succeed 100%?** Ideal amplification at the chosen k is already
probabilistic (0.9453125); hardware returned 0.8515625. More Grover iterations do not
monotonically improve success, and the native implementation has 45 CZ gates.

**Is QAOA trained on the QPU?** The current hardware workflow trains angles locally
using ideal statevectors and samples the bound circuit physically. The app reports
that hybrid scope explicitly.

**Can arbitrary Python run?** No. The supported objective language is parsed and
validated; uploaded code is never evaluated, executed or dynamically imported.

## Freeze checklist

- Final report, PNG/SVG, raw JSON and presentation ZIP open successfully.
- `/hardware/` shows real measurements or an explicit recorded banner.
- Full-cap readiness disables new submissions without hiding existing results.
- One local live run succeeds with the chosen small preset.
- Projector scale and browser zoom are readable.
- Team can explain the models, units, bit order, baselines and timing scopes.
- Do not spend additional hardware quota simply to repeat the recorded proof.
