"""Explicit, idempotent five-experiment physical demo. Never print credentials."""

import argparse
from pathlib import Path

from app.compiler import hardware as ibm
from app.configuration import load_quantum_env
from app.quantum import hardware
from app.quantum.hardware_demo import demo_request
from app.schemas.hardware import HardwareRequest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--submit", action="store_true", help="Submit one capped physical job; reuse saved ID"
    )
    mode.add_argument(
        "--refresh", action="store_true", help="Retrieve the saved job only; never resubmit"
    )
    parser.add_argument(
        "--request-record",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".cache/physical-demo-request.json",
    )
    parser.add_argument("--output", type=Path, help="Save the sanitized result/evidence JSON")
    args = parser.parse_args()
    load_quantum_env()
    args.request_record.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        if args.request_record.exists():
            request = HardwareRequest.model_validate_json(args.request_record.read_text())
        elif args.submit:
            request = demo_request()
            with args.request_record.open("x") as file:
                file.write(request.model_dump_json(indent=2))
            args.request_record.chmod(0o600)
        else:
            raise ValueError("No saved demonstration request. Submit explicitly first.")
        record = hardware.submit(request) if args.submit else hardware.refresh(request.request_id)
        output = record.model_dump_json(indent=2)
        if args.output:
            args.output.write_text(output + "\n")
        print(
            record.model_dump_json(
                include={
                    "request_id",
                    "status",
                    "job_id",
                    "backend_name",
                    "measurement_complete",
                    "message",
                    "timings",
                }
            )
        )
        return 0
    except (ibm.HardwareRequestError, ibm.HardwareOperationError) as error:
        print(f"Hardware demo: {error.code}. {error}")
        return 1
    except Exception:
        print(
            "Hardware demo could not finish. Preserve the request record and recover its status "
            "before any new submission."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
