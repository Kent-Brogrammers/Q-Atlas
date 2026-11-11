"""Explicit single-job IBM sampling with durable IDs and conservative reservations.

No provider call occurs on import. This consumes Developer 3's shared angle search,
circuit and count decoder. The agent tests it with mocks; operators submit jobs.
"""

import contextlib
import hashlib
import io
import json
import logging
import os
import threading
from pathlib import Path
from time import perf_counter

from app.compiler.pipeline import prepare_benchmark
from app.experiments.optimization.solvers import run_classical
from app.quantum.qaoa import _best_sample
from app.quantum.qaoa_optimization import optimize_qaoa_angles
from app.schemas.compiler_hardware import (
    CompilerHardwareDevices,
    CompilerHardwareJob,
    CompilerHardwareMeasurement,
    CompilerHardwareRequest,
)
from app.schemas.contracts import QAOAConfig

STORE = Path(__file__).resolve().parents[2] / ".cache" / "compiler-qpu"
_sdk_lock = threading.Lock()


@contextlib.contextmanager
def _quiet_sdk():
    # Do not leak credential-bearing SDK error strings or diagnostic output.
    with _sdk_lock:
        previous = logging.root.manager.disable
        try:
            logging.disable(logging.CRITICAL)
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                yield
        finally:
            logging.disable(previous)


def _settings():
    token = os.environ.get("QUANTUM-KEY") or os.environ.get("QATLAS_QUANTUM_KEY")
    instance = os.environ.get("QATLAS_IBM_INSTANCE")
    if not token or not instance:
        raise ValueError("Restart dev.sh and provide the IBM token and instance.")
    folder = STORE / hashlib.sha256(instance.encode()).hexdigest()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    budget = min(600, max(1, int(os.environ.get("QATLAS_COMPILER_QPU_BUDGET_SECONDS", "60"))))
    return token, instance, folder, budget


def _service(token, instance):
    from qiskit_ibm_runtime import QiskitRuntimeService

    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance)


def _write(path, record):
    temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(record.model_dump(mode="json"), handle, allow_nan=False)
    temporary.chmod(0o600)
    temporary.replace(path)


def _read(path):
    return CompilerHardwareJob.model_validate_json(path.read_text())


def _reserved(folder):
    records = (_read(path) for path in folder.glob("*.json"))
    return sum(r.max_execution_seconds for r in records if r.status != "FAILED_BEFORE_SUBMISSION")


def devices():
    token, instance, folder, budget = _settings()
    with _quiet_sdk():
        names = sorted(
            b.name for b in _service(token, instance).backends(operational=True, simulator=False)
        )
    return CompilerHardwareDevices(
        backends=names, reserved_seconds=_reserved(folder), budget_seconds=budget
    )


def _prepare_circuit(qubo, config, backend):
    from qiskit import ClassicalRegister, transpile

    from app.quantum.qaoa_circuit import build_qaoa_circuit

    optimized = optimize_qaoa_angles(qubo, config)
    circuit, parameters = build_qaoa_circuit(qubo, p=1)
    circuit = circuit.assign_parameters(
        dict(zip(parameters, optimized.angles, strict=True)), strict=False
    )
    circuit.add_register(ClassicalRegister(qubo.num_variables, "meas"))
    circuit.measure(range(qubo.num_variables), range(qubo.num_variables))
    return (
        transpile(circuit, backend=backend, optimization_level=1, seed_transpiler=config.seed),
        optimized,
    )


def _submit(backend, circuit, request):
    from qiskit_ibm_runtime import SamplerV2

    sampler = SamplerV2(
        mode=backend,
        options={
            "max_execution_time": request.max_execution_seconds,
            "default_shots": request.shots,
            "environment": {"job_tags": [f"qatlas-{request.request_id}"]},
            "twirling": {"enable_gates": False, "enable_measure": False},
            "dynamical_decoupling": {"enable": False},
        },
    )
    return sampler.run([circuit], shots=request.shots)


