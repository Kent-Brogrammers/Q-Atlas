"""Durable, bounded IBM job execution for all five workspaces; no automatic simulation."""

import fcntl
from datetime import UTC, datetime
from importlib.metadata import version
from time import perf_counter

from app.compiler import hardware as ibm
from app.schemas.hardware import HardwareJob, HardwareRequest


def now():
    return datetime.now(UTC).isoformat()


def _read(path):
    try:
        return HardwareJob.model_validate_json(path.read_text())
    except (OSError, ValueError):
        raise ibm.HardwareOperationError(
            "HARDWARE_RECORD_UNREADABLE",
            (
                "Saved hardware evidence cannot be read. Preserve the original record; "
                "no new job was submitted."
            ),
        ) from None


def list_jobs(experiment=None):
    _, _, root, _ = ibm._settings()
    records = [_read(path) for path in (root / "experiments").glob("*.json")]
    selected = []
    for record in records:
        if experiment is None or record.task.kind == experiment:
            selected.append(record)
        elif record.task.kind == "suite":
            selected.extend(child for child in record.children if child.task.kind == experiment)
    return sorted(
        selected,
        key=lambda r: r.created_at_utc,
        reverse=True,
    )


def _submit(backend, circuits, request):
    from qiskit_ibm_runtime import SamplerV2

    return SamplerV2(
        mode=backend,
        options={
            "max_execution_time": request.max_execution_seconds,
            "default_shots": request.shots,
            "environment": {
                "job_tags": [f"qatlas-all-{request.request_id}", f"qatlas-{request.task.kind}"]
            },
            "twirling": {"enable_gates": False, "enable_measure": False},
            "dynamical_decoupling": {"enable": False},
        },
    ).run(circuits, shots=request.shots)


