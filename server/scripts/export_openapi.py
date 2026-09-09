"""Export OpenAPI schemas for both backend apps, without needing them running.

Imports the FastAPI `app` object directly from each of client_api and admin_api
and calls .openapi() on it — this only builds the schema dict from route
declarations, it never opens a socket or a real DB connection, so it works
the same whether Docker is up or not.

Usage (from repo root or anywhere):
    server/.venv/Scripts/python.exe server/scripts/export_openapi.py
    (or, if the venv is already active: python server/scripts/export_openapi.py)

Re-run this any time routes change, before regenerating the Postman
collection (generate_postman.py) or committing to docs/.
"""

import json
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
DOCS_DIR = REPO_ROOT / "docs"

sys.path.insert(0, str(SERVER_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from admin_api.main import app as admin_app  # noqa: E402
from client_api.main import app as client_app  # noqa: E402

EXPORTS = [
    (client_app, DOCS_DIR / "openapi_client.json"),
    (admin_app, DOCS_DIR / "openapi_admin.json"),
]


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    for app, out_path in EXPORTS:
        schema = app.openapi()
        out_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(REPO_ROOT)} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
