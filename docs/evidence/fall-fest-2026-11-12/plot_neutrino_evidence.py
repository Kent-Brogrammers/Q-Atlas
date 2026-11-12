"""Render saved festival evidence; performs no simulation or hardware access.

Run from the repository root with backend/.venv/bin/python and a writable
MPLCONFIGDIR. Requires the existing optional benchmarks extra (matplotlib).
"""

import json
from pathlib import Path
from statistics import median

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


def main():
    directory = Path(__file__).resolve().parent
    report = json.loads((directory / "neutrino-resonance.json").read_text())
    runs = report["runs"]
    coordinates = runs[0]["response"]["coordinates"]
    reference = [
        point["numerical"]["other"] for point in runs[0]["response"]["results"]
    ]
    colors = {256: "#bf6c17", 1024: "#137d89", 4096: "#5b48ab"}
    fig, (curve, error) = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
    curve.plot(
        coordinates, reference, color="#202f43", label="Independent SciPy reference"
    )
    for shots, color in colors.items():
        selected = [
            run for run in runs if run["request"]["experiment"]["shots"] == shots
        ]
        assert len(selected) == 3
        assert all(run["response"]["coordinates"] == coordinates for run in selected)
        values = [
            [run["response"]["results"][i]["measured"]["other"] for run in selected]
            for i in range(len(coordinates))
        ]
        medians = [median(group) for group in values]
        curve.errorbar(
            coordinates,
            medians,
            yerr=[
                [
                    middle - min(group)
                    for middle, group in zip(medians, values, strict=True)
                ],
                [
                    max(group) - middle
                    for middle, group in zip(medians, values, strict=True)
                ],
            ],
            fmt="o",
            capsize=3,
            markersize=4,
            color=color,
            label=f"{shots} shots: median and range, 3 seeds",
        )
        errors = [
            point["absolute_errors"]["sampling"]["other"]
            for run in selected
            for i, point in enumerate(run["response"]["results"])
            if i != 4
        ]
        error.scatter([shots] * len(errors), errors, color=color, alpha=0.35, s=20)
        error.scatter(
            shots, median(errors), color=color, marker="D", s=65, edgecolor="black"
        )
    curve.axvline(coordinates[4], color="#555555", linestyle=":", linewidth=1)
    curve.set(
        title="Matter-enhanced flavor conversion",
        xlabel="Matter potential (normalized units)",
        ylabel="Electron-to-other conversion probability",
        ylim=(-0.035, 1.07),
    )
    curve.legend(fontsize=8, loc="upper left")
    error.set_xscale("log", base=2)
    error.set_xticks(list(colors), [str(shots) for shots in colors])
    error.set(
        title="Finite-shot error away from resonance",
        xlabel="Shots per point",
        ylabel="Absolute measured-minus-ideal probability",
    )
    error.text(
        0.98,
        0.97,
        "Dots: 8 coordinates x 3 seeds\nDiamonds: pooled medians\nDescriptive values, not confidence intervals",
        transform=error.transAxes,
        va="top",
        ha="right",
        fontsize=8,
    )
    for axis in (curve, error):
        axis.grid(alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        "Q-Atlas | Previously measured local Aer simulation | 12 Nov 2026\n"
        "1 qubit; theta=0.2; splitting/energy=1; distance=4.033699; no QPU or speedup claim",
        fontsize=11,
    )
    fig.savefig(directory / "neutrino-resonance.png", dpi=180)
    fig.savefig(directory / "neutrino-resonance.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
