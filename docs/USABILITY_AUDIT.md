# Final usability audit

## Simplified workflow revision

The later usability pass replaces the four-step compiler with **Python input → Run
→ Results**. Generated source is optional; preparing a non-executing plan is no
longer a user-facing step. Shared hardware callbacks retain the actual submitted,
recovered or recorded job in Results. A newly completed active job opens Results
automatically. Results retain the original hardware inputs and job ID.

Each experiment has one execution choice: this computer or physical IBM QPU.
Local settings, hardware settings, connection tools and repeated parameter studies
are optional details. Previously completed measurements have a direct View result
action. Hardware comparison cards explain the answer and its difference from the
classical reference before timing/resource details. Single-point comparisons use
cards rather than a plot with an arbitrary x coordinate. Duration units adjust
between ns, µs, ms and s, preserving small nonzero measurements.

Optimization includes a real 16-choice, 120-edge dense workload, checking 65,536
assignments. A new local run measured **1707.3424 ms classical** and **6025.949365 ms
Aer**, with optimum -459, best sample -441, gap 18. These are matched optimization
inputs, both executed locally; there is no speedup claim. The
[raw request and response](evidence/larger-workload-2026-11-12.json) are archived.
The larger example is explicitly local; physical optimization remains bounded to
eight choices, and compiler translation remains bounded to six.

The incoming main branch's interactive Neutrino lab, search Wilson intervals,
gate counts, benchmark sweeps and backend improvements are retained. The original
audit below describes the earlier layout and verification.

Merged verification: **1134 backend tests**, **17 frontend test files**, seven
compiler tests, Ruff, Svelte/TypeScript, generated types and production build
passed. **15 browser checks** cover three-step compiler conversion, actual QPU
results in Results, automatic local Results navigation, rejected input, live
Materials/Search, the incoming Neutrino lab, the larger workload, and all routes
on a phone. No page errors or hardware submissions occurred. See
[the workflow verification](evidence/simplified-workflows-2026-11-12.json).

Audited all eight routes at 1440px, 900px and 390px, including navigation,
page orientation, section access, keyboard controls and the compiler workflow.

| Finding | Implemented change |
| --- | --- |
| Large hardware forms and saved analytics pushed local controls far down each experiment | Hardware is an expandable section on experiment pages; the dedicated physical analytics page opens it by default |
| Long pages made it difficult to find studies or return to navigation | Local experiment, Physical QPU and Parameter study shortcuts; sticky breadcrumb with a Navigation link; anchor offsets keep targets visible |
| Tablet navigation required recognizing icons | Page names remain visible at tablet widths; active-page markers and phone labels are retained |
| Overview offered destinations without a recommended first action | Added a short Neutrino Lab walkthrough and a direct report/download link |
| Materials described the whole page as simulator-only despite physical support | Clarified the available local and physical paths |
| Duplicate navigation label elements complicated accessible names | Each link now uses a single visible label |

Verification: **25 browser checks passed**, comprising eight routes at three widths
plus compiler conversion → Test → archived hardware → live local comparison.
Section jumps, keyboard disclosure, retained physical evidence, active navigation
and horizontal overflow were checked. No JavaScript page errors or hardware
submissions occurred. Desktop, tablet and phone screenshots were visually reviewed.
See [the browser record](evidence/usability-audit-2026-11-12.json).

Frontend tests (12 test files), seven compiler tests, Svelte/TypeScript (zero errors
or warnings), formatting, generated API types and production build passed. This
audit changes frontend presentation only; the earlier 1068-test backend gate remains
applicable. It does not change experiment contracts, algorithms or measurements.

The first browser rehearsal used a secondary preview port, which the backend's
configured CORS policy does not allow. The successful rehearsal used the normal
http://127.0.0.1:5173/ origin. Use that address for the presentation.

This is a task-based engineering audit, not a study with first-time users. Presenters
should still rehearse on their actual laptop and projector.
