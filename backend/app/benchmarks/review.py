"""Check saved neutrino evidence and export a human-readable local review.

Checks establish internal consistency of the saved measurements and summaries.
Scientific interpretation and review of provenance remain with the experiment
owners. Review performs file I/O and arithmetic over existing records.
"""

import argparse
import os
import re
from datetime import timedelta
from hashlib import sha256
from html import escape
from math import isclose
from pathlib import Path

from app.benchmarks import neutrinos
from app.benchmarks.artifacts import write_text_exclusive
from app.benchmarks.neutrinos import NeutrinoBenchmarkReport, NeutrinoShotSummary, SampleStatistics

MAX_REPORT_BYTES = 25_000_000


def _check_statistics(actual: SampleStatistics, expected: SampleStatistics) -> None:
    if actual.count != expected.count:
        raise ValueError("saved summary sample count disagrees with raw records")
    for name in ("minimum", "median", "maximum", "sample_stdev"):
        left, right = getattr(actual, name), getattr(expected, name)
        if left is None or right is None:
            if left != right:
                raise ValueError("saved summary availability disagrees with raw records")
        elif not isclose(left, right, rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("saved summary statistics disagree with raw records")


def _check_summary(actual: NeutrinoShotSummary, expected: NeutrinoShotSummary) -> None:
    if (
        actual.shots != expected.shots
        or actual.repetitions != expected.repetitions
        or len(actual.points) != len(expected.points)
    ):
        raise ValueError("saved summary grouping disagrees with the plan")
    _check_statistics(actual.request_wall_ms, expected.request_wall_ms)
    for point, reference in zip(actual.points, expected.points, strict=True):
        if not isclose(point.coordinate, reference.coordinate, rel_tol=0, abs_tol=1e-12):
            raise ValueError("saved summary coordinate disagrees with raw records")
        if point.timing_ms.keys() != reference.timing_ms.keys():
            raise ValueError("saved summary timing fields disagree with raw records")
        for name, statistics in reference.timing_ms.items():
            _check_statistics(point.timing_ms[name], statistics)
        if point.absolute_errors.keys() != reference.absolute_errors.keys():
            raise ValueError("saved summary error families disagree with raw records")
        for name, errors in reference.absolute_errors.items():
            saved = point.absolute_errors[name]
            if errors is None or saved is None:
                if errors != saved:
                    raise ValueError("saved analytical availability disagrees with raw records")
            else:
                if errors.keys() != saved.keys():
                    raise ValueError("saved summary flavor channels disagree with raw records")
                for flavor, statistics in errors.items():
                    _check_statistics(saved[flavor], statistics)


def validate_neutrino_report(report: NeutrinoBenchmarkReport) -> NeutrinoBenchmarkReport:
    """Return a validated snapshot after recomputing summaries from raw records."""
    report = NeutrinoBenchmarkReport.model_validate(report.model_dump(mode="python"), strict=True)
    plan = report.plan
    if report.created_at_utc.utcoffset() != timedelta(0):
        raise ValueError("saved report requires an aware UTC creation time")
    if not all(report.environment.get(name) for name in ("python", "system", "machine")):
        raise ValueError("saved report is missing environment provenance")
    if len(report.runs) != len(plan.shot_counts) * len(plan.seeds):
        raise ValueError("saved report is missing or duplicating planned runs")
    if len(report.summaries) != len(plan.shot_counts):
        raise ValueError("saved report is missing or duplicating shot summaries")
    if report.elapsed_ms >= plan.total_timeout_seconds * 1000:
        raise ValueError("saved completed report exceeds its suite budget")
    if sum(run.request_wall_ms for run in report.runs) > report.elapsed_ms + 1e-6:
        raise ValueError("saved curve durations exceed the suite elapsed time")

    versions = None
    index = 0
    for summary_index, shots in enumerate(plan.shot_counts):
        group = []
        for seed in plan.seeds:
            run = report.runs[index]
            expected = neutrinos._configured_request(
                plan.request, shots, seed, run.request.timeout_seconds
            )
            if run.request != expected:
                raise ValueError("saved request order or settings disagree with the plan")
            if run.request.timeout_seconds > min(
                plan.request.timeout_seconds, plan.total_timeout_seconds
            ):
                raise ValueError("saved request exceeds its configured budget")
            if run.request_wall_ms >= run.request.timeout_seconds * 1000:
                raise ValueError("saved completed curve exceeds its request budget")
            neutrinos._validate_response(run.request, run.response)
            for record in run.response.results:
                if versions is not None and record.versions != versions:
                    raise ValueError("saved simulation versions differ between records")
                versions = record.versions
            group.append(run)
            index += 1
        recomputed = neutrinos._summarize(shots, group)
        _check_summary(report.summaries[summary_index], recomputed)
        report.summaries[summary_index] = recomputed
    return report


def _cell(value) -> str:
    """Escape metadata for literal Markdown table content."""
    text = escape(str(value)).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#!|])", r"\\\1", text)


def _number(value: float | None) -> str:
    return "unavailable" if value is None else format(value, ".8g")


def _table(headers, rows) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows),
        "",
    ]


