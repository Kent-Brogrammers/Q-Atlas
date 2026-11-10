# Compiler: send, receive and remote timing

The provider is not connected. No transfer timings have been measured or estimated.
Compiler comparison plans now reserve the following nullable millisecond fields in
`communication_timing`. The browser download and offline preflight ZIP's `plan.json`
include them automatically; all values are currently `null`.

```json
{
  "submission_ms": null,
  "result_retrieval_ms": null,
  "queue_ms": null,
  "remote_processing_ms": null,
  "round_trip_ms": null
}
```

This is an additive compiler-plan preparation contract for D2/D3/D5 review. It does
not change shared `TimingBreakdown`, `elapsed_ms`, algorithm timers, hardware backend
types, or the execution opt-in. No measurements are fabricated by compilation/planning.
Local Aer has no remote quantum-computer transfer; it must not populate these fields
with CPU simulation time or a fictitious network zero.

## Measurement boundaries for tomorrow

| Field | Definition | How to collect after authorization |
| --- | --- | --- |
| `submission_ms` | Client time from immediately before preparing/submitting the provider request until its job acknowledgement arrives | One monotonic client timer around that submission operation; record job ID immediately |
| `result_retrieval_ms` | Client time downloading and decoding results already known to be ready | Time the ready-result fetch and decoding; if the SDK call blocks for execution, leave this isolated field null |
| `queue_ms` | Provider-reported remote waiting interval | Use provider event timestamps/durations with documented meaning; unavailable stays null |
| `remote_processing_ms` | Provider-reported processing interval | Record its precise scope and units; do not assume it equals billed QPU seconds |
| `round_trip_ms` | Client wall time from the submission start above through final decoded result availability | Keep one monotonic timer across acknowledgement, polling, waiting and retrieval |

These are operation durations, not a claim to isolate pure wire latency. Submission
can include serialization, authentication, network transfer and service handling.
Retrieval can include network transfer and client decoding. A blocking result call
that waits for the device cannot be labelled just download time. In that case keep
isolated retrieval unknown and record the complete round trip.

Record UTC timestamps for traceability and monotonic durations for elapsed time.
Never subtract a timestamp from one machine's clock from another machine's timestamp.
Provider queue/processing durations need their own documented clock and definitions.

## Accounting without double counting

For a single job, the observed round trip already contains sending, waiting, remote
processing, polling/delivery overhead and receiving. It is **not** an extra component
to add on top of those parts. Provider intervals can overlap client intervals, so do
not force their sum to equal the observed total or subtract to infer missing latency.

For multiple jobs, keep a per-job record. A hardware optimization loop can submit more
than one job per comparison. Measure the complete comparison wall clock separately,
including local preparation/training, all necessary provider exchanges and result
interpretation. Do not multiply one sample transfer time by an assumed iteration count.
If jobs overlap, summing job round trips also does not give comparison wall time.

Report these views side by side when available:

- Classical end-to-end optimization time for the same mathematical instance.
- Quantum solver/device processing time with its documented scope.
- Full quantum comparison wall time, including required remote communication/waiting.
- Queue and send/receive breakdown where genuinely measurable.
- Actual provider-reported quota usage, separately from wall-clock time.

Browser-to-Q-Atlas HTTP time and UI rendering are separate from backend-to-provider
communication. Neither source conversion duration nor a local ping measures a future
quantum job's transfer latency. The shared solver timer definitions stay unchanged.
A future provider adapter/result-schema extension must explicitly state whether
communication and queue are included before any performance ratio is displayed.

## Testing-day record

Before the first approved submission, the operator records the repository commit,
source/plan hashes, device, SDK version, configured limits, and authorization. Start
the round-trip clock before submission; save acknowledgement/job ID before polling.
When results are ready, time retrieval only if that interval is separable. Preserve
raw provider timing metadata and units together with decoded counts and usage.

Keep the measured record beside the immutable preparation bundle, rather than editing
the hashed ZIP in place. For example, save `communication-record.json` with the five
fields above, actual job ID, UTC start/end, timer scope, outcome, and provider event
metadata. Use `null` for unavailable components, preserve a measured `0`, and mark
any manually supplied estimates as estimates in a separate record. The existing
compiler plan remains a preparation artifact, not a measured benchmark result.

On failure/cancellation, retain the attempted job's status and elapsed wait without
calling it a completed round trip. Recover an existing job ID after disconnects;
do not resubmit automatically just to obtain a timing sample. Do not run probes or
hardware jobs under the current no-execution instruction.

## Remaining connection work

Developer 3 adds timers at the actual provider submission/retrieval boundaries and
preserves raw provider metadata. Developers 2/3/5 then agree how measured records
enter benchmark results and the analytics page. Until that adapter and measured-result
contract exist, this update exports and displays placeholders only. It performs no
provider request, quota lookup, timing probe, local simulation or quantum execution.
