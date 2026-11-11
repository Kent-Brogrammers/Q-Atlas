"""Search sweep grid, evidence, deadline and publication regressions."""

import json
from pathlib import Path

import pytest

from app.experiments.search import sweep
from app.schemas.contracts import SearchResult


@pytest.fixture
def measured_result():
    path = Path(__file__).resolve().parents[3] / "frontend/src/lib/search/previously-measured.json"
    return SearchResult.model_validate(json.loads(path.read_text())["curve"][0])


@pytest.fixture
def fake_runner(monkeypatch, measured_result):
    requests = []

    def run(request):
        requests.append(request)
        result = measured_result.model_copy(deep=True)
        result.metadata.parameters = request.model_copy(deep=True)
        result.metadata.seed = request.config.seed
        result.metrics.shots = request.config.shots
        result.metrics.successful_shots = 0
        result.metrics.success_probability = 0
        result.metrics.quantum_oracle_queries = request.iterations
        result.metrics.quantum_total_oracle_queries = request.iterations * request.config.shots
        return result

    monkeypatch.setattr(sweep, "run_search", run)
    monkeypatch.setattr(sweep, "source_provenance", lambda: {"source_revision": "test"})
    return requests


@pytest.mark.parametrize(
    "patch",
    [
        {"num_qubits": 7},
        {"marked_states": ["01"]},
        {"marked_states": ["001", "001"]},
        {"iterations": [0, 0]},
        {"iterations": [33]},
        {"shot_counts": [0]},
        {"shot_counts": [10001]},
        {"seeds": [-1]},
        {"seeds": [2**32]},
        {"seeds": [42, 42]},
        {"total_timeout_seconds": float("nan")},
        {"iterations": list(range(33)), "seeds": list(range(16))},
    ],
)
def test_reject_invalid_plan(patch):
    with pytest.raises(ValueError):
        sweep.SearchSweepPlan(**patch)


def test_cartesian_grid_and_single_trial_summary(fake_runner):
    plan = sweep.SearchSweepPlan(iterations=[0, 2], shot_counts=[64, 128], seeds=[7])
    report = sweep.run_sweep(plan)
    assert [(r.iterations, r.config.shots, r.config.seed) for r in fake_runner] == [
        (0, 64, 7),
        (0, 128, 7),
        (2, 64, 7),
        (2, 128, 7),
    ]
    assert len(report["runs"]) == len(report["summaries"]) == 4
    assert all(item["sample_standard_deviation"] is None for item in report["summaries"])
    assert report["plan"] == plan.model_dump(mode="json")


def test_summary_computes_sample_statistics(measured_result):
    other = measured_result.model_copy(deep=True)
    measured_result.metrics.success_probability = 0.25
    other.metrics.success_probability = 0.75
    summary = sweep.summarize([measured_result, other])[0]
    assert summary["mean_success_probability"] == 0.5
    assert summary["minimum_success_probability"] == 0.25
    assert summary["maximum_success_probability"] == 0.75
    assert summary["sample_standard_deviation"] == pytest.approx(0.35355339059)


def test_total_deadline_caps_worker_budget(monkeypatch, fake_runner):
    ticks = iter([0, 0.5, 1.1])
    monkeypatch.setattr(sweep, "perf_counter", lambda: next(ticks))
    with pytest.raises(TimeoutError):
        sweep.run_sweep(
            sweep.SearchSweepPlan(
                iterations=[0], shot_counts=[64], seeds=[1], total_timeout_seconds=1
            )
        )
    assert len(fake_runner) == 1
    assert fake_runner[0].config.timeout_seconds == 0.5


def test_mismatched_evidence_rejected(monkeypatch, fake_runner):
    original = sweep.run_search

    def wrong(request):
        result = original(request)
        result.metadata.seed += 1
        return result

    monkeypatch.setattr(sweep, "run_search", wrong)
    with pytest.raises(ValueError, match="mismatched"):
        sweep.run_sweep(sweep.SearchSweepPlan(iterations=[0], shot_counts=[64], seeds=[1]))


def test_failed_run_leaves_no_report(monkeypatch, tmp_path, fake_runner):
    def fail(_):
        raise TimeoutError("test timeout")

    monkeypatch.setattr(sweep, "run_search", fail)
    destination = tmp_path / "results.json"
    assert sweep.main(["--output", str(destination)]) == 1
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_write_preserves_existing_file_and_cleans_temporary(tmp_path):
    destination = tmp_path / "results.json"
    sweep.write_report({"runs": []}, destination)
    with pytest.raises(FileExistsError):
        sweep.write_report({"replaced": True}, destination)
    assert json.loads(destination.read_text()) == {"runs": []}
    assert list(tmp_path.iterdir()) == [destination]


def test_existing_output_prevents_any_simulation(tmp_path, fake_runner):
    destination = tmp_path / "existing.json"
    destination.write_text("keep")
    assert sweep.main(["--output", str(destination)]) == 1
    assert fake_runner == []
    assert destination.read_text() == "keep"


def test_cli_writes_custom_multiple_target_plan(tmp_path, fake_runner):
    destination = tmp_path / "results.json"
    assert (
        sweep.main(
            [
                "--marked-states",
                "001",
                "110",
                "--iterations",
                "0",
                "2",
                "--shots",
                "64",
                "--seeds",
                "7",
                "8",
                "--output",
                str(destination),
            ]
        )
        == 0
    )
    report = json.loads(destination.read_text())
    assert len(report["runs"]) == 4
    assert report["plan"]["marked_states"] == ["001", "110"]


def test_source_provenance_records_sweep_code():
    provenance = sweep.source_provenance()
    assert len(provenance["source_revision"]) == 40
    assert type(provenance["working_tree_dirty"]) is bool
    assert "backend/app/experiments/search/sweep.py" in provenance["source_sha256"]
    assert all(len(value) == 64 for value in provenance["source_sha256"].values())


def test_versions_cannot_change_mid_sweep(monkeypatch, fake_runner):
    original = sweep.run_search

    def changed(request):
        result = original(request)
        if len(fake_runner) > 1:
            result.metadata.versions["qiskit"] = "different"
        return result

    monkeypatch.setattr(sweep, "run_search", changed)
    with pytest.raises(ValueError, match="versions changed"):
        sweep.run_sweep(sweep.SearchSweepPlan(iterations=[0], shot_counts=[64], seeds=[1, 2]))


def test_publication_failure_removes_temporary_file(monkeypatch, tmp_path):
    def fail(*_):
        raise OSError("publication failed")

    monkeypatch.setattr(sweep.os, "link", fail)
    with pytest.raises(OSError, match="publication failed"):
        sweep.write_report({"runs": []}, tmp_path / "results.json")
    assert list(tmp_path.iterdir()) == []
