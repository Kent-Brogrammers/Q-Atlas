"""Allowlisted science declarations reuse the Neutrino Lab and its worker deadline."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.api.neutrinos import run
from app.compiler.analysis import Rejected
from app.compiler.neutrinos import compile_neutrino, parse_neutrino
from app.schemas.compiler_neutrinos import CompiledNeutrino, NeutrinoSource
from app.schemas.contracts import ErrorDetail
from app.schemas.neutrinos import NeutrinoResponse

router = APIRouter(prefix="/neutrinos", tags=["compiler"])


def rejected(exc):
    return error_response(
        422,
        ErrorDetail(
            code="VALIDATION_ERROR", message=exc.diagnostic.message, diagnostics=[exc.diagnostic]
        ),
    )


@router.post("/generate", response_model=CompiledNeutrino)
def generate(request: NeutrinoSource) -> CompiledNeutrino | JSONResponse:
    try:
        return compile_neutrino(request.source)
    except Rejected as exc:
        return rejected(exc)
    except ImportError:
        return error_response(
            501,
            ErrorDetail(
                code="NOT_IMPLEMENTED",
                message="Install the locked quantum dependencies to generate neutrino circuits.",
            ),
        )


@router.post("/benchmark", response_model=NeutrinoResponse)
def benchmark(request: NeutrinoSource) -> NeutrinoResponse | JSONResponse:
    try:
        experiment = parse_neutrino(request.source)
    except Rejected as exc:
        return rejected(exc)
    return run(experiment)
