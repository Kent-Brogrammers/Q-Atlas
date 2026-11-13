"""Package a fixed whitelist of reports/evidence; never include credentials or caches."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[2]
    documents = [
        "FINAL_SCIENCE_REPORT.md",
        "PRESENTATION_RUNBOOK.md",
        "PRESENTATION_READINESS.md",
        "USABILITY_AUDIT.md",
        "IBM_HARDWARE_ALL_EXPERIMENTS.md",
        "NEUTRINOS.md",
        "MATERIALS.md",
        "COMPILER.md",
        "BENCHMARK_METHODOLOGY.md",
        "SCIENTIFIC_HYPOTHESIS.md",
    ]
    physical = [
        "five-experiments.json",
        "provenance.json",
        "RESULTS.md",
        "final-results.png",
        "final-results.svg",
        "executed-circuits.qpy",
        "executed-circuits.json",
        "statistical-summary.json",
        "ideal-materials-reference.json",
        "plot_final_results.py",
        "browser-verification.json",
        "final-presentation-verification.json",
    ]
    local = ["neutrino-resonance.json", "neutrino-resonance.png", "provenance.json"]
    paths = [root / "docs" / name for name in documents]
    paths += [root / "docs/evidence/ibm-qpu-2026-11-12" / name for name in physical]
    paths += [root / "docs/evidence/fall-fest-2026-11-12" / name for name in local]
    paths.append(root / "docs/evidence/usability-audit-2026-11-12.json")
    paths.append(root / "docs/evidence/simplified-workflows-2026-11-12.json")
    paths.append(root / "docs/evidence/larger-workload-2026-11-12.json")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing presentation artifact: {path.name}")
    destination = root / "frontend/static/q-atlas-presentation.zip"
    manifest = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, str(path.relative_to(root)))
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
        archive.writestr(
            "START_HERE.txt",
            (
                "Q-Atlas presentation evidence\n\n"
                "Read docs/FINAL_SCIENCE_REPORT.md and docs/PRESENTATION_RUNBOOK.md.\n"
                "Figure: docs/evidence/ibm-qpu-2026-11-12/final-results.png\n"
                "Raw measurements and exact executed circuits are in the same folder.\n"
                "This pack contains evidence only; app source is in the Q-Atlas repo.\n"
                "No environment file, credentials, SDK account or local cache is included.\n"
            ),
        )
    print(f"Prepared presentation ZIP: {len(paths)} artifacts, {destination.stat().st_size} bytes")


if __name__ == "__main__":
    main()
