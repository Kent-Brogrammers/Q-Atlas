"""Run local neutrino benchmark evidence with python -m app.benchmarks."""

import argparse
import os
import tempfile
from pathlib import Path

from app.benchmarks.neutrinos import (
    NeutrinoBenchmarkPlan,
    NeutrinoBenchmarkReport,
    run_neutrino_benchmark,
)
from app.schemas.neutrinos import NeutrinoRequest


def write_report(report: NeutrinoBenchmarkReport, destination: Path) -> None:
    """Publish a fully serialized file atomically, preserving any existing path."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".neutrino-benchmark-",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(report.model_dump_json(indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repeat local two-flavor neutrino simulations.")
    parser.add_argument(
        "--request", required=True, type=Path, help="Existing NeutrinoRequest JSON."
    )
    parser.add_argument("--shots", nargs="+", type=int, default=[256, 1024])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument(
        "--total-timeout", type=float, default=120, help="Whole-suite budget in seconds."
    )
    parser.add_argument("--output", required=True, type=Path, help="An unused JSON output path.")
    args = parser.parse_args(argv)
    try:
        if os.path.lexists(args.output) or not args.output.parent.is_dir():
            raise OSError("Output needs an existing directory and an unused filename")
        request = NeutrinoRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
        plan = NeutrinoBenchmarkPlan(
            request=request,
            shot_counts=args.shots,
            seeds=args.seeds,
            total_timeout_seconds=args.total_timeout,
        )
        report = run_neutrino_benchmark(plan)
        write_report(report, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Benchmark failed. {error}")
        return 1
    print(f"Saved {len(report.runs)} measured local Aer curves to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
