"""Developer 4: Grover and classical search boundary."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented
from app.schemas.contracts import SearchRequest, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/run", response_model=SearchResult)
def run(request: SearchRequest) -> JSONResponse:
    return not_implemented("Search benchmark", 4)
