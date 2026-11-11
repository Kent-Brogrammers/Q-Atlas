"""Record the three neutrino examples as one checked, local evidence archive."""

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from app.benchmarks.__main__ import write_report
from app.benchmarks.neutrinos import NeutrinoBenchmarkPlan, run_neutrino_benchmark
from app.benchmarks.review import review_neutrino_report
from app.schemas.neutrinos import NeutrinoRequest

ROOT = Path(__file__).resolve().parents[3]
CASES = ("vacuum-distance", "matter-resonance", "layered-distance")


def _source_provenance(root: Path) -> dict:
    """Fingerprint the implementation and dependency definitions, using an allowlist."""

    def git(*arguments: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *arguments], cwd=root, capture_output=True, text=True, timeout=5
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    status = git("status", "--porcelain", "--untracked-files=all")
    paths = [
        *sorted((root / "backend/app/benchmarks").glob("*.py")),
        *sorted((root / "backend/app/experiments/neutrinos").glob("*.py")),
        root / "backend/app/schemas/contracts.py",
        root / "backend/app/schemas/neutrinos.py",
        root / "backend/pyproject.toml",
        root / "backend/uv.lock",
    ]
    return {
        "source_revision": git("rev-parse", "HEAD"),
        "working_tree_dirty": None if status is None else bool(status),
        "source_sha256": {
            path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
    }


def record_neutrino_demo(request_directory: Path, destination: Path) -> None:
    """Publish a complete ZIP exclusively after all three bounded suites pass review.

    Requests are snapshotted before execution. Every case uses the established
    shot/seed grid with a 120-second suite budget. Source changes during recording
    abort publication. A failed or interrupted recording cleans up staged files.
    """
    if os.path.lexists(destination) or not destination.parent.is_dir():
        raise OSError("Output needs an existing directory and an unused filename")
    requests = {case: (request_directory / f"{case}.json").read_bytes() for case in CASES}
    plans = {
        case: NeutrinoBenchmarkPlan(
            request=NeutrinoRequest.model_validate_json(content),
            shot_counts=[256, 1024, 4096],
            seeds=[42, 142, 242],
            total_timeout_seconds=120,
        )
        for case, content in requests.items()
    }
    provenance = _source_provenance(ROOT)
    with TemporaryDirectory(prefix=".q-atlas-neutrino-demo-", dir=destination.parent) as name:
        staging = Path(name)
        rows = []
        for case, plan in plans.items():
            (staging / f"{case}.json").write_bytes(requests[case])
            expected_plan = plan.model_dump(mode="python")
            report = run_neutrino_benchmark(plan)
            if report.plan.model_dump(mode="python") != expected_plan:
                raise ValueError("recorded plan differs from the snapshotted demo request")
            evidence = staging / f"{case}-evidence.json"
            write_report(report, evidence)
            review = review_neutrino_report(evidence)
            (staging / f"{case}-review.md").write_text(review, encoding="utf-8")
            points = sum(len(run.response.results) for run in report.runs)
            rows.append(f"| {case} | {plan.request.axis} | {len(report.runs)} | {points} |")

        metadata = {
            "bundle_version": 1,
            "source": "previously_measured_neutrino_demo",
            "recording_method": "run_neutrino_benchmark",
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            **provenance,
        }
        (staging / "provenance.json").write_text(
            json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        readme = [
            "# Q-Atlas neutrino demonstration evidence",
            "",
            "Previously measured local Qiskit Aer results in normalized units, using the",
            "effective two-flavor model with an electron initial state.",
            "",
            "Each case uses 256, 1024 and 4096 shots with base seeds 42, 142 and 242.",
            "Each point uses its base seed plus the coordinate index modulo 2**32.",
            "Each case has its own 120-second suite budget with zero warmup runs.",
            "",
            "| Case | Axis | Recorded curves | Point records |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "The request JSON files preserve the input bytes. The evidence JSON files",
            "retain full-precision measurements, counts, errors, timings and versions.",
            "Each Markdown review was checked against its corresponding evidence file.",
            "",
            "The ideal Aer–SciPy differences describe numerical circuit agreement.",
            "Measured–ideal differences describe finite-shot sampling error. The separate",
            "timing scopes cover different workloads. The shot groups reuse seeds and",
            "each coordinate has three observations per shot count.",
            "",
            "provenance.json records the source revision, initial working-tree status,",
            "and hashes of the simulation, benchmark, schema and dependency files.",
            "A dirty working tree requires retaining those hashes alongside the revision.",
            "Unavailable Git metadata is recorded as null. Checksums establish integrity.",
            "Scientific interpretation and provenance review remain with the owners.",
            "",
            "After extracting, verify the files with `shasum -a 256 -c SHA256SUMS`.",
            "The repository's docs/NEUTRINO_BENCHMARKING.md gives reproduction commands.",
            "",
        ]
        (staging / "README.md").write_text("\n".join(readme), encoding="utf-8")
        members = sorted(staging.iterdir())
        manifest = "".join(
            f"{sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in members
        )
        checksum_file = staging / "SHA256SUMS"
        checksum_file.write_text(manifest, encoding="utf-8")
        members.append(checksum_file)
        archive_path = staging / "evidence.zip"
        with ZipFile(archive_path, "x", compression=ZIP_DEFLATED) as archive:
            for path in members:
                archive.write(path, path.name)
        after = _source_provenance(ROOT)
        if any(after[key] != provenance[key] for key in ("source_revision", "source_sha256")):
            raise RuntimeError("source files or revision changed during demo recording")
        with archive_path.open("rb") as archive:
            os.fsync(archive.fileno())
        os.link(archive_path, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--requests", required=True, type=Path, help="Directory containing the three demo requests."
    )
    parser.add_argument("--output", required=True, type=Path, help="An unused ZIP output path.")
    args = parser.parse_args(argv)
    try:
        record_neutrino_demo(args.requests, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Demo recording failed. {error}")
        return 1
    print(f"Saved previously measured local Aer demo bundle to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
