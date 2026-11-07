"""Structured failures without leaking source input or exception internals."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.contracts import Diagnostic, ErrorDetail, ErrorResponse


def error_response(status_code: int, error: ErrorDetail) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=ErrorResponse(error=error).model_dump(mode="json")
    )


def not_implemented(feature: str, owner: int) -> JSONResponse:
    return error_response(
        501,
        ErrorDetail(
            code="NOT_IMPLEMENTED",
            message=f"{feature} is not implemented. Developer {owner} owns this feature.",
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Deliberately omit Pydantic's input and ctx: they may contain submitted source.
        diagnostics = [
            Diagnostic(
                code=error["type"],
                message=f"{'.'.join(map(str, error['loc']))}: invalid value",
                severity="error",
            )
            for error in exc.errors()
        ]
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                diagnostics=diagnostics,
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        messages = {404: "Route not found.", 405: "Method not allowed."}
        error = ErrorDetail(
            code=codes.get(exc.status_code, "HTTP_ERROR"),
            message=messages.get(exc.status_code, "Request failed."),
        )
        response = error_response(exc.status_code, error)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(Exception)
    async def internal_error(_request: Request, _exc: Exception) -> JSONResponse:
        return error_response(
            500,
            ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected server error occurred.",
            ),
        )
