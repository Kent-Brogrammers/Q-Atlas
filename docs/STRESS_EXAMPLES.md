# Q-Atlas stress examples

## One scalable benchmark and graph command

Install the locked extras (`uv sync --locked --all-extras` in `backend/`), then run:

```sh
.venv/bin/python -m scripts.benchmark_stress_examples \
  --sizes 6 8 10 12 14 16 --layers 1 --seeds 7 42 99 --instances 3 \
  --max-iterations 20 --shots 1024 \
  --output /tmp/qatlas-scaling.json --plot /tmp/qatlas-scaling
```

This one script saves raw JSON, summary CSV, and PNG/SVG graphs. Adjust sizes,
layers, seeds, shots, and the number of independent problems per batch. Each solver
solves the **same full batch**; `--instances 3` triples work for all three methods,
not just the classical baseline. It can bring exact classical batch time above
two seconds naturally, while remaining within the existing 16-qubit contract.
There are no sleeps or extra classical-only tasks in the timing path.

The graph shows median batch runtime versus qubits, objective gap, transpiled
circuit depth, and pair-gate count. QAOA shading spans the observed min/max across
seeds. Timing uses full solver intervals, including local angle training, and
the labels identify local simulation. Failed batches retain partial raw evidence
and are excluded from completed-batch summaries. Repetitions do not certify an
advantage; compare the heuristic and solution quality too.

Matplotlib is an optional `benchmarks` extra. Output files must be new. The script
checkpoints after each batch and records revision, dirty-tree status, platform,
versions, exact inputs/configuration, and its own source hash.

A classical result around 0.5 ms versus a quantum-path result around 2000 ms is
plausible for a tiny problem. Six bits have only 64 assignments. Changing their
weights cannot turn that into a large search space. The compiler currently accepts
at most six bits; the shared local runner accepts up to 16 (65,536 assignments).

The three new **Compiler → Example** entries exercise dense weighted Max-Cut,
balanced workloads, and conflicting task selection. Their definitions and exact
reference values are in the [example catalog](../examples/compiler/programs/README.md#stress-examples-also-in-the-ui-picker).
Choose one, click **Load example**, then **Convert Python**. Conversion submits no job.

## Larger examples with the existing local runner

From `backend/`, with the existing quantum extra installed, run a bounded local
comparison. This invokes exact enumeration, local Aer QAOA, and the existing
eight-start classical bit-flip heuristic. It uses no account or hardware quota.

```sh
.venv/bin/python -m scripts.benchmark_stress_examples --qubits 8 --p 1 --output /tmp/qatlas-dense-8.json
.venv/bin/python -m scripts.benchmark_stress_examples --qubits 12 --p 1 --output /tmp/qatlas-dense-12.json
.venv/bin/python -m scripts.benchmark_stress_examples --qubits 16 --p 1 --output /tmp/qatlas-dense-16.json
```

The fixed `qatlas-stress-v1` family has all pairs connected with integer weights
1–9. Each edge's weight is `1 + first_byte(SHA256("qatlas-stress-v1:i:j")) % 9`.
Vertex subsets keep their weights, and the six-vertex case matches the compiler
Max-Cut example. At 8, 12, and 16 qubits there are 28, 66, and 120 interacting
pairs per QAOA layer. These are stress instances, not proven hard instances.

Compare connectivity and depth independently of width:

```sh
.venv/bin/python -m scripts.benchmark_stress_examples --qubits 16 --shape sparse --p 1 --output /tmp/qatlas-sparse-16.json
.venv/bin/python -m scripts.benchmark_stress_examples --qubits 12 --p 2 --max-iterations 100 --seed 7 --output /tmp/qatlas-dense-12-p2-seed7.json
```

The sparse graph keeps nearest and next-nearest neighbors plus the closing edge;
16 vertices have 30 interacting pairs. Increasing `p` adds both gates and optimizer
parameters. A fixed finite optimization budget need not yield better solutions
at larger `p`. Repeat with seeds 7, 42, and 99 before interpreting a favorable run.

To compare a compiler example locally, without submitting hardware work:

```sh
.venv/bin/python -m scripts.benchmark_stress_examples --source ../examples/compiler/programs/stress_partition_6.py --p 2 --output /tmp/qatlas-partition-6.json
```

Source is parsed and validated as text, never executed or imported. Larger graphs
enter as validated graph/QUBO data, so this does not bypass compiler validation.
Defaults are 20 expectation evaluations, 1024 final shots, seed 42, and 30 seconds
per solver. A timeout is a failed run, not a measured solution; increase budgets
only deliberately within the existing maximum of 60 seconds per solver. The
commands create new output files and refuse to overwrite earlier records.

## What to compare

The JSON includes the full input/configuration, package versions, UTC timestamp,
runner hash, raw solver records, and both sampled and heuristic gaps to the exact
optimum. Retain the repository revision and machine details with the files.
Compare end-to-end runtime **and** gaps across sizes and seeds. Include the classical
heuristic so an expensive exact solve is not the only classical competitor.

Local QAOA time includes worker startup, statevector preparation and repeated
expectation evaluations, transpilation, and final sampling. Its implementation
also enumerates all `2^n` costs to score statevectors. More qubits increase that
classical simulation workload too. Separate optimizer/transpilation/sampling
timers are recorded; they need not sum to the entire interval.

If viewing the IBM results page, **QPU usage** is a different measurement from
local QAOA end-to-end time and excludes local angle training. Check the field's
label before interpreting a 2000 ms reading. See [hardware timing](COMPILER_IBM_HARDWARE.md#what-runs-where).

These examples expose scaling and approximation limits. They do not promise a
runtime crossover. A claim of quantum advantage would require larger validated
instances, competitive classical methods, comparable solution quality, and complete
hardware-assisted timing, beyond the current compiler and runner limits.
