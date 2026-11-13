"""Local plan bounds, independently checked summary arithmetic, and real runner calls."""

import json
import multiprocessing as mp
import os
import subprocess
import sys
from copy import deepcopy
from functools import partial
from hashlib import sha256
from pathlib import Path
from time import perf_counter, sleep
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from app.benchmarks import demo, neutrinos, review
from app.experiments.neutrinos import runner
from app.experiments.neutrinos.model import Experiment, Layer
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


def _blocked_worker(connection, payload, *, marker):
    Path(marker).write_text("entered native work")
    sleep(30)


def synthetic_response(request):
    """Synthetic probabilities/timings for bookkeeping tests, confined to tests."""
    total = sum(layer.distance for layer in request.experiment.layers)
    extent = total if request.axis == "distance" else request.max_potential
    coordinates = [extent * i / (request.samples - 1) for i in range(request.samples)]
    if not extent:
        coordinates = [0.0]
    records = []
    for index, coordinate in enumerate(coordinates):
        layers = deepcopy(request.experiment.layers)
        if request.axis == "potential":
            layers[0].potential = coordinate
        elif index != len(coordinates) - 1:
            layers = [layers[0].model_copy(update={"distance": coordinate})]
        zero_distance = request.axis == "distance" and coordinate == 0
        count_other = (
            0 if zero_distance else request.experiment.seed % 3 * request.experiment.shots // 4
        )
        measured_other = count_other / request.experiment.shots
        ideal_other = 0.0 if zero_distance else 0.5
        reference = {"electron": 1 - ideal_other, "other": ideal_other}
        error = abs(measured_other - ideal_other)
        errors = {"electron": error, "other": error}
        analytical = None
        analytical_error = None
        if len(layers) == 1:
            analytical = {**reference, "frequency": 1, "theta_m": 0.2, "mixing_strength": 0.5}
            analytical_error = {"electron": 0, "other": 0}
        configuration = request.experiment.model_copy(
            update={"layers": layers, "seed": (request.experiment.seed + index) % 2**32}
        )
        records.append(
            {
                "experiment": "q_neutrino",
                "status": "completed",
                "backend": "aer_simulator",
                "simulated": True,
                "configuration": configuration,
                "analytical": analytical,
                "numerical": reference,
                "ideal": reference,
                "measured": {"electron": 1 - measured_other, "other": measured_other},
                "absolute_errors": {
                    "ideal_vs_numerical": {"electron": 0, "other": 0},
                    "sampling": errors,
                    "total": errors,
                    "analytical_vs_numerical": analytical_error,
                },
                "numerics": {
                    "reference_norm": 1,
                    "ideal_norm": 1,
                    "state_error_l2": 0,
                    "subdivision_check": {
                        "subdivisions_per_layer": 2,
                        "state_change_l2": 0,
                        "scope": "synthetic fixture",
                    },
                    "approximation": "synthetic fixture",
                },
                "num_qubits": 1,
                "circuit_depth": 4,
                "shots": request.experiment.shots,
                "counts": {"0": request.experiment.shots - count_other, "1": count_other},
                "basis_gates": ["ry", "rz"],
                "timing_ms": {
                    "classical": 1,
                    "convergence_check": 1,
                    "circuit_end_to_end": 5,
                    "ideal_execution": 1,
                },
                "quantum_timing": {
                    "includes_queue": False,
                    "includes_transpilation": True,
                    "includes_optimizer": False,
                    "includes_sampling": True,
                    "transpilation_ms": 1,
                    "sampling_ms": 2,
                },
                "versions": {"qiskit": "synthetic fixture"},
            }
        )
    return NeutrinoResponse(axis=request.axis, coordinates=coordinates, results=records)


@pytest.fixture
def plan():
    return neutrinos.NeutrinoBenchmarkPlan(
        request=NeutrinoRequest(experiment=Experiment(layers=[Layer(distance=1)]), samples=2),
        shot_counts=[8, 16],
        seeds=[0, 1, 2],
    )


