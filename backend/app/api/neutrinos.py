"""Effective two-flavor simulation endpoint, in normalized units only."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.experiments.neutrinos.runner import NeutrinoDependencyError, run_neutrinos
from app.schemas.contracts import ErrorDetail, ErrorResponse
from app.schemas.neutrinos import NeutrinoRequest, NeutrinoResponse

router = APIRouter(prefix="/neutrinos", tags=["neutrinos"])


@router.post(
    "/run",
    response_model=NeutrinoResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Quantum dependencies unavailable"},
        504: {"model": ErrorResponse, "description": "Neutrino runtime budget exceeded"},
    },
)
def run(request: NeutrinoRequest) -> NeutrinoResponse | JSONResponse:
    try:
        return run_neutrinos(request)
    except TimeoutError:
        return error_response(
            504, ErrorDetail(code="TIMEOUT", message="Neutrino simulation timed out.")
        )
    except NeutrinoDependencyError:
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message="Install neutrino simulation dependencies: uv sync --locked --all-extras.",
            ),
        )
