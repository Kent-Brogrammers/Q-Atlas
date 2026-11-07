"""Developer 1: spin simulation and exact reference boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented
from app.schemas.contracts import MaterialsRequest, MaterialsResult

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("/run", response_model=MaterialsResult)
def run(request: MaterialsRequest) -> JSONResponse:
    return not_implemented("Materials benchmark", 1)
