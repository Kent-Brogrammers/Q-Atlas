"""Local experimental inputs, all in the normalized units defined in NEUTRINOS.md."""

from math import pi
from typing import Literal

from pydantic import Field

from app.schemas.contracts import Contract, Seed


class Parameters(Contract):
    theta: float = Field(default=0.2, ge=0, le=pi / 2)
    delta_m2: float = Field(default=1, ge=-10, le=10)
    energy: float = Field(default=1, ge=0.01, le=100)
    particle: Literal["neutrino", "antineutrino"] = "neutrino"


class Layer(Contract):
    distance: float = Field(ge=0, le=100)
    potential: float = Field(default=0, ge=0, le=10)


class Experiment(Contract):
    parameters: Parameters = Field(default_factory=Parameters)
    layers: list[Layer] = Field(min_length=1, max_length=64)
    shots: int = Field(default=4096, ge=1, le=100_000)
    seed: Seed = 42


class DensitySweep(Contract):
    experiment: Experiment
    potentials: list[float] = Field(min_length=1, max_length=41)
