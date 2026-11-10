"""Developer 4: Grover and classical search boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.experiments.search.runner import SearchDependencyError, run_search
from app.experiments.search.settings import request_diagnostics
from app.schemas.contracts import ErrorDetail, ErrorResponse, SearchRequest, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/run",
    response_model=SearchResult,
    responses={
        503: {"model": ErrorResponse, "description": "Quantum dependencies unavailable"},
        504: {"model": ErrorResponse, "description": "Search runtime budget exceeded"},
    },
)
def run(request: SearchRequest) -> SearchResult | JSONResponse:
    """Compare local Grover simulation with classical search on the same targets."""
    if diagnostics := request_diagnostics(request):
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Unsupported search parameters.",
                diagnostics=diagnostics,
            ),
        )
    try:
        return run_search(request)
    except TimeoutError:
        return error_response(
            504,
            ErrorDetail(code="TIMEOUT", message="Search exceeded config.timeout_seconds."),
        )
    except SearchDependencyError:
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message="Search requires the backend quantum extra: uv sync --locked --all-extras.",
            ),
        )
