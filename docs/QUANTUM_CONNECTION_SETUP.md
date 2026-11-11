# Qiskit connection setup: no automatic jobs

The IBM Quantum Runtime SDK is an optional `hardware` extra, pinned to 0.47.0.
This setup assumes an **IBM Quantum Platform** token; confirm the actual provider
before connecting. No hardware job, session, sampler, estimator, or simulator run
is invoked by the connection checker. Existing app execution defaults are unchanged.
The ten-minute allowance is reserved for the operator's explicitly approved tests.

Setup verification: Qiskit 2.6.2, Aer 0.18.2 and IBM Runtime 0.47.0 installed;
SDK imports and 378 compiler/mocked-connection tests passed. The offline check found
no token or instance in the backend process environment. Authentication was not
attempted, and no provider service, circuit execution or job submission was performed.

## Local dependencies

From `backend/`, install the locked environment:

```sh
uv sync --locked --extra quantum --extra hardware
```

## Credential configuration

The easiest local startup is now `./dev.sh` from the repository root. In a terminal,
it asks for a hidden API token and then the IBM instance name/CRN. Enter skips setup;
already configured environment values are reused. Credentials go only to the backend
child process and are not persisted, echoed, or sent to Vite. It does not connect or
submit jobs. Set `QATLAS_SKIP_QUANTUM_PROMPT=1` to suppress prompts.

Prompted credentials belong to that running backend, not your parent terminal.
To run the separate connection checker in another terminal, configure that terminal
using the manual instructions below. The launcher never silently authenticates.

`QUANTUM-KEY` is treated as an environment-variable name, **not a literal token**.
It is supported if your launcher already provides that variable. Hyphens are not
valid in ordinary Bash variable names, so use `QATLAS_QUANTUM_KEY` for Bash.
Never put a token into a tracked file, command-line argument, frontend setting or chat.
The checker does not load local environment files or save SDK accounts automatically.

If the credential is not already provided by your environment, enter it yourself in
a local Bash terminal (the token is hidden and is not placed in shell history):

```sh
read -r -s -p 'IBM Quantum token: ' QATLAS_QUANTUM_KEY
printf '\n'
export QATLAS_QUANTUM_KEY
export QATLAS_IBM_INSTANCE='your-instance-name-or-CRN'
```

Use the intended IBM instance name/CRN from your account. The checker requires it
explicitly to avoid automatic instance selection. The variable exists only in the
terminal and its child processes; another running backend will not inherit it.
Do not share its value or upload environment files. When finished, use
`unset QATLAS_QUANTUM_KEY` (and close the terminal as appropriate).

## Offline readiness: safe default

```sh
cd backend
.venv/bin/python -m scripts.check_quantum_connection
```

This reports installed versions and credential/instance **presence only**. It never
constructs a provider service. Exit code 1 means a required setting/package is missing.
It does not certify authentication, remaining allowance, or hardware readiness.

## Operator-only connection check: metadata, no circuits

After confirming the provider and setting the instance, you can run:

```sh
.venv/bin/python -m scripts.check_quantum_connection --connect
```

This authenticates to IBM and lists operational nonsimulator backends. It does not
submit work or use QPU execution time; it does make service metadata requests.
SDK exceptions/logs are suppressed rather than echoing credential-bearing details.
No account configuration is saved. The command does not select a device or enable
compiler execution. Network/authentication can fail; that never triggers a retry job.

## Before spending any of the ten minutes

Confirm remaining allowance in the provider dashboard, identify the exact device and
agree how much is reserved for other team members. Connection success does not check
remaining quota. Do not run an unbounded hardware optimizer loop as a smoke test.

The compiler still generates code/plans; its existing opt-in enables **local Aer only**.
A physical-provider adapter and hardware result/provenance contract remain separate.
This connection setup must not label local Aer output as QPU output. A future reviewed
submission should use one tiny bound circuit, explicit shots and a conservative job
execution limit, save the job ID immediately, and retrieve that job after a disconnect
rather than submit a duplicate. Only the operator should authorize that submission.

Provider job execution limits control QPU usage rather than general wall-clock wait;
do not equate queue time or the browser timeout with the ten-minute allowance.
Check the actual account's rules before choosing a numeric cap. No numeric hardware
budget is spent or assumed by this setup.

See [the testing-day runbook](DEVELOPER_2_TESTING_DAY.md) and
[communication timing guide](COMPILER_COMMUNICATION_TIMING.md).

References: [version-pinned IBM service constructor and account selection](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/0.47/qiskit-runtime-service),
[IBM execution-limit documentation](https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time).
