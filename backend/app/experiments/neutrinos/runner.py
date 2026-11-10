"""Bound web execution in a disposable worker; core API needs no quantum imports."""

import logging
import multiprocessing as mp
from multiprocessing.connection import Connection
from time import perf_counter

from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


class NeutrinoDependencyError(RuntimeError):
    """Optional simulation dependencies are unavailable."""


def _worker(connection: Connection, payload: dict) -> None:
    try:
        from app.experiments.neutrinos.web import run_curve

        response = run_curve(NeutrinoRequest.model_validate(payload))
        connection.send(("ok", response.model_dump(mode="json")))
    except ImportError:
        connection.send(("dependency_missing", None))
    except Exception:
        logging.getLogger(__name__).exception("Neutrino worker failed")
        connection.send(("error", None))
    finally:
        connection.close()


def run_neutrinos(request: NeutrinoRequest) -> NeutrinoResponse:
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker, args=(writer, request.model_dump(mode="json")), daemon=True
    )
    deadline = perf_counter() + request.timeout_seconds
    try:
        process.start()
        writer.close()
        if not reader.poll(max(0, deadline - perf_counter())):
            raise TimeoutError("Neutrino simulation exceeded its wall-clock budget")
        try:
            status, payload = reader.recv()
        except EOFError as exc:
            raise RuntimeError("Neutrino worker exited without a result") from exc
        if perf_counter() > deadline:
            raise TimeoutError("Neutrino simulation exceeded its wall-clock budget")
        if status == "dependency_missing":
            raise NeutrinoDependencyError("Install the backend quantum dependencies")
        if status != "ok":
            raise RuntimeError("Neutrino simulation failed")
        return NeutrinoResponse.model_validate(payload)
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
