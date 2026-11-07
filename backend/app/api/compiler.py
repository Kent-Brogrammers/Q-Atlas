"""Developer 2: parse/validate only; never execute submitted source."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import not_implemented
from app.schemas.contracts import (
    CompilerAnalyzeRequest,
    CompilerAnalyzeResult,
    CompilerBenchmarkRequest,
    CompilerBenchmarkResult,
)

router = APIRouter(prefix="/compiler", tags=["compiler"])


@router.post("/analyze", response_model=CompilerAnalyzeResult)
def analyze(request: CompilerAnalyzeRequest) -> JSONResponse:
    return not_implemented("Compiler analysis", 2)


@router.post("/benchmark", response_model=CompilerBenchmarkResult)
def benchmark(request: CompilerBenchmarkRequest) -> JSONResponse:
    return not_implemented("Compiler benchmark", 2)
