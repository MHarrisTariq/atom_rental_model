from __future__ import annotations

from fastapi import Request

try:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency 'slowapi'. Install it with: python -m pip install slowapi"
    ) from e


limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return limiter._rate_limit_exceeded_handler(request, exc)

