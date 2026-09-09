#!/usr/bin/env bash
# Convert the OpenAPI exports (docs/openapi_client.json, docs/openapi_admin.json)
# into Postman Collections, using Postman's own official converter
# (openapi-to-postmanv2 on npm — high download count, maintained by Postman).
#
# Run export_openapi.py first so the OpenAPI files it reads are current.
#
# Usage (from repo root or anywhere, needs Node/npm on PATH):
#   bash server/scripts/generate_postman.sh
#
# npx downloads/caches the converter on first run; a pinned version keeps
# output stable across re-runs and across future sessions.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"
CONVERTER_VERSION="6.3.3"

npx --yes "openapi-to-postmanv2@${CONVERTER_VERSION}" \
    -s "$DOCS_DIR/openapi_client.json" \
    -o "$DOCS_DIR/postman_collection_client.json" \
    -p

npx --yes "openapi-to-postmanv2@${CONVERTER_VERSION}" \
    -s "$DOCS_DIR/openapi_admin.json" \
    -o "$DOCS_DIR/postman_collection_admin.json" \
    -p

echo "Wrote docs/postman_collection_client.json and docs/postman_collection_admin.json"
