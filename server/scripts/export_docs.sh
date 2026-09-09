#!/usr/bin/env bash
# Regenerate every /docs deliverable that's derived from code: both OpenAPI
# schemas, both Postman collections, and the ERD (image + Mermaid text).
#
# Run this once after any change to routes (client_api/admin_api) or to the
# table/relationship definitions in server/shared/models — nothing here is
# hand-maintained, everything is regenerated from source.
#
# Requirements (one-time setup):
#   - Python venv with server/requirements.txt AND
#     server/scripts/requirements-docs.txt installed
#   - Node/npm on PATH (used via npx for the Postman conversion)
#
# Usage (from repo root, bash):
#   bash server/scripts/export_docs.sh
# On Windows, run each step directly instead if you don't have bash:
#   <venv>/Scripts/python.exe server/scripts/export_openapi.py
#   <venv>/Scripts/python.exe server/scripts/generate_erd.py
#   bash server/scripts/generate_postman.sh   (or run the two npx commands inside it)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python"
fi

echo "== 1/3: OpenAPI export =="
"$PYTHON" "$SCRIPT_DIR/export_openapi.py"

echo "== 2/3: ERD generation =="
"$PYTHON" "$SCRIPT_DIR/generate_erd.py"

echo "== 3/3: Postman collections (from the OpenAPI files just written) =="
bash "$SCRIPT_DIR/generate_postman.sh"

echo "Done. Review changes under docs/ before committing."
