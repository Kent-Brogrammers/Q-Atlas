"""Cancelable search boundary; optional quantum dependencies load only in the worker."""

import logging
import multiprocessing as mp
from multiprocessing.connection import Connection
from time import perf_counter

from app.experiments.search.settings import request_diagnostics
from app.schemas.contracts import SearchRequest, SearchResult


class SearchDependencyError(RuntimeError):
    """Install the optional quantum extra to run the experiment."""


def _worker(connection: Connection, payload: dict) -> None:
    try:
        from app.experiments.search.experiment import run_experiment

        result = run_experiment(SearchRequest.model_validate(payload))
        connection.send(("ok", result.model_dump(mode="json")))
    except ImportError:
        connection.send(("dependency_missing", None))
    except Exception:
        logging.getLogger(__name__).exception("Search worker failed")
        connection.send(("error", None))
    finally:
        connection.close()


def run_search(request: SearchRequest) -> SearchResult:
    """Enforce a total wall-clock budget including process startup and both solvers.

    Terminate and reap the worker even when a native simulator call is stuck.
    Reported solver timings exclude this process/IPC overhead; the budget does not.
    """
    if diagnostics := request_diagnostics(request):
        raise ValueError("; ".join(item.message for item in diagnostics))
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
            raise TimeoutError("Search exceeded config.timeout_seconds")
        try:
            status, payload = reader.recv()
        except EOFError as exc:
            raise RuntimeError("Search worker exited without a result") from exc
        if status == "dependency_missing":
            raise SearchDependencyError("Install the backend quantum extra to run search")
        if status != "ok":
            raise RuntimeError("Search simulation failed")
        result = SearchResult.model_validate(payload)
        if perf_counter() >= deadline:
            raise TimeoutError("Search exceeded config.timeout_seconds")
        return result
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
