"""Developer 2: parse/validate only; never execute submitted source."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response, not_implemented
from app.compiler.analysis import analyze_source
from app.compiler.generation import generate_source
from app.compiler.pipeline import CompilationError, benchmark_source
from app.schemas.contracts import (
    CompilerAnalyzeRequest,
    CompilerAnalyzeResult,
    CompilerBenchmarkRequest,
    CompilerBenchmarkResult,
    CompilerGenerateRequest,
    CompilerGenerateResult,
    ErrorDetail,
    ErrorResponse,
)

router = APIRouter(prefix="/compiler", tags=["compiler"])


@router.post("/analyze", response_model=CompilerAnalyzeResult)
def analyze(request: CompilerAnalyzeRequest) -> CompilerAnalyzeResult:
    return analyze_source(request.source)


@router.post("/generate", response_model=CompilerGenerateResult)
def generate(request: CompilerGenerateRequest) -> CompilerGenerateResult:
    return generate_source(request.source, request.p)


@router.post(
    "/benchmark",
    response_model=CompilerBenchmarkResult,
    responses={504: {"model": ErrorResponse, "description": "Solver runtime budget exceeded"}},
)
def benchmark(request: CompilerBenchmarkRequest) -> CompilerBenchmarkResult | JSONResponse:
    try:
        return benchmark_source(request.source, request.config)
    except CompilationError as exc:
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Source is outside the supported compiler subset.",
                diagnostics=exc.diagnostics,
            ),
        )
    except NotImplementedError:
        return not_implemented("Shared compiler benchmark solvers", 3)
    except TimeoutError:
        return error_response(
            504,
            ErrorDetail(code="TIMEOUT", message="A shared solver exceeded its runtime budget."),
        )
