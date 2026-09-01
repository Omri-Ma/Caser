import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Cookies are scoped to the whole family of subdomains (".lvh.me") rather than
# one origin, so the same login session works on every tenant subdomain and
# on the tenant-less dashboard — this is why sessions are cookies, not a
# bearer token in localStorage (localStorage is locked to one origin).
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "lvh.me")
COOKIE_DOMAIN = f".{BASE_DOMAIN}"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
ACCESS_COOKIE_NAME = "casehub_access"
REFRESH_COOKIE_NAME = "casehub_refresh"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(payload: dict, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(identity_id: int, token_version: int) -> str:
    return _create_token(
        {"identity_id": identity_id, "token_version": token_version, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(identity_id: int, token_version: int) -> str:
    return _create_token(
        {"identity_id": identity_id, "token_version": token_version, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def set_session_cookies(response: Response, identity_id: int, token_version: int) -> None:
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        create_access_token(identity_id, token_version),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain=COOKIE_DOMAIN,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        create_refresh_token(identity_id, token_version),
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
        domain=COOKIE_DOMAIN,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=COOKIE_DOMAIN)