@pytest.fixture
def fake_runner(monkeypatch):
    mock = Mock(side_effect=synthetic_response)
    monkeypatch.setattr(neutrinos, "run_neutrinos", mock)
    return mock


@pytest.mark.parametrize(
    "patch",
    [
        {"shot_counts": []},
        {"shot_counts": [0]},
        {"shot_counts": [100001]},
        {"shot_counts": [True]},
        {"shot_counts": [8, 8]},
        {"seeds": []},
        {"seeds": [1, 1]},
        {"seeds": [-1]},
        {"seeds": [2**32]},
        {"seeds": [True]},
        {"total_timeout_seconds": 0},
        {"total_timeout_seconds": 601},
        {"shot_counts": list(range(1, 9)), "seeds": list(range(5))},
        {"shot_counts": [100000], "seeds": list(range(11))},
    ],
)
def test_invalid_and_excessive_plans_are_rejected(plan, patch):
    with pytest.raises(ValidationError):
        neutrinos.NeutrinoBenchmarkPlan.model_validate({**plan.model_dump(), **patch})


def test_each_scheduled_request_obeys_the_existing_web_work_limit(plan):
    payload = plan.model_dump()
    payload["request"]["samples"] = 41
    payload["shot_counts"] = [20000]
    with pytest.raises(ValidationError, match="500000"):
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)


def test_repetitions_preserve_raw_records_and_group_by_shots_and_coordinate(plan, fake_runner):
    before = plan.model_dump()
    report = neutrinos.run_neutrino_benchmark(plan)
    assert plan.model_dump() == before
    assert [(run.request.experiment.shots, run.request.experiment.seed) for run in report.runs] == [
        (8, 0),
        (8, 1),
        (8, 2),
        (16, 0),
        (16, 1),
        (16, 2),
    ]
    assert fake_runner.call_count == 6
    assert report.status == "completed"
    assert report.created_at_utc.utcoffset().total_seconds() == 0
    assert report.environment["python"]
    assert report.elapsed_ms > 0
    for run in report.runs:
        assert run.response == synthetic_response(run.request)
        assert run.request_wall_ms >= 0
    for group in report.summaries:
        assert group.repetitions == group.request_wall_ms.count == 3
        assert [point.coordinate for point in group.points] == [0, 1]
        initial = group.points[0].absolute_errors["sampling"]["other"]
        assert initial.minimum == initial.median == initial.maximum == initial.sample_stdev == 0
        statistics = group.points[1].absolute_errors["sampling"]["other"]
        assert statistics.count == 3
        assert (statistics.minimum, statistics.median, statistics.maximum) == (0, 0.25, 0.5)
        assert statistics.sample_stdev == 0.25
        assert group.points[1].timing_ms["classical"].median == 1
        assert group.points[1].timing_ms["sampling_ms"].median == 2
    assert neutrinos.NeutrinoBenchmarkReport.model_validate_json(report.model_dump_json()) == report


def test_one_repetition_preserves_unknown_spread_and_unavailable_analytical_errors(
    plan, fake_runner
):
    payload = plan.model_dump()
    payload["seeds"] = [42]
    payload["shot_counts"] = [8]
    payload["request"]["experiment"]["layers"] = [
        {"distance": 0.5, "potential": 0.2},
        {"distance": 0.5, "potential": 1.4},
    ]
    report = neutrinos.run_neutrino_benchmark(
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)
    )
    point = report.summaries[0].points[-1]
    assert point.absolute_errors["analytical_vs_numerical"] is None
    assert point.absolute_errors["sampling"]["other"].sample_stdev is None


def test_unmeasured_timing_stays_null_with_zero_observations(plan, monkeypatch):
    def response(request):
        result = synthetic_response(request)
        for record in result.results:
            record.quantum_timing.sampling_ms = None
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    result = neutrinos.run_neutrino_benchmark(plan)
    statistics = result.summaries[0].points[0].timing_ms["sampling_ms"]
    assert statistics.count == 0
    assert statistics.minimum is statistics.median is statistics.maximum is None


