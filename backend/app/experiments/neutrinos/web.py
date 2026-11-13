"""Build measured curves by calling the validated local experiment at each point."""

import numpy as np

from app.experiments.neutrinos.experiment import run
from app.experiments.neutrinos.model import Experiment, Layer
from app.experiments.neutrinos.physics import coefficients
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse


def curve_points(request: NeutrinoRequest) -> list[tuple[float, Experiment]]:
    """The same validated point inputs for exported circuits and measured web curves."""
    experiment = request.experiment
    total = sum(layer.distance for layer in experiment.layers)
    extent = request.max_potential if request.axis == "potential" else total
    grid = np.linspace(0, extent, request.samples).tolist() if extent else [0.0]
    points = []
    for index, coordinate in enumerate(grid):
        if request.axis == "potential":
            layers = [Layer(distance=experiment.layers[0].distance, potential=coordinate)]
        else:
            remaining = coordinate
            layers = []
            for layer in experiment.layers:
                length = min(remaining, layer.distance)
                layers.append(Layer(distance=length, potential=layer.potential))
                remaining = max(0, remaining - length)
                if remaining == 0:
                    break
            if index == len(grid) - 1:
                layers = experiment.layers
        point = Experiment(
            parameters=experiment.parameters,
            layers=layers,
            shots=experiment.shots,
            seed=(experiment.seed + index) % 2**32,
        )
        points.append((coordinate, point))
    return points


def run_curve(request: NeutrinoRequest) -> NeutrinoResponse:
    experiment = request.experiment
    points = curve_points(request)
    grid = [coordinate for coordinate, _ in points]
    results = [run(point) for _, point in points]
    parameters = experiment.parameters
    _, vacuum_z = coefficients(parameters, 0)
    sign = 1 if parameters.particle == "neutrino" else -1
    resonance = -sign * vacuum_z
    has_resonance = (
        0 < parameters.theta < np.pi / 2 and parameters.theta != np.pi / 4 and resonance > 0
    )
    return NeutrinoResponse(
        axis=request.axis,
        coordinates=grid,
        results=results,
        resonance_potential=float(resonance) if has_resonance else None,
    )
