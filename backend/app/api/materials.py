"""Developer 1: spin simulation and exact reference boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.experiments.materials.runner import (
    MaterialsDependencyError,
    request_diagnostics,
    run_materials,
)
from app.schemas.contracts import ErrorDetail, ErrorResponse, MaterialsRequest, MaterialsResult

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post(
    "/run",
    response_model=MaterialsResult,
    responses={
        503: {"model": ErrorResponse, "description": "Quantum dependencies unavailable"},
        504: {"model": ErrorResponse, "description": "Materials runtime budget exceeded"},
    },
)
def run(request: MaterialsRequest) -> MaterialsResult | JSONResponse:
    diagnostics = request_diagnostics(request)
    if diagnostics:
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Unsupported materials parameters.",
                diagnostics=diagnostics,
            ),
        )
    try:
        return run_materials(request)
    except TimeoutError:
        return error_response(
            504,
            ErrorDetail(
                code="TIMEOUT",
                message="Materials simulation exceeded config.timeout_seconds.",
            ),
        )
    except MaterialsDependencyError:
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message=(
                    "Materials requires the backend quantum extra: uv sync --locked --all-extras."
                ),
            ),
        )
