"""Offline readiness by default; --connect only authenticates/lists IBM backends.

No primitives, circuits, sessions, batches or submission API are used here.
"""

import argparse
import contextlib
import io
import json
import logging
import os
from importlib.metadata import PackageNotFoundError, version


def _service_factory(**kwargs):
    from qiskit_ibm_runtime import QiskitRuntimeService

    return QiskitRuntimeService(**kwargs)


def main(argv=None, *, environ=None, service_factory=None, output=None):
    parser = argparse.ArgumentParser(description="Check Qiskit setup without submitting jobs.")
    parser.add_argument("--connect", action="store_true", help="Authenticate and list devices only")
    args = parser.parse_args(argv)
    env = os.environ if environ is None else environ
    # The hyphenated name works in os.environ, but is not a normal shell identifier.
    token = env.get("QUANTUM-KEY") or env.get("QATLAS_QUANTUM_KEY")
    instance = env.get("QATLAS_IBM_INSTANCE")
    versions = {}
    for package in ("qiskit", "qiskit-ibm-runtime"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    report = {
        "mode": "connection_only" if args.connect else "offline",
        "versions": versions,
        "token_present": bool(token and token.strip()),
        "instance_present": bool(instance and instance.strip()),
        "jobs_submitted": 0,
        "message": "Offline check only. No provider contacted.",
    }
    code = (
        0
        if all(versions.values()) and report["token_present"] and report["instance_present"]
        else 1
    )
    if args.connect:
        if code:
            report["message"] = "Missing SDK, token environment setting, or explicit IBM instance."
        else:
            # SDK exception strings, account objects and logs can contain credentials.
            # Never echo them. This short-lived CLI restores logging state on exit.
            previous_logging = logging.root.manager.disable
            try:
                logging.disable(logging.CRITICAL)
                with (
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    service = (service_factory or _service_factory)(
                        channel="ibm_quantum_platform", token=token, instance=instance
                    )
                    backends = service.backends(operational=True, simulator=False)
                    names = sorted(backend.name for backend in backends)
                report["backends"] = names
                report["message"] = "Authenticated and listed devices. No quantum job submitted."
            except Exception:
                code = 1
                report["message"] = (
                    "Connection failed. Verify provider, instance, access and network."
                )
            finally:
                logging.disable(previous_logging)
    print(json.dumps(report, indent=2), file=output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
