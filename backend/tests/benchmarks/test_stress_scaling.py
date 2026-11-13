"""Synthetic timing fixtures verify aggregation, never presented as measurements."""

import csv
import json

import pytest

from scripts import benchmark_stress_examples as stress


@pytest.fixture
def fake_measure(monkeypatch):
    calls = []

    def measure(graph, config, source):
        calls.append((graph.num_vertices, config.p, config.seed, source["instance"]))
        base = graph.num_vertices + config.seed
        return {
            "comparison": {
                "classical": {"elapsed_ms": base},
                "quantum": {"elapsed_ms": 2 * base},
                "metrics": {
                    "optimality_gap": config.seed,
                    "circuit_depth": len(graph.edges) * config.p * 2,
                },
            },
            "heuristic": {"elapsed_ms": base / 10},
            "heuristic_optimality_gap": 0,
        }

    monkeypatch.setattr(stress, "measure_case", measure)
    return calls


def test_sweep_runs_equal_batches_and_exports_measured_aggregates(fake_measure, tmp_path):
    output = tmp_path / "scaling.json"
    assert (
        stress.main(
            [
                "--sizes",
                "6",
                "8",
                "--layers",
                "1",
                "2",
                "--seeds",
                "1",
                "3",
                "--instances",
                "2",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    record = json.loads(output.read_text())
    assert len(fake_measure) == 16
    assert len(record["batches"]) == 8
    assert len(record["summary"]) == 4
    row = record["summary"][0]
    assert (row["qubits"], row["p"], row["instances"], row["repetitions"]) == (6, 1, 2, 2)
    assert row["exact_ms"] == 16  # Median of the matched sums 14 and 18.
    assert row["exact_ms_min"] == 14 and row["exact_ms_max"] == 18
    assert row["qaoa_ms"] == 32 and row["heuristic_ms"] == pytest.approx(1.6)
    assert row["pair_gates"] == 15 and row["circuit_depth"] == 30
    assert record["simulated"] is True
    with output.with_suffix(".csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 4


def test_failed_batch_retains_partial_evidence_without_zero_timings(
    fake_measure, monkeypatch, tmp_path
):
    original = stress.measure_case

    def timeout_second(graph, config, source):
        if source["instance"] == 1:
            raise TimeoutError("synthetic deadline")
        return original(graph, config, source)

    monkeypatch.setattr(stress, "measure_case", timeout_second)
    output = tmp_path / "failed.json"
    assert stress.main(["--sizes", "6", "--instances", "2", "--output", str(output)]) == 1
    report = json.loads(output.read_text())
    assert report["summary"] == []
    batch = report["batches"][0]
    assert batch["status"] == "failed" and len(batch["runs"]) == 1
    assert "exact_ms" not in batch
    assert not output.with_suffix(".csv").exists()


def test_plot_contains_exportable_png_and_svg(fake_measure, tmp_path):
    pytest.importorskip("matplotlib")
    output = tmp_path / "plot-data.json"
    prefix = tmp_path / "scaling"
    assert stress.main(["--sizes", "6", "8", "--plot", str(prefix), "--output", str(output)]) == 0
    assert prefix.with_suffix(".png").read_bytes().startswith(b"\x89PNG")
    assert "<svg" in prefix.with_suffix(".svg").read_text()


@pytest.mark.parametrize(
    "options",
    [
        ["--sizes", "6", "6"],
        ["--sizes", "6", "--seeds", "7", "7"],
        ["--sizes", "6", "--instances", "9"],
        ["--sizes", "18"],
    ],
)
def test_invalid_sweeps_fail_before_measurement(fake_measure, tmp_path, options):
    with pytest.raises(SystemExit):
        stress.main([*options, "--output", str(tmp_path / "unused.json")])
    assert fake_measure == []
