# Neutrino Oscillation Lab: proposed frontend handoff

**Status: discussion draft for Nick (Developer 1) and Developer 5. Not an approved
backend contract.** No neutrino endpoint, backend schema change, physics calculation,
or example neutrino result is implemented by this frontend branch. The existing
materials simulation and all existing APIs remain separate and unchanged.

The draft TypeScript shapes are in
`frontend/src/lib/neutrinos/proposal.ts`. They are deliberately outside
`frontend/src/types/api.generated.ts` and the canonical experiment discriminator.
The existing `RunConfig`, `SolverResult`, and provenance field types are reused
from generated OpenAPI types. `neutrinos` is a UI navigation ID and proposed future
response discriminator, not a value currently accepted by the backend.

## What the page does now

`/neutrinos/` shows grouped configuration controls, all disabled until the team
agrees on capabilities and a transport contract. No energy, distance, shot, flavor,
or environment default is presented as supported. Matter parameters can be inspected
in an expandable section, but cannot be submitted. There is no request or export
action in the current page. Draft-export helpers remain internal and explicitly
label their output as unapproved local settings, not runnable API requests.

The chart has probability axes but no curves, assumed flavor channels, or example
dataset. Comparison, accuracy, and circuit/execution details are expandable and
remain explicitly unavailable. The frontend performs no neutrino evolution or
accuracy calculation. Methodology is a separate primary route; the original
experiment workspaces remain at their existing URLs outside primary navigation.

## 1. Nick must declare implemented model capabilities

Agree on a capability payload before enabling the model controls:

- A stable model ID, label, approximation description, and assumptions.
- An ordered list of supported flavor/state IDs, display labels, and symbols.
  State which initial IDs are supported and which output channels are represented.
- Supported environments: vacuum, constant-density matter, or both.
- Valid energy, baseline, sampling-grid, shots, and matter-parameter limits.
- Any parameter-set choices, references, mixing conventions, mass ordering, and
  neutrino versus antineutrino scope. The current UI targets neutrinos only.

Do not infer model size or a flavor pair from its title. A two-state approximation
may represent a particular pair or effective state; its names must be explicit.
Three-flavor support remains unconfirmed. No tau curve or extra zero-valued channel
is supplied unless the backend declares and returns it.

## 2. Proposed request settings to agree

`ProposedNeutrinoRequest` contains:

| Field | Proposed meaning |
| --- | --- |
| `model_id`, `initial_flavor_id` | IDs from the approved capability catalog |
| `energy_gev` | Positive neutrino energy, in GeV |
| `distance_km` | Nonnegative terminal propagation distance, in km |
| `distance_samples` | Number of backend-generated propagation points; limits/default pending |
| `environment` | Discriminated vacuum or uniform-matter settings |
| `config` | Existing generated `RunConfig`, subject to agreed neutrino support |

Vacuum carries only `kind=vacuum`. Matter carries `kind=constant_density`,
`density_g_cm3`, and dimensionless `electron_fraction`. Confirm mass-density versus
electron-number-density conventions, electron fraction meaning, unit conversion,
and the matter-potential sign in the backend. The browser never performs those
conversions. The retained draft serializer omits stale matter values for vacuum settings.

The configuration draft intentionally omits a sampling-grid default and model
parameters that have not been agreed. Nick should expose the effective parameter
set in the result, rather than relying on undocumented frontend constants.

**Transport paths are undecided.** Choose the route and capability discovery mechanism
with the API/frontend owners; this branch adds neither a client method nor a POST to
an invented URL. Do not send neutrino payloads to `/api/materials/run`, whose existing
spin-system request/response contract must continue to work.

## 3. Proposed results for the display

`ProposedNeutrinoResult` is a discussion shape, not a replacement for a generated
backend model. Confirm how it will extend the established benchmark envelope:

- Completed status, instance ID, simulator backend, effective request, and the exact
  supported model definition used for that run.
- A strictly increasing `distances_km` grid; for a single distance, one point is valid.
- One series per returned flavor ID, with aligned classical probabilities, Qiskit
  probabilities, and backend-calculated absolute errors. Use null for unavailable
  entries. Preserve physical zero; do not fill missing channels with zero or
  interpolate across missing points.
- Existing solver/timing fields for the classical and Qiskit calculations. Probability
  is not a minimization objective; leave inapplicable `objective` / `best_bitstring`
  fields null. Keep the required timing-inclusion flags and declared scopes.
- Actual qubit count, transpiled depth and its scope, measured shots per point,
  and total shots. Statevector probabilities may have no sampled shots; return null.
- Backend-calculated maximum absolute probability error, RMS error, normalization
  deviation, declared tolerance, and whether the comparison meets it. Agree on
  aggregation over distances/flavors and the normalization/leakage definition.
  Missing errors/tolerances stay null; the frontend never invents an accuracy score.
- Distinguish statevector probabilities from finite-shot estimates. Report uncertainty
  or repeated-run statistics where available, without calling sampling deviation
  physical-model error or assuming error components add.

The plot renders only series also named in the returned model. Duplicate series,
misaligned arrays, invalid probabilities, and non-increasing distance grids are
excluded from plotting; no data is repaired or normalized in the browser. The
backend remains authoritative for validation and scientific correctness.

## 4. Scientific record and validation owned by Nick

Return the independent classical method and Qiskit construction method, effective
mixing/mass parameters with units and source, flavor-to-basis encoding, unused-state
policy, assumptions, seed, package versions, simulator method, and timing scopes.
The classical reference should be constructed independently of the Qiskit circuit,
not derived by converting that circuit to a matrix.

Agree on known-limit tests, including zero propagation distance, vacuum limits,
probability conservation within the declared modeled space, circuit sign/unit
conventions, and shot uncertainty. A simulator comparison measures accuracy; it does
not establish QPU performance or quantum advantage.

For physical background, the [PDG review, sections 14.4–14.5](https://pdg.lbl.gov/2025/reviews/rpp2025-rev-neutrino-mixing.pdf)
distinguishes vacuum propagation from the matter potential. The page uses this only
for explanatory text. It contains no mixing constants or propagation formula.
Variable-density, collective/interacting-neutrino, and supernova models are out of scope.

## 5. Integration sequence after agreement

1. Nick implements validated capabilities and experiment models under the agreed
   shared schema, preserving the Materials API and scientific ownership boundaries.
2. Agree on endpoint paths, structured validation/dependency/timeout errors, work
   limits, and execution availability. Reuse the existing error conventions.
3. Regenerate OpenAPI types with `npm run types:generate`; replace the proposal types
   with generated imports. Add one typed method to the existing shared client.
4. Bind approved capabilities to the selectors and gate requests by model/environment
   support. Invalidate old results after settings change; display the returned effective
   configuration so old vacuum results cannot be labeled as a new matter run.
5. Wire probabilities and backend accuracy/statistics into the existing panels,
   showing simulation provenance and preserving unavailable values. Add integration
   tests against Nick's independent reference and review desktop/mobile rendering.
