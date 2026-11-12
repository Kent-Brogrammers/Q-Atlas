"""Optional backend-only IBM settings; dotenv contents are data, never shell code."""

import os
import re
import shlex
from collections.abc import Iterable, MutableMapping
from pathlib import Path

TOKEN_NAMES = ("QUANTUM-KEY", "QATLAS_QUANTUM_KEY")
INSTANCE_NAMES = ("QATLAS_IBM_INSTANCE", "QUANTUM-CDN")


def load_quantum_env(
    *,
    environ: MutableMapping[str, str] | None = None,
    paths: Iterable[Path] | None = None,
) -> None:
    """Load only optional quantum settings, preserving existing environment values.

    The repository .env takes priority over backend/.env. QUANTUM-CDN is an alias
    for the IBM instance name/CRN. Missing, unreadable or malformed entries are
    ignored; no values or file contents are logged, interpolated or executed.
    """
    env = os.environ if environ is None else environ
    root = Path(__file__).resolve().parents[2]
    candidates = (root / ".env", root / "backend/.env") if paths is None else paths
    allowed = set(TOKEN_NAMES + INSTANCE_NAMES)
    values: dict[str, str] = {}
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        for line in content.splitlines():
            match = re.fullmatch(r"\s*(?:export\s+)?([\w-]+)\s*=\s*(.*?)\s*", line)
            if not match or match[1] not in allowed:
                continue
            raw = match[2]
            if raw.startswith(("'", '"')):
                try:
                    parts = shlex.split(raw, comments=True)
                except ValueError:
                    continue
                if len(parts) != 1:
                    continue
                value = parts[0]
            else:
                value = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
            if value:
                target = "QATLAS_QUANTUM_KEY" if match[1] in TOKEN_NAMES else "QATLAS_IBM_INSTANCE"
                values.setdefault(target, value)
    for names, target in (
        (TOKEN_NAMES, "QATLAS_QUANTUM_KEY"),
        (INSTANCE_NAMES, "QATLAS_IBM_INSTANCE"),
    ):
        if any(name in env for name in names):
            continue
        if target in values:
            env[target] = values[target]
