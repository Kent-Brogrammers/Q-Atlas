"""Export the runtime API contract without starting a server or loading quantum packages."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

print(json.dumps(app.openapi(), indent=2))
