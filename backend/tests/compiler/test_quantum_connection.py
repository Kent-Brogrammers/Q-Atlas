"""No credentials, network, Qiskit execution or provider jobs used."""

import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

from scripts import check_quantum_connection as check


def test_offline_check_never_constructs_a_service(monkeypatch):
    monkeypatch.setattr(check, "version", lambda _: "test-version")
    factory, output = Mock(side_effect=AssertionError), io.StringIO()
    assert (
        check.main(
            [],
            environ={"QUANTUM-KEY": "fake-secret", "QATLAS_IBM_INSTANCE": "test"},
            service_factory=factory,
            output=output,
        )
        == 0
    )
    assert "fake-secret" not in output.getvalue()
    assert json.loads(output.getvalue())["jobs_submitted"] == 0
    factory.assert_not_called()


def test_connect_is_read_only_and_preserves_exact_token(monkeypatch):
    monkeypatch.setattr(check, "version", lambda _: "test-version")
    service = SimpleNamespace(backends=Mock(return_value=[SimpleNamespace(name="device")]))
    factory, output = Mock(return_value=service), io.StringIO()
    assert (
        check.main(
            ["--connect"],
            environ={"QUANTUM-KEY": "fake-secret", "QATLAS_IBM_INSTANCE": "test"},
            service_factory=factory,
            output=output,
        )
        == 0
    )
    factory.assert_called_once_with(
        channel="ibm_quantum_platform", token="fake-secret", instance="test"
    )
    service.backends.assert_called_once_with(operational=True, simulator=False)
    assert json.loads(output.getvalue())["backends"] == ["device"]
    assert "fake-secret" not in output.getvalue()


def test_missing_instance_prevents_connection(monkeypatch):
    monkeypatch.setattr(check, "version", lambda _: "test-version")
    factory = Mock(side_effect=AssertionError)
    assert (
        check.main(
            ["--connect"],
            environ={"QATLAS_QUANTUM_KEY": "fake-secret"},
            service_factory=factory,
            output=io.StringIO(),
        )
        == 1
    )
    factory.assert_not_called()


def test_cdn_alias_provides_explicit_instance(monkeypatch):
    monkeypatch.setattr(check, "version", lambda _: "test-version")
    factory, output = Mock(side_effect=AssertionError), io.StringIO()
    assert (
        check.main(
            [],
            environ={"QUANTUM-KEY": "fake-token", "QUANTUM-CDN": "fake-instance"},
            service_factory=factory,
            output=output,
        )
        == 0
    )
    assert json.loads(output.getvalue())["instance_present"] is True
    assert "fake-token" not in output.getvalue()
    factory.assert_not_called()


def test_sdk_failure_is_sanitized(monkeypatch):
    monkeypatch.setattr(check, "version", lambda _: "test-version")
    output = io.StringIO()
    assert (
        check.main(
            ["--connect"],
            environ={"QUANTUM-KEY": "fake-secret", "QATLAS_IBM_INSTANCE": "test"},
            service_factory=Mock(side_effect=RuntimeError("fake-secret")),
            output=output,
        )
        == 1
    )
    assert "fake-secret" not in output.getvalue()
