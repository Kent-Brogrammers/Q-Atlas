"""Check a running compiler API using health/analysis only; never invoke a solver."""

import argparse
import json
import math
import sys
from collections.abc import Sequence
from http.client import HTTPException
from pathlib import Path
from typing import TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.contracts import QUBO, CompilerAnalyzeResult, HealthResponse  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "compiler"
ALLOWED_ROUTES = frozenset({("GET", "/health"), ("POST", "/compiler/analyze")})
MAX_RESPONSE_BYTES = 1_000_000
REJECTED_SOURCE = "@qatlas.objective(num_bits=3)\ndef cost(x):\n    return sum(x)\n"


class CheckFailure(Exception):
    """A concise check failure safe to display without response/source contents."""


def _base_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme in ("http", "https")
            and parts.hostname
            and "@" not in parts.netloc
            and not parts.query
            and not parts.fragment
        )
        _ = parts.port  # Validate a supplied port without echoing the URL in an error.
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError(
            "Use an HTTP(S) API root without credentials, query, or fragment."
        )
    return parts.geturl().rstrip("/")


def _timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timeout must be a number in (0, 60] seconds.") from exc
    if not math.isfinite(seconds) or not 0 < seconds <= 60:
        raise argparse.ArgumentTypeError("Timeout must be a number in (0, 60] seconds.")
    return seconds


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AnalysisClient:
    """A restricted HTTP client, with a finite socket timeout and no redirects."""

    def __init__(self, base_url: str, timeout: float, opener: OpenerDirector | None = None):
        self.base_url = base_url
        self.timeout = timeout
        self.opener = opener if opener is not None else build_opener(_NoRedirects())

    def request(self, method: str, path: str, payload: dict | None = None) -> object:
        if (method, path) not in ALLOWED_ROUTES:
            raise CheckFailure("Only GET /health and POST /compiler/analyze are allowed.")
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise CheckFailure(f"Expected HTTP 200, got HTTP {response.status}.")
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            suffix = " Redirects are not followed." if 300 <= status < 400 else ""
            raise CheckFailure(f"Expected HTTP 200, got HTTP {status}.{suffix}") from None
        except TimeoutError:
            raise CheckFailure("HTTP request timed out.") from None
        except URLError as exc:
            message = (
                "HTTP request timed out."
                if isinstance(exc.reason, TimeoutError)
                else "Cannot connect to the API; check the server and API root."
            )
            raise CheckFailure(message) from None
        except OSError:
            raise CheckFailure("HTTP connection failed while reading the API response.") from None
        except HTTPException:
            raise CheckFailure("HTTP response could not be read completely.") from None
        if len(body) > MAX_RESPONSE_BYTES:
            raise CheckFailure("API response exceeds the smoke check's size limit.")
        try:
            return json.loads(body)
        except ValueError:
            raise CheckFailure("API response is not valid JSON.") from None


def _validation_failure(exc: ValidationError) -> CheckFailure:
    errors = exc.errors(include_input=False, include_context=False)
    fields = [
        f"{'.'.join(map(str, item['loc'])) or 'response'} ({item['type']})" for item in errors[:3]
    ]
    return CheckFailure("Response validation failed: " + ", ".join(fields))


def _differences(expected: object, actual: object, path: str = "qubo") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        differences = []
        for key in sorted(expected.keys() | actual.keys()):
            field = f"{path}.{key}"
            if key not in actual:
                differences.append(f"{field}: missing field")
            elif key not in expected:
                differences.append(f"{field}: unexpected field")
            else:
                differences.extend(_differences(expected[key], actual[key], field))
        return differences
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}.length: expected {len(expected)}, got {len(actual)}"]
        return [
            difference
            for i, (a, b) in enumerate(zip(expected, actual, strict=True))
            for difference in _differences(a, b, f"{path}[{i}]")
        ]
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    if isinstance(actual, (int, float)) and actual == 0 and math.copysign(1, actual) < 0:
        return [f"{path}: expected canonical +0, got -0"]
    return []


