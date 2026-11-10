"""Developer 3: shared QAOA and classical optimization boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.experiments.optimization.experiment import run_optimization
from app.experiments.optimization.maxcut import MaxCutConversionError
from app.schemas.contracts import (
    ErrorDetail,
    ErrorResponse,
    OptimizationRequest,
    OptimizationResult,
)

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post(
    "/run",
    response_model=OptimizationResult,
    responses={
        503: {"model": ErrorResponse, "description": "Quantum dependencies unavailable"},
        504: {"model": ErrorResponse, "description": "Solver runtime budget exceeded"},
    },
)
def run(request: OptimizationRequest) -> OptimizationResult | JSONResponse:
    """Compare an exact classical solve and local Aer QAOA on a graph or QUBO."""
    try:
        return run_optimization(request)
    except MaxCutConversionError:
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Max-Cut coefficients overflow. Rescale the graph edge weights.",
            ),
        )
    except TimeoutError:
        return error_response(
            504,
            ErrorDetail(code="TIMEOUT", message="A shared solver exceeded config.timeout_seconds."),
        )
    except ImportError:
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message=(
                    "Optimization requires the backend quantum extra. "
                    "Run uv sync --locked --all-extras."
                ),
            ),
        )