def test_potential_axis_and_seed_wrap_use_the_existing_contract(plan, fake_runner):
    payload = plan.model_dump()
    payload["request"].update(axis="potential", max_potential=1.5)
    payload["seeds"] = [2**32 - 1]
    result = neutrinos.run_neutrino_benchmark(
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)
    )
    assert result.runs[0].response.coordinates == [0, 1.5]
    assert result.runs[0].response.results[1].configuration.seed == 0


@pytest.mark.parametrize(
    "field,value",
    [
        (("axis",), "potential"),
        (("results",), []),
        (("coordinates", 0), 0.5),
        (("results", 1, "configuration", "seed"), 19),
        (("results", 1, "configuration", "parameters", "energy"), 2),
        (("results", 1, "configuration", "layers", 0, "distance"), 2),
        (("results", 1, "shots"), 7),
        (("results", 1, "counts", "0"), -1),
        (("results", 1, "counts", "0"), True),
        (("results", 1, "counts"), {"10": 8}),
        (("results", 1, "measured", "other"), 0.1),
        (("results", 1, "ideal", "other"), -1),
        (("results", 1, "absolute_errors", "sampling", "other"), 0.9),
        (("results", 1, "analytical"), None),
        (("results", 1, "timing_ms", "classical"), -1),
        (("results", 1, "timing_ms", "ideal_execution"), 10),
        (("results", 1, "quantum_timing", "sampling_ms"), 10),
    ],
)
def test_inconsistent_measurement_records_are_rejected(plan, monkeypatch, field, value):
    def response(request):
        result = synthetic_response(request)
        parent = result
        for part in field[:-1]:
            parent = parent[part] if isinstance(parent, (list, dict)) else getattr(parent, part)
        if isinstance(parent, (list, dict)):
            parent[field[-1]] = value
        else:
            setattr(parent, field[-1], value)
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(ValueError):
        neutrinos.run_neutrino_benchmark(plan)


def test_version_changes_abort_comparison(plan, monkeypatch):
    def response(request):
        result = synthetic_response(request)
        result.results[-1].versions["qiskit"] = str(request.experiment.seed)
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(ValueError, match="versions changed"):
        neutrinos.run_neutrino_benchmark(plan)


def test_runner_mutation_is_detected_without_changing_the_callers_plan(plan, monkeypatch):
    before = plan.model_dump()

    def response(request):
        request.experiment.seed += 1
        return synthetic_response(request)

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(ValueError, match="changed its input"):
        neutrinos.run_neutrino_benchmark(plan)
    assert plan.model_dump() == before


def test_suite_budget_reduces_each_worker_budget(plan, monkeypatch):
    now = 0

    def response(request):
        nonlocal now
        now += 1
        return synthetic_response(request)

    monkeypatch.setattr(neutrinos, "perf_counter", lambda: now)
    mock = Mock(side_effect=response)
    monkeypatch.setattr(neutrinos, "run_neutrinos", mock)
    payload = {**plan.model_dump(), "shot_counts": [8], "total_timeout_seconds": 3.5}
    result = neutrinos.run_neutrino_benchmark(
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)
    )
    assert [call.args[0].timeout_seconds for call in mock.call_args_list] == [3.5, 2.5, 1.5]
    assert result.elapsed_ms == 3000


def test_late_worker_result_does_not_produce_a_completed_report(plan, monkeypatch):
    now = 0

    def response(request):
        nonlocal now
        now += 2
        return synthetic_response(request)

    monkeypatch.setattr(neutrinos, "perf_counter", lambda: now)
    mock = Mock(side_effect=response)
    monkeypatch.setattr(neutrinos, "run_neutrinos", mock)
    payload = {**plan.model_dump(), "total_timeout_seconds": 1}
    with pytest.raises(TimeoutError):
        neutrinos.run_neutrino_benchmark(neutrinos.NeutrinoBenchmarkPlan.model_validate(payload))
    assert mock.call_count == 1


