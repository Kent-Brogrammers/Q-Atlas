"""Developer 3's local repeated-run evidence, consuming Nick's existing web runner.

The plan and report are local artifact models. Nick and Developer 5 should review
any future API integration. Physics, web schemas, and timing scopes belong to the
existing experiment implementation.
"""

import platform
from collections.abc import Iterable
from datetime import UTC, datetime
from math import isclose
from statistics import median, stdev
from time import perf_counter
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.experiments.neutrinos.runner import run_neutrinos
from app.schemas.contracts import Contract, NonNegative, Seed
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


def _configured_request(
    template: NeutrinoRequest, shots: int, seed: int, timeout_seconds: float
) -> NeutrinoRequest:
    payload = template.model_dump(mode="python")
    payload["experiment"].update(shots=shots, seed=seed)
    payload["timeout_seconds"] = timeout_seconds
    return NeutrinoRequest.model_validate(payload)


class NeutrinoBenchmarkPlan(Contract):
    """One physical curve repeated in shot-count order, then base-seed order."""

    request: NeutrinoRequest
    shot_counts: list[Annotated[int, Field(strict=True)]] = Field(
        default_factory=lambda: [256, 1024], min_length=1, max_length=8
    )
    seeds: list[Annotated[Seed, Field(strict=True)]] = Field(
        default_factory=lambda: [42, 43, 44], min_length=1, max_length=16
    )
    total_timeout_seconds: float = Field(default=120, ge=0.01, le=600)

    @model_validator(mode="after")
    def bounded_work(self):
        if len(set(self.shot_counts)) != len(self.shot_counts):
            raise ValueError("shot_counts must be unique")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be unique")
        if len(self.shot_counts) * len(self.seeds) > 32:
            raise ValueError("a benchmark supports at most 32 curve requests")
        for shots in self.shot_counts:
            _configured_request(self.request, shots, self.seeds[0], self.request.timeout_seconds)
        if sum(self.shot_counts) * len(self.seeds) * self.request.samples > 2_000_000:
            raise ValueError("scheduled samples * shots must not exceed 2000000")
        return self


class SampleStatistics(Contract):
    """Sample standard deviation is available for at least two observations."""

    count: int = Field(ge=0)
    minimum: float | None
    median: float | None
    maximum: float | None
    sample_stdev: NonNegative | None


class NeutrinoBenchmarkRun(Contract):
    request: NeutrinoRequest
    response: NeutrinoResponse
    request_wall_ms: NonNegative


class NeutrinoPointSummary(Contract):
    coordinate: float
    absolute_errors: dict[str, dict[str, SampleStatistics] | None]
    timing_ms: dict[str, SampleStatistics]


class NeutrinoShotSummary(Contract):
    shots: int
    repetitions: int
    request_wall_ms: SampleStatistics
    points: list[NeutrinoPointSummary]


class NeutrinoBenchmarkReport(Contract):
    format_version: Literal[1] = 1
    status: Literal["completed"] = "completed"
    created_at_utc: datetime
    warmup_policy: Literal["fresh worker per curve with zero warmup runs"] = (
        "fresh worker per curve with zero warmup runs"
    )
    environment: dict[str, str]
    plan: NeutrinoBenchmarkPlan
    runs: list[NeutrinoBenchmarkRun]
    summaries: list[NeutrinoShotSummary]
    elapsed_ms: NonNegative


def _statistics(values: Iterable[float | None]) -> SampleStatistics:
    measured = [value for value in values if value is not None]
    return SampleStatistics(
        count=len(measured),
        minimum=min(measured) if measured else None,
        median=median(measured) if measured else None,
        maximum=max(measured) if measured else None,
        sample_stdev=stdev(measured) if len(measured) > 1 else None,
    )


