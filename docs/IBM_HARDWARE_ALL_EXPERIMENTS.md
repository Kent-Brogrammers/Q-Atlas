# Physical IBM execution and analytics for all five experiments

**Completed hardware evidence:** all five experiences ran on `ibm_marrakesh` in IBM
job **`dbr0sthabdes73fp2v60`**. Eight circuits produced 1024 samples, 128 per circuit.
IBM reported **2.0 seconds of usage for the whole job**. See the
[results report](evidence/ibm-qpu-2026-11-12/RESULTS.md),
[raw counts and references](evidence/ibm-qpu-2026-11-12/five-experiments.json), and
[source provenance](evidence/ibm-qpu-2026-11-12/provenance.json).

## Use the app

Restart `./dev.sh` after updating. The backend loads optional `QUANTUM-KEY` and
`QUANTUM-CDN` from `.env` (`QUANTUM-CDN` is the IBM instance name/CRN). Credentials
remain backend-only. No hardware job is submitted on startup or page load.

Open **Physical QPU Analytics** at `/hardware/` to view the completed shared job and
all five classical/QPU comparisons. Each individual experiment page also loads its
saved physical result. Compiler results are in **Convert Python → Continue to test**.
The compiler's old hardware tracker remains available to recover earlier jobs.

Every workspace has **Run on IBM QPU**, explicit device selection or automatic
least-busy selection, raw-evidence download, status checking, and cancellation.
Queued/unknown/failed requests are displayed as statuses, never measurements.
The new shared path is independent of `QATLAS_ENABLE_COMPILER_AER`; that flag controls
only local compiler simulation.

QPU-specific shots, curve points, Trotter steps and QAOA layers are displayed
separately from local simulator settings. Inspect **Effective hardware request**.
Stored results retain their original inputs when page settings change. This matters
when viewing the small recorded demo beside a larger newly selected problem.

## What runs where

| Experiment | Classical reference | Physical work |
| --- | --- | --- |
| Compiler | Safe AST extraction, exhaustive QUBO equivalence, exact solve; shared local angle training | Bound shared QAOA circuit sampled on the QPU |
| Optimization | Same canonical graph/QUBO exact solve; shared local angle training | Same shared QAOA circuit sampled on the QPU |
| Search | Lexicographic classical search, expected/worst query counts, ideal amplification formula | Existing marked-state oracle and diffusion circuit |
| Materials | Independent dense Hamiltonian evolution and observables | Existing Trotter circuit; Z and X measurement circuits at each chosen time |
| Neutrinos | Independent SciPy evolution for each profile/coordinate | Existing flavor-propagation circuit for each chosen coordinate |

QAOA remains a hybrid workflow: angles are trained locally using the existing shared
engine, followed by physical sampling. This does not claim QPU-based optimizer
training. No duplicate QAOA solver or user-source execution was introduced.

## Analytics and timing

The results show classical and measured QPU quantities side by side, absolute
observable/probability error or objective gap, native transpiled circuit depth,
logical qubits, actual shots and raw counts. Provider job IDs link to IBM workloads.

Timings keep separate scopes: classical reference; local training; preparation
(which contains classical/training work); transpilation; submission; retrieval;
provider created-to-running and running-to-finished intervals; provider QPU usage;
and observed wall time. Observed wall time includes polling delay. Provider RUNNING
includes provider classical work/contention and is not pure QPU execution time.
[IBM timing guidance](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/monitor-job)

In a shared job, each experiment has separate counts and classical time. Its QPU
usage and provider intervals are unknown individually. The UI labels shared usage
as belonging to the whole job and never divides or charges that value to a child
experiment. No runtime speedup is inferred from these tiny, differently scoped paths.

## Bounds, reservations and recovery

- One submitted job is capped at 10 seconds and 128 shots per circuit.
- QAOA hardware supports at most 2 layers, 40 local evaluations (UI uses 20),
  6 compiler bits or 8 direct optimization variables.
- Search supports at most 6 qubits, 8 marked targets and 8 iterations.
- Materials supports open Ising chains of 2–4 spins, at most 32 Trotter steps and 5 times.
- Neutrinos supports at most 9 points and 8 layers; the UI offers at most 5 points.
- Native circuits are bounded to depth 2500 and 20000 aggregate instructions.
- All new and legacy compiler jobs share the existing per-instance reservation cap
  (`QATLAS_COMPILER_QPU_BUDGET_SECONDS`, default 60). Completed, measured jobs with
  valid provider usage count that usage rounded up to whole seconds. Active,
  cancelled, unknown or unmeasured jobs retain their full reservation; failures
  known to precede submission cost zero. A shared suite counts its parent once.
  This cap is not the account's measured remaining balance.

Before this demo the local ledger reserved 50 seconds. The shared five-experiment
job used the final 10-second reservation; its measured provider usage was 2 seconds.
The cap was not increased. The original accounting kept completed reservations
permanently and disabled Run at 60/60. The corrected ledger reconciles the four
completed jobs to their recorded 2-second usage, retaining 20 seconds for queued/
cancelled jobs: 28 seconds charged, 32 available. No new physical job was needed
for this fix. Restart the backend to load it; refresh readiness in the UI.

The server saves an idempotent UUID and reservation before remote submission. It
records `SUBMISSION_UNKNOWN` before calling IBM. Repeating the same request returns
the existing record. Lost acknowledgements are recovered through the unique
`qatlas-all-<request UUID>` tag; the server never automatically resubmits them.
Submission and polling use a per-request lock so a poll cannot overwrite a job ID.
Malformed result counts remain unmeasured and are never converted into evidence.

## API and CLI

Additive endpoints leave existing simulator contracts unchanged:

- `GET /api/hardware/demo`: bounded five-experiment request; submits nothing.
- `GET /api/hardware/devices`: accessible physical devices and shared local cap.
- `POST /api/hardware/submit`: confirmed request with typed task, UUID, device/auto,
  shots and execution cap. Task kinds cover all five experiences and a bounded suite.
- `GET /api/hardware/jobs?experiment=materials`: local saved evidence, including
  the matching child of a shared job; no provider lookup.
- `GET /api/hardware/jobs/{UUID}`: refresh/recover the existing job only.
- `POST /api/hardware/jobs/{UUID}/cancel`: cancel the existing job only.

From `backend/`, retrieve the completed demo without submitting another job:

```sh
.venv/bin/python -m scripts.run_hardware_demo --refresh --output /tmp/physical-qpu.json
```

`--submit` is an explicit physical operation. The CLI saves its request in ignored
`.cache/physical-demo-request.json` before connecting and reuses that ID on reruns.
Changing `--request-record` intentionally selects another request; the shared cap
still applies. Preserve these request records and the original backend instance.

Initial hardware-release validation: full backend suite **1067 passed**, plus frontend tests,
Svelte/TypeScript checks, regenerated API types, lint/format and production build.
Tests use dummy credentials and mocked provider services; the physical evidence
above comes from the separately submitted and completed real IBM job.

Read-only production browser verification passed eight checks: all five workspaces
rendered the actual job, exports retained raw counts and `simulated: false`, the
shared-job hub displayed all five analyses, archived evidence downloaded, and the
390px mobile layout fit. This verification submitted zero jobs. See the
[browser verification record](evidence/ibm-qpu-2026-11-12/browser-verification.json).

The final presentation release adds quota readiness, explicit offline physical
evidence, a new science report and presentation exports. Its updated gates are
**1068 backend tests** and **16 browser checks**, with zero new hardware submissions;
see [presentation readiness](PRESENTATION_READINESS.md).