def test_each_request_budget_is_enforced_within_a_longer_suite_budget(plan, monkeypatch):
    now = 0

    def response(request):
        nonlocal now
        now += 1
        return synthetic_response(request)

    monkeypatch.setattr(neutrinos, "perf_counter", lambda: now)
    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    payload = plan.model_dump()
    payload["request"]["timeout_seconds"] = 0.5
    with pytest.raises(TimeoutError, match="request budget"):
        neutrinos.run_neutrino_benchmark(neutrinos.NeutrinoBenchmarkPlan.model_validate(payload))


def test_failure_stops_remaining_repetitions(plan, monkeypatch):
    mock = Mock(side_effect=runner.NeutrinoDependencyError("missing quantum extra"))
    monkeypatch.setattr(neutrinos, "run_neutrinos", mock)
    with pytest.raises(runner.NeutrinoDependencyError):
        neutrinos.run_neutrino_benchmark(plan)
    assert mock.call_count == 1


def test_failure_after_a_success_stops_remaining_repetitions(plan, monkeypatch):
    completed = 0

    def response(request):
        nonlocal completed
        completed += 1
        if completed == 2:
            raise TimeoutError("later curve expired")
        return synthetic_response(request)

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(TimeoutError):
        neutrinos.run_neutrino_benchmark(plan)
    assert completed == 2


def test_preparation_belongs_to_the_suite_deadline(plan, monkeypatch):
    clock = iter([0, 200])
    monkeypatch.setattr(neutrinos, "perf_counter", lambda: next(clock))
    mock = Mock(side_effect=AssertionError("must not start after expiry"))
    monkeypatch.setattr(neutrinos, "run_neutrinos", mock)
    with pytest.raises(TimeoutError):
        neutrinos.run_neutrino_benchmark(plan)
    mock.assert_not_called()


def test_summary_assembly_belongs_to_the_suite_deadline(plan, fake_runner, monkeypatch):
    now = 0
    summarize = neutrinos._summarize

    def slow_summary(shots, runs):
        nonlocal now
        now += 2
        return summarize(shots, runs)

    monkeypatch.setattr(neutrinos, "perf_counter", lambda: now)
    monkeypatch.setattr(neutrinos, "_summarize", slow_summary)
    payload = {**plan.model_dump(), "shot_counts": [8], "seeds": [0], "total_timeout_seconds": 1}
    with pytest.raises(TimeoutError):
        neutrinos.run_neutrino_benchmark(neutrinos.NeutrinoBenchmarkPlan.model_validate(payload))


def test_deadline_stops_native_worker_and_reaps_it(plan, monkeypatch, tmp_path):
    marker = tmp_path / "entered-native-work"
    monkeypatch.setattr(runner, "_worker", partial(_blocked_worker, marker=str(marker)))
    before = {process.pid for process in mp.active_children()}
    payload = {**plan.model_dump(), "total_timeout_seconds": 5}
    started = perf_counter()
    with pytest.raises(TimeoutError):
        neutrinos.run_neutrino_benchmark(neutrinos.NeutrinoBenchmarkPlan.model_validate(payload))
    assert marker.is_file()
    assert perf_counter() - started < 8
    assert {process.pid for process in mp.active_children()} <= before


@pytest.mark.parametrize("potential", [0, 0.9])
def test_real_runner_records_and_summaries_match_current_neutrino_schema(plan, potential):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    payload = plan.model_dump()
    payload["shot_counts"] = [64, 128]
    payload["seeds"] = [42, 43]
    payload["request"]["experiment"]["layers"][0]["potential"] = potential
    report = neutrinos.run_neutrino_benchmark(
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)
    )
    assert len(report.runs) == 4
    for run in report.runs:
        assert run.response.model == "effective_two_flavor"
        assert run.response.units == "normalized"
        assert sum(run.response.results[-1].counts.values()) == run.request.experiment.shots
    for group in report.summaries:
        errors = [
            run.response.results[-1].absolute_errors.sampling.other
            for run in report.runs
            if run.request.experiment.shots == group.shots
        ]
        assert group.points[-1].absolute_errors["sampling"]["other"].minimum == min(errors)
        assert group.points[-1].absolute_errors["sampling"]["other"].maximum == max(errors)
        assert group.points[-1].absolute_errors["ideal_vs_numerical"]["other"].maximum < 1e-12


