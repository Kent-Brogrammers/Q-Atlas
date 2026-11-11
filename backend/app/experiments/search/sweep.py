"""Bounded, reproducible search batches: python -m app.experiments.search.sweep."""

import argparse
import json
import os
import platform
import subprocess
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from itertools import product
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter
from typing import Self

from pydantic import Field, model_validator

from app.experiments.search.runner import run_search
from app.experiments.search.settings import request_diagnostics
from app.schemas.contracts import Contract, RunConfig, SearchRequest, SearchResult

ROOT = Path(__file__).resolve().parents[4]


class SearchSweepPlan(Contract):
    """One marked set; Cartesian product of explicit iterations, shots and seeds."""

    num_qubits: int = Field(default=3, ge=1, le=6)
    marked_states: list[str] = Field(default_factory=lambda: ["001"], min_length=1, max_length=64)
    iterations: list[int] = Field(
        default_factory=lambda: list(range(7)), min_length=1, max_length=33
    )
    shot_counts: list[int] = Field(default_factory=lambda: [256, 1024], min_length=1, max_length=8)
    seeds: list[int] = Field(default_factory=lambda: [42, 43, 44], min_length=1, max_length=16)
    timeout_seconds: float = Field(default=30, gt=0, le=60)
    total_timeout_seconds: float = Field(default=300, gt=0, le=3600)

    @model_validator(mode="after")
    def validate_grid(self) -> Self:
        for name, values, maximum in (
            ("iterations", self.iterations, 32),
            ("shot_counts", self.shot_counts, 10000),
            ("seeds", self.seeds, 2**32 - 1),
        ):
            minimum = 1 if name == "shot_counts" else 0
            if len(set(values)) != len(values) or any(
                value < minimum or value > maximum for value in values
            ):
                raise ValueError(f"{name} must contain unique values in {minimum}..{maximum}")
        if len(self.iterations) * len(self.shot_counts) * len(self.seeds) > 256:
            raise ValueError("a search sweep supports at most 256 runs")
        SearchRequest(num_qubits=self.num_qubits, marked_states=self.marked_states)
        return self


def source_provenance() -> dict:
    """Record source identity without reading environment credentials."""

    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments], cwd=ROOT, capture_output=True, text=True, timeout=5
        )
        if result.returncode:
            raise RuntimeError("Git source provenance could not be read")
        return result.stdout.strip()

    paths = [
        *sorted(Path(__file__).parent.glob("*.py")),
        ROOT / "backend/app/schemas/contracts.py",
    ]
    return {
        "source_revision": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
        "environment": {"python": platform.python_version(), "system": platform.system()},
    }


def summarize(results: list[SearchResult]) -> list[dict]:
    """Group runs by iteration and shots; ranges describe observed seeded trials."""
    groups: dict[tuple[int, int], list[SearchResult]] = {}
    for result in results:
        parameters = result.metadata.parameters
        groups.setdefault((parameters.iterations, parameters.config.shots), []).append(result)
    summaries = []
    for (iteration, shots), runs in groups.items():
        probabilities = [run.metrics.success_probability for run in runs]
        summaries.append(
            {
                "iterations": iteration,
                "shots_per_run": shots,
                "seeds": [run.metadata.seed for run in runs],
                "repetitions": len(runs),
                "mean_success_probability": mean(probabilities),
                "minimum_success_probability": min(probabilities),
                "maximum_success_probability": max(probabilities),
                "sample_standard_deviation": stdev(probabilities) if len(runs) > 1 else None,
                "theoretical_success_probability": runs[0].metrics.theoretical_success_probability,
                "median_classical_ms": median(run.classical.elapsed_ms for run in runs),
                "median_quantum_ms": median(run.quantum.elapsed_ms for run in runs),
            }
        )
    return summaries


def run_sweep(plan: SearchSweepPlan) -> dict:
    """Use the existing isolated runner, including startup in each run's budget."""
    plan = SearchSweepPlan.model_validate(plan.model_dump())
    provenance = source_provenance()
    started = perf_counter()
    results = []
    versions = None
    for iteration, shots, seed in product(plan.iterations, plan.shot_counts, plan.seeds):
        remaining = plan.total_timeout_seconds - (perf_counter() - started)
        if remaining <= 0:
            raise TimeoutError("Search sweep exceeded its total timeout")
        request = SearchRequest(
            num_qubits=plan.num_qubits,
            marked_states=plan.marked_states,
            iterations=iteration,
            config=RunConfig(
                shots=shots, seed=seed, timeout_seconds=min(plan.timeout_seconds, remaining)
            ),
        )
        if diagnostics := request_diagnostics(request):
            raise ValueError(diagnostics[0].message)
        result = SearchResult.model_validate(run_search(request).model_dump())
        if (
            result.metadata.parameters != request
            or result.metadata.seed != seed
            or result.metrics.shots != shots
            or result.metrics.successful_shots is None
            or result.metrics.success_probability is None
            or result.metrics.theoretical_success_probability is None
            or result.classical is None
            or result.classical.elapsed_ms is None
            or result.quantum is None
            or result.quantum.elapsed_ms is None
            or not result.metadata.simulated
            or not result.metadata.versions
        ):
            raise ValueError("Search runner returned incomplete or mismatched evidence")
        if versions is not None and result.metadata.versions != versions:
            raise ValueError("Package versions changed during the search sweep")
        versions = result.metadata.versions
        results.append(result)
        if perf_counter() - started >= plan.total_timeout_seconds:
            raise TimeoutError("Search sweep exceeded its total timeout")
    summaries = summarize(results)
    return {
        "format_version": 1,
        "source": "measured_local_search_sweep",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        **provenance,
        "plan": plan.model_dump(mode="json"),
        "elapsed_ms": (perf_counter() - started) * 1000,
        "notice": (
            "Local Aer simulation, not QPU execution or evidence of runtime speedup. "
            "Ranges and sample standard deviations are descriptive, not confidence intervals. "
            "Seeds are reused across iteration/shot groups; groups are not independent replicates. "
            "Solver timings exclude worker startup; suite timing includes runner overhead, "
            "but excludes provenance collection and file serialization."
        ),
        "runs": [result.model_dump(mode="json") for result in results],
        "summaries": summaries,
    }


def write_report(report: dict, destination: Path) -> None:
    """Publish complete JSON without replacing any existing file or symlink."""
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-qubits", type=int, default=3)
    parser.add_argument("--marked-states", nargs="+", default=["001"])
    parser.add_argument("--iterations", nargs="+", type=int, default=list(range(7)))
    parser.add_argument("--shots", nargs="+", type=int, default=[256, 1024])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--total-timeout", type=float, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if os.path.lexists(args.output) or not args.output.parent.is_dir():
            raise ValueError("Output requires an existing directory and an unused filename")
        plan = SearchSweepPlan(
            num_qubits=args.num_qubits,
            marked_states=args.marked_states,
            iterations=args.iterations,
            shot_counts=args.shots,
            seeds=args.seeds,
            timeout_seconds=args.timeout,
            total_timeout_seconds=args.total_timeout,
        )
        report = run_sweep(plan)
        write_report(report, args.output)
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"Search sweep failed: {error}")
        return 1
    print(f"Saved {len(report['runs'])} measured search runs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
