# Connecting compute for the presentation

Users should keep the same workflow: load ordinary Python, mark an objective, and
convert it. They should not write circuit gates, select variational parameters, or
put provider credentials into their scripts. The backend owns the eventual execution
adapter. Today conversion and comparison planning remain nonexecuting.

## Confirm what the allocation provides

The provider/cluster has not been identified yet. A quantum processing unit (QPU)
and an HPC supercomputer running a quantum simulator need different connections.
Do not assume an SSH login, IBM account, or hardware backend is already configured.
No credentials have been inspected and no compute jobs have been submitted.

## Integration boundary

```mermaid
flowchart LR
    A[Marked Python region] --> B[Verified QUBO and shared gate plan]
    B --> C[Developer 3 shared QAOA runner]
    C --> D[Explicitly authorized provider adapter]
    D --> E[Normalized results and honest provenance]
    E --> F[Frontend result display]
```

The compiler sends validated mathematical data to the runner. It never sends an
uploaded script to a Python executor. Source names map to the existing canonical
bit order; naming and width inference do not change that interface.

Before enabling execution, Developer 3 must finish the shared runner and classical
baseline integration, and Developers 3 and 5 must agree the provider configuration,
execution opt-in, queued-job/status handling, deadlines, and result contract. Current
contracts permit only `backend=aer_simulator` and `simulated=true`: adding QPU output
requires a coordinated schema/provenance change and regenerated frontend types.
Changing an API key or URL alone cannot enable a correct hardware path.

## If the allocation is IBM Quantum

Use the provider SDK only in the backend adapter, with credentials kept on the backend.
Pin its version and follow the matching official
[Sampler quickstart](https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-sampler).
The documented flow creates a service, selects the approved backend, transpiles to
its instruction set, and samples the prepared circuit. The SDK API has changed over
time; do not paste an older `SamplerV2` example into an unpinned environment.

IBM currently documents ten minutes of QPU time per 28-day rolling window on its Open
Plan. Its `max_execution_time` limit measures QPU usage, not HTTP or wall-clock time;
completed-job metrics expose quantum seconds. Confirm the actual remaining allowance,
set a conservative per-job limit, and account for cumulative use across jobs.
[IBM execution limits](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time)
also explain that a session/batch TTL is not a substitute for controlling running jobs.

For this demo, start with one tiny problem and one approved sampling job, rather than
an unbounded hardware optimization loop. Modest shots and disabling unnecessary
mitigation work conserve usage; IBM documents these controls in
[Minimize job run time](https://quantum.cloud.ibm.com/docs/en/guides/minimize-time).
Any local angle training must be separately authorized. If angles are trained locally
and only final sampling uses a QPU, label that two-stage method accurately; do not
present it as end-to-end hardware optimization or omit training time in a full comparison.

## If the allocation is an HPC cluster

Use the cluster's documented scheduler/service and a trusted deployed runner. The
adapter stages the validated QUBO/config or circuit artifact, submits the approved job,
and collects its ID, status, output, and resource usage. Exact submission commands and
time limits depend on that cluster and must be filled in after it is identified.

Running Qiskit Aer on a cluster is still simulation. Keep `simulated=true`, record the
actual method/machine, and do not describe it as execution on a physical QPU. Never
stage and execute arbitrary uploaded Python as a shortcut to this integration.

## Presentation checklist

- Keep conversion and planning as the default; hardware submission requires explicit
  authorization and a reviewed server-side opt-in. Loading a page or file submits no job.
- Prepare the tiny objective and approved settings beforehand. Preserve its source hash,
  normalized instance, bit order, parameter order, version information, and deadline.
- Enforce both local wait/cancellation behavior and provider limits. A browser timeout
  must not silently leave a paid remote job running. Do not automatically retry jobs.
- Record job ID, device/method, queue and execution intervals, actual usage, returned
  counts, logical-to-physical mapping, assignment, and recomputed objective.
- Compare equivalent optimization tasks. Whole-application timing remains a separate
  trusted harness; see [benchmark planning](COMPILER_BENCHMARK_PLAN.md).
- Keep an honestly labeled fallback: static previews now, or actual previously measured
  results with provenance after an authorized rehearsal. Synthetic fixtures are not results.

This guide prepares the connection design. It adds no provider SDK, credential lookup,
hardware-enabled command, simulator run, or execution toggle. The allocation remains unused.
