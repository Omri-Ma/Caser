import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Make `import shared` / `import admin_api` / `import client_api` resolve
# regardless of where pytest is invoked from (repo root or server/).
SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
sys.path.insert(0, str(SERVER_ROOT))

load_dotenv(REPO_ROOT / ".env")

# Point DATABASE_URL at the dedicated test database *before* shared.database
# (imported below, transitively) builds its module-level engine off of it —
# tests must never run against the real dev database.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set — see .env.example")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from admin_api.main import app as admin_app  # noqa: E402
from client_api.main import app as client_app  # noqa: E402
from shared.database import Base, get_db  # noqa: E402
from shared.models import Case, CaseAssignment, Identity, Membership, Tenant  # noqa: E402, F401
from shared.models.enums import CaseStatus, UserRole  # noqa: E402, F401
from shared.security import ACCESS_COOKIE_NAME, create_access_token, hash_password  # noqa: E402
from shared.tenant import BASE_DOMAIN  # noqa: E402

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db():
    """A fresh schema per test — cheap enough at this table count, and it
    guarantees isolation regardless of commits made inside routes.
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_client(db):
    def _override_get_db():
        yield db

    admin_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(admin_app) as c:
        yield c
    admin_app.dependency_overrides.clear()


@pytest.fixture()
def client_client(db):
    def _override_get_db():
        yield db

    client_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(client_app) as c:
        yield c
    client_app.dependency_overrides.clear()


# --- Fixture-building helpers (bypass the API for fast, direct setup) ---


def make_tenant(db, subdomain: str, name: str = "Test Firm", active: bool = True) -> Tenant:
    tenant = Tenant(name=name, subdomain=subdomain, active=active)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def make_identity(db, email: str, name: str = "Test User") -> Identity:
    identity = Identity(name=name, email=email, password_hash=hash_password("password123"))
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


def make_membership(db, identity_id: int, tenant_id: int, role: UserRole) -> Membership:
    membership = Membership(identity_id=identity_id, tenant_id=tenant_id, role=role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def make_case(db, tenant_id: int, title: str = "Test Case", status: CaseStatus = CaseStatus.OPEN) -> Case:
    case = Case(tenant_id=tenant_id, title=title, status=status)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def make_assignment(db, tenant_id: int, case_id: int, membership_id: int) -> CaseAssignment:
    assignment = CaseAssignment(tenant_id=tenant_id, case_id=case_id, membership_id=membership_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def auth_for(identity: Identity, subdomain: str) -> tuple[dict, dict]:
    """Build the (headers, cookies) pair a request needs to look like it came
    from a logged-in identity on the given tenant subdomain. Passed directly
    per-request (not via the client's cookie jar) to sidestep cookie-domain
    matching entirely — the jar treats "Host" header spoofing and real cookie
    domains as separate concerns, and we only care about the former here.
    """
    token = create_access_token(identity.id, identity.token_version)
    headers = {"Host": f"{subdomain}.{BASE_DOMAIN}"}
    cookies = {ACCESS_COOKIE_NAME: token}
    return headers, cookies
