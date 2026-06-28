from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from commons.config import get_configs
from commons.rate_limit import limiter
from loggers.helper import get_logger
from middlewares.request_id_middleware import RequestIDMiddleware
from middlewares.request_logging_middleware import RequestLoggingMiddleware

logger = get_logger(__name__)


def register_middlewares(app: FastAPI) -> None:
    """Register all middlewares on the FastAPI application.

    Execution order (outermost → innermost):
        RequestID → RequestLogging → SlowAPI → CORS → Handler

    Starlette wraps in LIFO order, so middlewares are added in reverse execution order.
    RequestLoggingMiddleware is skipped entirely when LOG_REQUESTS is false.
    """
    cfg = get_configs()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ALLOW_ORIGINS,
        allow_credentials=cfg.CORS_ALLOW_CREDENTIALS,
        allow_methods=cfg.CORS_ALLOW_METHODS,
        allow_headers=cfg.CORS_ALLOW_HEADERS,
    )

    # LIMITER
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # LOG REQUESTS
    if cfg.LOG_REQUESTS:
        skip_paths = tuple(cfg.LOG_SKIP_PATHS)
        app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=cfg.LOG_REQUEST_BODY,
            log_response_body=cfg.LOG_RESPONSE_BODY,
            max_body_bytes=cfg.LOG_MAX_BODY_BYTES,
            max_list_items=cfg.LOG_MAX_LIST_ITEMS,
            max_string_length=cfg.LOG_MAX_STRING_LENGTH,
            skip_paths=skip_paths,
        )

        skip_summary = ",".join(skip_paths) if skip_paths else "none"
        logger.info(
            "request logging: ENABLED "
            "(req_body=%s, resp_body=%s, max_body_bytes=%d, skip_paths=%s)",
            cfg.LOG_REQUEST_BODY,
            cfg.LOG_RESPONSE_BODY,
            cfg.LOG_MAX_BODY_BYTES,
            skip_summary,
        )
    else:
        logger.info(
            "request logging: DISABLED — set LOG_REQUESTS=true in .env to enable"
        )

    # REQUEST ID
    app.add_middleware(RequestIDMiddleware)
