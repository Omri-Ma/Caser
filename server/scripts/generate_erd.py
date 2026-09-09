"""Generate an ERD image from the SQLAlchemy models in server/shared/models.

Imports shared.models (which populates shared.database.Base.metadata with
every table + ForeignKey-derived relationship) and hands that metadata
straight to eralchemy2 — no live DB connection needed, and no separate
Graphviz install either: eralchemy2 pulls in pygraphviz, which for this
project's platform/version ships graphviz's `dot` engine bundled in its wheel.

Usage (from repo root or anywhere):
    server/.venv/Scripts/python.exe server/scripts/generate_erd.py
    (or, if the venv is already active: python server/scripts/generate_erd.py)

Requires: pip install eralchemy2 (already in server/requirements.txt).
Re-run this any time a table or relationship changes in shared/models/.
"""

import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
DOCS_DIR = REPO_ROOT / "docs"

sys.path.insert(0, str(SERVER_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from eralchemy2 import render_er  # noqa: E402

from shared.database import Base  # noqa: E402
import shared.models  # noqa: E402, F401  (populates Base.metadata as a side effect)


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    png_path = DOCS_DIR / "erd.png"
    mermaid_path = DOCS_DIR / "erd.mmd.md"

    render_er(Base.metadata, str(png_path), title="CaseHub ERD")
    print(f"Wrote {png_path.relative_to(REPO_ROOT)}")

    # Also emit a text-based Mermaid ER diagram alongside the PNG — easy to
    # diff in PRs and to view directly on GitHub, unlike a binary image.
    render_er(Base.metadata, str(mermaid_path), mode="mermaid_er", title="CaseHub ERD")
    print(f"Wrote {mermaid_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
