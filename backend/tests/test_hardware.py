"""Mock provider jobs and real local circuit construction. No external QPU or credentials."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.compiler import hardware as ibm
from app.quantum import hardware
from app.schemas.hardware import HardwareRequest

CASES = {
    "compiler": {
        "source": "@qatlas.objective\ndef cost(red, blue): return 5 - 2*red + blue",
        "config": {"max_iterations": 5},
    },
    "optimization": {
        "problem": {
            "kind": "graph",
            "num_vertices": 2,
            "edges": [{"i": 0, "j": 1, "coefficient": 1}],
        },
        "config": {"max_iterations": 5},
    },
    "search": {"num_qubits": 2, "marked_states": ["01"], "iterations": 1},
    "materials": {
        "num_spins": 2,
        "field": 0,
        "evolution_time": 1,
        "trotter_steps": 1,
        "time_samples": 1,
    },
    "neutrinos": {
        "experiment": {"parameters": {"theta": 0}, "layers": [{"distance": 1}]},
        "samples": 2,
    },
}


def request(kind, **changes):
    return HardwareRequest(
        task={"kind": kind, "parameters": CASES[kind]},
        request_id=uuid4(),
        confirmed=True,
        **changes,
    )


@pytest.fixture
def provider(monkeypatch, tmp_path):
    import qiskit

    monkeypatch.setenv("QATLAS_QUANTUM_KEY", "invented-test-token")
    monkeypatch.delenv("QUANTUM-KEY", raising=False)
    monkeypatch.setenv("QATLAS_IBM_INSTANCE", "invented-test-instance")
    monkeypatch.setenv("QATLAS_COMPILER_QPU_BUDGET_SECONDS", "20")
    monkeypatch.setattr(ibm, "STORE", tmp_path)
    backend = SimpleNamespace(name="ibm_test", num_qubits=127, simulator=False)
    job = SimpleNamespace(
        job_id=lambda: "mock-job",
        status=lambda: "DONE",
        result=Mock(),
        cancel=Mock(),
        metrics=lambda: {
            "usage": {"quantum_seconds": 1.2},
            "timestamps": {
                "created": "2026-11-12T00:00:00Z",
                "running": "2026-11-12T00:00:02Z",
                "finished": "2026-11-12T00:00:03Z",
            },
        },
    )
    service = SimpleNamespace(
        backends=lambda **kwargs: [backend],
        least_busy=lambda **kwargs: backend,
        backend=lambda name: backend,
        job=lambda job_id: job,
        jobs=Mock(return_value=[job]),
    )
    monkeypatch.setattr(ibm, "_service", Mock(return_value=service))
    monkeypatch.setattr(qiskit, "transpile", lambda circuits, **kwargs: circuits)
    submit = Mock(return_value=job)
    monkeypatch.setattr(hardware, "_submit", submit)
    return job, service, submit


@pytest.mark.parametrize("kind", CASES)
def test_five_real_circuit_builders_decode_physical_results_and_preserve_evidence(provider, kind):
    job, _, submitted = provider
    r = request(kind)
    record = hardware.submit(r)
    assert record.status == "SUBMITTED"
    assert record.simulated is False
    assert record.num_qubits in (1, 2)
    assert all(c.num_clbits == record.num_qubits for c in submitted.call_args.args[1])
    counts = {
        "compiler": [{"01": 128}],
        "optimization": [{"01": 128}],
        "search": [{"10": 128}],
        "materials": [{"00": 128}, {"00": 64, "11": 64}],
        "neutrinos": [{"0": 128}, {"0": 128}],
    }[kind]
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda c=c: c)))
        for c in counts
    ]
    completed = hardware.refresh(r.request_id)
    assert completed.measurement_complete
    assert completed.counts == counts
    assert all(m.absolute_error < 1e-10 for m in completed.metrics)
    assert completed.timings.quantum_seconds == 1.2
    assert completed.timings.provider_queue_ms == 2000
    assert completed.timings.provider_execution_ms == 1000
    assert completed.timings.observed_wall_ms >= completed.timings.classical_ms
    assert "invented-test-token" not in completed.model_dump_json()
    assert hardware.submit(r).job_id == "mock-job"
    submitted.assert_called_once()
    assert hardware.list_jobs(kind)[0].measurement_complete
    # Completed physical use is charged once, rounded up, rather than keeping all 10s.
    assert hardware.readiness().reserved_seconds == 2
    assert hardware.readiness().remaining_reservation_seconds == 18


def test_unknown_acknowledgement_is_recoverable_and_never_resubmits(provider):
    job, service, submitted = provider
    submitted.side_effect = RuntimeError("invented-test-token")
    r = request("search")
    assert hardware.submit(r).status == "SUBMISSION_UNKNOWN"
    assert hardware.submit(r).status == "SUBMISSION_UNKNOWN"
    submitted.assert_called_once()
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"10": 128})))
    ]
    record = hardware.refresh(r.request_id)
    assert record.measurement_complete and record.job_id == "mock-job"
    service.jobs.assert_called_once_with(job_tags=[f"qatlas-all-{r.request_id}"], limit=2)


def test_shared_budget_and_conflicting_request_id_block_duplicate_jobs(provider):
    _, _, submitted = provider
    a, b = request("search"), request("neutrinos")
    hardware.submit(a)
    hardware.submit(b)
    assert ibm.devices().reserved_seconds == 20
    with pytest.raises(ibm.HardwareRequestError, match="cap reached"):
        hardware.submit(request("materials"))
    with pytest.raises(ibm.HardwareRequestError, match="different hardware"):
        hardware.submit(a.model_copy(update={"shots": 64}))
    assert submitted.call_count == 2


def test_five_experiment_bundle_uses_one_reservation_and_separate_measurements(provider):
    job, _, submitted = provider
    r = HardwareRequest(
        task={
            "kind": "suite",
            "parameters": [
                {"kind": kind, "parameters": parameters} for kind, parameters in CASES.items()
            ],
        },
        request_id=uuid4(),
        confirmed=True,
    )
    record = hardware.submit(r)
    assert len(record.children) == 5
    assert ibm.devices().reserved_seconds == 10
    counts = [
        {"01": 128},
        {"01": 128},
        {"10": 128},
        {"00": 128},
        {"00": 64, "11": 64},
        {"0": 128},
        {"0": 128},
    ]
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda c=c: c)))
        for c in counts
    ]
    result = hardware.refresh(r.request_id)
    assert result.measurement_complete and len(result.children) == 5
    assert all(child.measurement_complete for child in result.children)
    assert all(child.job_id == "mock-job" for child in result.children)
    assert all(child.timings.quantum_seconds is None for child in result.children)
    assert all(child.shared_job_timings.quantum_seconds == 1.2 for child in result.children)
    assert hardware.readiness().reserved_seconds == 2  # Parent charged once, never per child.
    assert hardware.list_jobs("materials")[0].task.kind == "materials"
    assert hardware.list_jobs("compiler")[0].measurement_complete
    submitted.assert_called_once()


@pytest.mark.parametrize(
    "status,usage,measured,expected",
    [
        ("DONE", 1.2, True, 2),
        ("DONE", 0, True, 0),
        ("DONE", 12.1, True, 13),
        ("DONE", None, True, 10),
        ("DONE", -1, True, 10),
        ("DONE", float("nan"), True, 10),
        ("DONE", float("inf"), True, 10),
        ("DONE", 2, False, 10),
        ("RUNNING", 2, True, 10),
        ("SUBMISSION_UNKNOWN", 2, True, 10),
        ("CANCELLED", None, False, 10),
        ("ERROR", None, False, 10),
        ("FAILED_BEFORE_SUBMISSION", None, False, 0),
    ],
)
def test_completed_usage_accounting_preserves_uncertain_reservations(
    status, usage, measured, expected
):
    assert ibm._charge(status, 10, usage, measured) == expected


def test_invalid_results_remain_unmeasured_and_never_fabricate(provider):
    job, _, submitted = provider
    r = request("search")
    hardware.submit(r)
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"10": 127})))
    ]
    record = hardware.refresh(r.request_id)
    assert not record.measurement_complete and record.counts == [] and record.metrics == []
    assert hardware.readiness().reserved_seconds == 10
    assert "retrieval failed" in record.message
    submitted.assert_called_once()


def test_resource_limits_precede_any_provider_or_submission(provider):
    _, _, submitted = provider
    r = request("search")
    r.task.parameters.iterations = 9
    with pytest.raises(ValueError, match="8 iterations"):
        hardware.submit(r)
    submitted.assert_not_called()


def test_readiness_reports_shared_cap_without_contacting_provider(provider):
    _, _, submitted = provider
    ready = hardware.readiness()
    assert ready.configured and ready.remaining_reservation_seconds == 20
    ibm._service.assert_not_called()
    hardware.submit(request("search"))
    hardware.submit(request("materials"))
    ibm._service.reset_mock()
    full = hardware.readiness()
    assert full.reserved_seconds == 20 and full.remaining_reservation_seconds == 0
    assert "cap is full" in full.message
    ibm._service.assert_not_called()
    assert submitted.call_count == 2


def test_cancel_uses_existing_job_and_keeps_reservation(provider):
    job, _, submitted = provider
    r = request("search")
    hardware.submit(r)
    job.status = lambda: "CANCELLED"
    record = hardware.refresh(r.request_id, cancel=True)
    assert record.status == "CANCELLED" and not record.measurement_complete
    assert ibm.devices().reserved_seconds == 10
    job.cancel.assert_called_once()
    submitted.assert_called_once()


def test_polling_during_submission_cannot_overwrite_the_acknowledged_job(provider):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    job, _, submitted = provider
    entered, release = threading.Event(), threading.Event()

    def delayed_submit(*args):
        entered.set()
        assert release.wait(5)
        return job

    submitted.side_effect = delayed_submit
    job.result.return_value = [
        SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"10": 128})))
    ]
    r = request("search")
    with ThreadPoolExecutor(max_workers=2) as pool:
        submission = pool.submit(hardware.submit, r)
        assert entered.wait(5)
        retrieval = pool.submit(hardware.refresh, r.request_id)
        release.set()
        assert submission.result(timeout=10).job_id == "mock-job"
        assert retrieval.result(timeout=10).measurement_complete
    assert hardware.list_jobs("search")[0].job_id == "mock-job"
    submitted.assert_called_once()


def test_api_requires_confirmation_and_sanitizes_configuration_failure(client, monkeypatch):
    r = request("search").model_dump(mode="json")
    r["confirmed"] = False
    assert client.post("/api/hardware/submit", json=r).status_code == 422
    monkeypatch.setattr(
        ibm,
        "_settings",
        Mock(
            side_effect=ibm.HardwareRequestError(
                "HARDWARE_CONFIGURATION_REQUIRED", "Configure optional hardware settings."
            )
        ),
    )
    response = client.get("/api/hardware/devices")
    assert response.status_code == 422
    assert "Configure optional hardware" in response.json()["error"]["message"]
