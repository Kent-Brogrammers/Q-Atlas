"""Offline preparation artifacts. No source execution, solver calls, or provider access."""

import hashlib
import io
import json
import platform
from importlib.metadata import version
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from app.compiler.generation import generate_source
from app.compiler.pipeline import CompilationError, prepare_benchmark
from app.schemas.contracts import QAOAConfig


def build_preflight_bundle(source: str, config: QAOAConfig) -> bytes:
    """Freeze validated inputs and a nonexecuting plan in a reproducible ZIP.

    The bundle is evidence of compilation only. Its Python files remain untrusted
    text and must never be imported or executed by a preparation/review tool.
    Fixed archive paths and timestamps avoid caller-controlled extraction paths.
    """
    plan = prepare_benchmark(source, config)
    generated = generate_source(source, p=config.p)
    if generated.status != "supported":
        raise CompilationError(generated.diagnostics)
    generated_source = generated.artifact.source.encode("utf-8")
    if hashlib.sha256(generated_source).hexdigest() != plan.generated_source_sha256:
        raise ValueError("generation and planning disagree")
    files = {
        "input.py": source.encode("utf-8"),
        "generated.py": generated_source,
        "plan.json": (plan.model_dump_json(indent=2) + "\n").encode(),
        "README.txt": (
            b"Q-Atlas offline compiler preflight; no solver or quantum execution.\n"
            b"input.py and generated.py are source TEXT, not approved runnable applications.\n"
            b"Do not import or execute them. Preserved surrounding Python is not validated.\n"
            b"plan.json records canonical minimization, parameters, and disabled execution.\n"
            b"Bitstrings are x[0]-first; provider count strings need explicit mapping.\n"
            b"No angles, hardware settings, credentials, or performance results are included.\n"
            b"Follow docs/DEVELOPER_2_TESTING_DAY.md before any authorized execution.\n"
        ),
    }
    manifest = {
        "format_version": 1,
        "status": "prepared_not_executed",
        "problem_id": plan.problem_id,
        "versions": {"python": platform.python_version(), "pydantic": version("pydantic")},
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for name, data in files.items()
        },
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        for name, data in files.items():
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.external_attr = 0o600 << 16
            archive.writestr(entry, data)
    return buffer.getvalue()
