"""Atomic publication shared by local benchmark evidence and review documents."""

import os
import tempfile
from pathlib import Path


def write_text_exclusive(content: str, destination: Path) -> None:
    """Publish complete UTF-8 text while preserving an existing destination."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".neutrino-benchmark-",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
