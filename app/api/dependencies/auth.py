from __future__ import annotations

import json
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import ForbiddenException, RateLimitException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.session import get_db
from app.repositories.user import UserRepository

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db=Depends(get_db),
):
    if credentials is None:
        raise UnauthorizedException("Authentication credentials were not provided.")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise UnauthorizedException(str(exc)) from exc

    if payload.get("token_type") != "access":
        raise UnauthorizedException("An access token is required.")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedException("Token payload is invalid.")

    request.state.auth_payload = payload
    user = await UserRepository(db).get_by_id(UUID(subject))
    if user is None or not user.is_active or user.deactivated_at is not None:
        raise UnauthorizedException("Current user is no longer active.")
    return user


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "customer": {
        "security.manage",
        "sessions.manage",
        "dashboard.read",
        "beneficiary.manage",
        "statement.export",
        "kyc.submit",
        "support.write",
        "recurring_transfer.manage",
    },
    "support": {"support.review", "kyc.read", "fraud.read", "users.read"},
    "admin": {"*"},
    "compliance": {"fraud.read", "fraud.review", "audit.read", "kyc.read", "kyc.review"},
    "auditor": {"fraud.read", "audit.read", "kyc.read"},
}


def require_roles(*roles: str):
    async def dependency(current_user=Depends(get_current_user)):
        user_roles = {role.name for role in current_user.roles}
        if not user_roles.intersection(set(roles)):
            raise ForbiddenException("You do not have permission to access this resource.")
        return current_user

    return dependency


def require_permissions(*permissions: str):
    async def dependency(current_user=Depends(get_current_user)):
        user_roles = {role.name for role in current_user.roles}
        granted: set[str] = set()
        for role in user_roles:
            granted.update(ROLE_PERMISSIONS.get(role, set()))
        if "*" in granted:
            return current_user
        if not set(permissions).issubset(granted):
            raise ForbiddenException("You do not have permission to access this resource.")
        return current_user

    return dependency


async def _request_json(request: Request) -> dict:
    try:
        raw = await request.body()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def rate_limit(
    namespace: str,
    *,
    limit: int | None = None,
    window_seconds: int | None = None,
    key_strategy: str = "ip",
):
    async def dependency(request: Request, redis=Depends(get_redis)):
        client_ip = request.client.host if request.client else "unknown"
        allowed_requests = limit or settings.auth_rate_limit_requests
        ttl = window_seconds or settings.auth_rate_limit_window_seconds
        body = await _request_json(request)
        extra = "na"

        if key_strategy == "ip_email":
            extra = str(body.get("email", "")).lower() or "anonymous"
        elif key_strategy == "user":
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
            if token:
                try:
                    extra = str(decode_token(token).get("sub") or "anonymous")
                except ValueError:
                    extra = "anonymous"
        elif key_strategy == "user_purpose":
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
            try:
                extra = str(decode_token(token).get("sub") or "anonymous")
            except ValueError:
                extra = "anonymous"
            extra = f"{extra}:{body.get('purpose', 'none')}"

        key = f"ratelimit:{namespace}:{client_ip}:{extra}:{request.url.path}"
        current_requests = await redis.incr(key)
        if current_requests == 1:
            await redis.expire(key, ttl)
        if current_requests > allowed_requests:
            raise RateLimitException("Too many attempts. Please wait and try again.")

    return dependency
