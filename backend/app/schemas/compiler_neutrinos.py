"""Additive scientific compiler contracts; QUBO compilation retains its contract."""

from pydantic import Field

from app.schemas.contracts import Contract, GeneratedPythonArtifact
from app.schemas.neutrinos import NeutrinoRequest


class NeutrinoSource(Contract):
    source: str = Field(min_length=1, max_length=20_000)


class CompiledNeutrino(Contract):
    request: NeutrinoRequest
    artifact: GeneratedPythonArtifact
    circuit_diagram: str
    method: str = "Validated neutrino declaration → exact layer rotations; no QAOA or QUBO"
