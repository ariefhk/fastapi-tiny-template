"""HTTP request/response logging middleware with redaction.

For every request, logs a single multi-line entry containing:

  request:
    method, path, query, headers (auth fields redacted), body (sensitive
    fields redacted, parsed as JSON when possible)
  response:
    status_code, headers, body, elapsed_ms

Body parsing only happens for ``application/json`` content. Non-JSON bodies
(file uploads, binary downloads, streaming responses) are summarised by size
so we never log raw bytes.

Redaction constants (``REDACT_HEADERS``, ``REDACT_BODY_FIELDS``) live in
``middlewares.helper`` and can be extended by importers
(e.g. ``from middlewares.helper import REDACT_BODY_FIELDS; REDACT_BODY_FIELDS.add("ssn")``).

Bodies larger than ``max_body_bytes`` are not logged in full — just a size
marker. The default cap is intentionally low so the log volume stays bounded
even when someone POSTs a large payload by mistake.
"""

import json
import time
from typing import Any, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from loggers.helper import get_logger
from middlewares.helper import (
    decode_json_body,
    is_json,
    redact_headers,
    redact_value,
    truncate_for_display,
)

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request/response as a single pretty-printed JSON entry.

    Skips path prefixes in ``skip_paths`` (default: docs/openapi/health) so
    the log isn't drowned by Swagger or liveness probes.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_request_body: bool = True,
        log_response_body: bool = True,
        max_body_bytes: int = 10_000,
        max_list_items: int = 5,
        max_string_length: int = 200,
        skip_paths: tuple[str, ...] = (
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ),
    ) -> None:
        """Configure logging knobs and path skip-list.

        ``max_list_items`` and ``max_string_length`` are display caps applied
        after redaction. Pass 0 to disable the respective cap.
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_bytes = max_body_bytes
        self.max_list_items = max_list_items
        self.max_string_length = max_string_length
        self.skip_paths = skip_paths

    async def dispatch(self, request: Request, call_next):
        """Capture, redact, truncate, and log the request/response pair."""
        for prefix in self.skip_paths:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        start = time.perf_counter()
        request_body_logged = await self._capture_request_body(request)

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response, response_body_logged = await self._capture_response_body(response)

        def shape(value: Any) -> Any:
            return truncate_for_display(
                redact_value(value),
                max_list_items=self.max_list_items,
                max_string_length=self.max_string_length,
            )

        record: dict[str, Any] = {
            "request": {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "headers": redact_headers(dict(request.headers)),
                "body": shape(request_body_logged),
            },
            "response": {
                "status_code": response.status_code,
                "headers": redact_headers(dict(response.headers)),
                "body": shape(response_body_logged),
                "elapsed_ms": round(elapsed_ms, 2),
            },
        }

        logger.info(
            "%s %s -> %d (%.2fms)\n%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
        )

        return response

    async def _capture_request_body(self, request: Request) -> Any:
        """Read and cache the request body so the route handler can re-read it.

        Re-injects the body into the ASGI receive channel because
        ``BaseHTTPMiddleware`` does not do this automatically.
        """
        if not self.log_request_body:
            return None
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None

        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive

        if not body:
            return None
        if len(body) > self.max_body_bytes:
            return f"[request body too large: {len(body)} bytes]"
        if not is_json(request.headers.get("content-type")):
            return f"[non-json request body: {len(body)} bytes]"
        return decode_json_body(body)

    async def _capture_response_body(self, response: Response) -> tuple[Response, Any]:
        """Drain the response body so we can log it, then return a fresh Response.

        ``BaseHTTPMiddleware`` always hands us a ``StreamingResponse``-shaped
        object. We exhaust it, log it, and rebuild a plain ``Response`` so
        downstream callers still get the bytes. SSE and octet-stream responses
        are never buffered to avoid breaking live streams.
        """
        if not self.log_response_body:
            return response, None

        content_type = response.headers.get("content-type", "")
        if (
            "text/event-stream" in content_type
            or "application/octet-stream" in content_type
        ):
            return response, "[streaming response — body not captured]"

        streaming = cast(StreamingResponse, response)
        body_chunks: list[bytes] = []
        async for chunk in streaming.body_iterator:
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(bytes(chunk))
        body_bytes = b"".join(body_chunks)

        new_response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        if not body_bytes:
            return new_response, None
        if len(body_bytes) > self.max_body_bytes:
            return new_response, f"[response body too large: {len(body_bytes)} bytes]"
        if not is_json(response.headers.get("content-type")):
            return new_response, f"[non-json response body: {len(body_bytes)} bytes]"

        return new_response, decode_json_body(body_bytes)
