# Developer 2: current next steps

Updated 2026-11-10.

Read [the comprehensive testing-day runbook](DEVELOPER_2_TESTING_DAY.md) for the
current implementation status, offline bundle command, safe test selection,
Developer 3/5 handoffs, provider decisions, day-of sequence and evidence template.

The previous roadmap is retained in git history. Its broad test selections and
statements that both shared solvers are stubs are obsolete after main PRs #6–#9.
The classical baseline and shared local Aer QAOA runner are implemented, including
angle optimization, final sampling and result assembly (PR #13). Compiler integration
uses that runner. Its HTTP execution now defaults off and requires backend opt-in
`QATLAS_ENABLE_COMPILER_AER=1` after separate local-simulation authorization.
Use only the inspected compiler test selection during the current no-execution phase.

1. Freeze one primary objective and one backup with independent expected values.
2. Export their offline preflight bundles and retain the repository commit.
3. Run compiler/frontend checks and rehearse upload → convert → download → plan.
4. Review the completed local-runner handoff and plan authorized execution verification with Developer 3.
5. Confirm the actual provider and the meaning of the ten-minute allowance.
6. Complete the reviewed hardware contract and UI integration with Developer 5.
7. Execute a job only after separate explicit authorization and budget approval.

No hardware, simulator, or supercomputer execution is authorized by this roadmap.