@pytest.mark.parametrize(
    "patch",
    [
        {"axis": "potential", "max_potential": 1.2},
        {
            "experiment": {
                "layers": [{"distance": 0.5, "potential": 0.2}, {"distance": 0.5, "potential": 1.4}]
            }
        },
        {"experiment": {"layers": [{"distance": 0}]}},
    ],
)
def test_real_layered_potential_and_zero_extent_curves(plan, patch):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    payload = plan.model_dump()
    payload["shot_counts"] = [64]
    payload["seeds"] = [42]
    payload["request"].update(patch)
    report = neutrinos.run_neutrino_benchmark(
        neutrinos.NeutrinoBenchmarkPlan.model_validate(payload)
    )
    assert len(report.runs) == 1
    assert len(report.summaries[0].points) == len(report.runs[0].response.results)
    for point in report.summaries[0].points:
        assert point.absolute_errors["sampling"]["other"].count == 1
        assert point.absolute_errors["ideal_vs_numerical"]["other"].maximum < 1e-12


@pytest.fixture
def saved_report(plan, fake_runner, tmp_path):
    report = neutrinos.run_neutrino_benchmark(plan)
    source = tmp_path / "recorded.json"
    source.write_text(report.model_dump_json(indent=2))
    return source


def test_saved_review_recomputes_summaries_and_preserves_source(saved_report, monkeypatch):
    original = saved_report.read_bytes()
    blocked = Mock(side_effect=AssertionError("review must use saved data"))
    monkeypatch.setattr(neutrinos, "run_neutrinos", blocked)
    markdown = review.review_neutrino_report(saved_report)
    assert saved_report.read_bytes() == original
    assert sha256(original).hexdigest() in markdown
    assert "Previously measured local Qiskit Aer" in markdown
    assert "6 recorded curves, 12 raw scientific records" in markdown
    assert "| 8 | 1 | other | 3 | 0 | 0.25 | 0.25 | 0.25 | 0 |" in markdown
    assert "Suite elapsed time" in markdown
    blocked.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        (("runs",), []),
        (("summaries",), []),
        (("runs", 0, "request", "experiment", "seed"), 10),
        (("runs", 0, "request", "experiment", "layers", 0, "potential"), 0.5),
        (("runs", 0, "response", "results", 1, "counts", "0"), 1),
        (("runs", 0, "response", "results", 1, "configuration", "layers", 0, "potential"), 0.5),
        (("runs", 0, "response", "results", 1, "versions", "qiskit"), "changed"),
        (("summaries", 0, "repetitions"), 12),
        (("summaries", 0, "request_wall_ms", "median"), 999),
        (("summaries", 0, "shots"), 12),
        (("summaries", 0, "points"), []),
        (("summaries", 0, "points", 0, "coordinate"), 0.5),
        (("summaries", 0, "points", 0, "absolute_errors", "sampling", "other", "count"), 99),
        (("summaries", 0, "points", 0, "absolute_errors", "sampling", "other", "median"), 0.5),
        (
            ("summaries", 0, "points", 0, "absolute_errors", "sampling", "tau"),
            {"count": 3, "minimum": 0, "median": 0, "maximum": 0, "sample_stdev": 0},
        ),
        (("summaries", 0, "points", 0, "absolute_errors", "analytical_vs_numerical"), None),
        (("summaries", 0, "points", 0, "timing_ms"), {}),
        (("environment", "python"), ""),
        (("created_at_utc",), "2026-11-10T12:00:00"),
        (("created_at_utc",), "2026-11-10T12:00:00+01:00"),
        (("elapsed_ms",), 0),
        (("elapsed_ms",), 120000),
    ],
)
def test_saved_inconsistencies_fail_review(saved_report, field, value):
    payload = json.loads(saved_report.read_text())
    parent = payload
    for key in field[:-1]:
        parent = parent[key]
    parent[field[-1]] = value
    saved_report.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        review.review_neutrino_report(saved_report)


