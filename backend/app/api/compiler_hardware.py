"""Explicit compiler QPU operations; importing or browsing the compiler submits nothing."""

import logging
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.compiler import hardware
from app.compiler.pipeline import CompilationError
from app.schemas.compiler_hardware import (
    CompilerHardwareDevices,
    CompilerHardwareJob,
    CompilerHardwareRequest,
)
from app.schemas.contracts import Diagnostic, ErrorDetail

router = APIRouter(prefix="/hardware", tags=["compiler hardware"])
logger = logging.getLogger(__name__)


def _call(operation):
    try:
        return operation()
    except CompilationError as error:
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Unsupported objective.",
                diagnostics=error.diagnostics,
            ),
        )
    except hardware.HardwareRequestError as error:
        logger.warning("Compiler hardware request rejected: %s", error.code)
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message=str(error),
                diagnostics=[Diagnostic(code=error.code, message=str(error), severity="error")],
            ),
        )
    except hardware.HardwareOperationError as error:
        logger.warning("Compiler hardware operation failed: %s", error.code)
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message=str(error),
                diagnostics=[Diagnostic(code=error.code, message=str(error), severity="error")],
            ),
        )
    except ValueError:
        logger.warning("Compiler hardware request rejected: HARDWARE_VALIDATION_FAILED")
        return error_response(
            422,
            ErrorDetail(
                code="VALIDATION_ERROR",
                message="Check credentials/instance, experiment resource limits, "
                "and remaining shared reservation cap.",
            ),
        )
    except Exception:
        return error_response(
            503,
            ErrorDetail(
                code="HTTP_ERROR",
                message="IBM operation failed. Recover your recorded request/job ID "
                "before considering another submission.",
            ),
        )


@router.get("/devices", response_model=CompilerHardwareDevices)
def devices() -> CompilerHardwareDevices | JSONResponse:
    return _call(hardware.devices)


@router.post("/submit", response_model=CompilerHardwareJob)
def submit(request: CompilerHardwareRequest) -> CompilerHardwareJob | JSONResponse:
    return _call(lambda: hardware.submit(request))


@router.get("/jobs/{request_id}", response_model=CompilerHardwareJob)
def status(request_id: UUID) -> CompilerHardwareJob | JSONResponse:
    return _call(lambda: hardware.refresh(request_id))


@router.post("/jobs/{request_id}/cancel", response_model=CompilerHardwareJob)
def cancel(request_id: UUID) -> CompilerHardwareJob | JSONResponse:
    return _call(lambda: hardware.refresh(request_id, cancel=True))