def _validate_response(request: NeutrinoRequest, response: NeutrinoResponse) -> None:
    """Check measurement bookkeeping and alignment without computing propagation."""
    extent = request.max_potential
    if request.axis == "distance":
        extent = sum(layer.distance for layer in request.experiment.layers)
    expected = [extent * index / (request.samples - 1) for index in range(request.samples)]
    if extent == 0:
        expected = [0.0]
    if response.axis != request.axis or len(response.results) != len(expected):
        raise ValueError("neutrino result does not match the requested curve")
    if len(response.coordinates) != len(expected) or any(
        not isclose(actual, wanted, rel_tol=0, abs_tol=1e-12)
        for actual, wanted in zip(response.coordinates, expected, strict=True)
    ):
        raise ValueError("neutrino result coordinates do not match the request")
    for index, record in enumerate(response.results):
        configuration = record.configuration
        if (
            configuration.seed != (request.experiment.seed + index) % 2**32
            or configuration.shots != request.experiment.shots
            or record.shots != request.experiment.shots
            or configuration.parameters != request.experiment.parameters
        ):
            raise ValueError("neutrino result configuration does not match the request")
        if request.axis == "distance":
            distance = sum(layer.distance for layer in configuration.layers)
            if not isclose(distance, response.coordinates[index], rel_tol=0, abs_tol=1e-12):
                raise ValueError("neutrino point configuration does not match its distance")
            layers = configuration.layers
            original_layers = request.experiment.layers
            if len(layers) > len(original_layers):
                raise ValueError("neutrino point contains layers outside the input profile")
            for layer_index, layer in enumerate(layers):
                original = original_layers[layer_index]
                if (
                    layer.potential != original.potential
                    or layer.distance > original.distance
                    or (layer_index < len(layers) - 1 and layer.distance != original.distance)
                ):
                    raise ValueError("neutrino point does not follow the ordered input profile")
        else:
            layer = request.experiment.layers[0].model_copy(
                update={"potential": response.coordinates[index]}
            )
            if configuration.layers != [layer]:
                raise ValueError("neutrino point configuration does not match its potential")
        if (
            not record.counts
            or set(record.counts) - {"0", "1"}
            or any(count < 0 for count in record.counts.values())
            or sum(record.counts.values()) != record.shots
        ):
            raise ValueError("neutrino measurement counts do not match shots")
        for name in ("numerical", "ideal", "measured"):
            probabilities = getattr(record, name).model_dump()
            if any(value < -1e-10 or value > 1 + 1e-10 for value in probabilities.values()):
                raise ValueError("neutrino probabilities are outside their numerical tolerance")
            if not isclose(sum(probabilities.values()), 1, rel_tol=0, abs_tol=1e-10):
                raise ValueError("neutrino probabilities are unnormalized")
        comparisons = [
            ("ideal_vs_numerical", record.ideal, record.numerical),
            ("sampling", record.measured, record.ideal),
            ("total", record.measured, record.numerical),
        ]
        if (record.analytical is None) != (record.absolute_errors.analytical_vs_numerical is None):
            raise ValueError("neutrino analytical error availability is inconsistent")
        if record.analytical is not None:
            comparisons.append(("analytical_vs_numerical", record.analytical, record.numerical))
        for flavor, key in (("electron", "0"), ("other", "1")):
            measured = getattr(record.measured, flavor)
            if not isclose(
                measured, record.counts.get(key, 0) / record.shots, rel_tol=0, abs_tol=1e-12
            ):
                raise ValueError("neutrino measured probabilities disagree with counts")
            for name, left, right in comparisons:
                reported = getattr(getattr(record.absolute_errors, name), flavor)
                expected_error = abs(getattr(left, flavor) - getattr(right, flavor))
                if not isclose(reported, expected_error, rel_tol=0, abs_tol=1e-12):
                    raise ValueError("neutrino error fields disagree with probabilities")
        durations = record.timing_ms.model_dump().values()
        components = (
            record.timing_ms.ideal_execution,
            record.quantum_timing.transpilation_ms,
            record.quantum_timing.sampling_ms,
        )
        if record.circuit_depth < 0 or any(value < 0 for value in durations):
            raise ValueError("neutrino depth and timings must be nonnegative")
        if any(
            value is not None and value > record.timing_ms.circuit_end_to_end + 1e-9
            for value in components
        ):
            raise ValueError("neutrino circuit timing component exceeds its total")
    if (
        request.axis == "distance"
        and response.results[-1].configuration.layers != request.experiment.layers
    ):
        raise ValueError("neutrino endpoint does not match the complete input profile")


