"""Offline preparation and mutable shared-result boundary regressions."""

import hashlib
import io
import json
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from app.compiler import pipeline
from app.compiler.preflight import build_preflight_bundle
from app.schemas.contracts import QAOAConfig, SolverResult
from scripts.prepare_compiler_day import main

SOURCE = "@qatlas.objective\ndef score(red, blue): return 7 - red + 2*red*blue\n"


def test_bundle_preserves_text_hashes_and_settings_without_execution(monkeypatch, tmp_path):
    classical, quantum = Mock(side_effect=AssertionError), Mock(side_effect=AssertionError)
    monkeypatch.setattr(pipeline.solvers, "run_classical", classical)
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", quantum)
    sentinel = tmp_path / "never-created"
    source = f"open({str(sentinel)!r}, 'w').write('unsafe')\n" + SOURCE
    config = QAOAConfig(p=2, shots=64, seed=7)
    bundle = build_preflight_bundle(source, config)
    assert bundle == build_preflight_bundle(source, config)
    with ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {
            "input.py",
            "generated.py",
            "plan.json",
            "manifest.json",
            "README.txt",
        }
        assert archive.read("input.py").decode() == source
        manifest = json.loads(archive.read("manifest.json"))
        for name, record in manifest["files"].items():
            assert record["sha256"] == hashlib.sha256(archive.read(name)).hexdigest()
            assert record["bytes"] == len(archive.read(name))
        plan = json.loads(archive.read("plan.json"))
        assert plan["config"]["p"] == 2 and plan["config"]["shots"] == 64
        assert plan["quantum_execution_enabled"] is plan["script_execution_enabled"] is False
        assert plan["communication_timing"] == {
            "submission_ms": None,
            "result_retrieval_ms": None,
            "queue_ms": None,
            "remote_processing_ms": None,
            "round_trip_ms": None,
        }
        assert plan["generated_source_sha256"] == manifest["files"]["generated.py"]["sha256"]
        assert plan["source_sha256"] == manifest["files"]["input.py"]["sha256"]
    assert not sentinel.exists()
    classical.assert_not_called()
    quantum.assert_not_called()


@pytest.mark.parametrize("data", [b"", b"x" * 80_001, b"\xff", b"print('unsupported')"])
def test_cli_bad_inputs_leave_no_bundle(tmp_path, data):
    source, target = tmp_path / "source.py", tmp_path / "bundle.zip"
    source.write_bytes(data)
    assert main([str(source), "--output", str(target)]) == 1
    assert not target.exists()


def test_cli_never_overwrites_a_frozen_bundle(tmp_path):
    source, target = tmp_path / "source.py", tmp_path / "bundle.zip"
    source.write_text(SOURCE)
    assert main([str(source), "--output", str(target)]) == 0
    original = target.read_bytes()
    source.write_text(SOURCE.replace("7", "8"))
    assert main([str(source), "--output", str(target)]) == 1
    assert target.read_bytes() == original


@pytest.mark.parametrize("field", ["elapsed_ms", "timing"])
def test_mutated_classical_result_is_rejected_before_quantum(monkeypatch, field):
    result = SolverResult(
        algorithm="brute_force",
        elapsed_ms=1,
        objective=6,
        best_bitstring="10",
        timing=dict(
            includes_queue=False,
            includes_transpilation=False,
            includes_optimizer=False,
            includes_sampling=False,
        ),
    )
    if field == "elapsed_ms":
        result.elapsed_ms = -1
    else:
        result.timing.sampling_ms = float("nan")
    monkeypatch.setattr(pipeline.solvers, "run_classical", Mock(return_value=result))
    quantum = Mock(side_effect=AssertionError)
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", quantum)
    with pytest.raises(ValueError):
        pipeline.benchmark_source(SOURCE, QAOAConfig())
    quantum.assert_not_called()
