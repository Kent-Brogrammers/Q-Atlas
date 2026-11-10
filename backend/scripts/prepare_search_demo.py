"""Rehearse the real search API and record an explicitly labeled offline demo."""

import argparse
import json
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas.contracts import SearchResult  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "frontend/src/lib/search/previously-measured.json"
SOURCE = "previously_measured_search_demo"


def validate_bundle(bundle: dict) -> None:
    """Check provenance and evidence before treating a file as recorded demo data."""
    if bundle.get("source") != SOURCE or bundle.get("bundle_version") != 1:
        raise ValueError("unrecognized recorded-demo format")
    recorded = datetime.fromisoformat(bundle["recorded_at_utc"])
    if recorded.tzinfo is None:
        raise ValueError("recording timestamp must include a timezone")
    if bundle.get("recording_method") != "local_fastapi_testclient":
        raise ValueError("recording method must identify the local API")
    hashes = bundle.get("source_sha256", {})
    environment = bundle.get("environment", {})
    if (
        not isinstance(bundle.get("source_revision"), str)
        or not bundle["source_revision"]
        or type(bundle.get("working_tree_dirty")) is not bool
        or not hashes
        or not isinstance(environment.get("python"), str)
        or not isinstance(environment.get("system"), str)
        or not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in hashes.values()
        )
    ):
        raise ValueError("recorded demo requires source revision and SHA-256 provenance")
    curve = [SearchResult.model_validate(item) for item in bundle["curve"]]
    trials = [SearchResult.model_validate(item) for item in bundle["trials"]]
    if len(curve) != 7 or len(trials) != 3:
        raise ValueError("demo requires seven curve points and three trials")
    for index, result in enumerate(curve):
        if result.metadata.parameters.iterations != index or result.metadata.seed != 42:
            raise ValueError("recorded curve must use iterations 0–6 with seed 42")
    for index, result in enumerate(trials):
        if result.metadata.parameters.iterations != 2 or result.metadata.seed != 42 + index:
            raise ValueError("recorded trials must use iteration 2 and seeds 42–44")
    for result in curve + trials:
        parameters = result.metadata.parameters
        if (
            parameters.num_qubits != 3
            or parameters.marked_states != ["001"]
            or result.metrics.shots != 1024
            or parameters.config.shots != 1024
            or parameters.config.seed != result.metadata.seed
        ):
            raise ValueError("unexpected demo configuration")
        if (
            result.metrics.successful_shots is None
            or result.classical is None
            or result.quantum is None
            or result.metrics.classical_observed_queries != 2
            or result.metrics.quantum_total_oracle_queries != parameters.iterations * 1024
            or not result.metadata.versions
        ):
            raise ValueError("recorded demo is missing measured evidence")
        if (
            result.metrics.success_probability != result.metrics.successful_shots / 1024
            or result.metadata.versions != curve[0].metadata.versions
            or result.problem_id != curve[0].problem_id
        ):
            raise ValueError("recorded demo evidence or versions are inconsistent")


def prepare_bundle(client: TestClient) -> dict:
    """All saved measurements come from the actual endpoint, never mock responses."""
    config = {"shots": 1024, "seed": 42, "timeout_seconds": 15}

    def run(width=3, targets=None, iterations=None, seed=42):
        response = client.post(
            "/api/search/run",
            json={
                "num_qubits": width,
                "marked_states": targets or ["001"],
                "iterations": iterations,
                "config": {**config, "seed": seed},
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Search demo failed: HTTP {response.status_code}: {response.text}")
        return SearchResult.model_validate(response.json()).model_dump(mode="json")

    curve = [run(iterations=index) for index in range(7)]
    trials = [run(iterations=2, seed=42 + index) for index in range(3)]
    for width, targets, iterations in [
        (2, ["01"], None),
        (3, ["001", "110"], None),
        (1, ["0", "1"], 0),
        (6, ["000001"], 32),
    ]:
        result = run(width, targets, iterations)
        if result["metrics"]["success_probability"] is None:
            raise RuntimeError("Search probe returned no measured probability")
    for patch in [{"marked_states": ["bad"]}, {"iterations": 33}, {"config": {"shots": 10001}}]:
        response = client.post(
            "/api/search/run",
            json={
                "num_qubits": 3,
                "marked_states": ["001"],
                **patch,
            },
        )
        if response.status_code != 422 or response.json()["error"]["code"] != "VALIDATION_ERROR":
            raise RuntimeError("Invalid-input regression check failed")
    response = client.post(
        "/api/search/run",
        json={
            "num_qubits": 3,
            "marked_states": ["001"],
            "config": {"timeout_seconds": 0.000001},
        },
    )
    if response.status_code != 504 or response.json()["error"]["code"] != "TIMEOUT":
        raise RuntimeError("Timeout regression check failed")

    def git(*arguments):
        result = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "unknown"

    source_paths = [
        *sorted((ROOT / "backend/app/experiments/search").glob("*.py")),
        ROOT / "backend/app/api/search.py",
        ROOT / "backend/app/schemas/contracts.py",
    ]
    bundle = {
        "bundle_version": 1,
        "source": SOURCE,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "recording_method": "local_fastapi_testclient",
        "source_revision": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        "environment": {"python": platform.python_version(), "system": platform.system()},
        "notice": (
            "Previously measured local simulator results; "
            "never present as a live run or quantum speedup."
        ),
        "regression_checks": {
            "curve": "passed",
            "trials": "passed",
            "multiple_targets": "passed",
            "boundary_sizes": "passed",
            "validation": "passed",
            "timeout": "passed",
        },
        "curve": curve,
        "trials": trials,
    }
    validate_bundle(bundle)
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify", action="store_true", help="Validate the saved file without simulation"
    )
    arguments = parser.parse_args()
    if arguments.verify:
        validate_bundle(json.loads(arguments.output.read_text(encoding="utf-8")))
        print("Recorded demo provenance and evidence validated; no simulation ran.")
        return
    with TestClient(app) as client:
        bundle = prepare_bundle(client)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    print(
        "Search API rehearsal passed: seven curve points, three trials, "
        "boundary/validation/timeout probes."
    )
    print(f"Previously measured demo saved to {arguments.output}")


if __name__ == "__main__":
    main()
