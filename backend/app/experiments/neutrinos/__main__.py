"""Run reproducible vacuum, density, and layered examples as JSON on stdout."""

import argparse
import json
from math import cos, pi, sin

import numpy as np

from app.experiments.neutrinos.experiment import density_sweep, run
from app.experiments.neutrinos.model import Experiment, Layer, Parameters


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["vacuum", "resonance", "layers"])
    parser.add_argument("--theta", type=float, default=0.2, help="mixing angle in radians")
    parser.add_argument(
        "--delta-m2", type=float, default=1, help="signed normalized mass splitting"
    )
    parser.add_argument("--energy", type=float, default=1, help="normalized energy")
    parser.add_argument("--distance", type=float, default=None, help="total normalized distance")
    parser.add_argument("--particle", choices=["neutrino", "antineutrino"], default="neutrino")
    parser.add_argument(
        "--potentials",
        type=float,
        nargs="+",
        default=None,
        help="density grid for resonance, or two potentials for equal-length layers",
    )
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        parameters = Parameters(
            theta=args.theta, delta_m2=args.delta_m2, energy=args.energy, particle=args.particle
        )
        distance = 1.0 if args.distance is None else args.distance
        if args.mode == "resonance":
            sign = 1 if args.particle == "neutrino" else -1
            resonance = sign * parameters.delta_m2 / parameters.energy * cos(2 * parameters.theta)
            frequency = abs(parameters.delta_m2 / parameters.energy * sin(2 * parameters.theta))
            if resonance <= 0 or frequency < 1e-12:
                raise ValueError(
                    "this demo requires a positive-density resonance and nonzero mixing"
                )
            distance = pi / (2 * frequency) if args.distance is None else args.distance
            grid = (
                args.potentials
                if args.potentials is not None
                else np.linspace(0, 2 * resonance, 21).tolist()
            )
            e = Experiment(
                parameters=parameters,
                layers=[Layer(distance=distance)],
                shots=args.shots,
                seed=args.seed,
            )
            output = {"resonance_potential": resonance, "results": density_sweep(e, grid)}
        else:
            potentials = (
                [0]
                if args.mode == "vacuum"
                else (args.potentials if args.potentials is not None else [0.2, 1.4])
            )
            if args.mode == "vacuum" and args.potentials is not None:
                raise ValueError("vacuum mode does not accept matter potentials")
            if args.mode == "layers" and len(potentials) != 2:
                raise ValueError("the layers demo needs exactly two potentials")
            output = run(
                Experiment(
                    parameters=parameters,
                    shots=args.shots,
                    seed=args.seed,
                    layers=[
                        Layer(distance=distance / len(potentials), potential=v) for v in potentials
                    ],
                )
            )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
