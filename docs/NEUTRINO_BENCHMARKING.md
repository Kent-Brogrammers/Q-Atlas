# Local neutrino benchmarking

Developer 3's local benchmark workflow repeats Nick's existing bounded
`run_neutrinos(NeutrinoRequest)` interface. It consumes the established
`NeutrinoResponse` and preserves each complete measured response.

The plan and report models in `app/benchmarks/neutrinos.py` define a local artifact
format. Nick and Developer 5 should review the selected scientific cases, summary
fields, and timing presentation before any API or frontend integration.

## Running a benchmark

From `backend/`, use the Python 3.12 environment with the existing quantum extra.
Save an established neutrino request to a local file, for example `/tmp/neutrino-request.json`.

```json
{
  "experiment": {
    "parameters": {"theta": 0.2, "delta_m2": 1, "energy": 1, "particle": "neutrino"},
    "layers": [{"distance": 1, "potential": 0}],
    "shots": 4096,
    "seed": 42
  },
  "axis": "distance",
  "samples": 3,
  "timeout_seconds": 30
}
```

```sh
.venv/bin/python -m app.benchmarks \
  --request /tmp/neutrino-request.json \
  --shots 256 1024 4096 \
  --seeds 42 43 44 \
  --total-timeout 120 \
  --output /tmp/neutrino-evidence.json
```

The command executes nine local curve requests. Shot counts and base seeds from
the CLI replace those two fields in the template. All physical settings, curve
coordinates, and per-request limits follow the existing neutrino interface.
Vacuum, constant-density matter, ordered layers, and potential sweeps use Nick's
implemented capabilities. Inputs use the normalized units documented in
[the neutrino guide](NEUTRINOS.md).

The output path must be unused. A complete report is serialized to a temporary
file and published atomically. Existing files and symlinks are preserved. Only
complete suites publish evidence files. Use a fresh filename for each recorded suite.

## Report contents

- The complete plan, effective requests, and full raw responses.
- A UTC creation time, Python version, OS, and machine architecture.
- The source simulation package versions within every raw record.
- A separate summary for each shot count and curve coordinate.
- Error distributions for each available flavor and error family.
- Timing distributions with sample count, minimum, median, maximum, and sample
  standard deviation. Standard deviation is null with fewer than two observations.
- Null analytical error summaries wherever the source has no analytical result.
- Timing statistics with null values and count zero wherever no timing was measured.

The source declares the effective two-flavor channels `electron` and `other`.
Raw probabilities, errors, and timings are retained at their measured precision.
Measurement bookkeeping, seed progression, coordinate alignment, and error
arithmetic are checked before aggregation. Inconsistent records abort the suite.

Base seeds are distinct within a plan. The existing curve runner increments each
base seed by point index modulo `2**32`. Each coordinate is summarized across its
repetitions separately. The same base seeds are reused across shot counts.

## Timing and interpretation

There is no explicit warmup. Each curve uses Nick's disposable worker. Later
requests can benefit from operating-system caches.

`request_wall_ms` includes worker startup, simulation, validation performed by the
runner, communication, and cleanup. The suite's `elapsed_ms` also includes plan
preparation, benchmark validation, and summary assembly. CLI file reading and
report serialization are outside that suite timer.

Each raw point retains Nick's existing timing scopes. The dense SciPy reference,
convergence check, ideal circuit execution, sampling, and circuit total are
summarized separately. Component intervals overlap their containing circuit timer.
The reference and circuit paths perform different workloads. Performance claims
require an agreed matching workload and additional evidence.

A higher shot count can yield a larger error in an individual stochastic run.
Interpret the repeated-run distributions with their recorded sample counts.

## Reviewing saved evidence

Export a Markdown review from an existing completed report.

```sh
.venv/bin/python -m app.benchmarks.review \
  /tmp/neutrino-evidence.json \
  --output /tmp/neutrino-review.md
```

Review checks the saved plan, exact repetition coverage and order, effective
requests, UTC creation time, recorded environment, package-version consistency,
curve budgets, measurement bookkeeping, ordered profiles, and curve coordinates.
Every summary is recomputed from the saved raw records, and the review uses those
recomputed statistics. Sample counts, nullable
availability, flavor channels, error families, and timing scopes must match.
Statistics permit relative floating-point differences up to `1e-12` and absolute
differences up to `1e-15`. Coordinate comparisons permit `1e-12` absolute difference.

The Markdown includes a SHA-256 digest of the exact source bytes, recorded
configuration and provenance, error summaries, and separate point and curve timing
tables. Values are displayed with eight significant digits. Full precision remains
in the original JSON. Unavailable analytical values and unmeasured timings retain
their meaning in the review.

Review consumes existing measurements through file I/O and arithmetic. The saved
report is bounded to 25 MB. The destination uses the same atomic exclusive
publication as the measurement CLI. Inconsistent evidence produces an error.

These checks establish internal consistency. Scientific interpretation and review
of the measurement provenance remain with the experiment owners. Nick and
Developer 5 should review the exported presentation before website integration.

## Reproducing the demonstration cases