def _summarize(shots: int, runs: list[NeutrinoBenchmarkRun]) -> NeutrinoShotSummary:
    points = []
    for index, coordinate in enumerate(runs[0].response.coordinates):
        rows = [run.response.results[index] for run in runs]
        errors = [row.absolute_errors.model_dump() for row in rows]
        error_statistics = {}
        for name, flavors in errors[0].items():
            if any((error[name] is None) != (flavors is None) for error in errors):
                raise ValueError("analytical error availability changed between repetitions")
            error_statistics[name] = (
                None
                if flavors is None
                else {
                    flavor: _statistics(error[name][flavor] for error in errors)
                    for flavor in flavors
                }
            )
        timing_statistics = {
            name: _statistics(getattr(row.timing_ms, name) for row in rows)
            for name in rows[0].timing_ms.model_dump()
        }
        for name in ("transpilation_ms", "sampling_ms"):
            timing_statistics[name] = _statistics(getattr(row.quantum_timing, name) for row in rows)
        points.append(
            NeutrinoPointSummary(
                coordinate=coordinate,
                absolute_errors=error_statistics,
                timing_ms=timing_statistics,
            )
        )
    return NeutrinoShotSummary(
        shots=shots,
        repetitions=len(runs),
        request_wall_ms=_statistics(run.request_wall_ms for run in runs),
        points=points,
    )


def run_neutrino_benchmark(plan: NeutrinoBenchmarkPlan) -> NeutrinoBenchmarkReport:
    """Repeat the existing bounded runner and return a complete local evidence report.

    Each curve receives the smaller of its own budget and the remaining suite
    budget. A failure aborts the suite. The suite timer includes preparation,
    workers, validation, and summary assembly. CLI serialization is outside it.
    Nick's internal point timers retain their original scopes and raw values.
    """
    started = perf_counter()
    plan = NeutrinoBenchmarkPlan.model_validate(plan.model_dump(mode="python"))
    deadline = started + plan.total_timeout_seconds
    runs = []
    summaries = []
    versions = None
    for shots in plan.shot_counts:
        group = []
        for seed in plan.seeds:
            remaining = deadline - perf_counter()
            if remaining < 0.01:
                raise TimeoutError("Neutrino benchmark exceeded its total budget")
            request = _configured_request(
                plan.request, shots, seed, min(plan.request.timeout_seconds, remaining)
            )
            original_request = request.model_dump(mode="python")
            request_started = perf_counter()
            response = run_neutrinos(request)
            request_wall_ms = (perf_counter() - request_started) * 1000
            if request_wall_ms >= request.timeout_seconds * 1000:
                raise TimeoutError("Neutrino curve exceeded its request budget")
            if request.model_dump(mode="python") != original_request:
                raise ValueError("neutrino runner changed its input request")
            if not isinstance(response, NeutrinoResponse):
                raise ValueError("neutrino runner returned an invalid response")
            response = NeutrinoResponse.model_validate(
                response.model_dump(mode="python"), strict=True
            )
            _validate_response(request, response)
            for record in response.results:
                if versions is not None and record.versions != versions:
                    raise ValueError("simulation package versions changed during the benchmark")
                versions = record.versions
            run = NeutrinoBenchmarkRun(
                request=request, response=response, request_wall_ms=request_wall_ms
            )
            runs.append(run)
            group.append(run)
            if perf_counter() >= deadline:
                raise TimeoutError("Neutrino benchmark exceeded its total budget")
        summaries.append(_summarize(shots, group))
    report = NeutrinoBenchmarkReport(
        created_at_utc=datetime.now(UTC),
        environment={
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        plan=plan,
        runs=runs,
        summaries=summaries,
        elapsed_ms=0,
    )
    finished = perf_counter()
    if finished >= deadline:
        raise TimeoutError("Neutrino benchmark exceeded its total budget")
    report.elapsed_ms = (finished - started) * 1000
    return report
