"""Synthetic IBM responses only. Never authenticate, train, transpile or submit jobs."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.compiler import hardware
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
    assert hardware.devices().reserved_seconds == 10


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
    source = "@qatlas.objective\ndef wide(a,b,c,d): return a+b+c+d"
    with pytest.raises(ValueError, match="three binary"):
        hardware.submit(request.model_copy(update={"source": source}))
    submit.assert_not_called()
    train.assert_not_called()
    service.backends.assert_not_called()


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
