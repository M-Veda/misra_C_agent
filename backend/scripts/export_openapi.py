"""Export OpenAPI schema from the FastAPI application."""

import json
from pathlib import Path

from misra_platform.main import app

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "shared" / "contracts" / "openapi.generated.json"


def export_openapi() -> None:
    schema = app.openapi()
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {OUTPUT_PATH}")


if __name__ == "__main__":
    export_openapi()