def submit(request: HardwareRequest):
    from app.quantum.hardware_experiments import prepare, problem_id, validate_task

    validate_task(request)
    token, instance, root, budget = ibm._settings()
    folder = root / "experiments"
    folder.mkdir(mode=0o700, exist_ok=True)
    path = folder / f"{request.request_id}.json"
    identity = problem_id(request)
    with (root / "reservation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            existing = _read(path)
            if (
                existing.problem_id != identity
                or existing.shots != request.shots
                or existing.max_execution_seconds != request.max_execution_seconds
                or (
                    request.backend_name is not None
                    and existing.backend_name != request.backend_name
                )
            ):
                raise ibm.HardwareRequestError(
                    "HARDWARE_REQUEST_CONFLICT",
                    (
                        "This request ID belongs to a different hardware run. Recover it "
                        "before starting another."
                    ),
                )
            return existing
        if (root / f"{request.request_id}.json").exists():
            raise ibm.HardwareRequestError(
                "HARDWARE_REQUEST_CONFLICT",
                "This ID is already used by the legacy compiler hardware tracker.",
            )
        if ibm._reserved(root) + request.max_execution_seconds > budget:
            raise ibm.HardwareRequestError(
                "HARDWARE_RESERVATION_LIMIT",
                (
                    "Shared QPU reservation cap reached. Check existing jobs and actual "
                    "provider usage; no new job was submitted."
                ),
            )
        record = HardwareJob(
            request_id=str(request.request_id),
            task=request.task,
            problem_id=identity,
            created_at_utc=now(),
            updated_at_utc=now(),
            status="PREPARING",
            backend_name=request.backend_name,
            shots=request.shots,
            max_execution_seconds=request.max_execution_seconds,
            versions={
                p: version(p)
                for p in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime", "numpy", "scipy")
            },
        )
        ibm._write(path, record)
    # Serialize submission with status/recovery so polling cannot overwrite an acknowledgement.
    with path.with_suffix(".lock").open("a") as operation_lock:
        fcntl.flock(operation_lock, fcntl.LOCK_EX)
        try:
            circuits = prepare(request, record)
            with ibm._quiet_sdk():
                from qiskit import transpile

                service = ibm._service(token, instance)
                if request.backend_name:
                    accessible = {
                        b.name for b in service.backends(operational=True, simulator=False)
                    }
                    if request.backend_name not in accessible:
                        raise ValueError("Choose an accessible physical device.")
                    backend = service.backend(request.backend_name)
                else:
                    backend = service.least_busy(
                        operational=True, simulator=False, min_num_qubits=record.num_qubits
                    )
                record.backend_name = backend.name
                if backend.num_qubits < record.num_qubits or getattr(backend, "simulator", False):
                    raise ValueError("A physical device with enough qubits is required.")
                started = perf_counter()
                compiled = transpile(
                    circuits,
                    backend=backend,
                    optimization_level=1,
                    seed_transpiler=42,
                    num_processes=1,
                )
                record.timings.transpilation_ms = (perf_counter() - started) * 1000
                record.circuit_depths = [c.depth() for c in compiled]
                offset = 0
                for child in record.children:
                    size = len(child.circuit_depths)
                    child.circuit_depths = record.circuit_depths[offset : offset + size]
                    offset += size
                if max(record.circuit_depths) > 2500 or sum(len(c.data) for c in compiled) > 20000:
                    raise ValueError(
                        "Compiled circuit resource cap exceeded. Use smaller settings."
                    )
                record.status = "SUBMISSION_UNKNOWN"
                record.updated_at_utc = now()
                ibm._write(path, record)
                started = perf_counter()
                job = _submit(backend, compiled, request)
                record.job_id = job.job_id()
                record.timings.submission_ms = (perf_counter() - started) * 1000
                record.status = "SUBMITTED"
                record.message = "Physical IBM job accepted. Check status to retrieve results."
        except Exception:
            if record.status == "PREPARING":
                record.status = "FAILED_BEFORE_SUBMISSION"
                record.message = (
                    "Preparation or device access failed before submission. Check "
                    "dependencies, device access and bounded settings. No QPU job was submitted."
                )
            else:
                record.message = (
                    "Submission acknowledgement is uncertain. Recover by request tag "
                    "before considering another job; this request will never resubmit."
                )
        record.updated_at_utc = now()
        _sync_children(record)
        ibm._write(path, record)
        return record


def _sync_children(record):
    for child in record.children:
        child.job_id = record.job_id
        child.backend_name = record.backend_name
        child.status = record.status
        child.updated_at_utc = record.updated_at_utc
        child.shared_job_timings = record.timings.model_copy(deep=True)
        child.message = record.message
        child.timing_note = (
            "Physical counts and classical references are specific to this experiment. "
            "Provider usage, queue and observed total time belong to the entire five-experiment "
            "shared job, not this experiment alone. No per-experiment QPU runtime is inferred."
        )


def _provider_timings(record, metrics):
    usage = metrics.get("usage", {}).get("quantum_seconds")
    if (
        isinstance(usage, (float, int))
        and not isinstance(usage, bool)
        and 0 <= usage < float("inf")
    ):
        record.timings.quantum_seconds = usage
    timestamps = metrics.get("timestamps", {})

    def interval(start, end):
        try:
            duration = (
                datetime.fromisoformat(timestamps[end].replace("Z", "+00:00"))
                - datetime.fromisoformat(timestamps[start].replace("Z", "+00:00"))
            ).total_seconds() * 1000
            return duration if duration >= 0 else None
        except (KeyError, ValueError, TypeError, AttributeError):
            return None

    record.timings.provider_queue_ms = interval("created", "running")
    record.timings.provider_execution_ms = interval("running", "finished")


def refresh(request_id, *, cancel=False):
    from app.quantum.hardware_experiments import decode

    token, instance, root, _ = ibm._settings()
    path = root / "experiments" / f"{request_id}.json"
    if not path.exists():
        raise ibm.HardwareRequestError(
            "HARDWARE_REQUEST_NOT_FOUND",
            (
                "No saved request under this instance. Recover the original "
                "backend/instance before submitting again."
            ),
        )
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = _read(path)
        if record.measurement_complete or record.status in (
            "FAILED_BEFORE_SUBMISSION",
            "PREPARING",
        ):
            return record
        try:
            with ibm._quiet_sdk():
                service = ibm._service(token, instance)
                if record.job_id is None and record.status == "SUBMISSION_UNKNOWN":
                    jobs = service.jobs(job_tags=[f"qatlas-all-{request_id}"], limit=2)
                    if len(jobs) == 1:
                        record.job_id = jobs[0].job_id()
                    else:
                        record.message = (
                            "Tagged submission is not uniquely recoverable yet. Check IBM "
                            "workloads; do not submit a duplicate."
                        )
                if record.job_id:
                    job = service.job(record.job_id)
                    if cancel:
                        job.cancel()
                    state = job.status()
                    record.status = state.name if hasattr(state, "name") else str(state)
                    if record.status == "DONE":
                        started = perf_counter()
                        result = job.result(timeout=15)
                        counts = [pub.data.meas.get_counts() for pub in result]
                        record.timings.retrieval_ms = (perf_counter() - started) * 1000
                        decode(record, counts)
                        record.timings.observed_wall_ms = (
                            datetime.now(UTC) - datetime.fromisoformat(record.created_at_utc)
                        ).total_seconds() * 1000
                        try:
                            _provider_timings(record, job.metrics())
                        except Exception:
                            pass
                        record.message = (
                            "Physical QPU measurements received; raw counts and classical "
                            "comparisons are available."
                        )
                    elif record.status in ("ERROR", "CANCELLED"):
                        record.message = (
                            "The physical job failed or was cancelled. No measurement is reported; "
                            "check IBM workloads."
                        )
        except Exception:
            record.message = (
                "Provider status/result retrieval failed. Keep this request/job ID and "
                "retry retrieval; no new job was submitted."
            )
        record.updated_at_utc = now()
        _sync_children(record)
        ibm._write(path, record)
        return record
