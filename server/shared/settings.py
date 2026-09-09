from typing import Optional

from sqlalchemy.orm import Session

from shared.models import Setting

# Key convention for the firm's public "about" blurb (CLAUDE.md's public
# homepage requirement) — read by client_api's public profile route, written
# by admin_api's branding route. Shared here (not duplicated per app) so the
# key name and lookup logic can't drift between the two backends.
ABOUT_KEY = "about"


def get_setting(db: Session, tenant_id: int, key: str) -> Optional[str]:
    setting = db.query(Setting).filter(Setting.tenant_id == tenant_id, Setting.key == key).first()
    return setting.value if setting else None


def set_setting(db: Session, tenant_id: int, key: str, value: Optional[str]) -> None:
    setting = db.query(Setting).filter(Setting.tenant_id == tenant_id, Setting.key == key).first()
    if setting is None:
        db.add(Setting(tenant_id=tenant_id, key=key, value=value))
    else:
        setting.value = value