def submit(request: CompilerHardwareRequest):
    import fcntl

    config = QAOAConfig(p=1, shots=request.shots, max_iterations=20, timeout_seconds=30)
    plan = prepare_benchmark(request.source, config)
    # prepare_benchmark enforces the compiler's shared one-to-six-input limit.
    token, instance, folder, budget = _settings()
    path = folder / f"{request.request_id}.json"
    # Cross-process lock only for reservation/claim; never across remote calls.
    with (folder / "reservation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            existing = _read(path)
            if (
                existing.problem_id != plan.problem_id
                or existing.backend_name != request.backend_name
                or existing.shots != request.shots
                or existing.max_execution_seconds != request.max_execution_seconds
            ):
                raise ValueError("This request ID already belongs to another hardware test.")
            return existing
        if _reserved(folder) + request.max_execution_seconds > budget:
            raise ValueError(
                "Compiler QPU reservation cap reached. Check existing jobs and provider usage."
            )
        record = CompilerHardwareJob(
            request_id=str(request.request_id),
            status="PREPARING",
            backend_name=request.backend_name,
            problem_id=plan.problem_id,
            qubo=plan.qubo,
            local_training_config=config,
            shots=request.shots,
            max_execution_seconds=request.max_execution_seconds,
        )
        _write(path, record)
    try:
        record.classical = run_classical(plan.qubo, config)
        with _quiet_sdk():
            service = _service(token, instance)
            allowed = {b.name for b in service.backends(operational=True, simulator=False)}
            if request.backend_name not in allowed:
                raise ValueError("Select an accessible operational IBM QPU.")
            backend = service.backend(request.backend_name)
            circuit, optimized = _prepare_circuit(plan.qubo, config, backend)
            record.circuit_depth = circuit.depth()
            record.angles = list(optimized.angles)
            record.local_training_ms = optimized.elapsed_ms
            record.status = "SUBMISSION_UNKNOWN"
            _write(path, record)  # Never retry a potentially accepted submission.
            started = perf_counter()
            job = _submit(backend, circuit, request)
            record.job_id = job.job_id()
            record.submission_ms = (perf_counter() - started) * 1000
            record.status = "SUBMITTED"
            _write(path, record)
    except Exception:
        if record.status == "PREPARING":
            record.status = "FAILED_BEFORE_SUBMISSION"
        _write(path, record)
        # Operator must recover the tagged job in IBM if acknowledgement was lost.
    return record


def refresh(request_id, *, cancel=False):
    token, instance, folder, _ = _settings()
    path = folder / f"{request_id}.json"
    if not path.exists():
        raise ValueError("No recorded hardware request with this ID.")
    record = _read(path)
    if not record.job_id or record.measurement is not None:
        return record
    with _quiet_sdk():
        job = _service(token, instance).job(record.job_id)
        if cancel:
            job.cancel()
        status = job.status()
        record.status = status.name if hasattr(status, "name") else str(status)
        if record.status == "DONE":
            started = perf_counter()
            counts = job.result(timeout=15)[0].data.meas.get_counts()
            retrieval_ms = (perf_counter() - started) * 1000
            objective, bits = _best_sample(record.qubo, counts, record.shots)
            if record.classical is None or record.classical.objective is None:
                raise RuntimeError("Hardware record has no classical reference.")
            gap = objective - record.classical.objective
            if gap < -1e-9:
                raise RuntimeError("Hardware objective is below the exact classical optimum.")
            usage = None
            try:
                value = job.metrics().get("usage", {}).get("quantum_seconds")
                if isinstance(value, (int, float)) and 0 <= value < float("inf"):
                    usage = value
            except Exception:
                pass
            record.measurement = CompilerHardwareMeasurement(
                best_bitstring=bits,
                objective=objective,
                optimality_gap=max(0, gap),
                shots=sum(counts.values()),
                counts=counts,
                quantum_seconds=usage,
                retrieval_ms=retrieval_ms,
            )
    _write(path, record)
    return record