The [example requests](../examples/neutrinos/) use the same electron initial
flavor, mixing angle of 0.2 radians, and normalized splitting and energy of 1.
They cover three configurations from the [neutrino experiment guide](NEUTRINOS.md).

| Request | Curve | What to inspect |
| --- | --- | --- |
| [Vacuum](../examples/neutrinos/vacuum-distance.json) | Five distances from 0 to 1 at zero potential | The zero-distance control and the final conversion probability |
| [Constant-density matter](../examples/neutrinos/matter-resonance.json) | Nine potentials from 0 to 1.8421220 at distance 4.0336989 | The resonant point at potential 0.9210610 and its neighboring points |
| [Ordered layers](../examples/neutrinos/layered-distance.json) | Five distances from 0 to 1 across potentials 0.2 then 1.4 | The first layer ends at distance 0.5. Points beyond it use the numerical reference for the two-layer profile. |

From `backend/`, run the same shot and base-seed grid for each case. The
commands record 27 curves and 171 point results and verify the three reports.
Each case uses a separate suite budget. Keep the requests, raw reports, reviews,
and `recording-source.txt` together when sharing a recording.

```sh
output_dir=$(mktemp -d /tmp/q-atlas-neutrino-demo.XXXXXX)
(
  set -e
  git rev-parse HEAD
  git status --porcelain
) > "$output_dir/recording-source.txt"
(
  set -e
  for case_name in vacuum-distance matter-resonance layered-distance; do
    cp "../examples/neutrinos/$case_name.json" "$output_dir/$case_name.json"
    .venv/bin/python -m app.benchmarks \
      --request "$output_dir/$case_name.json" \
      --shots 256 1024 4096 --seeds 42 142 242 --total-timeout 120 \
      --output "$output_dir/$case_name-evidence.json"
    .venv/bin/python -m app.benchmarks.review \
      "$output_dir/$case_name-evidence.json" \
      --output "$output_dir/$case_name-review.md"
  done
  printf 'Evidence saved in %s\n' "$output_dir"
)
```

Compare ideal Aer and SciPy at each coordinate to check circuit agreement.
Compare the measured probability with ideal Aer at the same coordinate to
isolate sampling error. The resonant point approaches full conversion, so its
neighboring points are more informative about finite-shot variability. Each
shot count has three observations per coordinate, and the shot groups reuse
base seeds. Treat medians and ranges as descriptive results for these settings.

## Recording a shareable demonstration bundle

From `backend/`, record all three checked-in cases and their reviews in one ZIP.
Choose an unused output filename in an existing directory.

```sh
.venv/bin/python -m app.benchmarks.demo \
  --requests ../examples/neutrinos \
  --output /tmp/q-atlas-neutrino-demo.zip
```

The command uses the shot counts and base seeds above. All three requests are
snapshotted and validated before execution, and each case has a 120-second suite
budget. The recording invokes the existing benchmark runner and checks every
saved report with the existing review exporter.

The completed archive contains twelve files.

- Three original request JSON files.
- Three full-precision evidence JSON files and their three checked Markdown reviews.
- `README.md` with the recorded curve counts, interpretation and reproduction notes.
- `provenance.json` with an aware UTC timestamp, Git revision, initial dirty-tree
  status, and SHA-256 hashes of the benchmark, neutrino, schema and dependency files.
- `SHA256SUMS` covering the other eleven files.

The raw reports retain their existing local format. Each report preserves its
own measured environment and simulation package versions. Git metadata is null
when unavailable. A dirty-tree recording includes source hashes alongside its
revision. The file fingerprints identify the implementation used for the
recording, and scientific provenance review remains with the experiment owners.

Publication happens after all cases and reviews complete and the source revision
and fingerprints are checked for changes during recording. Failures clean up the
staging directory. Atomic exclusive publication preserves existing output paths,
including when another writer publishes to the same path during execution.

After extracting the archive to a directory, check its contents from that directory.

```sh
shasum -a 256 -c SHA256SUMS
```

Label this archive as previously measured local simulator evidence when sharing
it. Nick and Developer 5 should review its presentation before website integration.

## Bounds and failures

Plans support up to eight distinct shot counts, sixteen distinct base seeds,
thirty-two curve requests, and two million scheduled samples times shots. Every
request also obeys the established neutrino web bounds. The suite budget defaults
to 120 seconds and supports 0.01–600 seconds.

Each worker receives the smaller of its request budget and the suite's remaining
budget. Timeout aborts the suite and the existing runner terminates and reaps its
worker. OS cleanup can add latency after expiry. Missing dependencies and invalid
or inconsistent responses also abort the suite.

## Tests

```sh
.venv/bin/python -m pytest tests/benchmarks -q
.venv/bin/ruff check app/benchmarks tests/benchmarks
.venv/bin/ruff format --check app/benchmarks tests/benchmarks
```

Tests cover bounded plans, exact summary arithmetic, raw-record preservation,
missing values, input ownership, seed wrapping, inconsistent records, global
deadlines, native worker cleanup, atomic publication, and the real local CLI.
