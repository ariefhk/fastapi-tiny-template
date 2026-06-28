"""Per-request correlation ID — middleware + contextvar + log filter.

Goal: every log line emitted while serving an HTTP request carries the
same ``request_id`` so an operator can grep the entire request chain out
of structured log storage with one query.

Three pieces:

  * ``request_id_var`` — a ``ContextVar`` that holds the active request's
    id. Set per-request in the middleware; readable from anywhere
    (including code on the same asyncio Task that started the request).

  * ``RequestIDMiddleware`` — Starlette middleware. On the way in, picks
    up the inbound ``X-Request-Id`` header if the client sent one, else
    generates a UUID4. Writes it back as ``X-Request-Id`` on the way out
    so the client / upstream proxy can correlate too.

  * ``RequestIDLogFilter`` — a ``logging.Filter`` that copies the current
    contextvar onto every ``LogRecord``. Wired into the JSON formatter in
    ``loggers/logging.py`` so it ends up as a top-level field in each log
    line. Outside a request (boot, scheduler, scripts) the field is "-".

Why a contextvar (not ``request.state``):
  * Async code emits logs from places that don't have the ``Request``
    object on hand — services, repositories, jobs called via gather().
  * ``ContextVar`` is the standard cross-coroutine carrier; it's what
    asyncio uses for its own per-task state.
"""

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from logging import Filter, LogRecord

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-Id"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Stamp every request with a correlation ID, propagate it both ways."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Resolve or generate the request ID, set the contextvar, echo it in the response.

        The contextvar is always reset in a ``finally`` block to prevent
        task-pool workers from leaking one request's ID into the next log line.
        """
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if incoming else uuid.uuid4().hex

        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RequestIDLogFilter(Filter):
    """Copy the active request id onto every LogRecord as ``record.request_id``."""

    def filter(self, record: LogRecord) -> bool:
        """Attach the current request ID to the log record. Returns True to always emit."""
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        return True
