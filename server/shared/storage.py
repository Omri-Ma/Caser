import os
import uuid
from pathlib import Path

# In server/shared on purpose, not duplicated per app (unlike pagination.py/
# errors.py): admin_api has to be able to read back the exact files
# client_api writes (the storage key format must match byte-for-byte for
# that to work at all), so this is a genuine cross-app invariant, not a
# per-app presentation choice. See CLAUDE.md's Multi-tenancy architecture /
# docs/ai_usage.md for the full reasoning.
STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "./server/storage")).resolve()


def save_file(file_bytes: bytes, tenant_id: int, case_id: int, original_filename: str) -> str:
    """Save bytes to local disk under a per-tenant/per-case folder with a
    generated unique name — never trusts the original filename for the path
    (avoids collisions and path traversal). Returns a storage key (relative
    path) to persist in Documents.file_url. Swapping to a different storage
    backend later (e.g. S3) only means changing what this module returns
    (an object key instead of a filesystem path) — callers never touch disk
    paths directly.
    """
    extension = Path(original_filename).suffix[:10]
    storage_key = f"{tenant_id}/{case_id}/{uuid.uuid4().hex}{extension}"
    full_path = STORAGE_ROOT / storage_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)
    return storage_key


def save_tenant_logo(file_bytes: bytes, tenant_id: int, original_filename: str) -> str:
    """Same idea as save_file, but for a tenant's public logo — not tied to
    a case, and only ever one live file per tenant (a re-upload just
    overwrites the previous storage key's slot by writing a new one; the
    caller is responsible for updating Tenants.logo_url to point at it).
    """
    extension = Path(original_filename).suffix[:10]
    storage_key = f"logos/{tenant_id}/{uuid.uuid4().hex}{extension}"
    full_path = STORAGE_ROOT / storage_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_bytes)
    return storage_key


def get_file_url(storage_key: str) -> str:
    """Resolve a storage key back to something the caller can actually read
    from. For local disk this is the absolute path (used to stream the file
    via FastAPI's FileResponse); a cloud backend would return a signed URL
    here instead — this is the one function a storage-backend swap touches.
    """
    return str(STORAGE_ROOT / storage_key)


def delete_file(storage_key: str) -> None:
    """Permanently remove the underlying file — only ever called from the
    permanent-delete flow (archive/restore just toggle Documents.archived_at,
    the file itself stays untouched).
    """
    path = STORAGE_ROOT / storage_key
    if path.exists():
        path.unlink()