def test_duplicate_and_reordered_runs_fail_review(saved_report):
    payload = json.loads(saved_report.read_text())
    duplicate = {**payload, "runs": [*payload["runs"], payload["runs"][0]]}
    saved_report.write_text(json.dumps(duplicate))
    with pytest.raises(ValueError, match="duplicating"):
        review.review_neutrino_report(saved_report)
    payload["runs"][0], payload["runs"][1] = payload["runs"][1], payload["runs"][0]
    saved_report.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="order or settings"):
        review.review_neutrino_report(saved_report)


def test_saved_request_and_summary_budgets_are_checked(saved_report):
    report = neutrinos.NeutrinoBenchmarkReport.model_validate_json(saved_report.read_text())
    report.elapsed_ms = 40000
    report.runs[0].request_wall_ms = 30000
    with pytest.raises(ValueError, match="request budget"):
        review.validate_neutrino_report(report)
    report.runs[0].request_wall_ms = 1
    report.runs[0].request.timeout_seconds = 60
    with pytest.raises(ValueError, match="configured budget"):
        review.validate_neutrino_report(report)


def test_saved_review_preserves_unknown_values(plan, monkeypatch, tmp_path):
    def response(request):
        result = synthetic_response(request)
        for record in result.results:
            record.quantum_timing.sampling_ms = None
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    plan.seeds = [42]
    report = neutrinos.run_neutrino_benchmark(plan)
    source = tmp_path / "single.json"
    source.write_text(report.model_dump_json())
    markdown = review.review_neutrino_report(source)
    assert "unavailable" in markdown
    assert (
        "| 8 | 0 | sampling\\_ms | 0 | unavailable | unavailable | unavailable | unavailable |"
        in markdown
    )


def test_saved_summary_float_tolerance_supports_round_trip_recomputation(saved_report):
    report = neutrinos.NeutrinoBenchmarkReport.model_validate_json(saved_report.read_text())
    report.summaries[0].points[1].absolute_errors["sampling"]["other"].median += 1e-16
    validated = review.validate_neutrino_report(report)
    assert validated.summaries[0].points[1].absolute_errors["sampling"]["other"].median == 0.25
    assert report.summaries[0].points[1].absolute_errors["sampling"]["other"].median > 0.25


def test_review_escapes_metadata_as_literal_markdown(saved_report):
    payload = json.loads(saved_report.read_text())
    payload["environment"]["machine"] = "arm64|![image](https://example.invalid)\n<script>"
    saved_report.write_text(json.dumps(payload))
    markdown = review.review_neutrino_report(saved_report)
    assert "arm64\\|\\!\\[image\\]\\(https://example.invalid\\) &lt;script&gt;" in markdown
    assert "\n<script>" not in markdown


def test_oversized_saved_report_is_rejected(saved_report, monkeypatch):
    monkeypatch.setattr(review, "MAX_REPORT_BYTES", 10)
    with pytest.raises(ValueError, match="review limit"):
        review.review_neutrino_report(saved_report)


def test_saved_review_cli_preserves_existing_outputs(saved_report, tmp_path, monkeypatch):
    destination = tmp_path / "review.md"
    destination.write_text("existing review")
    review_function = Mock(side_effect=AssertionError("must preserve the output"))
    monkeypatch.setattr(review, "review_neutrino_report", review_function)
    assert review.main([str(saved_report), "--output", str(destination)]) == 1
    assert destination.read_text() == "existing review"
    review_function.assert_not_called()


def test_invalid_saved_report_produces_no_review(saved_report, tmp_path):
    saved_report.write_text('{"status": "completed"}')
    destination = tmp_path / "review.md"
    assert review.main([str(saved_report), "--output", str(destination)]) == 1
    assert not destination.exists()
    assert not list(tmp_path.glob(".neutrino-benchmark-*"))


