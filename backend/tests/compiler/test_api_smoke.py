"""Controlled HTTP responses for the smoke CLI; no server or quantum jobs required."""

import io
import json
from email.message import Message
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPHandler, build_opener
from urllib.response import addinfourl

import pytest

from app.compiler.analysis import analyze_source
from app.schemas.contracts import HealthResponse
from scripts import check_compiler_api as smoke

EXPECTED_CHECKS = len(json.loads((smoke.EXAMPLES / "expected_qubos.json").read_text())) + 2


class Response(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode())
        self.status = status


class Opener:
    def __init__(self, respond):
        self.respond = respond
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request.get_method(), urlsplit(request.full_url).path, timeout))
        return self.respond(request)


def valid_response(request):
    if request.get_method() == "GET":
        return Response(HealthResponse().model_dump(mode="json"))
    # The fake HTTP response uses the safe analyzer; the expected fixture is independent JSON.
    source = json.loads(request.data)["source"]
    return Response(analyze_source(source).model_dump(mode="json"))


def run(opener):
    output = io.StringIO()
    code = smoke.main(
        ["--base-url", "http://127.0.0.1:8000/api/", "--timeout", "0.5"],
        opener=opener,
        output=output,
    )
    return code, output.getvalue()


def test_all_examples_and_rejection_use_only_health_and_analysis():
    opener = Opener(valid_response)
    code, output = run(opener)
    assert code == 0
    assert f"{EXPECTED_CHECKS}/{EXPECTED_CHECKS} analysis-only checks passed" in output
    assert "PASS unsupported_call" in output
    assert len(opener.requests) == EXPECTED_CHECKS
    assert set(opener.requests) == {
        ("GET", "/api/health", 0.5),
        ("POST", "/api/compiler/analyze", 0.5),
    }
    assert "experiment readiness does not gate analysis" in output


@pytest.mark.parametrize(
    "broken",
    [
        "coefficient",
        "shape",
        "missing_preview",
        "executed",
        "wrong_width",
        "wrong_layers",
        "signed_zero",
        "missing_depth",
    ],
)
def test_response_mismatches_fail_with_useful_fields_and_continue(broken):
    def respond(request):
        if request.get_method() == "GET":
            return valid_response(request)
        payload = analyze_source(json.loads(request.data)["source"]).model_dump(mode="json")
        if payload["status"] == "supported":
            if broken == "coefficient":
                payload["qubo"]["linear"][0] += 1
            elif broken == "shape":
                return Response(
                    {"status": "supported", "diagnostics": [], "secret_input": "private contents"}
                )
            elif broken == "missing_preview":
                payload["circuit"] = None
            elif broken == "executed":
                payload["circuit"]["executed"] = True
            elif broken == "wrong_width":
                payload["circuit"]["num_qubits"] = min(16, payload["qubo"]["num_variables"] + 1)
            elif broken == "wrong_layers":
                from app.quantum.circuits import build_qaoa_preview

                payload["circuit"] = build_qaoa_preview(
                    analyze_source(json.loads(request.data)["source"]).qubo, 2
                ).model_dump(mode="json")
            elif broken == "signed_zero":
                for i, value in enumerate(payload["qubo"]["linear"]):
                    if value == 0:
                        payload["qubo"]["linear"][i] = -0.0
                        break
            else:
                del payload["circuit"]["depth"]
        return Response(payload)

    opener = Opener(respond)
    code, output = run(opener)
    assert code == 1
    assert "FAIL " in output and "PASS unsupported_call" in output
    assert "private contents" not in output
    assert len(opener.requests) == EXPECTED_CHECKS
    if broken == "coefficient":
        assert "qubo.linear[0]" in output and "expected" in output
    if broken == "signed_zero":
        assert "expected canonical +0" in output


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError(),
        URLError(TimeoutError()),
        URLError("private connection information"),
        OSError("private socket information"),
        IncompleteRead(b"private", 100),
    ],
)
def test_health_connection_errors_fail_fast_and_are_sanitized(failure):
    def respond(_request):
        raise failure

    opener = Opener(respond)
    code, output = run(opener)
    assert code == 1
    assert "FAIL setup/health" in output
    assert "private" not in output
    assert "No source cases submitted" in output
    assert len(opener.requests) == 1


@pytest.mark.parametrize("bad", ["http_status", "json", "empty_health", "oversized"])
def test_bad_http_or_health_payload_is_not_reported_as_ready(bad):
    def respond(_request):
        if bad == "http_status":
            return Response({}, 503)
        if bad == "empty_health":
            return Response({})
        response = Response({})
        response.seek(0)
        response.write(
            b"private invalid JSON" if bad == "json" else b"x" * (smoke.MAX_RESPONSE_BYTES + 1)
        )
        response.seek(0)
        return response

    code, output = run(Opener(respond))
    assert code == 1
    assert "PASS health" not in output
    assert "private invalid JSON" not in output


def test_redirect_to_an_execution_endpoint_is_never_followed():
    paths = []

    class RedirectingTransport(HTTPHandler):
        def http_open(self, request):
            paths.append(urlsplit(request.full_url).path)
            assert paths == ["/api/health"]
            headers = Message()
            headers["Location"] = "http://127.0.0.1:8000/api/compiler/benchmark"
            response = addinfourl(io.BytesIO(b""), headers, request.full_url, code=302)
            response.msg = "Found"
            return response

    opener = build_opener(RedirectingTransport(), smoke._NoRedirects())
    code, output = run(opener)
    assert code == 1
    assert "HTTP 302" in output and "Redirects are not followed" in output
    assert paths == ["/api/health"]


@pytest.mark.parametrize(
    "path", ["/compiler/benchmark", "/optimization/run", "/materials/run", "/search/run"]
)
def test_client_refuses_execution_routes_before_transport(path):
    opener = Opener(valid_response)
    with pytest.raises(smoke.CheckFailure, match="Only GET"):
        smoke.AnalysisClient("http://127.0.0.1:8000/api", 1, opener).request("POST", path, {})
    assert opener.requests == []


@pytest.mark.parametrize(
    "args",
    [
        ["--timeout", "0"],
        ["--timeout", "nan"],
        ["--timeout", "61"],
        ["--base-url", "file:///tmp/input"],
        ["--base-url", "http://name:private@example.com/api"],
        ["--base-url", "http://localhost/api?token=private"],
    ],
)
def test_invalid_cli_options_never_contact_a_server(args, capsys):
    opener = Opener(valid_response)
    with pytest.raises(SystemExit) as exc:
        smoke.main(args, opener=opener)
    assert exc.value.code == 2
    assert opener.requests == []
    assert "private" not in capsys.readouterr().err


def test_invalid_fixtures_fail_before_contacting_api(tmp_path):
    (tmp_path / "expected_qubos.json").write_text('{"../outside.py": {}}')
    opener = Opener(valid_response)
    output = io.StringIO()
    assert smoke.main([], examples_dir=tmp_path, opener=opener, output=output) == 1
    assert opener.requests == []


def test_http_error_is_reported_without_echoing_its_body():
    error = HTTPError(
        "http://127.0.0.1:8000/api/health", 500, "private message", {}, io.BytesIO(b"private body")
    )

    def respond(_request):
        raise error

    code, output = run(Opener(respond))
    assert code == 1 and "HTTP 500" in output
    assert "private" not in output
