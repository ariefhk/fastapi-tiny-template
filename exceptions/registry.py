import logging
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from commons.response import APIResponse


def register_exceptions(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application.

    Handles:
    - HTTPException: returns the detail message with HTTP_<status_code> code
    - RequestValidationError: returns per-field validation details with VALIDATION_ERROR code
    - RateLimitExceeded: returns 429 with RATE_LIMIT_EXCEEDED code
    - Exception: logs the traceback and returns 500 with INTERNAL_SERVER_ERROR code
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Return a structured error response for HTTPException, using the detail as the message."""
        if isinstance(exc.detail, str):
            message = exc.detail
        else:
            message = "An error occurred"
        code = "HTTP_" + str(exc.status_code)
        return APIResponse.error(
            request,
            message=message,
            code=code,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Return a 422 response with per-field validation error details, stripping location prefixes."""
        details: List[dict] = []
        for error in exc.errors():
            error_type = error.get("type", "")

            if error_type == "json_invalid":
                details.append({"field": None, "message": "Invalid JSON body"})
                continue

            loc = error.get("loc", ())
            field_parts = [
                str(part)
                for part in loc
                if part not in ("body", "query", "path", "header", "cookie")
                and not isinstance(part, int)
            ]
            field = ".".join(field_parts) if field_parts else None

            details.append({"field": field, "message": error["msg"]})

        return APIResponse.error(
            request,
            message="Validation error",
            code="VALIDATION_ERROR",
            details=details,
            status_code=422,
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        """Return a 429 response when the client exceeds the configured rate limit."""
        return APIResponse.error(
            request,
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Log unhandled exceptions and return a generic 500 response."""
        logging.getLogger("api").exception("Unhandled error: %s", exc)

        return APIResponse.error(
            request,
            message="Internal server error",
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )
