"""Developer 3: shared QAOA and classical optimization boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented
from app.schemas.contracts import OptimizationRequest, OptimizationResult

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("/run", response_model=OptimizationResult)
def run(request: OptimizationRequest) -> JSONResponse:
    return not_implemented("Optimization benchmark", 3)
