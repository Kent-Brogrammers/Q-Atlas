"""Bounded local scaling examples; reuse shared solvers, never execute source text."""

import argparse
import csv
import json
import platform
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from statistics import median

from app.compiler.generation import generate_source
from app.experiments.optimization.experiment import run_optimization
from app.experiments.optimization.heuristics import run_heuristic
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import GraphInput, OptimizationRequest, QAOAConfig, QUBOInput

WIDTHS = (6, 8, 10, 12, 14, 16)


def build_stress_graph(width: int, shape: str = "dense", instance: int = 0) -> GraphInput:
    """Fixed positive weights, nested vertex sets, dense or sparse connectivity."""
    if width not in WIDTHS or shape not in ("dense", "sparse") or not 0 <= instance < 8:
        raise ValueError("Use 6–16 even vertices, dense/sparse connectivity, and instance 0–7")
    edges = []
    for i, j in combinations(range(width), 2):
        if shape == "sparse" and j - i not in (1, 2) and (i, j) != (0, width - 1):
            continue
        key = f"qatlas-stress-v1:{i}:{j}" + (f":{instance}" if instance else "")
        weight = 1 + sha256(key.encode()).digest()[0] % 9
        edges.append({"i": i, "j": j, "coefficient": weight})
    return GraphInput(kind="graph", num_vertices=width, edges=edges)


def measure_case(selected, config, source_record):
    request = OptimizationRequest(problem=selected, config=config)
    comparison = run_optimization(request)
    qubo = comparison.metadata.qubo
    heuristic = run_heuristic(qubo, config)
    if evaluate_qubo(qubo, heuristic.best_bitstring) != heuristic.objective:
        raise ValueError("Heuristic objective does not match returned assignment")
    return {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "simulated": True,
        "method": "local_aer_statevector_training_then_local_sampling",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "input": source_record,
        "request": request.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
        "heuristic": heuristic.model_dump(mode="json"),
        "heuristic_optimality_gap": heuristic.objective - comparison.classical.objective,
    }


def summarize_batches(batches):
    """Keep only complete matched batches; failures are never zero-duration runs."""
    groups = {}
    for batch in batches:
        if batch["status"] == "completed":
            groups.setdefault((batch["qubits"], batch["p"]), []).append(batch)
    summary = []
    for (width, layers), trials in sorted(groups.items()):
        row = {
            "qubits": width,
            "p": layers,
            "instances": trials[0]["instances"],
            "repetitions": len(trials),
        }
        for field in (
            "exact_ms",
            "heuristic_ms",
            "qaoa_ms",
            "qaoa_gap",
            "heuristic_gap",
            "circuit_depth",
            "pair_gates",
        ):
            values = [trial[field] for trial in trials]
            row[field] = median(values)
            row[field + "_min"] = min(values)
            row[field + "_max"] = max(values)
        summary.append(row)
    return summary


def plot_scaling(summary, prefix):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not summary:
        raise ValueError("No completed matched batches to plot; inspect the raw failure records")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    runtime, gap, depth, pairs = axes.flat
    widths = sorted({row["qubits"] for row in summary})
    for field, label, color in [
        ("exact_ms", "Classical exact", "#555555"),
        ("heuristic_ms", "Classical heuristic", "#d58900"),
    ]:
        values = [
            median(row[field] for row in summary if row["qubits"] == n) / 1000 for n in widths
        ]
        runtime.plot(widths, values, "o-", label=label, color=color)
    for layers in sorted({row["p"] for row in summary}):
        rows = [row for row in summary if row["p"] == layers]
        x = [row["qubits"] for row in rows]
        label = f"QAOA p={layers}"
        runtime.plot(x, [row["qaoa_ms"] / 1000 for row in rows], "o-", label=label)
        runtime.fill_between(
            x,
            [row["qaoa_ms_min"] / 1000 for row in rows],
            [row["qaoa_ms_max"] / 1000 for row in rows],
            alpha=0.15,
        )
        gap.plot(x, [row["qaoa_gap"] for row in rows], "o-", label=label)
        depth.plot(x, [row["circuit_depth"] for row in rows], "o-", label=label)
        pairs.plot(x, [row["pair_gates"] for row in rows], "o-", label=label)
    gap.plot(
        widths,
        [median(row["heuristic_gap"] for row in summary if row["qubits"] == n) for n in widths],
        "o--",
        label="Classical heuristic",
    )
    runtime.axhline(2, ls=":", color="#888888", label="2 seconds")
    runtime.set_yscale("log")
    runtime.set_ylabel("Matched batch runtime (seconds, log scale)")
    gap.set_ylabel("Worst objective gap in batch (median across trials)")
    depth.set_ylabel("Largest transpiled circuit depth in batch")
    pairs.set_ylabel("Pair gates per circuit before transpilation")
    for ax in axes.flat:
        ax.set_xlabel("Qubits per problem")
        ax.set_xticks(widths)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    count = summary[0]["instances"]
    fig.suptitle(
        f"Q-Atlas local Aer scaling · {count} independent problem(s) per batch\n"
        "Same batch for every solver · end-to-end solver time · no QPU measurements"
    )
    for suffix in (".png", ".svg"):
        path = prefix.with_suffix(suffix)
        with path.open("xb") as handle:
            fig.savefig(handle, format=suffix[1:], dpi=160)
    plt.close(fig)


