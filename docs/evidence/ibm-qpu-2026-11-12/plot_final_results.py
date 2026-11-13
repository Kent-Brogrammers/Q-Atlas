"""Render recorded physical measurements; no API, credentials or quantum jobs.

From the repository root:
MPLCONFIGDIR=/tmp/qatlas-matplotlib backend/.venv/bin/python \
    docs/evidence/ibm-qpu-2026-11-12/plot_final_results.py
"""

import hashlib
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binomtest

matplotlib.use("Agg")


def wilson(successes, shots):
    result = binomtest(successes, shots).proportion_ci(method="wilson")
    return [float(result.low), float(result.high)]


def mean_standard_error(counts, observation):
    shots = sum(counts.values())
    mean = sum(count * observation(bits) for bits, count in counts.items()) / shots
    variance = sum(
        count * (observation(bits) - mean) ** 2 for bits, count in counts.items()
    )
    return mean, float(np.sqrt(variance / (shots - 1) / shots))


def main():
    directory = Path(__file__).resolve().parent
    source = directory / "five-experiments.json"
    parent = json.loads(source.read_text())
    assert parent["measurement_complete"] and parent["simulated"] is False
    records = {record["task"]["kind"]: record for record in parent["children"]}
    search, neutrinos, materials = [
        records[k] for k in ("search", "neutrinos", "materials")
    ]
    shots = search["shots"]
    marked = search["task"]["parameters"]["marked_states"]
    successes = sum(
        count for bits, count in search["counts"][0].items() if bits[::-1] in marked
    )
    probability = successes / shots
    search_ci = wilson(successes, shots)
    coordinates = neutrinos["classical_reference"]["coordinates"]
    exact = [
        point["other"] for point in neutrinos["classical_reference"]["probabilities"]
    ]
    converted = [counts.get("1", 0) for counts in neutrinos["counts"]]
    measured = [count / neutrinos["shots"] for count in converted]
    intervals = [wilson(count, neutrinos["shots"]) for count in converted]
    z, x = materials["counts"]
    parameters = materials["task"]["parameters"]
    width, coupling, field = (
        parameters["num_spins"],
        parameters["coupling"],
        parameters["field"],
    )

    def spins(bits):
        return np.array([1 if bit == "0" else -1 for bit in bits[::-1]])

    magnetization, mz_se = mean_standard_error(
        z, lambda bits: float(np.mean(spins(bits)))
    )
    energy_z, ez_se = mean_standard_error(
        z, lambda bits: float(-coupling * np.sum(spins(bits)[:-1] * spins(bits)[1:]))
    )
    energy_x, ex_se = mean_standard_error(
        x, lambda bits: float(-field * np.sum(spins(bits)))
    )
    assert width == 2
    energy = energy_z + energy_x
    energy_se = float(np.hypot(ez_se, ex_se))
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    ax = axes[0, 0]
    values = [1, search["classical_reference"]["ideal_success"], probability]
    ax.bar([0, 1, 2], values, color=["#77818e", "#318c8c", "#6653b6"])
    ax.errorbar(
        [2],
        [probability],
        yerr=[[probability - search_ci[0]], [search_ci[1] - probability]],
        fmt="none",
        color="black",
        capsize=5,
    )
    ax.set(
        xticks=[0, 1, 2],
        xticklabels=[
            "Classical\ncompleted search",
            "Ideal Grover\nprediction",
            "Physical QPU\n109 / 128",
        ],
        ylim=(0, 1.12),
        ylabel="Marked-state success probability",
        title="Search: distinguish theory and physical outcomes",
    )
    ax = axes[0, 1]
    ax.plot(
        coordinates, exact, "o-", color="#77818e", label="Independent exact reference"
    )
    ax.errorbar(
        coordinates,
        measured,
        yerr=[
            [p - ci[0] for p, ci in zip(measured, intervals, strict=True)],
            [ci[1] - p for p, ci in zip(measured, intervals, strict=True)],
        ],
        fmt="o",
        color="#6653b6",
        capsize=5,
        label="Physical QPU, 128 shots per point",
    )
    ax.set(
        xlabel="Matter potential (normalized)",
        ylabel="Electron-to-other conversion",
        ylim=(-0.04, 1.12),
        title="Neutrinos: matter-enhanced conversion",
    )
    ax.legend(fontsize=8)
    ax = axes[1, 0]
    reference = materials["classical_reference"]["observables"][0]
    positions = np.arange(2)
    ax.bar(
        positions - 0.18,
        [reference["magnetization_z"], reference["energy"]],
        width=0.36,
        color="#77818e",
        label="Exact reference",
    )
    ax.bar(
        positions + 0.18,
        [magnetization, energy],
        width=0.36,
        color="#6653b6",
        label="Physical QPU",
    )
    ax.errorbar(
        positions + 0.18,
        [magnetization, energy],
        yerr=1.96 * np.array([mz_se, energy_se]),
        fmt="none",
        color="black",
        capsize=5,
    )
    ax.set(
        xticks=positions,
        xticklabels=["Mean Z\nmagnetization", "Total energy"],
        ylabel="Dimensionless observable",
        title="Materials: two-spin dynamics at t=1",
    )
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    ax.axis("off")
    ax.set_title("Optimization and complete resource accounting")
    ax.text(
        0.02,
        0.97,
        "Compiler objective: exact 3; QPU best 3; gap 0\nTriangle Max-Cut: exact -2; QPU best -2; gap 0\n\nBest samples are not mean objective values.\n\n8 circuits, 1024 shots, one shared physical job\nProvider usage: 2.0 s for the entire job\nClassical references: 8.690 ms total\nLocal angle training: 1.449 s\n\nNo practical quantum speedup established.",
        va="top",
        transform=ax.transAxes,
        fontsize=11,
        linespacing=1.5,
    )
    for ax in axes.flat[:3]:
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        "Q-Atlas | Real IBM QPU measurements on ibm_marrakesh\n"
        "Job dbr0sthabdes73fp2v60 | Previously measured, not a new run\n"
        "Error bars: conditional 95% shot intervals; exclude device bias, drift and model error",
        fontsize=12,
    )
    fig.savefig(directory / "final-results.png", dpi=180)
    fig.savefig(directory / "final-results.svg")
    plt.close(fig)
    summary = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "job_id": parent["job_id"],
        "search_successes": successes,
        "search_shots": shots,
        "search_wilson_95": search_ci,
        "neutrino_coordinates": coordinates,
        "neutrino_successes": converted,
        "neutrino_wilson_95": intervals,
        "materials_magnetization": magnetization,
        "materials_magnetization_se": mz_se,
        "materials_energy": energy,
        "materials_energy_se": energy_se,
        "uncertainty_scope": "Wilson 95% binomial intervals for probabilities. Materials bars use approximate 95% mean intervals from joint-shot sample variances and independent Z/X batches. These conditional sampling intervals do not include device bias, drift, Trotter or model uncertainty. One device job is not an independent repetition study.",
    }
    (directory / "statistical-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
