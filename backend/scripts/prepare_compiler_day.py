"""Run from backend/: python -m scripts.prepare_compiler_day SOURCE --output BUNDLE.zip."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from app.compiler.pipeline import CompilationError
from app.compiler.preflight import build_preflight_bundle
from app.schemas.contracts import QAOAConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare compiler evidence without execution.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p", type=int, default=1)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        config = QAOAConfig(p=args.p, shots=args.shots, seed=args.seed)
        with args.source.open("rb") as handle:
            data = handle.read(80_001)
        if len(data) > 80_000:
            raise ValueError("source exceeds the 80,000-byte file limit")
        source = data.decode("utf-8")
        if not source.strip() or len(source) > 20_000:
            raise ValueError("source must contain 1–20,000 characters")
        bundle = build_preflight_bundle(source, config)
        # Never replace a frozen artifact, including a symlink to another file.
        with args.output.open("xb") as handle:
            handle.write(bundle)
    except CompilationError as error:
        codes = ", ".join(sorted({diagnostic.code for diagnostic in error.diagnostics}))
        print(f"REJECTED: {codes}. Use the compiler UI for source diagnostics.")
        return 1
    except (OSError, UnicodeError, ValueError, ValidationError):
        print("FAILED: check input size/UTF-8, settings, and a writable, unused output path.")
        return 1
    print("Prepared offline bundle. No source, generated code, solver, or quantum job executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