def test_normal_review_cli_publishes_saved_data_without_quantum_imports(saved_report, tmp_path):
    destination = tmp_path / "review.md"
    backend = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.benchmarks.review",
            str(saved_report),
            "--output",
            str(destination),
        ],
        cwd=backend,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Checked saved neutrino evidence" in result.stdout
    assert sha256(saved_report.read_bytes()).hexdigest() in destination.read_text()
    code = (
        "import sys; from app.benchmarks.review import main; "
        "assert not any(name in sys.modules for name in ('numpy', 'scipy', 'qiskit', 'qiskit_aer'))"
    )
    imported = subprocess.run(
        [sys.executable, "-c", code], cwd=backend, capture_output=True, text=True, timeout=10
    )
    assert imported.returncode == 0, imported.stderr


def test_intermediate_distance_record_must_follow_the_input_potential(plan, monkeypatch):
    plan.request.samples = 3

    def response(request):
        result = synthetic_response(request)
        result.results[1].configuration.layers[0].potential = 0.5
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(ValueError, match="ordered input profile"):
        neutrinos.run_neutrino_benchmark(plan)


def test_intermediate_layers_must_traverse_complete_earlier_layers(plan, monkeypatch):
    plan.request.samples = 3
    plan.request.experiment.layers = [
        Layer(distance=0.5, potential=0.2),
        Layer(distance=0.5, potential=1.4),
    ]

    def response(request):
        result = synthetic_response(request)
        result.results[1].configuration.layers = [
            Layer(distance=0.25, potential=0.2),
            Layer(distance=0.25, potential=1.4),
        ]
        return result

    monkeypatch.setattr(neutrinos, "run_neutrinos", response)
    with pytest.raises(ValueError, match="ordered input profile"):
        neutrinos.run_neutrino_benchmark(plan)


@pytest.fixture
def demo_requests(plan, tmp_path):
    directory = tmp_path / "requests"
    directory.mkdir()
    for case in demo.CASES:
        (directory / f"{case}.json").write_text(plan.request.model_dump_json())
    return directory


@pytest.fixture
def demo_source(monkeypatch):
    source = {
        "source_revision": "a" * 40,
        "working_tree_dirty": True,
        "source_sha256": {"backend/app/benchmarks/demo.py": "b" * 64},
    }
    probe = Mock(side_effect=lambda _: deepcopy(source))
    monkeypatch.setattr(demo, "_source_provenance", probe)
    return source, probe


def test_demo_archive_preserves_requests_evidence_review_and_checksums(
    demo_requests, demo_source, fake_runner, tmp_path
):
    destination = tmp_path / "evidence.zip"
    originals = {path.name: path.read_bytes() for path in demo_requests.iterdir()}
    demo.record_neutrino_demo(demo_requests, destination)
    assert fake_runner.call_count == 27
    assert not list(tmp_path.glob(".q-atlas-neutrino-demo-*"))
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist())) == 12
        provenance = json.loads(archive.read("provenance.json"))
        for key, value in demo_source[0].items():
            assert provenance[key] == value
        assert provenance["source"] == "previously_measured_neutrino_demo"
        manifest = archive.read("SHA256SUMS").decode().splitlines()
        assert len(manifest) == 11
        assert {line.split("  ")[1] for line in manifest} == set(archive.namelist()) - {
            "SHA256SUMS"
        }
        for line in manifest:
            digest, name = line.split("  ")
            assert sha256(archive.read(name)).hexdigest() == digest
        for case in demo.CASES:
            assert archive.read(f"{case}.json") == originals[f"{case}.json"]
            raw = archive.read(f"{case}-evidence.json")
            report = review.validate_neutrino_report(
                neutrinos.NeutrinoBenchmarkReport.model_validate_json(raw)
            )
            assert report.plan.shot_counts == [256, 1024, 4096]
            assert report.plan.seeds == [42, 142, 242]
            assert report.plan.request.model_dump_json().encode() == originals[f"{case}.json"]
            assert sha256(raw).hexdigest() in archive.read(f"{case}-review.md").decode()
        assert "Previously measured local Qiskit Aer" in archive.read("README.md").decode()
    assert {path.name: path.read_bytes() for path in demo_requests.iterdir()} == originals


