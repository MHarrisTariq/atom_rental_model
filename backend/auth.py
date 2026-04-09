from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from jose import JWTError, jwt
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency 'python-jose'. Install it with: python -m pip install python-jose[cryptography]"
    ) from e


_bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    return os.environ.get("SMART_PRICING_JWT_SECRET", "dev-secret-change-me")


def _algo() -> str:
    return os.environ.get("SMART_PRICING_JWT_ALG", "HS256")


def create_access_token(*, subject: str, role: str, minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_algo())


def get_current_role(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_algo()])
        role = str(payload.get("role") or "")
        if not role:
            raise HTTPException(status_code=401, detail="Invalid token")
        return role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(role: str = Depends(get_current_role)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return role

