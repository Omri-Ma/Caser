from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_tenant_scoped(model, obj_id: int, tenant_id: int, db: Session, not_found_detail: str = "Not found"):
    """Look up a row by id, but only if it belongs to the given tenant.

    Every route that accepts a foreign id from the request (e.g. a
    membership_id to assign to a case) MUST look it up through this instead
    of a plain `.filter(model.id == obj_id)` — a bare id lookup only proves
    the row exists *somewhere*, not that it belongs to the tenant making the
    request. This is the one place that check happens, so no route can
    accidentally skip it.
    """
    obj = db.query(model).filter(model.id == obj_id, model.tenant_id == tenant_id).first()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)
    return obj
