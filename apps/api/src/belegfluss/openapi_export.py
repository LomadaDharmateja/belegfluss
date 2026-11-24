"""Write the API's OpenAPI schema to a file (the contract the web app is generated from, ADR-0011).

Usage: python -m belegfluss.openapi_export <path/to/openapi.json>
"""

import json
import sys
from pathlib import Path

from belegfluss.main import create_app


def schema_json() -> str:
    return json.dumps(create_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m belegfluss.openapi_export <output-file>")
    # newline="\n": identical bytes on Windows and Linux (CI compares the file).
    Path(sys.argv[1]).write_text(schema_json(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
