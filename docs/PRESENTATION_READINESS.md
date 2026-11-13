# Final presentation-readiness audit

The release criteria are five working experiment routes, measured physical-QPU
evidence, fair classical comparisons, explicit failure/status behavior, reproducible
exports, offline presentation material and a science report matching the challenge.
The original project specification remains the source of truth.

The subsequent [usability audit](USABILITY_AUDIT.md) improved section navigation,
tablet labels and local/hardware organization. All 25 navigation and workflow
browser checks passed at desktop, tablet and phone widths.

## Findings and implemented fixes

| Finding | Implemented result | Evidence / verification |
| --- | --- | --- |
| Optimization was a fixture-only page | Real shared classical/QAOA endpoint; graph presets, cycle sizes and custom graph/QUBO input | Live browser comparison and study/export checks |
| Compiler browser flow stopped at planning | Explicit local comparison and shared physical-QPU submission; local results persist into analytics | Compiler end-to-end browser flow; safe-source tests |
| Four experiences lacked physical execution | Five adapters reuse established circuits and independent references | Completed IBM job `dbr0sthabdes73fp2v60`; eight circuits, five experiments |
| Little remaining local reservation | One capped shared job covers all five, without increasing the cap | One 10-second reservation; provider usage 2.0 seconds |
| Polls could race submission acknowledgement | Per-request submission/status locking and idempotent recovery tags | Concurrent polling, duplicate-ID and lost-acknowledgement tests |
| New submissions could hit a full cap after clicking Run | Read-only readiness endpoint and preflight button disabling | Local reservation shown before submitting; no provider call for readiness |
| Hardware evidence depended on backend availability | Explicit archived physical-demo loader with dated recorded banner and raw export | Offline browser rehearsal; archive clone/provenance unit test |
| Saved results could look newly measured | Timestamp, retained original inputs, explicit archived mode and named exports | Live/recorded browser checks; no automatic error fallback |
| Study controls could imply unlimited work | Finite grids, seeds, shot and request caps, suite deadline, cancellation and partial evidence | Plan/runner tests and failure/cancellation browser rehearsal |
| Runtime could be confused with QPU usage | Separate classical, training, compilation, network, provider and wall scopes; shared-job usage labeled | Physical analytics tables and final report |
| A useful scientific figure was missing | Standalone PNG/SVG from actual hardware counts, with conditional shot intervals | `plot_final_results.py`, raw hash and statistical summary |
| Exact physical circuits were not archived | Retrieved original job inputs as QPY, plus native gate counts and qubit mappings | Eight executed circuits, metadata and digest |
| Reports described earlier incomplete states | New final science report; old report marked historical; current runbook and release guide | Methodology downloads and presentation pack |

## Automated gates

Required gates: backend pytest, Ruff lint/format, frontend tests, compiler tests,
Svelte/TypeScript checks, generated-type check and production build. Hardware tests
use mocked services and invented credentials; the physical evidence is a separate
completed real job. Final automated results: **1068 backend tests passed**, with 68 dependency
warnings; all 12 frontend test-file subtests and seven compiler tests passed.
Svelte/TypeScript reported zero errors and warnings. Ruff, generated API types,
format checks and production build passed. The final browser rehearsal passed all
**16 checks**, with **zero hardware submissions**. Its
[verification record](evidence/ibm-qpu-2026-11-12/final-presentation-verification.json)
is retained with the release evidence.

Browser coverage includes live local runs, physical result rendering on every route,
study exports, input edits, invalid custom inputs, backend failure, cancellation,
partial failed suites, saved-job recovery, explicit recorded loading, scientific
downloads, and desktop/mobile layouts. Readiness and offline checks submit no jobs.

## Presentation scope and remaining human tasks

The app is ready to present its bounded models and recorded hardware experiment.
No additional physical jobs are necessary to demonstrate that all five ran on a QPU.
The original ledger filled the local reservation cap by retaining completed job
reservations. The subsequent accounting fix reconciles completed measured jobs to
recorded provider usage (rounded up); active or uncertain jobs keep full caps.
The same 60-second budget now has 32 seconds available in the inspected ledger.
See the [hardware guide](IBM_HARDWARE_ALL_EXPERIMENTS.md).

Before the session, the presenters still need to:

1. Rehearse the chosen five-minute narrative on the actual presentation laptop.
2. Open the final report, figure and presentation ZIP before entering the room.
3. Retain the selected source tree/revision and avoid last-minute dependency updates.
4. Verify the projector/browser scale and carry the offline figure/report fallback.

Future research, outside the completed demonstration: stronger performance studies,
independent repeated hardware jobs, device-error attribution, full three-flavor or
interacting-neutrino models, and a measured platform setup-effort study. These are
scientific extensions, not claims made by the current release.
