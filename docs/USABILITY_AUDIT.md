# Final usability audit

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
