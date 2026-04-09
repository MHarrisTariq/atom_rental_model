from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable

from fastapi import Request, Response


def configure_logging() -> None:
    level = os.environ.get("SMART_PRICING_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_context_middleware(request: Request, call_next: Callable):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response: Response = await call_next(request)
    dur_ms = (time.perf_counter() - start) * 1000.0
    response.headers["x-request-id"] = rid
    response.headers["x-response-time-ms"] = f"{dur_ms:.2f}"
    return response


def setup_prometheus(app) -> None:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
    except Exception:
        return
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