def _check_analysis(raw: object, expected: QUBO | None) -> None:
    try:
        result = CompilerAnalyzeResult.model_validate(raw, strict=True)
    except ValidationError as exc:
        raise _validation_failure(exc) from None
    if expected is None:
        if result.status != "rejected":
            raise CheckFailure("Expected rejected analysis for an unsupported call.")
        if not any(
            d.code == "UNSUPPORTED_SYNTAX" and d.severity == "error" for d in result.diagnostics
        ):
            raise CheckFailure("Expected an UNSUPPORTED_SYNTAX error diagnostic.")
        if (
            "qubo" not in raw
            or raw["qubo"] is not None
            or "circuit" not in raw
            or raw["circuit"] is not None
        ):
            raise CheckFailure("Rejected analysis must explicitly return null qubo and circuit.")
        return
    if result.status != "supported":
        raise CheckFailure("Expected supported analysis for the example.")
    if any(d.severity == "error" for d in result.diagnostics):
        raise CheckFailure("Supported analysis contains an error diagnostic.")
    differences = _differences(expected.model_dump(mode="json"), raw["qubo"])
    if differences:
        raise CheckFailure("; ".join(differences[:5]))
    if result.circuit is None:
        raise CheckFailure("circuit: expected an unexecuted symbolic preview, got null.")
    if result.circuit.num_qubits != expected.num_variables:
        raise CheckFailure("circuit.num_qubits does not match the QUBO width.")
    if (
        raw["circuit"].get("executed") is not False
        or "depth" not in raw["circuit"]
        or raw["circuit"]["depth"] is not None
    ):
        raise CheckFailure("circuit must explicitly declare executed=false and depth=null.")
    if result.circuit.p != 1:
        raise CheckFailure("circuit.p: Analyze should preview one layer.")


def _examples(directory: Path) -> list[tuple[str, str, QUBO]]:
    try:
        expected = json.loads((directory / "expected_qubos.json").read_text(encoding="utf-8"))
        if not isinstance(expected, dict) or not expected:
            raise ValueError
        cases = []
        for filename, payload in sorted(expected.items()):
            if Path(filename).name != filename or Path(filename).suffix != ".py":
                raise ValueError
            path = directory / filename
            if path.resolve().parent != directory.resolve():
                raise ValueError
            cases.append(
                (
                    filename,
                    path.read_text(encoding="utf-8"),
                    QUBO.model_validate(payload, strict=True),
                )
            )
        return cases
    except (OSError, ValueError):
        raise CheckFailure(
            "Cannot load valid source examples and expected QUBOs from the fixture directory."
        ) from None


def main(
    argv: Sequence[str] | None = None,
    *,
    examples_dir: Path = EXAMPLES,
    opener: OpenerDirector | None = None,
    output: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        type=_base_url,
        default="http://127.0.0.1:8000/api",
        help="API root (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=_timeout,
        default=5.0,
        help="Socket timeout in seconds, >0 and <=60 (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    stream = output if output is not None else sys.stdout
    client = AnalysisClient(args.base_url, args.timeout, opener)
    try:
        cases = _examples(examples_dir)
        raw = client.request("GET", "/health")
        if (
            not isinstance(raw, dict)
            or raw.get("status") != "ok"
            or raw.get("service") != "q-atlas"
        ):
            raise CheckFailure("Health response must identify status=ok and service=q-atlas.")
        try:
            HealthResponse.model_validate(raw, strict=True)
        except ValidationError as exc:
            raise _validation_failure(exc) from None
    except CheckFailure as exc:
        print(f"FAIL setup/health: {exc}", file=stream)
        print("No source cases submitted. No execution endpoints requested.", file=stream)
        return 1
    print("PASS health: API ready; experiment readiness does not gate analysis.", file=stream)
    passed, total = 1, len(cases) + 2
    for filename, source, expected in [*cases, ("unsupported_call", REJECTED_SOURCE, None)]:
        try:
            _check_analysis(
                client.request("POST", "/compiler/analyze", {"source": source}), expected
            )
        except CheckFailure as exc:
            print(f"FAIL {filename}: {exc}", file=stream)
        else:
            passed += 1
            print(f"PASS {filename}", file=stream)
    print(
        f"{passed}/{total} analysis-only checks passed. No execution endpoints requested.",
        file=stream,
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