@pytest.mark.parametrize("kind", ["file", "symlink", "dangling_symlink"])
def test_demo_existing_destinations_are_preserved_before_measurement(
    demo_requests, fake_runner, tmp_path, kind
):
    destination = tmp_path / "evidence.zip"
    original = tmp_path / "original.zip"
    if kind == "file":
        destination.write_bytes(b"earlier recording")
    else:
        if kind == "symlink":
            original.write_bytes(b"earlier recording")
        try:
            destination.symlink_to(original)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"symlink creation unavailable: {error}")
    assert demo.main(["--requests", str(demo_requests), "--output", str(destination)]) == 1
    assert os.path.lexists(destination)
    if kind != "dangling_symlink":
        assert destination.read_bytes() == b"earlier recording"
    fake_runner.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "invalid", "over_budget"])
def test_demo_validates_all_case_inputs_before_starting(demo_requests, fake_runner, tmp_path, kind):
    last = demo_requests / f"{demo.CASES[-1]}.json"
    if kind == "missing":
        last.unlink()
    elif kind == "invalid":
        last.write_text("{invalid json")
    else:
        payload = json.loads(last.read_text())
        payload["samples"] = 41
        payload["experiment"]["shots"] = 100000
        last.write_text(json.dumps(payload))
    destination = tmp_path / "evidence.zip"
    assert demo.main(["--requests", str(demo_requests), "--output", str(destination)]) == 1
    assert not destination.exists()
    fake_runner.assert_not_called()


@pytest.mark.parametrize(
    "error", [TimeoutError("expired"), RuntimeError("failed"), KeyboardInterrupt()]
)
def test_demo_failure_in_final_case_cleans_staging_and_publishes_nothing(
    demo_requests, demo_source, fake_runner, tmp_path, error
):
    def fail_in_last_case(request):
        if fake_runner.call_count > 18:
            raise error
        return synthetic_response(request)

    fake_runner.side_effect = fail_in_last_case
    with pytest.raises(type(error)):
        demo.record_neutrino_demo(demo_requests, tmp_path / "evidence.zip")
    assert list(tmp_path.iterdir()) == [demo_requests]


@pytest.mark.parametrize("kind", ["plan", "summary"])
def test_demo_checks_saved_measurements_before_publication(
    demo_requests, demo_source, fake_runner, monkeypatch, tmp_path, kind
):
    def corrupt(plan):
        report = neutrinos.run_neutrino_benchmark(plan)
        if kind == "plan":
            report.plan.request.experiment.parameters.energy += 1
        else:
            report.summaries[0].points[-1].absolute_errors["sampling"]["other"].median = 999
        return report

    monkeypatch.setattr(demo, "run_neutrino_benchmark", corrupt)
    with pytest.raises(ValueError):
        demo.record_neutrino_demo(demo_requests, tmp_path / "evidence.zip")
    assert list(tmp_path.iterdir()) == [demo_requests]


@pytest.mark.parametrize("key", ["source_revision", "source_sha256"])
def test_demo_detects_source_changes_during_recording(
    demo_requests, demo_source, fake_runner, tmp_path, key
):
    source, probe = demo_source
    after = deepcopy(source)
    after[key] = "changed" if key == "source_revision" else {}
    probe.side_effect = [source, after]
    with pytest.raises(RuntimeError, match="changed during"):
        demo.record_neutrino_demo(demo_requests, tmp_path / "evidence.zip")
    assert list(tmp_path.iterdir()) == [demo_requests]


def test_demo_concurrent_publication_preserves_the_completed_recording(
    demo_requests, demo_source, fake_runner, monkeypatch, tmp_path
):
    original_link = os.link
    destination = tmp_path / "evidence.zip"

    def competing_link(source, output):
        if source.name == "evidence.zip":
            output.write_bytes(b"concurrent complete recording")
        original_link(source, output)

    monkeypatch.setattr(demo.os, "link", competing_link)
    with pytest.raises(FileExistsError):
        demo.record_neutrino_demo(demo_requests, destination)
    assert destination.read_bytes() == b"concurrent complete recording"
    assert not list(tmp_path.glob(".q-atlas-neutrino-demo-*"))
