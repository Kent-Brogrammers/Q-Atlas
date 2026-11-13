"""CLI validation, complete artifact publication, and the normal local entry point."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from app.benchmarks import __main__ as cli
from app.benchmarks import demo
from app.benchmarks.neutrinos import NeutrinoBenchmarkReport
from app.experiments.neutrinos.model import Experiment, Layer
from app.schemas.neutrinos import NeutrinoRequest


@pytest.fixture
def request_file(tmp_path):
    path = tmp_path / "request.json"
    path.write_text(
        NeutrinoRequest(
            experiment=Experiment(layers=[Layer(distance=1)]), samples=2
        ).model_dump_json()
    )
    return path


def test_cli_supplies_the_validated_plan_and_publishes_output(request_file, tmp_path, monkeypatch):
    destination = tmp_path / "evidence.json"
    report = Mock(runs=[object(), object()])
    report.model_dump_json.return_value = '{"fixture": true}'
    benchmark = Mock(return_value=report)
    monkeypatch.setattr(cli, "run_neutrino_benchmark", benchmark)
    assert (
        cli.main(
            [
                "--request",
                str(request_file),
                "--shots",
                "16",
                "32",
                "--seeds",
                "4",
                "5",
                "--total-timeout",
                "40",
                "--output",
                str(destination),
            ]
        )
        == 0
    )
    plan = benchmark.call_args.args[0]
    assert plan.shot_counts == [16, 32]
    assert plan.seeds == [4, 5]
    assert plan.total_timeout_seconds == 40
    assert json.loads(destination.read_text()) == {"fixture": True}
    assert not list(tmp_path.glob(".neutrino-benchmark-*"))


@pytest.mark.parametrize("kind", ["file", "symlink", "dangling_symlink"])
def test_existing_output_is_preserved_before_computation(request_file, tmp_path, monkeypatch, kind):
    destination = tmp_path / "evidence.json"
    original = tmp_path / "original.json"
    if kind == "file":
        destination.write_text("previous measured evidence")
    else:
        if kind == "symlink":
            original.write_text("previous measured evidence")
        try:
            destination.symlink_to(original)
        except (NotImplementedError, OSError) as error:
            pytest.skip(f"symlink creation unavailable: {error}")
    benchmark = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setattr(cli, "run_neutrino_benchmark", benchmark)
    assert cli.main(["--request", str(request_file), "--output", str(destination)]) == 1
    assert os.path.lexists(destination)
    if kind != "dangling_symlink":
        assert destination.read_text() == "previous measured evidence"
    benchmark.assert_not_called()


def test_concurrent_publication_preserves_the_winning_output(tmp_path, monkeypatch):
    destination = tmp_path / "evidence.json"
    original_link = os.link

    def competing_link(temporary, output):
        output.write_text("concurrent evidence")
        original_link(temporary, output)

    monkeypatch.setattr(cli.os, "link", competing_link)
    report = Mock()
    report.model_dump_json.return_value = '{"fixture": true}'
    with pytest.raises(FileExistsError):
        cli.write_report(report, destination)
    assert destination.read_text() == "concurrent evidence"
    assert not list(tmp_path.glob(".neutrino-benchmark-*"))


def test_serialization_failure_leaves_no_partial_output(tmp_path):
    destination = tmp_path / "evidence.json"
    report = Mock()
    report.model_dump_json.side_effect = ValueError("serialization failed")
    with pytest.raises(ValueError):
        cli.write_report(report, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".neutrino-benchmark-*"))


@pytest.mark.parametrize("failure", [TimeoutError("budget expired"), RuntimeError("runner failed")])
def test_failed_suite_produces_no_completed_artifact(request_file, tmp_path, monkeypatch, failure):
    destination = tmp_path / "evidence.json"
    monkeypatch.setattr(cli, "run_neutrino_benchmark", Mock(side_effect=failure))
    assert cli.main(["--request", str(request_file), "--output", str(destination)]) == 1
    assert not destination.exists()


def test_invalid_plan_stops_before_computation(request_file, tmp_path, monkeypatch):
    benchmark = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setattr(cli, "run_neutrino_benchmark", benchmark)
    assert (
        cli.main(
            [
                "--request",
                str(request_file),
                "--shots",
                "0",
                "--output",
                str(tmp_path / "evidence.json"),
            ]
        )
        == 1
    )
    benchmark.assert_not_called()


def test_core_benchmark_import_keeps_simulation_dependencies_lazy():
    code = (
        "import sys; from app.benchmarks.__main__ import main; "
        "assert not any(name in sys.modules for name in "
        "('numpy', 'scipy', 'qiskit', 'qiskit_aer'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr


def test_real_cli_produces_a_valid_complete_evidence_file(request_file, tmp_path):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    destination = tmp_path / "evidence.json"
    backend = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.benchmarks",
            "--request",
            str(request_file),
            "--shots",
            "64",
            "128",
            "--seeds",
            "42",
            "43",
            "--output",
            str(destination),
        ],
        cwd=backend,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = NeutrinoBenchmarkReport.model_validate_json(destination.read_text())
    assert len(report.runs) == 4
    assert [group.shots for group in report.summaries] == [64, 128]
    assert all(group.repetitions == 2 for group in report.summaries)
    assert "Saved 4 measured local Aer curves" in result.stdout


def test_demo_source_fingerprint_preserves_unknown_git_and_uses_only_allowlisted_paths(
    tmp_path, monkeypatch
):
    paths = [
        "backend/app/benchmarks/demo.py",
        "backend/app/experiments/neutrinos/physics.py",
        "backend/app/schemas/contracts.py",
        "backend/app/schemas/neutrinos.py",
        "backend/pyproject.toml",
        "backend/uv.lock",
    ]
    for name in [*paths, "backend/app/experiments/search/runner.py"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("source fixture")
    monkeypatch.setattr(demo.subprocess, "run", Mock(side_effect=FileNotFoundError("git")))
    provenance = demo._source_provenance(tmp_path)
    assert provenance["source_revision"] is None
    assert provenance["working_tree_dirty"] is None
    assert provenance["source_sha256"] == {
        name: sha256(b"source fixture").hexdigest() for name in paths
    }


@pytest.mark.parametrize("status,expected", [("", False), (" M source.py", True)])
def test_demo_records_actual_revision_and_dirty_state(monkeypatch, status, expected):
    probe = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout=status),
            subprocess.CompletedProcess([], 0, stdout="a" * 40 + "\n"),
        ]
    )
    monkeypatch.setattr(demo.subprocess, "run", probe)
    provenance = demo._source_provenance(demo.ROOT)
    assert provenance["source_revision"] == "a" * 40
    assert provenance["working_tree_dirty"] is expected
    assert probe.call_args.kwargs["cwd"] == demo.ROOT
    assert probe.call_args.kwargs["timeout"] == 5


def test_demo_import_and_help_keep_optional_quantum_packages_lazy():
    code = (
        "import sys; from app.benchmarks import demo; "
        "assert not any(name in sys.modules for name in "
        "('numpy', 'scipy', 'qiskit', 'qiskit_aer')); demo.main(['--help'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "--requests" in result.stdout


def test_real_demo_cli_records_and_packages_all_three_examples(tmp_path):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    destination = tmp_path / "evidence.zip"
    requests = demo.ROOT / "examples/neutrinos"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.benchmarks.demo",
            "--requests",
            str(requests),
            "--output",
            str(destination),
        ],
        cwd=demo.ROOT / "backend",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Saved previously measured local Aer demo bundle" in result.stdout
    points = 0
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        for case in demo.CASES:
            raw = archive.read(f"{case}-evidence.json")
            report = NeutrinoBenchmarkReport.model_validate_json(raw)
            assert len(report.runs) == 9
            points += sum(len(run.response.results) for run in report.runs)
            assert sha256(raw).hexdigest() in archive.read(f"{case}-review.md").decode()
            assert archive.read(f"{case}.json") == (requests / f"{case}.json").read_bytes()
        provenance = json.loads(archive.read("provenance.json"))
        assert (
            provenance["source_sha256"]["backend/app/benchmarks/demo.py"]
            == sha256((demo.ROOT / "backend/app/benchmarks/demo.py").read_bytes()).hexdigest()
        )
        assert provenance["recording_method"] == "run_neutrino_benchmark"
    assert points == 171
    assert not list(tmp_path.glob(".q-atlas-neutrino-demo-*"))
