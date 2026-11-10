"""Developer 2: safe conversion and opt-in solver comparison; never execute source."""

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response, not_implemented
from app.compiler.analysis import analyze_source
from app.compiler.generation import generate_source
from app.compiler.pipeline import CompilationError, benchmark_source, prepare_benchmark
from app.schemas.contracts import (
    CompilerAnalyzeRequest,
    CompilerAnalyzeResult,
    CompilerBenchmarkPlan,
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


@router.post("/benchmark/plan", response_model=CompilerBenchmarkPlan)
def benchmark_plan(request: CompilerBenchmarkRequest) -> CompilerBenchmarkPlan | JSONResponse:
    try:
        return prepare_benchmark(request.source, request.config)
    except CompilationError as exc:
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Source is outside the supported compiler subset.",
                diagnostics=exc.diagnostics,
            ),
        )


@router.post(
    "/benchmark",
    response_model=CompilerBenchmarkResult,
    responses={504: {"model": ErrorResponse, "description": "Solver runtime budget exceeded"}},
)
def benchmark(request: CompilerBenchmarkRequest) -> CompilerBenchmarkResult | JSONResponse:
    try:
        # A new shared runner must not turn compilation-only deployments into executors.
        # Validate first so unsupported source retains its ordinary diagnostic response.
        if os.environ.get("QATLAS_ENABLE_COMPILER_AER") != "1":
            prepare_benchmark(request.source, request.config)
            return error_response(
                501,
                ErrorDetail(
                    code="NOT_IMPLEMENTED",
                    message="Compiler comparison execution is disabled on this server. "
                    "Source conversion and comparison planning remain available.",
                ),
            )
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
    except ImportError:
        return error_response(
            501,
            ErrorDetail(
                code="NOT_IMPLEMENTED",
                message="Compiler Aer comparison requires the backend quantum dependencies.",
            ),
        )
    except TimeoutError:
        return error_response(
            504,
            ErrorDetail(code="TIMEOUT", message="A shared solver exceeded its runtime budget."),
        )
