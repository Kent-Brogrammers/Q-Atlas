"""Additive physical-device endpoints. No jobs are submitted on startup or page load."""

from uuid import UUID

from fastapi import APIRouter

from app.api.compiler_hardware import _call
from app.compiler import hardware as ibm
from app.quantum import hardware
from app.schemas.compiler_hardware import CompilerHardwareDevices
from app.schemas.hardware import HardwareJob, HardwareRequest

router = APIRouter(prefix="/hardware", tags=["physical quantum hardware"])


@router.get("/devices", response_model=CompilerHardwareDevices)
def devices():
    return _call(ibm.devices)


@router.get("/demo", response_model=HardwareRequest)
def demo():
    from app.quantum.hardware_demo import demo_request

    return demo_request()


@router.get("/jobs", response_model=list[HardwareJob])
def jobs(experiment: str | None = None):
    return _call(lambda: hardware.list_jobs(experiment))


@router.post("/submit", response_model=HardwareJob)
def submit(request: HardwareRequest):
    return _call(lambda: hardware.submit(request))


@router.get("/jobs/{request_id}", response_model=HardwareJob)
def status(request_id: UUID):
    return _call(lambda: hardware.refresh(request_id))


@router.post("/jobs/{request_id}/cancel", response_model=HardwareJob)
def cancel(request_id: UUID):
    return _call(lambda: hardware.refresh(request_id, cancel=True))
