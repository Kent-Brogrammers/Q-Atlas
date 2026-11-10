"""Build measured curves by calling the validated local experiment at each point."""

import numpy as np

from app.experiments.neutrinos.experiment import density_sweep, run
from app.experiments.neutrinos.model import Experiment, Layer
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


def run_curve(request: NeutrinoRequest) -> NeutrinoResponse:
    experiment = request.experiment
    total = sum(layer.distance for layer in experiment.layers)
    extent = request.max_potential if request.axis == "potential" else total
    grid = np.linspace(0, extent, request.samples).tolist() if extent else [0.0]
    if request.axis == "potential":
        results = density_sweep(experiment, grid)
    else:
        results = []
        for index, distance in enumerate(grid):
            remaining = distance
            layers = []
            for layer in experiment.layers:
                length = min(remaining, layer.distance)
                layers.append(Layer(distance=length, potential=layer.potential))
                remaining = max(0, remaining - length)
                if remaining == 0:
                    break
            # Retain the exact input baseline at the last point despite summation roundoff.
            if index == len(grid) - 1:
                layers = experiment.layers
            point = Experiment(
                parameters=experiment.parameters,
                layers=layers,
                shots=experiment.shots,
                seed=(experiment.seed + index) % 2**32,
            )
            results.append(run(point))
    return NeutrinoResponse(axis=request.axis, coordinates=grid, results=results)
