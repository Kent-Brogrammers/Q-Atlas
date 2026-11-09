# Compiler comparison preparation and future execution

The compiler accepts complete files around one marked objective, supports bounded
local numeric vectors, and can prepare a reproducible classical/QAOA comparison.
Preparation does not run the uploaded/generated script, either solver, a simulator,
hardware, or the supercomputer. No credentials or external quota are used.

## Use the current frontend

1. Open `/compiler` with the local API and frontend running.
2. In **Generate script**, choose an **Example program** and click **Load example**,
   or load your own `.py` file. The catalog includes two supported programs and three
   deliberate rejections; [the example README](../examples/compiler/programs/README.md)
   documents their expected outcomes and generated output files.
3. Select QAOA layers and click **Generate Python script**. Review the source download,
   objective diagnostics, canonical QUBO, and unexecuted circuit preview.
4. For supported source, click **Prepare comparison**.
5. Inspect both future paths and effective settings, then **Download comparison plan**.

Objective-only Analyze also supports preparation, with one preview layer. The page
never submits its execution endpoint. **Run comparison — execution disabled** is a
disabled control with no execution handler. Editing/loading source or changing layers
or workflow clears the generated script and plan; a late request cannot restore them.
Changing an example selection does not replace the source until **Load example** is clicked.

## What is compared

Both paths optimize the same server-verified canonical QUBO:

| Path | Future shared interface | Current execution |
| --- | --- | --- |
| Classical, no quantum interactions | `app.experiments.optimization.solvers.run_classical(qubo, config)` | Not run |
| QAOA, initially a local Aer simulator target | `app.quantum.qaoa.run_qaoa(qubo, config)` | Not run |

This is **objective optimization**, not whole-application timing. Parsing an objective
or calling `cost(x)` once is not a fair baseline for a QAOA optimization loop. Ordinary
imports, helpers, classes, I/O, and main-program code are preserved as opaque text;
they do not enter a Python executor or either solver. There is no script runner.

The full-file adapter is connected to the existing benchmark pipeline: it revalidates
the complete file through static generation, passes only the verified QUBO/config
to the shared runners, and validates their returned objectives/assignments. Integration
tests patch both runner boundaries. No synthetic results are served by the real API.
The underlying execution endpoint remains dependent on Developer 3's stubs; the new
frontend uses only the planning endpoint, even after another owner replaces those stubs.

## API and reproducibility

`POST /api/compiler/benchmark/plan` reuses `CompilerBenchmarkRequest`:

```json
{"source":"... complete source text ...", "config":{"p":2,"shots":1024,"seed":42}}
```

Defaults/bounds come from the existing `QAOAConfig`: p 1–8, shots 1–100,000, seed an
unsigned 32-bit integer, COBYLA, at most 1000 iterations, timeout >0 and <=60 seconds
per solver. The frontend uses selected p in generation mode (1 in objective-only mode)
and server defaults for the remaining fields. Default configuration is p=1,
shots=1024, seed=42, max_iterations=100, timeout_seconds=30.

HTTP 200 `CompilerBenchmarkPlan` contains:

- `status=planned` and `comparison_scope=objective_optimization`.
- `script_execution_enabled=false` and `quantum_execution_enabled=false`. They are
  literal false response fields; no request option can enable execution.
- Stable `problem_id` computed from the canonical instance; source formatting does
  not change the instance ID.
- SHA-256 of the exact source text and generated source text, plus the builder entrypoint.
  Unlike the instance ID, these hashes track formatting and code changes.
- The verified QUBO, effective QAOA config, and matching unexecuted circuit preview.
- Shared runner names and explicit remaining blockers.

There are no solutions, timings, measured depths, samples, success rates, or speedup
claims in this model. The schema rejects true execution flags and a circuit whose
width or p disagrees with the QUBO/config. Invalid source or configuration returns
the existing structured HTTP 422 envelope before either runner is touched.
The backend stores no submitted/generated file or execution job.

## Next integration steps

1. Try a real intended script using the supported objective subset. Save its source,
   mathematical meaning, expected QUBO, and exact rejection/mismatch if any. Full files
   are accepted around the marked region; arbitrary Python algorithms are not
   automatically translated into QAOA.
2. Relay this plan and [DEVELOPER_3_HANDOFF.md](DEVELOPER_3_HANDOFF.md) to Developer 3,
   and the page handoff to Developer 5. Shared runner ownership, bit order, objective
   sense, gate plan, and solver timing conventions remain unchanged.
3. Developer 3 supplies the actual shared classical/QAOA implementations, result
   validation, and deadline enforcement. Routine compiler tests remain mocked.
4. Agree an explicit execution opt-in and separately authorize any local simulator
   phase. The plan endpoint must stay nonexecuting. No hardware backend or automatic
   fallback to hardware is currently supported.
5. Then verify tiny objective comparisons with known arithmetic references, correct
   parameter/count order, provenance, real timers, and structured failures. Source
   parsing, verification, code generation, and common boundary work stay outside
   both solver-reported intervals. Use [BENCHMARK_METHODOLOGY.md](BENCHMARK_METHODOLOGY.md).

## Before whole-application timing

Running uploaded Python is outside the current project execution contract. Do not add
an API subprocess, dynamic import, `eval`, or `exec` to make a full script executable.
Whole-application timing needs a separate agreed design: a developer-reviewed trusted
application entrypoint, fixed inputs/outputs, equivalent classical/QAOA work, measured
common work, explicit quantum-call controls, deadlines, and a dedicated process/resource
boundary. That design also needs owners for output validation and timing provenance.

The current plan records that blocker rather than pretending its solver timers describe
the entire application. Hardware execution needs its own later authorization and quota
controls; the ten-minute supercomputer allocation remains untouched.
