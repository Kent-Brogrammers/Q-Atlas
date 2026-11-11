# Compiler: an operator-submitted IBM QPU test

The compiler can submit **one physical IBM QPU sampling job per confirmed request**.
Conversion and planning still execute no submitted Python. Opening the page or
starting `dev.sh` does not authenticate or submit work. Hardware tests are separate
from the older opt-in local Aer benchmark endpoint.

## First test

1. Install the locked optional dependencies from `backend/` if necessary:
   `uv sync --locked --extra quantum --extra hardware`.
2. Restart `./dev.sh` from the repository root. Enter your token at the hidden
   prompt, then the intended IBM instance name or CRN. Credentials remain in the
   backend process; no saved account or frontend credential field is created.
3. Open `http://127.0.0.1:5173/compiler`. Use the default example, or a supported
   objective with **one to three binary inputs**. Keep **one circuit layer**.
4. Choose **Convert Python**, review the generated code, then **Continue to test**.
5. Click **Load IBM devices**. This authenticates and requests device metadata;
   it does not submit a circuit. Select an accessible operational device.
6. Check the remaining allowance in your IBM dashboard and agree on the team's
   allocation. Check the authorization box, then **Submit one IBM QPU job**.
   This requests **128 shots** and `max_execution_time=10` seconds.
7. Keep the recorded request ID and provider job ID. Click **Check hardware job**
   to fetch status/results. There is no automatic polling or resubmission.
8. Once complete, **Download QPU record**. It includes the QUBO, actual config,
   trained angles, circuit depth, exact classical result, raw counts, decoded
   solution, canonical optimality gap, measured send/receive time and provider
   QPU usage when available. Physical measurements are labeled `simulated: false`.

An unsupported objective is rejected before submission. The surrounding application
is never run: this tests the extracted optimization objective, not a complete
Python application's runtime. The downloaded generated script builds a circuit;
it does not automatically submit IBM jobs when downloaded or converted.

## What runs where

The compiler validates its allowlisted AST and normalized QUBO. Developer 3's
classical exact solver supplies the reference optimum. Developer 3's shared QAOA
angle optimizer trains locally using a seeded search, at most 20 evaluations and
a 30-second local deadline. The existing shared circuit builder supplies the
parameterized circuit. The adapter binds the resulting angles, measures logical
bit `i` into classical bit `i`, and transpiles for the selected device.

Only the final bound circuit goes to IBM's `SamplerV2` in **job mode**. There is no
session, batch, hardware optimizer loop, or application submission retry. Gate
and measurement twirling and dynamical decoupling are explicitly disabled for
this small initial test. The adapter uses the shared count decoder: IBM raw
strings are reversed into the API's `x0`-first bit order before objective scoring.
The gap is sampled canonical cost minus the exact canonical minimum; original
maximization objectives have already been normalized by the compiler.

This is **local angle training followed by physical sampling**. It is not a
fully hardware-trained QAOA benchmark. Classical enumeration time, local training
time, provider QPU usage and network timing cover different work; they cannot
establish quantum speedup. Queue, remote processing and full round-trip time
remain unmeasured rather than being invented from manual refresh intervals.

## Protecting the ten-minute allowance

The per-job cap is a requested IBM QPU-usage limit, not a wall-clock deadline.
Provider validation can reject a job whose estimated duration exceeds the cap.
A browser timeout, long queue or failed acknowledgement does **not** prove the
job was rejected and does not cancel it. Check the existing job rather than
creating a new test. Never raise the cap just to bypass an unexplained error.

There is also a conservative **local compiler reservation cap of 60 seconds**
per IBM instance. Each request reserves its entire requested cap before any
potential submission. Completed, canceled, errored and ambiguous submissions
retain that reservation. Only a failure known to occur before submission frees
it. This is not IBM's remaining balance and excludes jobs from other machines,
tools and team members.

`QATLAS_COMPILER_QPU_BUDGET_SECONDS` can set that local cap from 1 to 600 seconds
before launching the backend. Leave the default for initial testing; increase
it only after reviewing the provider dashboard and the team allocation. A value
of 600 does not mean 600 seconds remain in your account.

Reservations and job records are stored under the ignored private directory
`backend/.cache/compiler-qpu/`, partitioned by a hash of the instance identifier.
They contain no token or instance value. Keep this directory across restarts;
deleting it defeats local reservation accounting and duplicate prevention.
Reservation claims use a Linux/POSIX file lock and atomic record replacement.
This is a single-machine development workflow, not a distributed job service.

## Recovering without spending twice

The browser stores only the request UUID in local storage before sending a job.
After a reload it offers **Check hardware job**; it never submits automatically.
Keep the same browser origin/port and the same backend instance configuration.
The backend stores a claim before preparation and marks a request ambiguous
before calling the provider. Repeating the same request ID returns the existing
record; changing its problem, backend, shots or cap is rejected.

If status is `SUBMISSION_UNKNOWN`, do not create a replacement request. Look in
IBM workloads for the tag `qatlas-<request UUID>` and recover the provider job ID
there. The app deliberately does not retry an ambiguous submission. A process
crash during preparation can leave `PREPARING` reserved for manual investigation.
There is no automatic reservation reset or ambiguous-job recovery.

**Cancel hardware job** requests cancellation of the existing provider job. It
does not guarantee cancellation before execution or refund already used time.
**Start a new hardware test** appears only for terminal records. If the browser
lost its UUID, retain the request/job ID from the downloaded record and provider
dashboard; the API accepts the recorded UUID for status retrieval.

`FAILED_BEFORE_SUBMISSION` means no sampler submission was attempted. Verify the
dependencies, credentials/instance, selected device and local training setup,
then start a new hardware test. SDK exception text is suppressed to avoid
exposing credential-bearing diagnostics. Missing or invalid counts are not
reported as measurements, and results below the exact optimum are rejected.

## API and verification

- `GET /api/compiler/hardware/devices`: explicit metadata connection.
- `POST /api/compiler/hardware/submit`: source, backend name, UUID, required
  `confirmed: true`, shots 1–128, QPU cap 1–10 seconds.
- `GET /api/compiler/hardware/jobs/{request_id}`: existing-job status/results.
- `POST /api/compiler/hardware/jobs/{request_id}/cancel`: existing-job cancellation.

The generated frontend types come from these compiler-specific Pydantic schemas.
Existing local Aer response contracts and Developer 3's QAOA engines are unchanged.
Developer 3 should review the hybrid execution scope; Developer 5 should review
the hardware workflow before expanding it beyond this local operator use case.

Implementation verification uses mocked IBM services and synthetic results,
including duplicate suppression, ambiguous acknowledgements, reservation limits,
cancel/retrieve behavior, explicit sampler limits, count validation and bit order.
Circuit-construction verification binds parameters without executing a circuit.
**No physical job was submitted during implementation.** Authentication, device
availability and a real provider result still require the operator's first test.

References: [pinned Runtime 0.47 SamplerV2](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/0.47/sampler-v2),
[IBM execution limits and usage metrics](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/max-execution-time),
[credential setup](QUANTUM_CONNECTION_SETUP.md),
[communication timing definitions](COMPILER_COMMUNICATION_TIMING.md).
