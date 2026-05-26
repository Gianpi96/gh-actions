import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import request_id_var, tenant_id_var, user_id_var

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Injects request_id / user_id / tenant_id into ContextVars for the duration
    of each request so every log line automatically carries those fields.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        user_id    = request.headers.get("X-User-ID", "")
        tenant_id  = request.headers.get("X-Tenant-ID", "")

        rid_tok = request_id_var.set(request_id)
        uid_tok = user_id_var.set(user_id)
        tid_tok = tenant_id_var.set(tenant_id)

        t0 = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        finally:
            request_id_var.reset(rid_tok)
            user_id_var.reset(uid_tok)
            tenant_id_var.reset(tid_tok)