def _render(report: NeutrinoBenchmarkReport, digest: str) -> str:
    request = report.plan.request
    parameters = request.experiment.parameters
    versions = report.runs[0].response.results[0].versions
    lines = [
        "# Neutrino benchmark review",
        "",
        (
            "Previously measured local Qiskit Aer results in normalized units, "
            "using the effective two-flavor model."
        ),
        "",
        f"Recorded at {report.created_at_utc.isoformat()}.",
        "",
        f"Source JSON SHA-256 `{digest}`.",
        "",
        (
            "Internal consistency checks passed for raw bookkeeping, the repetition plan, "
            "and recomputed summaries. Scientific interpretation and provenance review "
            "remain with the experiment owners."
        ),
        "",
        "## Recorded configuration",
        "",
        (
            f"Curve axis `{request.axis}` with {request.samples} requested points. "
            f"Base seeds {', '.join(map(str, report.plan.seeds))}."
        ),
        "",
        (
            f"Mixing angle {parameters.theta:.8g} rad, splitting {parameters.delta_m2:.8g}, "
            f"energy {parameters.energy:.8g}, particle `{parameters.particle}`. "
            "Initial flavor is electron."
        ),
        "",
    ]
    lines.extend(
        _table(
            ["Layer", "Distance", "Potential"],
            [
                [index + 1, _number(layer.distance), _number(layer.potential)]
                for index, layer in enumerate(request.experiment.layers)
            ],
        )
    )
    lines.extend(
        [
            "## Provenance",
            "",
            (
                f"{len(report.runs)} recorded curves, "
                f"{sum(len(run.response.results) for run in report.runs)} raw scientific records."
            ),
            "",
        ]
    )
    lines.extend(
        _table(
            ["Field", "Recorded value"],
            [
                *report.environment.items(),
                *versions.items(),
                ("Warmup policy", report.warmup_policy),
            ],
        )
    )
    lines.extend(
        [
            "## Probability errors",
            "",
            (
                "Values have eight significant digits here. The source JSON retains full "
                "recorded precision. Analytical results can be unavailable for layered profiles."
            ),
            "",
        ]
    )
    errors = []
    timings = []
    for summary in report.summaries:
        for point in summary.points:
            for flavor in ("electron", "other"):
                analytical = point.absolute_errors["analytical_vs_numerical"]
                sampling = point.absolute_errors["sampling"][flavor]
                errors.append(
                    [
                        summary.shots,
                        _number(point.coordinate),
                        flavor,
                        sampling.count,
                        _number(point.absolute_errors["ideal_vs_numerical"][flavor].maximum),
                        _number(sampling.median),
                        _number(sampling.sample_stdev),
                        _number(point.absolute_errors["total"][flavor].median),
                        _number(analytical[flavor].maximum if analytical is not None else None),
                    ]
                )
            for name, statistics in point.timing_ms.items():
                timings.append(
                    [
                        summary.shots,
                        _number(point.coordinate),
                        name,
                        statistics.count,
                        _number(statistics.minimum),
                        _number(statistics.median),
                        _number(statistics.maximum),
                        _number(statistics.sample_stdev),
                    ]
                )
    lines.extend(
        _table(
            [
                "Shots",
                "Coordinate",
                "Flavor",
                "n",
                "Max ideal vs reference",
                "Median sampling",
                "Sampling SD",
                "Median total",
                "Max analytical vs reference",
            ],
            errors,
        )
    )
    lines.extend(
        [
            "## Timing by scientific point",
            "",
            (
                "All durations are milliseconds. Point scopes retain the experiment's original "
                "definitions. Circuit totals contain transpilation, ideal execution, and sampling. "
                "The SciPy reference and circuit paths perform different workloads."
            ),
            "",
        ]
    )
    lines.extend(
        _table(
            [
                "Shots",
                "Coordinate",
                "Scope",
                "n",
                "Minimum ms",
                "Median ms",
                "Maximum ms",
                "Sample SD ms",
            ],
            timings,
        )
    )
    lines.extend(
        [
            "## Curve wall time",
            "",
            (
                "Curve wall time includes worker startup, simulation, communication, runner "
                "validation, and cleanup. Suite elapsed time also includes benchmark preparation, "
                "validation, and summary assembly. File serialization is outside that interval."
            ),
            "",
        ]
    )
    lines.extend(
        _table(
            ["Shots", "n", "Minimum ms", "Median ms", "Maximum ms", "Sample SD ms"],
            [
                [
                    summary.shots,
                    summary.request_wall_ms.count,
                    _number(summary.request_wall_ms.minimum),
                    _number(summary.request_wall_ms.median),
                    _number(summary.request_wall_ms.maximum),
                    _number(summary.request_wall_ms.sample_stdev),
                ]
                for summary in report.summaries
            ],
        )
    )
    lines.extend(
        [
            f"Recorded suite elapsed time {_number(report.elapsed_ms)} ms.",
            "",
            (
                "Results are grouped separately by shot count, coordinate, and flavor. "
                "Sample standard deviation is unavailable with fewer than two repetitions. "
                "Unmeasured timing statistics retain count zero and unavailable values."
            ),
            "",
            (
                "This review summarizes previously recorded measurements. Runtime advantage "
                "requires an agreed matching workload and further evidence. Nick and Developer 5 "
                "should review the local report presentation before website integration."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def review_neutrino_report(source: Path) -> str:
    """Check a bounded saved report and render its provenance and measured summaries."""
    with source.open("rb") as handle:
        data = handle.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("saved report exceeds the 25000000-byte review limit")
    report = NeutrinoBenchmarkReport.model_validate_json(data, strict=True)
    report = validate_neutrino_report(report)
    return _render(report, sha256(data).hexdigest())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check saved neutrino evidence and export Markdown."
    )
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--output", type=Path, required=True, help="An unused Markdown output path."
    )
    args = parser.parse_args(argv)
    try:
        if os.path.lexists(args.output) or not args.output.parent.is_dir():
            raise OSError("Output needs an existing directory and an unused filename")
        markdown = review_neutrino_report(args.report)
        write_text_exclusive(markdown, args.output)
    except (OSError, ValueError) as error:
        print(f"Review failed. {error}")
        return 1
    print(f"Checked saved neutrino evidence and wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
