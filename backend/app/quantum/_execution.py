"""Developer 3's bounded worker boundary for angle search and complete QAOA runs."""

import logging
import multiprocessing as mp
from collections.abc import Callable
from multiprocessing.connection import Connection
from time import perf_counter_ns

from app.schemas.contracts import QUBO, QAOAConfig


def _worker(
    connection: Connection,
    qubo_payload: dict,
    config_payload: dict,
    compute: Callable[[QUBO, QAOAConfig], object],
) -> None:
    try:
        result = compute(
            QUBO.model_validate(qubo_payload), QAOAConfig.model_validate(config_payload)
        )
        connection.send(("ok", result))
    except ImportError:
        connection.send(("dependency_missing", None))
    except ValueError as error:
        connection.send(("invalid", str(error)))
    except Exception:
        logging.getLogger(__name__).exception("QAOA worker failed")
        connection.send(("error", None))
    finally:
        connection.close()


def run_with_deadline(
    qubo: QUBO,
    config: QAOAConfig,
    compute: Callable[[QUBO, QAOAConfig], object],
    *,
    task_name: str,
) -> tuple[object, float]:
    """Run trusted Developer 3 computation and return its payload and elapsed ms.

    The budget includes startup, preparation, native work, IPC, and normal cleanup.
    Timeout cleanup terminates and reaps the worker, with OS cleanup latency.
    """
    started_ns = perf_counter_ns()
    deadline_ns = started_ns + int(config.timeout_seconds * 1_000_000_000)
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker,
        args=(writer, qubo.model_dump(mode="json"), config.model_dump(mode="json"), compute),
        daemon=True,
    )
    received = False
    try:
        process.start()
        writer.close()
        remaining_seconds = max(0, deadline_ns - perf_counter_ns()) / 1_000_000_000
        if not reader.poll(remaining_seconds):
            raise TimeoutError(f"{task_name} exceeded timeout_seconds")
        try:
            status, payload = reader.recv()
        except EOFError as error:
            raise RuntimeError(f"{task_name} worker exited without a result") from error
        received = True
        if perf_counter_ns() >= deadline_ns:
            raise TimeoutError(f"{task_name} exceeded timeout_seconds")
    finally:
        try:
            if process.pid is not None:
                if received:
                    process.join(timeout=0.05)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                process.close()
        finally:
            reader.close()
            writer.close()
    finished_ns = perf_counter_ns()
    if finished_ns >= deadline_ns:
        raise TimeoutError(f"{task_name} exceeded timeout_seconds")
    if status == "dependency_missing":
        raise ImportError("Install the backend quantum extra to run QAOA")
    if status == "invalid":
        raise ValueError(payload)
    if status != "ok":
        raise RuntimeError(f"{task_name} failed")
    return payload, (finished_ns - started_ns) / 1_000_000