def run_sweep(args):
    widths = args.sizes or [args.qubits]
    layers = args.layers or [args.p]
    seeds = args.seeds or [args.seed]
    if len(seeds) != len(set(seeds)) or len(widths) != len(set(widths)):
        raise ValueError("Use distinct sizes and seeds for independent repetition records")
    configs = [
        QAOAConfig(
            p=p,
            shots=args.shots,
            seed=seed,
            max_iterations=args.max_iterations,
            timeout_seconds=args.timeout_seconds,
        )
        for p in layers
        for seed in seeds
    ]
    if not 1 <= args.instances <= 8:
        raise ValueError("instances must be between 1 and 8")
    if args.plot:
        # Fail before any computation if plotting dependencies are unavailable.
        import matplotlib  # noqa: F401

        for suffix in (".png", ".svg"):
            if args.plot.with_suffix(suffix).exists():
                raise ValueError("Plot output already exists; choose a new prefix")
    csv_path = args.output.with_suffix(".csv")
    if csv_path == args.output or csv_path.exists():
        raise ValueError("Choose an unused JSON output path and matching CSV filename")
    root = Path(__file__).resolve().parents[2]
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = (
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
        ).stdout
        != ""
    )
    report = {
        "simulated": True,
        "platform": platform.platform(),
        "revision": revision,
        "working_tree_dirty": dirty,
        "shape": args.shape,
        "batches": [],
        "summary": [],
    }
    with args.output.open("x", encoding="utf-8") as handle:
        for width in widths:
            for config in configs:
                batch = {
                    "qubits": width,
                    "p": config.p,
                    "seed": config.seed,
                    "instances": args.instances,
                    "status": "completed",
                    "runs": [],
                }
                try:
                    for instance in range(args.instances):
                        graph = build_stress_graph(width, args.shape, instance)
                        batch["runs"].append(measure_case(graph, config, {"instance": instance}))
                    runs = batch["runs"]
                    for field, section in [("exact_ms", "classical"), ("qaoa_ms", "quantum")]:
                        batch[field] = sum(run["comparison"][section]["elapsed_ms"] for run in runs)
                    batch["heuristic_ms"] = sum(run["heuristic"]["elapsed_ms"] for run in runs)
                    batch["qaoa_gap"] = max(
                        run["comparison"]["metrics"]["optimality_gap"] for run in runs
                    )
                    batch["heuristic_gap"] = max(run["heuristic_optimality_gap"] for run in runs)
                    batch["circuit_depth"] = max(
                        run["comparison"]["metrics"]["circuit_depth"] for run in runs
                    )
                    batch["pair_gates"] = len(graph.edges) * config.p
                except (TimeoutError, ValueError, RuntimeError, ImportError) as error:
                    batch.update(status="failed", error=type(error).__name__ + ": " + str(error))
                report["batches"].append(batch)
                report["summary"] = summarize_batches(report["batches"])
                handle.seek(0)
                json.dump(report, handle, indent=2, allow_nan=False)
                handle.write("\n")
                handle.truncate()
                handle.flush()
                print(
                    f"{width} qubits, p={config.p}, seed={config.seed}: {batch['status']}",
                    flush=True,
                )
    if report["summary"]:
        with csv_path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(report["summary"][0]))
            writer.writeheader()
            writer.writerows(report["summary"])
    if args.plot:
        plot_scaling(report["summary"], args.plot)
    return 1 if any(batch["status"] == "failed" for batch in report["batches"]) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare exact, heuristic, and local Aer QAOA.")
    problem = parser.add_mutually_exclusive_group()
    problem.add_argument("--qubits", type=int, choices=WIDTHS, default=8)
    problem.add_argument("--source", type=Path, help="Compile input as text; never run/import it")
    problem.add_argument("--sizes", type=int, nargs="+", choices=WIDTHS, help="Run a scaling sweep")
    parser.add_argument("--shape", choices=("dense", "sparse"), default="dense")
    parser.add_argument("--p", type=int, default=1)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=int, nargs="+")
    parser.add_argument("--layers", type=int, nargs="+", choices=range(1, 9))
    parser.add_argument("--instances", type=int, default=1, help="Matched problems per timed batch")
    parser.add_argument("--plot", type=Path, help="PNG/SVG prefix (sweep mode)")
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new filename")
        if args.sizes or args.layers or args.seeds or args.instances != 1 or args.plot:
            if args.source:
                raise ValueError("Use graph sizes for sweeps; --source is a single compiler case")
            return run_sweep(args)
        config = QAOAConfig(
            p=args.p,
            shots=args.shots,
            seed=args.seed,
            max_iterations=args.max_iterations,
            timeout_seconds=args.timeout_seconds,
        )
        if args.source:
            with args.source.open("rb") as handle:
                data = handle.read(80_001)
            if len(data) > 80_000:
                raise ValueError("Source exceeds 80,000 bytes")
            source = data.decode("utf-8")
            generated = generate_source(source, p=config.p)
            if generated.status != "supported":
                raise ValueError("Rejected source: " + str(generated.diagnostics))
            selected = QUBOInput(kind="qubo", qubo=generated.qubo)
            source_record = {"source": source, "source_sha256": sha256(data).hexdigest()}
        else:
            selected = build_stress_graph(args.qubits, args.shape)
            source_record = {"family": "qatlas-stress-v1", "shape": args.shape}
        record = measure_case(selected, config, source_record)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, allow_nan=False)
            handle.write("\n")
    except (ValueError, OSError, ImportError, RuntimeError, TimeoutError) as error:
        parser.exit(1, f"FAILED: {error}\n")
    print(f"Saved local simulator record to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
