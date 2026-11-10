"""Run from backend/: uv run uvicorn app.main:app --reload --port 8000."""

import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import compiler, materials, optimization, search
from app.api.errors import register_error_handlers
from app.schemas.contracts import ErrorResponse, HealthResponse

app = FastAPI(
    title="Q-Atlas API",
    version="0.1.0",
    description=(
        "Local experiments API. Materials TFIM is available; other experiments return HTTP 501."
    ),
    responses={
        code: {"model": ErrorResponse, "description": description}
        for code, description in {
            422: "Request validation failed",
            501: "Feature not implemented",
            500: "Internal error",
            404: "Route not found",
            405: "Method not allowed",
        }.items()
    },
)
origins = os.getenv("QATLAS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
register_error_handlers(app)
api = APIRouter(prefix="/api")


@api.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    # API readiness only; this does not claim the quantum engines are implemented.
    return HealthResponse()


for router in (compiler.router, materials.router, optimization.router, search.router):
    api.include_router(router)
app.include_router(api)
