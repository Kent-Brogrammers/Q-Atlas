"""Bound local simulation in a disposable worker so native calls can be stopped.

This module imports no quantum packages: API startup still works with only core deps.
"""

import logging
import multiprocessing as mp
from multiprocessing.connection import Connection
from time import perf_counter

from app.schemas.contracts import Diagnostic, MaterialsRequest, MaterialsResult


class MaterialsDependencyError(RuntimeError):
    """The optional quantum dependency group is not installed."""


def request_diagnostics(request: MaterialsRequest) -> list[Diagnostic]:
    """Keep legacy schema fields; reject unsupported scaffold options explicitly at runtime."""
    diagnostics = []
    for invalid, field, message in [
        (request.model != "ising", "model", "only the transverse-field Ising model is implemented"),
        (request.boundary != "open", "boundary", "only open boundaries are implemented"),
        (request.num_spins > 4, "num_spins", "the implemented experiment supports 2–4 spins"),
        (abs(request.coupling) > 10, "coupling", "must be within [-10, 10]"),
        (abs(request.field) > 10, "field", "must be within [-10, 10]"),
        (
            request.time_samples * request.trotter_steps > 2048,
            "time_samples/trotter_steps",
            "time_samples * trotter_steps must not exceed 2048",
        ),
        (
            2 * request.time_samples * request.config.shots > 1_000_000,
            "config.shots/time_samples",
            "two measurement bases * time_samples * shots must not exceed 1000000",
        ),
        (
            request.time_samples > 1 and request.evolution_time == 0,
            "time_samples/evolution_time",
            "a sweep requires positive evolution_time; use time_samples=1 at t=0",
        ),
    ]:
        if invalid:
            diagnostics.append(
                Diagnostic(
                    code="MATERIALS_PARAMETER",
                    message=f"body.{field}: {message}",
                    severity="error",
                )
            )
    return diagnostics


def _worker(connection: Connection, payload: dict) -> None:
    try:
        from app.experiments.materials.experiment import run_experiment

        result = run_experiment(MaterialsRequest.model_validate(payload))
        connection.send(("ok", result.model_dump(mode="json")))
    except ImportError:
        connection.send(("dependency_missing", None))
    except Exception:
        logging.getLogger(__name__).exception("Materials worker failed")
        connection.send(("error", None))
    finally:
        connection.close()


def run_materials(request: MaterialsRequest) -> MaterialsResult:
    """Enforce a wall-clock budget including startup; kill/reap worker on timeout."""
    if request_diagnostics(request):
        raise ValueError("unsupported materials parameters")
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker, args=(writer, request.model_dump(mode="json")), daemon=True
    )
    deadline = perf_counter() + request.config.timeout_seconds
    try:
        process.start()
        writer.close()
        if not reader.poll(max(0, deadline - perf_counter())):
            raise TimeoutError("Materials simulation exceeded its wall-clock budget")
        try:
            status, payload = reader.recv()
        except EOFError as exc:
            raise RuntimeError("Materials worker exited without a result") from exc
        if perf_counter() > deadline:
            raise TimeoutError("Materials simulation exceeded its wall-clock budget")
        if status == "dependency_missing":
            raise MaterialsDependencyError("Install the backend quantum extra to run materials")
        if status != "ok":
            raise RuntimeError("Materials simulation failed")
        return MaterialsResult.model_validate(payload)
    finally:
        reader.close()
        writer.close()
        if process.pid is not None:
            process.join(timeout=0.05)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()
