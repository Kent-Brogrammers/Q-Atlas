"""Synthetic IBM responses only. Never authenticate, train, transpile or submit jobs."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.api import compiler_hardware
from app.compiler import hardware
from app.compiler.pipeline import CompilationError
from app.schemas.compiler_hardware import CompilerHardwareRequest
from app.schemas.contracts import QUBO, QAOAConfig, SolverResult, TimingBreakdown

SOURCE = "@qatlas.objective\ndef score(red, blue): return 5 - 2*red + blue"


@pytest.fixture
def mocked(monkeypatch, tmp_path):
    monkeypatch.setenv("QATLAS_QUANTUM_KEY", "fake-private-token")
    monkeypatch.delenv("QUANTUM-KEY", raising=False)
    monkeypatch.setenv("QATLAS_IBM_INSTANCE", "fake-instance")
    monkeypatch.setenv("QATLAS_COMPILER_QPU_BUDGET_SECONDS", "20")
    monkeypatch.setattr(hardware, "STORE", tmp_path)
    job = SimpleNamespace(
        job_id=lambda: "fake-job",
        status=lambda: "DONE",
        cancel=Mock(),
        result=Mock(
            return_value=[
                SimpleNamespace(
                    data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"01": 128}))
                )
            ]
        ),
        metrics=lambda: {"usage": {"quantum_seconds": 1.5}},
    )
    service = SimpleNamespace(
        backends=Mock(return_value=[SimpleNamespace(name="ibm_test")]),
        backend=Mock(return_value=object()),
        job=Mock(return_value=job),
    )
    monkeypatch.setattr(hardware, "_service", Mock(return_value=service))
    train = Mock(
        return_value=(
            SimpleNamespace(depth=lambda: 9),
            SimpleNamespace(angles=(0.2, 0.3), elapsed_ms=25),
        )
    )
    submit = Mock(return_value=job)
    classical = SolverResult(
        algorithm="brute_force",
        objective=3,
        best_bitstring="10",
        elapsed_ms=1,
        timing=TimingBreakdown(
            includes_queue=False,
            includes_transpilation=False,
            includes_optimizer=False,
            includes_sampling=False,
        ),
    )
    monkeypatch.setattr(hardware, "run_classical", Mock(return_value=classical))
    monkeypatch.setattr(hardware, "_prepare_circuit", train)
    monkeypatch.setattr(hardware, "_submit", submit)
    request = CompilerHardwareRequest(
        source=SOURCE, backend_name="ibm_test", request_id=uuid4(), confirmed=True
    )
    return request, submit, train, service, job


def test_physical_result_and_durable_duplicate_prevention(mocked):
    request, submit, train, service, job = mocked
    first = hardware.submit(request)
    again = hardware.submit(request)
    assert first.job_id == again.job_id == "fake-job"
    submit.assert_called_once()
    train.assert_called_once()
    completed = hardware.refresh(request.request_id)
    assert completed.measurement.simulated is False
    assert completed.measurement.best_bitstring == "10"
    assert completed.measurement.objective == 3
    assert completed.measurement.optimality_gap == 0
    assert completed.measurement.quantum_seconds == 1.5
    assert completed.measurement.shots == 128
    assert completed.angles == [0.2, 0.3] and completed.local_training_ms == 25
    assert hardware.refresh(request.request_id) == completed
    job.result.assert_called_once()
    assert hardware.devices().reserved_seconds == 2


def test_lost_acknowledgement_retains_reservation_and_never_retries(mocked):
    request, submit, _, _, _ = mocked
    submit.side_effect = RuntimeError("fake-private-token")
    result = hardware.submit(request)
    assert result.status == "SUBMISSION_UNKNOWN"
    assert "fake-private-token" not in result.model_dump_json()
    assert hardware.submit(request).status == "SUBMISSION_UNKNOWN"
    submit.assert_called_once()
    assert hardware.devices().reserved_seconds == 10


def test_sampler_uses_one_job_and_explicit_quota_options(monkeypatch):
    import sys

    sampler = Mock()
    factory = Mock(return_value=sampler)
    monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", SimpleNamespace(SamplerV2=factory))
    request = CompilerHardwareRequest(
        source=SOURCE, backend_name="ibm_test", request_id=uuid4(), confirmed=True
    )
    backend, circuit = object(), object()
    hardware._submit(backend, circuit, request)
    options = factory.call_args.kwargs["options"]
    assert factory.call_args.kwargs["mode"] is backend
    assert options["max_execution_time"] == 10
    assert options["twirling"] == {"enable_gates": False, "enable_measure": False}
    assert options["dynamical_decoupling"] == {"enable": False}
    assert options["environment"]["job_tags"] == [f"qatlas-{request.request_id}"]
    sampler.run.assert_called_once_with([circuit], shots=128)


def test_shared_circuit_binding_and_measurement_without_execution(monkeypatch):
    qiskit = pytest.importorskip("qiskit")
    transpile = Mock(side_effect=lambda circuit, **kwargs: circuit)
    monkeypatch.setattr(qiskit, "transpile", transpile)
    optimized = SimpleNamespace(angles=(0.2, 0.3), elapsed_ms=10)
    monkeypatch.setattr(hardware, "optimize_qaoa_angles", Mock(return_value=optimized))
    qubo = QUBO(num_variables=2, linear=[-2, 1], quadratic=[], constant=5)
    circuit, result = hardware._prepare_circuit(qubo, QAOAConfig(p=1), object())
    assert result is optimized and circuit.num_parameters == 0
    assert circuit.cregs[0].name == "meas"
    assert [
        circuit.find_bit(g.clbits[0]).index for g in circuit.data if g.operation.name == "measure"
    ] == [0, 1]


def test_width_limit_rejects_before_provider_contact(mocked):
    request, submit, train, service, _ = mocked
    source = "@qatlas.objective\ndef wide(a,b,c,d,e,f,g): return a+b+c+d+e+f+g"
    with pytest.raises(CompilationError):
        hardware.submit(request.model_copy(update={"source": source}))
    submit.assert_not_called()
    train.assert_not_called()
    service.backends.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [{"source": SOURCE.replace("+ blue", "+ 2*blue")}, {"backend_name": "ibm_other"}],
)
def test_reusing_id_for_a_different_test_has_actionable_error_and_never_resubmits(
    mocked, change, caplog
):
    request, submit, train, _, _ = mocked
    hardware.submit(request)
    response = compiler_hardware.submit(request.model_copy(update=change))
    assert response.status_code == 422
    error = json.loads(response.body)["error"]
    assert error["diagnostics"][0]["code"] == "HARDWARE_REQUEST_CONFLICT"
    assert "Check hardware job" in error["message"]
    assert "Start a new hardware test" in error["message"]
    assert "Compiler hardware request rejected: HARDWARE_REQUEST_CONFLICT" in caplog.text
    submit.assert_called_once()
    train.assert_called_once()
    assert hardware.devices().reserved_seconds == 10
    assert hardware.refresh(request.request_id).status == "DONE"


def test_reservation_rejection_is_distinct_from_request_conflict(mocked):
    request, submit, _, _, _ = mocked
    hardware.submit(request)
    hardware.submit(request.model_copy(update={"request_id": uuid4()}))
    response = compiler_hardware.submit(request.model_copy(update={"request_id": uuid4()}))
    assert response.status_code == 422
    error = json.loads(response.body)["error"]
    assert error["diagnostics"][0]["code"] == "HARDWARE_RESERVATION_LIMIT"
    assert "local compiler cap" in error["message"]
    assert submit.call_count == 2


def test_unexpected_value_errors_do_not_expose_exception_details():
    def rejected():
        raise ValueError("fake-private-token")

    response = compiler_hardware._call(rejected)
    assert response.status_code == 422
    assert "fake-private-token" not in response.body.decode()


def test_missing_request_is_actionable_and_never_contacts_provider(mocked):
    request, submit, train, service, _ = mocked
    response = compiler_hardware.status(request.request_id)
    assert response.status_code == 422
    assert (
        json.loads(response.body)["error"]["diagnostics"][0]["code"] == "HARDWARE_REQUEST_NOT_FOUND"
    )
    submit.assert_not_called()
    train.assert_not_called()
    service.job.assert_not_called()


@pytest.mark.parametrize("stage", ["authentication", "backends"])
def test_device_lookup_failure_is_sanitized_and_distinct_from_source_validation(
    mocked, stage, caplog
):
    _, submit, _, service, _ = mocked
    target = hardware._service if stage == "authentication" else service.backends
    target.side_effect = ValueError("fake-private-token fake-instance")
    response = compiler_hardware.devices()
    assert response.status_code == 503
    error = json.loads(response.body)["error"]
    assert error["diagnostics"][0]["code"] == "HARDWARE_DEVICE_LOOKUP_FAILED"
    assert "fake-private-token" not in response.body.decode() + caplog.text
    assert "fake-instance" not in response.body.decode() + caplog.text
    submit.assert_not_called()


def test_unreadable_record_blocks_accounting_without_contacting_provider(mocked):
    _, submit, _, service, _ = mocked
    _, _, folder, _ = hardware._settings()
    path = folder / "invalid.json"
    path.write_text("{}")
    response = compiler_hardware.devices()
    assert response.status_code == 503
    assert (
        json.loads(response.body)["error"]["diagnostics"][0]["code"] == "HARDWARE_RECORD_UNREADABLE"
    )
    assert path.read_text() == "{}"
    service.backends.assert_not_called()
    submit.assert_not_called()


def test_invalid_budget_is_identified_before_authentication(mocked, monkeypatch):
    _, submit, _, service, _ = mocked
    monkeypatch.setenv("QATLAS_COMPILER_QPU_BUDGET_SECONDS", "invalid")
    response = compiler_hardware.devices()
    assert response.status_code == 422
    assert json.loads(response.body)["error"]["diagnostics"][0]["code"] == "HARDWARE_BUDGET_INVALID"
    service.backends.assert_not_called()
    submit.assert_not_called()


@pytest.mark.parametrize(
    "name,optimum,bits",
    [("maxcut", -57, "000111"), ("partition", 4, "010110"), ("conflicts", -10, "010100")],
)
def test_stress_examples_pass_hardware_preparation_and_decode_mocked_samples(
    mocked, name, optimum, bits
):
    request, submit, _, _, job = mocked
    source = (
        Path(__file__).resolve().parents[3] / f"examples/compiler/programs/stress_{name}_6.py"
    ).read_text()
    hardware.run_classical.return_value = hardware.run_classical.return_value.model_copy(
        update={"objective": optimum, "best_bitstring": bits}
    )
    job.result.return_value[0].data.meas.get_counts = lambda: {bits[::-1]: 128}
    result = hardware.submit(request.model_copy(update={"source": source}))
    assert result.status == "SUBMITTED" and result.qubo.num_variables == 6
    completed = hardware.refresh(request.request_id)
    assert completed.measurement.best_bitstring == bits
    assert completed.measurement.objective == optimum
    assert completed.measurement.optimality_gap == 0
    submit.assert_called_once()


def test_six_qubit_portfolio_can_submit_and_decode_without_changing_job_caps(mocked):
    request, submit, _, _, job = mocked
    source = (
        Path(__file__).resolve().parents[3] / "examples/compiler/programs/portfolio_6.py"
    ).read_text()
    hardware.run_classical.return_value = hardware.run_classical.return_value.model_copy(
        update={"objective": -22, "best_bitstring": "110100"}
    )
    job.result.return_value[0].data.meas.get_counts = lambda: {"001011": 128}
    result = hardware.submit(request.model_copy(update={"source": source}))
    assert result.status == "SUBMITTED" and result.qubo.num_variables == 6
    assert result.shots == 128 and result.max_execution_seconds == 10
    completed = hardware.refresh(request.request_id)
    assert completed.measurement.best_bitstring == "110100"
    assert completed.measurement.optimality_gap == 0
    assert hardware.devices().reserved_seconds == 2
    submit.assert_called_once()


def test_preparation_failure_spends_nothing_and_budget_blocks_extra_jobs(mocked):
    request, submit, train, _, _ = mocked
    train.side_effect = TimeoutError("local training timed out")
    assert hardware.submit(request).status == "FAILED_BEFORE_SUBMISSION"
    submit.assert_not_called()
    assert hardware.devices().reserved_seconds == 0
    train.side_effect = None
    hardware.submit(request.model_copy(update={"request_id": uuid4()}))
    hardware.submit(request.model_copy(update={"request_id": uuid4()}))
    with pytest.raises(ValueError, match="reservation cap"):
        hardware.submit(request.model_copy(update={"request_id": uuid4()}))
    assert submit.call_count == 2


def test_cancel_and_bad_counts_do_not_resubmit(mocked):
    request, submit, _, _, job = mocked
    hardware.submit(request)
    job.status = lambda: "CANCELLED"
    assert hardware.refresh(request.request_id, cancel=True).status == "CANCELLED"
    job.cancel.assert_called_once()
    job.status = lambda: "DONE"
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"01": 127})))
    ]
    with pytest.raises(RuntimeError, match="requested shots"):
        hardware.refresh(request.request_id)
    submit.assert_called_once()


def test_api_requires_confirmation_and_bounded_request(client, mocked):
    request, submit, _, _, _ = mocked
    payload = request.model_dump(mode="json")
    for update in ({"confirmed": False}, {"shots": 129}, {"max_execution_seconds": 11}):
        assert (
            client.post("/api/compiler/hardware/submit", json={**payload, **update}).status_code
            == 422
        )
    submit.assert_not_called()
    assert client.get("/api/compiler/hardware/devices").status_code == 200
    result = client.post("/api/compiler/hardware/submit", json=payload)
    assert result.status_code == 200 and result.json()["job_id"] == "fake-job"
    assert (
        client.get(f"/api/compiler/hardware/jobs/{request.request_id}").json()["measurement"][
            "simulated"
        ]
        is False
    )
    assert client.post("/api/compiler/hardware/submit", json=payload).status_code == 200
    submit.assert_called_once()
